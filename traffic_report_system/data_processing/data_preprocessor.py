
"""
교통 데이터 전처리 모듈
작성일: 2025-05-12
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import numpy as np
import pandas as pd
from scipy import stats
from ..config import get_config

logger = logging.getLogger(__name__)

class TrafficDataPreprocessor:
    """교통 데이터 전처리를 관리하는 클래스"""
    
    def __init__(self):
        """
        교통 데이터 전처리기를 초기화합니다.
        """
        self.config = get_config("data_processing")
        self.outlier_method = self.config["outlier_detection"]["method"]
        self.outlier_threshold = self.config["outlier_detection"]["threshold"]
        self.missing_method = self.config["missing_value_handling"]["method"]
        self.missing_limit = self.config["missing_value_handling"]["limit"]
    
    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        교통 데이터를 전처리합니다.
        
        Args:
            df (pd.DataFrame): 원본 교통 데이터
            
        Returns:
            pd.DataFrame: 전처리된 교통 데이터
        """
        if df.empty:
            logger.warning("전처리할 데이터가 없습니다.")
            return df
        
        processed_df = df.copy()
        
        processed_df = self._convert_data_types(processed_df)
        
        processed_df = self._handle_missing_values(processed_df)
        
        processed_df = self._handle_outliers(processed_df)
        
        processed_df = self._create_derived_features(processed_df)
        
        return processed_df
    
    def _convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        데이터 타입을 변환합니다.
        
        Args:
            df (pd.DataFrame): 원본 데이터프레임
            
        Returns:
            pd.DataFrame: 타입 변환된 데이터프레임
        """
        if 'COL_DTM' in df.columns:
            df['COL_DTM'] = pd.to_datetime(df['COL_DTM'])
        
        numeric_cols = ['VOL', 'SPD', 'OCC', 'PASSING_TIME', 'TOTAL', 'RATIO']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        결측치를 처리합니다.
        
        Args:
            df (pd.DataFrame): 원본 데이터프레임
            
        Returns:
            pd.DataFrame: 결측치가 처리된 데이터프레임
        """
        missing_ratio = df.isnull().sum() / len(df)
        for col, ratio in missing_ratio.items():
            if ratio > 0:
                logger.info(f"컬럼 '{col}'의 결측치 비율: {ratio:.2%}")
        
        if self.missing_method == "drop":
            df = df.dropna()
            logger.info("결측치가 있는 행을 삭제했습니다.")
        
        elif self.missing_method == "interpolate":
            numeric_cols = ['VOL', 'SPD', 'OCC', 'PASSING_TIME', 'TOTAL', 'RATIO']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].interpolate(method='time', limit=self.missing_limit)
            logger.info(f"결측치를 시계열 보간 방식으로 처리했습니다. (제한: {self.missing_limit})")
        
        elif self.missing_method == "ffill":
            for col in df.columns:
                df[col] = df[col].ffill(limit=self.missing_limit)
            logger.info(f"결측치를 앞의 값으로 채웠습니다. (제한: {self.missing_limit})")
        
        elif self.missing_method == "bfill":
            for col in df.columns:
                df[col] = df[col].bfill(limit=self.missing_limit)
            logger.info(f"결측치를 뒤의 값으로 채웠습니다. (제한: {self.missing_limit})")
        
        elif self.missing_method == "mean":
            numeric_cols = ['VOL', 'SPD', 'OCC', 'PASSING_TIME', 'TOTAL', 'RATIO']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].fillna(df[col].mean())
            logger.info("결측치를 평균값으로 채웠습니다.")
        
        remaining_missing = df.isnull().sum().sum()
        if remaining_missing > 0:
            logger.warning(f"처리 후에도 {remaining_missing}개의 결측치가 남아있습니다.")
        
        return df
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        이상치를 처리합니다.
        
        Args:
            df (pd.DataFrame): 원본 데이터프레임
            
        Returns:
            pd.DataFrame: 이상치가 처리된 데이터프레임
        """
        numeric_cols = ['VOL', 'SPD', 'OCC', 'PASSING_TIME', 'RATIO']
        
        for col in numeric_cols:
            if col not in df.columns:
                continue
            
            if self.outlier_method == "z_score":
                z_scores = np.abs(stats.zscore(df[col], nan_policy='omit'))
                outliers = z_scores > self.outlier_threshold
                
                outlier_count = outliers.sum()
                if outlier_count > 0:
                    logger.info(f"컬럼 '{col}'에서 Z-score 방식으로 {outlier_count}개의 이상치를 발견했습니다.")
                    
                    df.loc[outliers, col] = np.nan
                    df[col] = df[col].interpolate(method='linear', limit=self.missing_limit)
            
            elif self.outlier_method == "iqr":
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - self.outlier_threshold * IQR
                upper_bound = Q3 + self.outlier_threshold * IQR
                
                outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
                
                outlier_count = outliers.sum()
                if outlier_count > 0:
                    logger.info(f"컬럼 '{col}'에서 IQR 방식으로 {outlier_count}개의 이상치를 발견했습니다.")
                    
                    df.loc[outliers, col] = np.nan
                    df[col] = df[col].interpolate(method='linear', limit=self.missing_limit)
        
        return df
    
    def _create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        파생 변수를 생성합니다.
        
        Args:
            df (pd.DataFrame): 원본 데이터프레임
            
        Returns:
            pd.DataFrame: 파생 변수가 추가된 데이터프레임
        """
        if 'STAT_DAY' in df.columns:
            df['DATE'] = pd.to_datetime(df['STAT_DAY'], format='%Y%m%d')
            df['YEAR'] = df['DATE'].dt.year
            df['MONTH'] = df['DATE'].dt.month
            df['DAY'] = df['DATE'].dt.day
        
        if 'STAT_HOUR' in df.columns and 'STAT_MIN' in df.columns:
            df['TIME'] = df['STAT_HOUR'].astype(str).str.zfill(2) + ':' + df['STAT_MIN'].astype(str).str.zfill(2)
            
            df['TIME_PERIOD'] = 'NON_PEAK'
            df.loc[(df['STAT_HOUR'].astype(int) >= 7) & (df['STAT_HOUR'].astype(int) <= 9), 'TIME_PERIOD'] = 'MORNING_PEAK'
            df.loc[(df['STAT_HOUR'].astype(int) >= 17) & (df['STAT_HOUR'].astype(int) <= 19), 'TIME_PERIOD'] = 'EVENING_PEAK'
        
        if 'SPD' in df.columns:
            df['TRAFFIC_STATUS'] = 'NORMAL'
            df.loc[df['SPD'] < 30, 'TRAFFIC_STATUS'] = 'CONGESTED'
            df.loc[df['SPD'] < 10, 'TRAFFIC_STATUS'] = 'SEVERELY_CONGESTED'
            df.loc[df['SPD'] > 80, 'TRAFFIC_STATUS'] = 'FREE_FLOW'
        
        if 'SPD' in df.columns and 'RATIO' not in df.columns:
            free_flow_speed = 80
            df['CONGESTION_RATIO'] = (1 - (df['SPD'] / free_flow_speed)).clip(0, 1) * 100
        
        return df
    
    def calculate_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        데이터의 주요 통계를 계산합니다.
        
        Args:
            df (pd.DataFrame): 데이터프레임
            
        Returns:
            Dict[str, Any]: 통계 정보
        """
        if df.empty:
            return {}
        
        stats_dict = {}
        
        numeric_cols = ['VOL', 'SPD', 'OCC', 'PASSING_TIME', 'RATIO']
        for col in numeric_cols:
            if col in df.columns:
                stats_dict[f"{col}_mean"] = df[col].mean()
                stats_dict[f"{col}_median"] = df[col].median()
                stats_dict[f"{col}_min"] = df[col].min()
                stats_dict[f"{col}_max"] = df[col].max()
                stats_dict[f"{col}_std"] = df[col].std()
        
        if 'TIME_PERIOD' in df.columns:
            for period in df['TIME_PERIOD'].unique():
                period_df = df[df['TIME_PERIOD'] == period]
                if 'SPD' in df.columns:
                    stats_dict[f"SPD_mean_{period}"] = period_df['SPD'].mean()
                if 'VOL' in df.columns:
                    stats_dict[f"VOL_mean_{period}"] = period_df['VOL'].mean()
        
        if 'TRAFFIC_STATUS' in df.columns:
            status_counts = df['TRAFFIC_STATUS'].value_counts(normalize=True) * 100
            for status, ratio in status_counts.items():
                stats_dict[f"{status}_ratio"] = ratio
        
        if 'TRAFFIC_STATUS' in df.columns:
            congestion_mask = df['TRAFFIC_STATUS'].isin(['CONGESTED', 'SEVERELY_CONGESTED'])
            stats_dict["congestion_time_ratio"] = congestion_mask.mean() * 100
        
        return stats_dict
