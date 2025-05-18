#!/usr/bin/env python3
import os
import sys
import signal
import json
import logging
import gi

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

from config import Config
from api_client import ApiClient
from rtsp_server import RtspServer

def signal_handler(sig, frame):
    logger.info("Exiting gracefully...")
    sys.exit(0)

def main():
    Gst.init(None)
    
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

if __name__ == "__main__":
    main()
