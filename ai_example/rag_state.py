#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAG 상태 정의 모듈
작성일: 2024-03-21
"""

from typing import Annotated, List, TypedDict, Literal
from langgraph.graph.message import add_messages
from langchain_core.documents import Document

class RAGState(TypedDict):
    """
    RAG 시스템의 상태를 정의합니다.
    
    Attributes:
        query (str): 사용자 질의
        think (str): reasoning_llm이 생성한 사고 과정
        documents (List[Document]): 검색된 문서 목록
        answer (str): answer_llm이 생성한 답변
        message (List): 메시지 저장
        mode (str): 모드 저장
    """
    query: str
    think: str
    documents: List[Document]
    answer: str
    message: Annotated[List, add_messages]
    mode: str 