
"""
교통 보고서 시스템 설정 모듈
작성일: 2025-05-12
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
LOG_DIR = os.path.join(BASE_DIR, "logs")

for directory in [DATA_DIR, REPORT_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)

ORACLE_CONFIG = {
    "host": os.getenv("ORACLE_HOST", ""),
    "port": os.getenv("ORACLE_PORT", "1521"),
    "service": os.getenv("ORACLE_SERVICE", ""),
    "user": os.getenv("ORACLE_USER", ""),
    "password": os.getenv("ORACLE_PASSWORD", ""),
}

LLM_CONFIG = {
    "model": "mistral:latest",  # 기본 모델
    "temperature": 0.1,
    "max_tokens": 2000,
}

REPORT_CONFIG = {
    "daily_report": {
        "format": ["markdown", "pdf"],
        "sections": ["summary", "traffic_analysis", "congestion_analysis", "incident_analysis", "recommendations"],
    },
    "weekly_report": {
        "format": ["markdown", "pdf"],
        "sections": ["executive_summary", "weekly_trends", "peak_analysis", "incident_summary", "recommendations"],
    },
    "monthly_report": {
        "format": ["markdown", "pdf"],
        "sections": ["executive_summary", "monthly_overview", "trend_analysis", "incident_patterns", "recommendations", "next_month_forecast"],
    },
}

VISUALIZATION_CONFIG = {
    "theme": "plotly",
    "color_scheme": "viridis",
    "default_width": 800,
    "default_height": 500,
}

DATA_PROCESSING_CONFIG = {
    "outlier_detection": {
        "method": "z_score",
        "threshold": 3.0,
    },
    "missing_value_handling": {
        "method": "interpolate",
        "limit": 5,
    },
}

def get_db_connection_string() -> str:
    """
    Oracle 데이터베이스 연결 문자열을 반환합니다.
    
    Returns:
        str: 데이터베이스 연결 문자열
    """
    return f"{ORACLE_CONFIG['user']}/{ORACLE_CONFIG['password']}@{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}/{ORACLE_CONFIG['service']}"

def get_config(section: str) -> Dict[str, Any]:
    """
    지정된 섹션의 설정을 반환합니다.
    
    Args:
        section (str): 설정 섹션 이름
        
    Returns:
        Dict[str, Any]: 설정 딕셔너리
    """
    config_map = {
        "oracle": ORACLE_CONFIG,
        "llm": LLM_CONFIG,
        "report": REPORT_CONFIG,
        "visualization": VISUALIZATION_CONFIG,
        "data_processing": DATA_PROCESSING_CONFIG,
    }
    
    return config_map.get(section, {})
