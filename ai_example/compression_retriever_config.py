#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
컨텍스트 압축 검색기 설정 모듈
작성일: 2024-03-21
"""

from typing import Optional
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.retrievers import BaseRetriever

class CompressionRetrieverSetup:
    """컨텍스트 압축 검색기 설정을 관리하는 클래스"""
    
    def __init__(
        self,
        base_retriever: BaseRetriever,
        model_name: str = "BAAI/bge-reranker-base",
        top_n: int = 5,
        device: Optional[str] = None
    ):
        """
        압축 검색기 설정을 초기화합니다.

        Args:
            base_retriever (BaseRetriever): 기본 검색기 인스턴스
            model_name (str): 재순위화 모델 이름 (기본값: "BAAI/bge-reranker-base")
            top_n (int): 상위 결과 수 (기본값: 5)
            device (Optional[str]): 사용할 디바이스 (예: "cuda", "cpu")
        """
        self.base_retriever = base_retriever
        self.model_name = model_name
        self.top_n = top_n
        self.device = device
        self._compression_retriever = None
        
    def _create_cross_encoder(self) -> HuggingFaceCrossEncoder:
        """
        크로스 인코더 모델을 생성합니다.
        
        Returns:
            HuggingFaceCrossEncoder: 생성된 크로스 인코더 모델
        """
        kwargs = {"model_name": self.model_name}
        if self.device:
            kwargs["device"] = self.device
            
        return HuggingFaceCrossEncoder(**kwargs)
    
    @property
    def compression_retriever(self) -> ContextualCompressionRetriever:
        """
        압축 검색기 인스턴스를 반환합니다.
        
        Returns:
            ContextualCompressionRetriever: 설정된 압축 검색기
        """
        if self._compression_retriever is None:
            model = self._create_cross_encoder()
            compressor = CrossEncoderReranker(
                model=model,
                top_n=self.top_n
            )
            self._compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=self.base_retriever
            )
        return self._compression_retriever
    
    def update_top_n(self, new_top_n: int) -> None:
        """
        상위 결과 수를 업데이트합니다.
        
        Args:
            new_top_n (int): 새로운 상위 결과 수
        """
        self.top_n = new_top_n
        self._compression_retriever = None  # 재생성을 위해 초기화
        
    def refresh_retriever(self) -> None:
        """압축 검색기를 새로 생성합니다."""
        self._compression_retriever = None

# 기본 압축 검색기 설정 예시 (실제 사용 시에는 base_retriever를 전달해야 함)
"""
from vector_store_config import default_vector_store_setup

default_compression_setup = CompressionRetrieverSetup(
    base_retriever=default_vector_store_setup.retriever
)
""" 