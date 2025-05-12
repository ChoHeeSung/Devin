#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
임베딩 설정 모듈
작성일: 2024-03-21
"""

from langchain_ollama import OllamaEmbeddings
from typing import Optional

class EmbeddingSetup:
    """임베딩 설정을 관리하는 클래스"""
    
    def __init__(
        self,
        model: str = "bge-m3:latest",
        base_url: Optional[str] = None
    ):
        """
        임베딩 설정을 초기화합니다.

        Args:
            model (str): 사용할 임베딩 모델명
            base_url (Optional[str]): Ollama 서버 URL (기본값: None)
        """
        self.model = model
        self.base_url = base_url
        self._embeddings = None
    
    @property
    def embeddings(self) -> OllamaEmbeddings:
        """
        임베딩 인스턴스를 반환합니다.
        
        Returns:
            OllamaEmbeddings: 설정된 임베딩 인스턴스
        """
        if self._embeddings is None:
            self._embeddings = self._create_embeddings()
        return self._embeddings
    
    def _create_embeddings(self) -> OllamaEmbeddings:
        """
        임베딩 인스턴스를 생성합니다.
        
        Returns:
            OllamaEmbeddings: 생성된 임베딩 인스턴스
        """
        kwargs = {"model": self.model}
        if self.base_url:
            kwargs["base_url"] = self.base_url
            
        return OllamaEmbeddings(**kwargs)
    
    def refresh_embeddings(self) -> None:
        """임베딩 인스턴스를 새로 생성합니다."""
        self._embeddings = self._create_embeddings()

# 기본 임베딩 설정 인스턴스 생성
default_embedding_setup = EmbeddingSetup()
default_embeddings = default_embedding_setup.embeddings 