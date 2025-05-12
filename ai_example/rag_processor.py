#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAG 처리 모듈
작성일: 2024-03-21
"""

from typing import Dict, Any, Literal
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from langchain.retrievers import ContextualCompressionRetriever
from langgraph.graph import START, StateGraph, END
from rag_state import RAGState

class RAGProcessor:
    """RAG 처리를 관리하는 클래스"""
    
    def __init__(
        self,
        compression_retriever: ContextualCompressionRetriever,
        reasoning_llm: BaseChatModel,
        answer_llm: BaseChatModel
    ):
        """
        RAG 처리기를 초기화합니다.

        Args:
            compression_retriever: 문서 검색기
            reasoning_llm: 추론용 LLM
            answer_llm: 답변 생성용 LLM
        """
        self.compression_retriever = compression_retriever
        self.reasoning_llm = reasoning_llm
        self.answer_llm = answer_llm
        
        # 프롬프트 템플릿 초기화
        self.reasoning_prompt = ChatPromptTemplate.from_template(
            """주어진 문서를 활용하여 사용자의 질문에 가장 적절한 답변을 작성 해주세요.
            
            질문 : {query}

            문서내용 : 
            {context}

            상세 추론 :"""
        )
        
        self.answer_prompt = ChatPromptTemplate.from_template(
            """ 사용자의 질문에 한글로 답변 하세요. 제공된 문서와 추론과정이 있다면, 최대한 활용 하세요

            질문 : {query}

            추론과정 : {thinking}

            문서 내용 :  {context}
            """
        )
    
    def classify_node(self, state: RAGState) -> Dict[str, str]:
        """
        질문을 분류하여 처리모드를 결정합니다.
        
        Args:
            state (RAGState): 현재 상태
            
        Returns:
            Dict[str, str]: 결정된 모드
        """
        query = state['query']
        if "Docling" in query:
            print("====검색 시작====")
            return {"mode": "retrieve"}
        else:
            print("====생성 시작====")
            return {"mode": "generate"}
    
    def route_by_mode(self, state: RAGState) -> Literal["retrieve", "generate"]:
        """
        모드에 따라 다음단계를 결정합니다.
        
        Args:
            state (RAGState): 현재 상태
            
        Returns:
            Literal["retrieve", "generate"]: 다음 단계
        """
        return state["mode"]
    
    def retrieve(self, state: RAGState) -> Dict[str, Any]:
        """
        질의를 기반으로 관련 문서를 검색합니다.
        
        Args:
            state (RAGState): 현재 상태
            
        Returns:
            Dict[str, Any]: 검색된 문서
        """
        query = state["query"]
        print("====검색시작===")
        documents = self.compression_retriever.invoke(query)
        for doc in documents:
            print(doc.page_content)
            print("-"*100)
        print("===검색 완료===")
        return {"documents": documents}
    
    def reasoning(self, state: RAGState) -> RAGState:
        """추론을 수행합니다."""
        query = state["query"]
        documents = state["documents"]
        context = "\n\n".join([doc.page_content for doc in documents])
        
        reasoning_chain = self.reasoning_prompt | self.reasoning_llm | StrOutputParser()
        thinking = reasoning_chain.invoke({"query": query, "context": context})
        
        # thinking이 아닌 think로 저장 (RAGState에 정의된 대로)
        return {
            "think": thinking  # 여기를 수정
        }
    
    def generate(self, state: RAGState) -> RAGState:
        """답변을 생성합니다."""
        query = state["query"]
        thinking = state["think"]  # 여기를 수정 (thinking -> think)
        documents = state["documents"]
        context = "\n\n".join([doc.page_content for doc in documents])
        
        print("====답변 생성 시작====")
        answer_chain = self.answer_prompt | self.answer_llm | StrOutputParser()
        answer = answer_chain.invoke({
            "query": query,
            "thinking": thinking,
            "context": context
        })
        
        print("====답변 생성 완료====")
        return {
            "answer": answer,
            "message": [HumanMessage(content=answer)]
        }
    
    def create_graph(self) -> StateGraph:
        """
        RAG 처리 그래프를 생성합니다.
        
        Returns:
            StateGraph: 생성된 처리 그래프
        """
        workflow = StateGraph(RAGState)
        
        # 노드 추가
        workflow.add_node("classifier", self.classify_node)
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("reasoning", self.reasoning)
        workflow.add_node("generate", self.generate)
        
        # 엣지 설정
        workflow.set_entry_point("classifier")
        workflow.add_conditional_edges(
            "classifier",
            self.route_by_mode,
            {
                "retrieve": "retrieve",
                "generate": "generate"
            }
        )
        workflow.add_edge("retrieve", "reasoning")
        workflow.add_edge("reasoning", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()

# 사용 예시:
"""
from llm_config import reasoning_llm, answer_llm
from compression_retriever_config import default_compression_retriever

rag_processor = RAGProcessor(
    compression_retriever=default_compression_retriever,
    reasoning_llm=reasoning_llm,
    answer_llm=answer_llm
)

graph = rag_processor.create_graph()
result = graph.invoke({
    "query": "사용자 질문",
    "think": "",
    "documents": [],
    "answer": "",
    "message": [],
    "mode": ""
})
""" 