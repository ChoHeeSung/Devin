#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
벡터 스토어 설정 모듈
작성일: 2024-03-21
"""

from typing import List, Optional, Dict
from datetime import datetime
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from langchain_core.retrievers import BaseRetriever
from qdrant_client import QdrantClient
from qdrant_client.http import models

class VectorStoreSetup:
    """벡터 스토어 설정을 관리하는 클래스"""
    
    def __init__(
        self,
        embedding: Embeddings,
        location: str = ":memory:",
        collection_name: Optional[str] = None,
        retrieval_mode: RetrievalMode = RetrievalMode.DENSE,
        search_k: int = 10,
        checkpoint_config: Optional[Dict[str, str]] = None  # 이 매개변수는 유지하되 사용하지 않음
    ):
        """
        벡터 스토어 설정을 초기화합니다.

        Args:
            embedding (Embeddings): 사용할 임베딩 인스턴스
            location (str): Qdrant 저장소 위치 (기본값: ":memory:")
            collection_name (Optional[str]): 컬렉션 이름 (기본값: None, 자동 생성됨)
            retrieval_mode (RetrievalMode): 검색 모드 (기본값: DENSE)
            search_k (int): 검색 결과 수 (기본값: 10)
            checkpoint_config (Optional[Dict[str, str]]): 체크포인터 설정
        """
        self.embedding = embedding
        self.location = location
        self.collection_name = collection_name or f"rag_collection_{datetime.now().strftime('%Y%m%d')}"
        self.retrieval_mode = retrieval_mode
        self.search_k = search_k
        self._vector_store = None
        self._retriever = None
        
    def create_vector_store(self, documents: List[Document]) -> QdrantVectorStore:
        """
        문서로부터 벡터 스토어를 생성합니다.
        """
        # 벡터 스토어 생성
        self._vector_store = QdrantVectorStore.from_documents(
            documents=documents,
            embedding=self.embedding,
            location=self.location,
            collection_name=self.collection_name,
            retrieval_mode=self.retrieval_mode
        )
        
        # retriever 초기화를 벡터 스토어 생성 직후에 수행
        self._retriever = self._vector_store.as_retriever(
            search_kwargs={'k': self.search_k}
        )
        
        return self._vector_store
    
    @property
    def vector_store(self) -> Optional[QdrantVectorStore]:
        """
        벡터 스토어 인스턴스를 반환합니다.
        
        Returns:
            Optional[QdrantVectorStore]: 벡터 스토어 인스턴스 또는 None
        """
        return self._vector_store
    
    @property
    def retriever(self) -> Optional[BaseRetriever]:
        """
        검색기 인스턴스를 반환합니다.
        
        Returns:
            Optional[BaseRetriever]: 검색기 인스턴스 또는 None
        """
        return self._retriever
    
    def update_search_k(self, new_k: int) -> None:
        """
        검색 결과 수를 업데이트합니다.
        
        Args:
            new_k (int): 새로운 검색 결과 수
        """
        self.search_k = new_k
        if self._vector_store is not None:
            self._retriever = self._vector_store.as_retriever(
                search_kwargs={'k': new_k}
            )

# 기본 벡터 스토어 설정 예시 (실제 사용 시에는 embedding 인스턴스를 전달해야 함)
"""
from embedding_config import default_embeddings

default_vector_store_setup = VectorStoreSetup(
    embedding=default_embeddings,
    collection_name="rag_collection_0228"
)
""" 