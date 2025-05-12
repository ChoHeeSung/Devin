#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
문서 로더 설정 모듈
작성일: 2024-03-21
"""

import os
from typing import List
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
from langchain_core.documents import Document

class DocumentLoaderSetup:
    """문서 로더 설정을 관리하는 클래스"""
    
    def __init__(self, file_path: str):
        """
        문서 로더를 초기화합니다.

        Args:
            file_path (str): PDF 파일 경로 또는 URL
        """
        self.file_path = file_path
        self._validate_file_path()
        
    def _validate_file_path(self) -> None:
        """파일 경로가 유효한지 검증합니다."""
        if self.file_path.startswith('http'):
            return
        
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {self.file_path}")
        
        if not self.file_path.lower().endswith('.pdf'):
            raise ValueError("PDF 파일만 지원됩니다.")
    
    def load_documents(self) -> List[Document]:
        """
        문서를 로드합니다.

        Returns:
            List[Document]: 로드된 문서 리스트
        """
        loader = DoclingLoader(
            file_path=self.file_path,
            export_type=ExportType.MARKDOWN,
        )
        
        return loader.load()

# 기본 문서 경로 설정
DEFAULT_PDF_PATH = "/Users/heesung/work/M_CHO/vds-server/CNITS-DE-007.1-인터페이스 설계서_VDS(표준) Ver 1.0.pdf"

# 기본 로더 인스턴스 생성
default_loader = DocumentLoaderSetup(DEFAULT_PDF_PATH) 