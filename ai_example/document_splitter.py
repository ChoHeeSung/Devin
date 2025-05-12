#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
문서 분할 모듈
작성일: 2024-03-21
"""

from typing import List, Dict, Optional
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document

class DocumentSplitter:
    """문서 분할을 관리하는 클래스"""
    
    def __init__(self, headers_to_split_on: Optional[List[Dict]] = None):
        """
        문서 분할 관리자를 초기화합니다.

        Args:
            headers_to_split_on (Optional[List[Dict]]): 분할할 헤더 레벨 설정
        """
        self.headers_to_split_on = headers_to_split_on or [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        
        self.splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on
        )
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        문서들을 헤더 기준으로 분할합니다.
        
        Args:
            documents (List[Document]): 분할할 문서 리스트
            
        Returns:
            List[Document]: 분할된 문서 리스트
        """
        splits = []
        for doc in documents:
            splits.extend(self.splitter.split_text(doc.page_content))
        return splits
    
    def print_sample_splits(self, splits: List[Document], sample_size: int = 3) -> None:
        """
        분할된 문서의 샘플을 출력합니다.
        
        Args:
            splits (List[Document]): 분할된 문서 리스트
            sample_size (int): 출력할 샘플 수
        """
        for d in splits[:sample_size]:
            print(f"- {d.page_content=}")
        if len(splits) > sample_size:
            print("...")
            
    def get_splits_by_header(self, documents: List[Document], header_level: str) -> List[Document]:
        """
        특정 헤더 레벨의 문서만 필터링합니다.
        
        Args:
            documents (List[Document]): 분할된 문서 리스트
            header_level (str): 필터링할 헤더 레벨 (예: "Header 1")
            
        Returns:
            List[Document]: 필터링된 문서 리스트
        """
        return [doc for doc in documents if doc.metadata.get("header_level") == header_level]

# 기본 분할 관리자 인스턴스 생성
default_splitter = DocumentSplitter() 