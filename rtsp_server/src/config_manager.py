import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

class ConfigManager:
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger('RTSP-Server')
        self.config_path = config_path or str(Path(__file__).parent.parent / 'config' / 'config.json')
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """설정 파일을 로드합니다."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f'config.json 로드 실패: {e}')
            raise

    def get_server_config(self) -> Dict[str, Any]:
        """서버 설정을 반환합니다."""
        return self.config.get('server', {})

    def get_api_config(self) -> Dict[str, Any]:
        """API 설정을 반환합니다."""
        return self.config.get('api', {})

    def get_global_settings(self) -> Dict[str, Any]:
        """전역 설정을 반환합니다."""
        return self.config.get('global_settings', {})

    def get_streams_config(self) -> Dict[str, Dict[str, Any]]:
        """스트림 설정을 반환합니다."""
        return self.config.get('streams', {})

    def get_logging_config(self) -> Dict[str, Any]:
        """로깅 설정을 반환합니다."""
        return self.config.get('logging', {})

    def create_stream_config(self, cctv_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """CCTV 목록을 스트림 설정으로 변환합니다."""
        streams = {}
        global_settings = self.get_global_settings()
        
        for cctv in cctv_list:
            equip_id = cctv['equipId']
            rtsp_url = cctv['sourceUrl']
            
            # 전역 설정과 기본값을 사용하여 스트림 설정 생성
            stream_config = {
                'input_url': rtsp_url,
                'output_path': f'/{equip_id}',
                'on_demand': global_settings.get('on_demand', {}).get('enabled', True),
                'max_clients': global_settings.get('on_demand', {}).get('default_max_clients', 5),
                'idle_timeout': global_settings.get('on_demand', {}).get('default_idle_timeout', 300),
                'buffer_size': global_settings.get('on_demand', {}).get('default_buffer_size', '10M'),
                'rtsp_transport': global_settings.get('stream_settings', {}).get('default_rtsp_transport', 'tcp')
            }
            
            streams[equip_id] = stream_config
        
        return streams 