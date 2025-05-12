
"""
Oracle 데이터베이스 연결 모듈
작성일: 2025-05-12
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import cx_Oracle
from ..config import get_config, get_db_connection_string

logger = logging.getLogger(__name__)

class OracleConnector:
    """Oracle 데이터베이스 연결 및 쿼리 실행을 관리하는 클래스"""
    
    def __init__(self):
        """
        Oracle 데이터베이스 연결 관리자를 초기화합니다.
        """
        self.oracle_config = get_config("oracle")
        self.connection = None
        
    def connect(self) -> bool:
        """
        Oracle 데이터베이스에 연결합니다.
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            
            connection_string = get_db_connection_string()
            self.connection = cx_Oracle.connect(connection_string)
            logger.info("Oracle 데이터베이스에 연결되었습니다.")
            return True
        except cx_Oracle.Error as e:
            error, = e.args
            logger.error(f"Oracle 데이터베이스 연결 실패: {error.message}")
            return False
    
    def disconnect(self) -> None:
        """
        Oracle 데이터베이스 연결을 종료합니다.
        """
        if self.connection:
            try:
                self.connection.close()
                logger.info("Oracle 데이터베이스 연결이 종료되었습니다.")
            except cx_Oracle.Error as e:
                error, = e.args
                logger.error(f"Oracle 데이터베이스 연결 종료 실패: {error.message}")
            finally:
                self.connection = None
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        SQL 쿼리를 실행하고 결과를 DataFrame으로 반환합니다.
        
        Args:
            query (str): 실행할 SQL 쿼리
            params (Optional[Dict[str, Any]]): 쿼리 파라미터
            
        Returns:
            pd.DataFrame: 쿼리 결과
        """
        if not self.connection:
            if not self.connect():
                return pd.DataFrame()
        
        try:
            return pd.read_sql(query, self.connection, params=params)
        except cx_Oracle.Error as e:
            error, = e.args
            logger.error(f"쿼리 실행 실패: {error.message}")
            logger.error(f"쿼리: {query}")
            logger.error(f"파라미터: {params}")
            return pd.DataFrame()
    
    def get_traffic_data(self, date: str, hour: Optional[str] = None, minute: Optional[str] = None, 
                         weekday: Optional[str] = None, link_id: Optional[str] = None) -> pd.DataFrame:
        """
        교통 데이터를 조회합니다.
        
        Args:
            date (str): 조회 날짜 (YYYYMMDD)
            hour (Optional[str]): 조회 시간 (HH)
            minute (Optional[str]): 조회 분 (MM)
            weekday (Optional[str]): 요일 (1-7)
            link_id (Optional[str]): 링크 ID
            
        Returns:
            pd.DataFrame: 교통 데이터
        """
        query = """
        SELECT STAT_DAY,
               STAT_HOUR,
               STAT_MIN,
               STAT_WEEKDAY,
               COL_DTM,
               LINK_ID,
               STATS_SE,
               VOL,
               SPD,
               OCC,
               PASSING_TIME,
               TOTAL,
               RATIO
        FROM ITS_PROC.LINK_STAT STAT 
        JOIN ITS_PROC.LINK_INFO INFO ON STAT.LINK_ID = INFO.LINK_ID
        WHERE STAT_DAY = :date
        """
        
        params = {"date": date}
        
        if hour is not None:
            query += " AND STAT_HOUR = :hour"
            params["hour"] = hour
        
        if minute is not None:
            query += " AND STAT_MIN = :minute"
            params["minute"] = minute
        
        if weekday is not None:
            query += " AND STAT_WEEKDAY = :weekday"
            params["weekday"] = weekday
        
        if link_id is not None:
            query += " AND STAT.LINK_ID = :link_id"
            params["link_id"] = link_id
        
        return self.execute_query(query, params)
    
    def get_daily_traffic_data(self, date: str) -> pd.DataFrame:
        """
        일일 교통 데이터를 조회합니다.
        
        Args:
            date (str): 조회 날짜 (YYYYMMDD)
            
        Returns:
            pd.DataFrame: 일일 교통 데이터
        """
        return self.get_traffic_data(date)
    
    def get_weekly_traffic_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        주간 교통 데이터를 조회합니다.
        
        Args:
            start_date (str): 시작 날짜 (YYYYMMDD)
            end_date (str): 종료 날짜 (YYYYMMDD)
            
        Returns:
            pd.DataFrame: 주간 교통 데이터
        """
        query = """
        SELECT STAT_DAY,
               STAT_HOUR,
               STAT_MIN,
               STAT_WEEKDAY,
               COL_DTM,
               LINK_ID,
               STATS_SE,
               VOL,
               SPD,
               OCC,
               PASSING_TIME,
               TOTAL,
               RATIO
        FROM ITS_PROC.LINK_STAT STAT 
        JOIN ITS_PROC.LINK_INFO INFO ON STAT.LINK_ID = INFO.LINK_ID
        WHERE STAT_DAY BETWEEN :start_date AND :end_date
        """
        
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        return self.execute_query(query, params)
    
    def get_monthly_traffic_data(self, year_month: str) -> pd.DataFrame:
        """
        월간 교통 데이터를 조회합니다.
        
        Args:
            year_month (str): 조회 년월 (YYYYMM)
            
        Returns:
            pd.DataFrame: 월간 교통 데이터
        """
        query = """
        SELECT STAT_DAY,
               STAT_HOUR,
               STAT_MIN,
               STAT_WEEKDAY,
               COL_DTM,
               LINK_ID,
               STATS_SE,
               VOL,
               SPD,
               OCC,
               PASSING_TIME,
               TOTAL,
               RATIO
        FROM ITS_PROC.LINK_STAT STAT 
        JOIN ITS_PROC.LINK_INFO INFO ON STAT.LINK_ID = INFO.LINK_ID
        WHERE SUBSTR(STAT_DAY, 1, 6) = :year_month
        """
        
        params = {"year_month": year_month}
        
        return self.execute_query(query, params)
