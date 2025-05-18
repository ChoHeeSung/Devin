#!/usr/bin/env python3
import os
import sys
import signal
import json
import logging
import platform
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

IS_MACOS = platform.system() == 'Darwin'
if IS_MACOS:
    logger.info("Running on macOS, setting up GStreamer environment")
    os.environ['PATH'] = f"/Library/Frameworks/GStreamer.framework/Versions/1.0/bin:{os.environ.get('PATH', '')}"
    os.environ['PKG_CONFIG_PATH'] = "/Library/Frameworks/GStreamer.framework/Versions/1.0/lib/pkgconfig"
    os.environ['DYLD_LIBRARY_PATH'] = "/Library/Frameworks/GStreamer.framework/Versions/1.0/lib"
    os.environ['GST_PLUGIN_PATH'] = "/Library/Frameworks/GStreamer.framework/Versions/1.0/lib/gstreamer-1.0"
    os.environ['PYTHONPATH'] = f"/Library/Frameworks/GStreamer.framework/Versions/1.0/lib/python3/site-packages:{os.environ.get('PYTHONPATH', '')}"
    
    try:
        result = subprocess.run(['which', 'gst-launch-1.0'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("GStreamer command-line tools not found. Make sure GStreamer is installed properly.")
            logger.warning("Download from: https://gstreamer.freedesktop.org/download/#macos")
    except Exception as e:
        logger.warning(f"Failed to check GStreamer installation: {e}")

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

from config import Config
from api_client import ApiClient
from rtsp_server import RtspServer

def signal_handler(sig, frame):
    logger.info("Exiting gracefully...")
    sys.exit(0)

def main():
    try:
        Gst.init(None)
        logger.info("GStreamer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize GStreamer: {e}")
        sys.exit(1)
    
    config_path = os.environ.get('CONFIG_PATH', 'config.json')
    config = Config(config_path)
    
    api_client = ApiClient(config)
    
    rtsp_server = RtspServer(config, api_client)
    
    rtsp_server.start()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    main_loop = GLib.MainLoop()
    try:
        main_loop.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
