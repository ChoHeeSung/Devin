import requests
import logging
from typing import Dict, Any, List, Optional

class APIClient:
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.api_config = config.get('api', {})
        self.base_url = self.api_config.get('base_url', '')
        self.timeout = self.api_config.get('timeout', 10)  # 기본 타임아웃 10초

    def fetch_cctv_list(self) -> Optional[List[Dict[str, Any]]]:
        """CCTV 목록을 API에서 가져옵니다."""
        endpoint = self.api_config.get('endpoints', {}).get('cctv_list', '/matrix/its/basic/device/cctvMaster/select')
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.logger.info(f'API 호출 시도: {url}')
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            data = response.json()
            if not data:
                self.logger.warning('API 응답이 비어있습니다.')
                return None
                
            self.logger.info(f'CCTV 목록 조회 성공: {len(data)}개 항목')
            return data
            
        except requests.exceptions.Timeout:
            self.logger.warning('API 호출 타임아웃')
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f'API 연결 실패: {str(e)}')
        except requests.exceptions.RequestException as e:
            self.logger.warning(f'API 호출 실패: {str(e)}')
        
        self.logger.info('API 호출 실패로 config.json의 설정을 사용합니다.')
        return None 