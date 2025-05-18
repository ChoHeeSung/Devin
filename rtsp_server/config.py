#!/usr/bin/env python3
import json
import logging

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, config_path):
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def get_server_rtsp_port(self):
        return self.config.get('server', {}).get('server_rtsp_port', ':8554')
    
    def get_on_demand(self):
        return self.config.get('stream_defaults', {}).get('on_demand', True)
    
    def get_disable_audio(self):
        return self.config.get('stream_defaults', {}).get('disable_audio', True)
    
    def get_debug(self):
        return self.config.get('stream_defaults', {}).get('debug', False)
    
    def get_api_url(self):
        return self.config.get('api', {}).get('cctv_master_url', '')
    
    def get_api_retry_interval(self):
        return self.config.get('api', {}).get('retry_interval', 30)
    
    def get_api_timeout(self):
        return self.config.get('api', {}).get('timeout', 10)
    
    def get_streams(self):
        return self.config.get('streams', {})
