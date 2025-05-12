#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
워크플로우 설정 모듈
작성일: 2024-03-21
"""

from typing import Optional, Dict, Any
from langgraph.graph import START, StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from rag_state import RAGState
from rag_processor import RAGProcessor

class WorkflowSetup:
    """워크플로우 설정을 관리하는 클래스"""
    
    def __init__(
        self,
        rag_processor: RAGProcessor,
        use_memory: bool = True
    ):
        """
        워크플로우 설정을 초기화합니다.

        Args:
            rag_processor (RAGProcessor): RAG 처리기 인스턴스
            use_memory (bool): 메모리 체크포인트 사용 여부
        """
        self.rag_processor = rag_processor
        self.use_memory = use_memory
        self._app = None
        
    @property
    def app(self) -> Any:
        """
        컴파일된 워크플로우 앱을 반환합니다.
        """
        if self._app is None:
            # RAGProcessor의 create_graph 메서드를 사용
            self._app = self.rag_processor.create_graph()
        return self._app
    
    def create_initial_state(self, query: str) -> RAGState:
        """초기 상태를 생성합니다."""
        return {
            "query": query,
            "think": "",
            "documents": [],
            "answer": "",
            "message": [],
            "mode": ""
        }
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """질의를 처리합니다."""
        initial_state = self.create_initial_state(query)
        return self.app.invoke(initial_state)

# 사용 예시:
"""
from rag_processor import RAGProcessor
from llm_config import reasoning_llm, answer_llm
from compression_retriever_config import default_compression_retriever

# RAG 프로세서 설정
rag_processor = RAGProcessor(
    compression_retriever=default_compression_retriever,
    reasoning_llm=reasoning_llm,
    answer_llm=answer_llm
)

# 워크플로우 설정
workflow_setup = WorkflowSetup(rag_processor)

# 질의 처리
result = workflow_setup.process_query("사용자 질문")
""" 