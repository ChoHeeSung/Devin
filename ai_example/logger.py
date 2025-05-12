#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
로깅 설정 모듈
작성일: 2024-03-21
"""

import os
from loguru import logger
from typing import Optional

class LoggerSetup:
    """로깅 설정을 관리하는 클래스"""
    
    @staticmethod
    def setup_logger(
        log_level: str = "INFO",
        log_file: str = "app.log",
        rotation: str = "10 MB",
        retention: str = "7 days"
    ) -> logger:
        """
        Loguru 로깅 설정을 초기화합니다.

        Args:
            log_level (str): 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file (str): 로그 파일 경로
            rotation (str): 로그 파일 순환 기준 (예: "10 MB", "1 day")
            retention (str): 로그 파일 보관 기간

        Returns:
            logger: 설정된 loguru 로거 인스턴스
        """
        # 기존 핸들러 제거
        logger.remove()
        
        # 로그 디렉토리 생성
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # 로거 설정
        logger.add(
            log_file,
            rotation=rotation,
            retention=retention,
            compression="zip",
            level=log_level.upper(),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
            encoding="utf-8"
        )

        # 콘솔 출력 설정
        logger.add(
            sink=lambda msg: print(msg),
            level=log_level.upper(),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

        return logger

# 기본 로거 인스턴스 생성
default_logger = LoggerSetup.setup_logger(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="logs/app.log"
) 