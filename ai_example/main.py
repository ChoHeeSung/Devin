#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAG 시스템 메인 실행 파일
작성일: 2024-03-21
"""

import os
from typing import Dict, Any
from document_loader import DocumentLoaderSetup
from document_splitter import DocumentSplitter
from embedding_config import EmbeddingSetup
from vector_store_config import VectorStoreSetup
from compression_retriever_config import CompressionRetrieverSetup
from rag_processor import RAGProcessor
from workflow_config import WorkflowSetup
from llm_config import LLMSetup
import signal
import sys
import subprocess
import atexit

class RAGSystem:
    """RAG 시스템을 관리하는 클래스"""
    
    def __init__(self, pdf_path: str):
        """
        RAG 시스템을 초기화합니다.
        
        Args:
            pdf_path (str): PDF 문서 경로
        """
        self.pdf_path = pdf_path
        self._initialize_components()
        
    def _initialize_components(self) -> None:
        """시스템 컴포넌트들을 초기화합니다."""
        # 문서 로더 설정
        self.doc_loader = DocumentLoaderSetup(self.pdf_path)
        
        # 문서 분할기 설정
        self.doc_splitter = DocumentSplitter()
        
        # 임베딩 설정
        self.embedding_setup = EmbeddingSetup(
            model="bge-m3:latest"
        )
        
        # LLM 설정
        self.llm_setup = LLMSetup()
        
        # 벡터 스토어 초기화를 먼저 수행
        print("문서 로딩 중...")
        docs = self.doc_loader.load_documents()
        
        print("문서 분할 중...")
        splits = self.doc_splitter.split_documents(docs)
        
        # 벡터 스토어 설정 및 초기화
        self.vector_store_setup = VectorStoreSetup(
            embedding=self.embedding_setup.embeddings,
            location=":memory:",  # 메모리에 저장
            collection_name="rag_collection_0228",
            search_k=10  # 검색 결과 수
        )
        print("벡터 스토어 생성 중...")
        self.vector_store_setup.create_vector_store(splits)
        
        # retriever가 초기화된 후에 압축 검색기 설정
        self.compression_setup = CompressionRetrieverSetup(
            base_retriever=self.vector_store_setup.retriever
        )
        
        # RAG 프로세서 설정
        self.rag_processor = RAGProcessor(
            compression_retriever=self.compression_setup.compression_retriever,
            reasoning_llm=self.llm_setup.get_reasoning_llm(),
            answer_llm=self.llm_setup.get_answer_llm()
        )
        
        # 워크플로우 설정
        self.workflow_setup = WorkflowSetup(
            rag_processor=self.rag_processor
        )
        
        print("시스템 초기화 완료")
    
    def initialize_system(self) -> None:
        """시스템이 이미 초기화되어 있으므로 추가 작업이 필요 없습니다."""
        pass

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        사용자 질의를 처리합니다.
        
        Args:
            query (str): 사용자 질의
            
        Returns:
            Dict[str, Any]: 처리 결과
        """
        return self.workflow_setup.process_query(query)

def check_ollama_status():
    """
    Ollama 서버가 실행 중인지 확인하고, 실행되지 않은 경우 시작합니다.
    """
    import requests
    import subprocess
    import time
    import platform

    def is_ollama_running():
        try:
            response = requests.get("http://localhost:11434/api/version")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False

    if not is_ollama_running():
        print("Ollama 서버가 실행되지 않았습니다. 시작을 시도합니다...")
        
        # 운영체제별 실행 명령어 설정
        if platform.system() == "Darwin":  # macOS
            start_cmd = "ollama serve"
        elif platform.system() == "Linux":
            start_cmd = "ollama serve"
        else:
            raise RuntimeError("지원되지 않는 운영체제입니다.")
            
        try:
            subprocess.Popen(start_cmd, shell=True)
            print("Ollama 서버 시작 중...")
            
            # 서버가 완전히 시작될 때까지 대기
            max_retries = 10
            for i in range(max_retries):
                if is_ollama_running():
                    print("Ollama 서버가 성공적으로 시작되었습니다.")
                    break
                if i == max_retries - 1:
                    raise RuntimeError("Ollama 서버 시작 시간이 초과되었습니다.")
                time.sleep(2)
        except Exception as e:
            raise RuntimeError(f"Ollama 서버 시작 중 오류 발생: {str(e)}")

def stop_ollama():
    """
    Ollama 서버를 안전하게 종료합니다.
    """
    try:
        print("\nOllama 서버를 종료합니다...")
        subprocess.run(["pkill", "ollama"], check=False)
        print("Ollama 서버가 종료되었습니다.")
    except Exception as e:
        print(f"Ollama 서버 종료 중 오류 발생: {str(e)}")

def signal_handler(signum, frame):
    """
    시그널 핸들러: Ctrl+C 등의 인터럽트 시그널 처리
    """
    print("\n프로그램 종료 신호를 받았습니다.")
    stop_ollama()
    sys.exit(0)

def main():
    """메인 함수"""
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 프로그램 종료 시 ollama 종료 함수 등록
    atexit.register(stop_ollama)
    
    try:
        # Ollama 상태 확인 및 시작
        check_ollama_status()
        
        # PDF 파일 경로 설정
        pdf_path = "/Users/heesung/work/M_CHO/vds-server/CNITS-DE-007.1-인터페이스 설계서_VDS(표준) Ver 1.0.pdf"
        
        # RAG 시스템 초기화
        print("\nRAG 시스템을 초기화하는 중입니다...")
        rag_system = RAGSystem(pdf_path)
        rag_system.initialize_system()
        
        print("\n=== RAG 시스템이 준비되었습니다 ===")
        print("질문을 입력하세요. 종료하려면 'quit' 또는 'exit'를 입력하세요.")
        
        while True:
            try:
                # 사용자 입력 받기
                query = input("\n질문> ").strip()
                
                # 종료 명령어 처리
                if query.lower() in ['quit', 'exit']:
                    print("프로그램을 종료합니다.")
                    break
                
                # 빈 입력 처리
                if not query:
                    print("질문을 입력해주세요.")
                    continue
                
                # 질의 처리
                result = rag_system.process_query(query)
                
                # 결과 출력
                print("\n=== 답변 ===")
                print(f"{result['answer']}")
                
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.")
                break
            except Exception as e:
                print(f"\n질의 처리 중 오류가 발생했습니다: {str(e)}")
                print("다시 시도해주세요.")
                continue
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    main() 