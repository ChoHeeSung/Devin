#!/usr/bin/env python3
import logging
import requests
import time
import threading

logger = logging.getLogger(__name__)

class ApiClient:
    def __init__(self, config):
        self.config = config
        self.streams = {}
        self.streams_lock = threading.Lock()
        
        self._load_streams_from_config()
        
        self.update_thread = threading.Thread(target=self._update_streams_periodically, daemon=True)
        self.update_thread.start()
    
    def _load_streams_from_config(self):
        with self.streams_lock:
            self.streams = self.config.get_streams()
            logger.info(f"Loaded {len(self.streams)} streams from config file")
    
    def _fetch_streams_from_api(self):
        api_url = self.config.get_api_url()
        timeout = self.config.get_api_timeout()
        
        try:
            response = requests.get(api_url, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            
            new_streams = {}
            for item in data:
                equip_id = item.get('equipId')
                rtsp_url = item.get('rtspUrl')
                
                if equip_id and rtsp_url:
                    new_streams[equip_id] = {'url': rtsp_url}
            
            with self.streams_lock:
                self.streams = new_streams
            
            logger.info(f"Updated {len(new_streams)} streams from API")
            return True
        
        except Exception as e:
            logger.error(f"Failed to fetch streams from API: {e}")
            return False
    
    def _update_streams_periodically(self):
        while True:
            success = self._fetch_streams_from_api()
            
            if not success:
                logger.warning("Using streams from config file as fallback")
                self._load_streams_from_config()
            
            time.sleep(self.config.get_api_retry_interval())
    
    def get_streams(self):
        with self.streams_lock:
            return self.streams.copy()
