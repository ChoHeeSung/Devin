#!/usr/bin/env python3
import logging
import platform
import sys

logger = logging.getLogger(__name__)

IS_MACOS = platform.system() == 'Darwin'

try:
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstRtspServer', '1.0')
    from gi.repository import Gst, GstRtspServer, GLib
except ImportError as e:
    logger.error(f"Failed to import GStreamer: {e}")
    if IS_MACOS:
        logger.error("On macOS, make sure GStreamer framework is installed at /Library/Frameworks/GStreamer.framework/")
        logger.error("Download from: https://gstreamer.freedesktop.org/download/#macos")
    else:
        logger.error("On Linux, install required packages with: sudo apt-get install python3-gi gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-rtsp libgstrtspserver-1.0-dev")
    sys.exit(1)
except ValueError as e:
    logger.error(f"Failed to initialize GStreamer: {e}")
    sys.exit(1)

import threading
import time

class RtspMediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, url, disable_audio=True):
        super().__init__()
        self.url = url
        self.disable_audio = disable_audio
        self.timeout = 5
    
    def do_create_element(self, url):
        pipeline_str = (
            f"rtspsrc location={self.url} latency=0 buffer-mode=auto "
            f"protocols=tcp timeout={self.timeout} retry=3 ! "
        )
        
        if self.disable_audio:
            pipeline_str += "application/x-rtp,media=video ! "
        
        if IS_MACOS:
            pipeline_str += (
                "rtph264depay ! "
                "h264parse ! "
                "queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 ! "
                "rtph264pay name=pay0 pt=96 config-interval=1 "
            )
        else:
            pipeline_str += (
                "rtph264depay ! "
                "h264parse ! "
                "queue max-size-buffers=2 ! "
                "rtph264pay name=pay0 pt=96 config-interval=1 "
            )
        
        logger.info(f"Creating pipeline: {pipeline_str}")
        try:
            return Gst.parse_launch(pipeline_str)
        except Exception as e:
            logger.error(f"Failed to create GStreamer pipeline: {e}")
            logger.error(f"Pipeline string: {pipeline_str}")
            
            logger.info("Using test source as fallback")
            fallback_pipeline = (
                "videotestsrc is-live=true ! "
                "video/x-raw,width=640,height=480,framerate=30/1 ! "
                "x264enc tune=zerolatency ! "
                "rtph264pay name=pay0 pt=96 config-interval=1"
            )
            return Gst.parse_launch(fallback_pipeline)

class RtspServer:
    def __init__(self, config, api_client):
        self.config = config
        self.api_client = api_client
        
        try:
            self.server = GstRtspServer.RTSPServer()
            self.mounts = self.server.get_mount_points()
            self.factories = {}  # Store factories for each stream
            
            self.server.set_service(self.config.get_server_rtsp_port().lstrip(':'))
            
            self._setup_streams()
            
            self.update_thread = threading.Thread(target=self._update_streams_periodically, daemon=True)
            self.update_thread.start()
        except Exception as e:
            logger.error(f"Failed to initialize RTSP server: {e}")
            if IS_MACOS:
                logger.error("On macOS, this could be due to GStreamer framework issues.")
                logger.error("Make sure GStreamer is properly installed and environment variables are set.")
            raise
    
    def _setup_streams(self):
        streams = self.api_client.get_streams()
        
        for stream_name, stream_info in streams.items():
            self._add_stream(stream_name, stream_info)
    
    def _add_stream(self, stream_name, stream_info):
        try:
            factory = RtspMediaFactory(stream_info['url'], self.config.get_disable_audio())
            
            factory.set_shared(True)  # Allow multiple clients to share one stream
            factory.set_eos_shutdown(True)  # Shutdown media when EOS is received
            
            factory.set_protocols(GstRtspServer.RTSPLowerTrans.TCP)
            
            if self.config.get_on_demand():
                try:
                    if hasattr(GstRtspServer.RTSPSuspendMode, 'IDLE'):
                        factory.set_suspend_mode(GstRtspServer.RTSPSuspendMode.IDLE)
                    elif hasattr(GstRtspServer.RTSPSuspendMode, 'RESET'):
                        factory.set_suspend_mode(GstRtspServer.RTSPSuspendMode.RESET)
                    else:
                        logger.warning(f"RTSPSuspendMode.IDLE and RTSPSuspendMode.RESET not available in this GStreamer version")
                except Exception as e:
                    logger.warning(f"Failed to set suspend mode: {e}")
                
                try:
                    if hasattr(GstRtspServer.RTSPTransportMode, 'PLAY'):
                        factory.set_transport_mode(GstRtspServer.RTSPTransportMode.PLAY)
                except Exception as e:
                    logger.warning(f"Failed to set transport mode: {e}")
            
            mount_point = f"/{stream_name}"
            self.mounts.add_factory(mount_point, factory)
            
            self.factories[stream_name] = factory
            
            logger.info(f"Added stream: {mount_point} -> {stream_info['url']}")
        except Exception as e:
            logger.error(f"Failed to add stream {stream_name}: {e}")
    
    def _remove_stream(self, stream_name):
        try:
            mount_point = f"/{stream_name}"
            self.mounts.remove_factory(mount_point)
            
            if stream_name in self.factories:
                del self.factories[stream_name]
            
            logger.info(f"Removed stream: {mount_point}")
        except Exception as e:
            logger.error(f"Failed to remove stream {stream_name}: {e}")
    
    def _update_streams_periodically(self):
        while True:
            try:
                current_streams = self.api_client.get_streams()
                
                mounted_streams = set(self.factories.keys())
                
                new_streams = set(current_streams.keys()) - mounted_streams
                removed_streams = mounted_streams - set(current_streams.keys())
                
                for stream_name in removed_streams:
                    self._remove_stream(stream_name)
                
                for stream_name in new_streams:
                    self._add_stream(stream_name, current_streams[stream_name])
            except Exception as e:
                logger.error(f"Error updating streams: {e}")
            
            time.sleep(10)  # Check for new streams every 10 seconds
    
    def start(self):
        try:
            self.server.attach(None)
            logger.info(f"RTSP server started on port {self.config.get_server_rtsp_port()}")
        except Exception as e:
            logger.error(f"Failed to start RTSP server: {e}")
            if IS_MACOS:
                logger.error("On macOS, this could be due to GStreamer framework issues.")
                logger.error("Make sure GStreamer is properly installed and environment variables are set.")
            raise
