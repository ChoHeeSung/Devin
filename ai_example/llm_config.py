#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM 설정 모듈
작성일: 2024-03-21
"""

from langchain_ollama import ChatOllama
from typing import Optional

class LLMSetup:
    """LLM 설정을 관리하는 클래스"""
    
    @staticmethod
    def get_reasoning_llm() -> ChatOllama:
        """
        추론용 LLM 인스턴스를 반환합니다.

        Returns:
            ChatOllama: Deepseek 모델 인스턴스
        """
        return ChatOllama(
            model="deepseek-r1:7b",
            stop=["</think>"],
        )
    
    @staticmethod
    def get_answer_llm() -> ChatOllama:
        """
        답변 생성용 LLM 인스턴스를 반환합니다.

        Returns:
            ChatOllama: Exaone 모델 인스턴스
        """
        return ChatOllama(
            model="exaone3.5",
            temperature=0.0
        )

# 기본 LLM 인스턴스 생성
reasoning_llm = LLMSetup.get_reasoning_llm()
answer_llm = LLMSetup.get_answer_llm() 