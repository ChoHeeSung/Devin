
"""
교통 데이터 로더 모듈
작성일: 2025-05-12
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
from ..database.oracle_connector import OracleConnector
from ..config import get_config, DATA_DIR

logger = logging.getLogger(__name__)

class TrafficDataLoader:
    """교통 데이터 로딩을 관리하는 클래스"""
    
    def __init__(self):
        """
        교통 데이터 로더를 초기화합니다.
        """
        self.oracle_connector = OracleConnector()
        self.data_dir = DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_daily_data(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        일일 교통 데이터를 로드합니다.
        
        Args:
            date (Optional[str]): 로드할 날짜 (YYYYMMDD), None인 경우 어제 날짜
            
        Returns:
            pd.DataFrame: 로드된 교통 데이터
        """
        if date is None:
            yesterday = datetime.now() - timedelta(days=1)
            date = yesterday.strftime("%Y%m%d")
        
        cache_file = os.path.join(self.data_dir, f"daily_{date}.parquet")
        
        if os.path.exists(cache_file):
            logger.info(f"캐시된 일일 데이터를 로드합니다: {date}")
            return pd.read_parquet(cache_file)
        
        logger.info(f"데이터베이스에서 일일 데이터를 로드합니다: {date}")
        df = self.oracle_connector.get_daily_traffic_data(date)
        
        if not df.empty:
            df.to_parquet(cache_file)
            logger.info(f"일일 데이터를 캐시 파일로 저장했습니다: {cache_file}")
        
        return df
    
    def load_weekly_data(self, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        주간 교통 데이터를 로드합니다.
        
        Args:
            end_date (Optional[str]): 주간의 마지막 날짜 (YYYYMMDD), None인 경우 어제 날짜
            
        Returns:
            pd.DataFrame: 로드된 교통 데이터
        """
        if end_date is None:
            yesterday = datetime.now() - timedelta(days=1)
            end_date = yesterday.strftime("%Y%m%d")
        
        end_date_obj = datetime.strptime(end_date, "%Y%m%d")
        start_date_obj = end_date_obj - timedelta(days=6)
        start_date = start_date_obj.strftime("%Y%m%d")
        
        cache_file = os.path.join(self.data_dir, f"weekly_{start_date}_to_{end_date}.parquet")
        
        if os.path.exists(cache_file):
            logger.info(f"캐시된 주간 데이터를 로드합니다: {start_date} ~ {end_date}")
            return pd.read_parquet(cache_file)
        
        logger.info(f"데이터베이스에서 주간 데이터를 로드합니다: {start_date} ~ {end_date}")
        df = self.oracle_connector.get_weekly_traffic_data(start_date, end_date)
        
        if not df.empty:
            df.to_parquet(cache_file)
            logger.info(f"주간 데이터를 캐시 파일로 저장했습니다: {cache_file}")
        
        return df
    
    def load_monthly_data(self, year_month: Optional[str] = None) -> pd.DataFrame:
        """
        월간 교통 데이터를 로드합니다.
        
        Args:
            year_month (Optional[str]): 로드할 년월 (YYYYMM), None인 경우 지난 달
            
        Returns:
            pd.DataFrame: 로드된 교통 데이터
        """
        if year_month is None:
            today = datetime.now()
            first_day_of_month = datetime(today.year, today.month, 1)
            last_month = first_day_of_month - timedelta(days=1)
            year_month = last_month.strftime("%Y%m")
        
        cache_file = os.path.join(self.data_dir, f"monthly_{year_month}.parquet")
        
        if os.path.exists(cache_file):
            logger.info(f"캐시된 월간 데이터를 로드합니다: {year_month}")
            return pd.read_parquet(cache_file)
        
        logger.info(f"데이터베이스에서 월간 데이터를 로드합니다: {year_month}")
        df = self.oracle_connector.get_monthly_traffic_data(year_month)
        
        if not df.empty:
            df.to_parquet(cache_file)
            logger.info(f"월간 데이터를 캐시 파일로 저장했습니다: {cache_file}")
        
        return df
    
    def load_custom_period_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        사용자 지정 기간의 교통 데이터를 로드합니다.
        
        Args:
            start_date (str): 시작 날짜 (YYYYMMDD)
            end_date (str): 종료 날짜 (YYYYMMDD)
            
        Returns:
            pd.DataFrame: 로드된 교통 데이터
        """
        cache_file = os.path.join(self.data_dir, f"custom_{start_date}_to_{end_date}.parquet")
        
        if os.path.exists(cache_file):
            logger.info(f"캐시된 사용자 지정 기간 데이터를 로드합니다: {start_date} ~ {end_date}")
            return pd.read_parquet(cache_file)
        
        logger.info(f"데이터베이스에서 사용자 지정 기간 데이터를 로드합니다: {start_date} ~ {end_date}")
        df = self.oracle_connector.get_weekly_traffic_data(start_date, end_date)
        
        if not df.empty:
            df.to_parquet(cache_file)
            logger.info(f"사용자 지정 기간 데이터를 캐시 파일로 저장했습니다: {cache_file}")
        
        return df
    
    def clear_cache(self, days_to_keep: int = 30) -> None:
        """
        오래된 캐시 파일을 삭제합니다.
        
        Args:
            days_to_keep (int): 보관할 일수
        """
        now = datetime.now()
        cutoff_date = now - timedelta(days=days_to_keep)
        
        for filename in os.listdir(self.data_dir):
            file_path = os.path.join(self.data_dir, filename)
            
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_mod_time < cutoff_date:
                os.remove(file_path)
                logger.info(f"오래된 캐시 파일을 삭제했습니다: {file_path}")
