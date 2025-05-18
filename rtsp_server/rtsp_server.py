#!/usr/bin/env python3
import logging
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib
import threading
import time

logger = logging.getLogger(__name__)

class RtspMediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, url, disable_audio=True):
        super().__init__()
        self.url = url
        self.disable_audio = disable_audio
    
    def do_create_element(self, url):
        pipeline_str = f"rtspsrc location={self.url} latency=0 buffer-mode=auto ! "
        
        if self.disable_audio:
            pipeline_str += "application/x-rtp,media=video ! "
        
        pipeline_str += (
            "rtph264depay ! "
            "h264parse ! "
            "queue max-size-buffers=2 ! "
            "rtph264pay name=pay0 pt=96 config-interval=1 "
        )
        
        logger.info(f"Creating pipeline: {pipeline_str}")
        return Gst.parse_launch(pipeline_str)

class RtspServer:
    def __init__(self, config, api_client):
        self.config = config
        self.api_client = api_client
        self.server = GstRtspServer.RTSPServer()
        self.mounts = self.server.get_mount_points()
        self.factories = {}  # Store factories for each stream
        
        self.server.set_service(self.config.get_server_rtsp_port().lstrip(':'))
        
        self._setup_streams()
        
        self.update_thread = threading.Thread(target=self._update_streams_periodically, daemon=True)
        self.update_thread.start()
    
    def _setup_streams(self):
        streams = self.api_client.get_streams()
        
        for stream_name, stream_info in streams.items():
            self._add_stream(stream_name, stream_info)
    
    def _add_stream(self, stream_name, stream_info):
        factory = RtspMediaFactory(stream_info['url'], self.config.get_disable_audio())
        
        factory.set_shared(True)  # Allow multiple clients to share one stream
        factory.set_eos_shutdown(True)  # Shutdown media when EOS is received
        
        if self.config.get_on_demand():
            factory.set_suspend_mode(GstRtspServer.RTSPSuspendMode.IDLE)
            factory.set_transport_mode(GstRtspServer.RTSPTransportMode.PLAY)
        
        mount_point = f"/{stream_name}"
        self.mounts.add_factory(mount_point, factory)
        
        self.factories[stream_name] = factory
        
        logger.info(f"Added stream: {mount_point} -> {stream_info['url']}")
    
    def _remove_stream(self, stream_name):
        mount_point = f"/{stream_name}"
        self.mounts.remove_factory(mount_point)
        
        if stream_name in self.factories:
            del self.factories[stream_name]
        
        logger.info(f"Removed stream: {mount_point}")
    
    def _update_streams_periodically(self):
        while True:
            current_streams = self.api_client.get_streams()
            
            mounted_streams = set(self.factories.keys())
            
            new_streams = set(current_streams.keys()) - mounted_streams
            removed_streams = mounted_streams - set(current_streams.keys())
            
            for stream_name in removed_streams:
                self._remove_stream(stream_name)
            
            for stream_name in new_streams:
                self._add_stream(stream_name, current_streams[stream_name])
            
            time.sleep(10)  # Check for new streams every 10 seconds
    
    def start(self):
        self.server.attach(None)
        logger.info(f"RTSP server started on port {self.config.get_server_rtsp_port()}")
