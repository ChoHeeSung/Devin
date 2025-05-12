#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
문서 저장 모듈
작성일: 2024-03-21
"""

import os
from typing import List
from langchain_core.documents import Document
from IPython.display import Markdown, display

class DocumentSaver:
    """문서 저장을 관리하는 클래스"""
    
    def __init__(self, save_dir: str = "/Users/heesung/work/M_CHO/vds-server/documents"):
        """
        문서 저장 관리자를 초기화합니다.

        Args:
            save_dir (str): 문서를 저장할 디렉토리 경로
        """
        self.save_dir = save_dir
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self) -> None:
        """저장 디렉토리가 존재하지 않으면 생성합니다."""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
    def display_markdown(self, document: Document) -> None:
        """
        문서를 마크다운 형식으로 출력합니다.
        
        Args:
            document (Document): 출력할 문서
        """
        display(Markdown(document.page_content))
    
    def save_to_markdown(self, document: Document, original_file_path: str) -> str:
        """
        문서를 마크다운 파일로 저장합니다.
        
        Args:
            document (Document): 저장할 문서
            original_file_path (str): 원본 파일 경로
            
        Returns:
            str: 저장된 파일의 경로
        """
        # 파일명 생성 (원본 PDF 파일명 기반)
        file_name = os.path.splitext(os.path.basename(original_file_path))[0] + ".md"
        save_path = os.path.join(self.save_dir, file_name)
        
        # 마크다운 파일로 저장
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(document.page_content)
            
        print(f"문서가 다음 경로에 저장되었습니다: {save_path}")
        return save_path
    
    def save_multiple_documents(self, documents: List[Document], original_file_path: str) -> List[str]:
        """
        여러 문서를 마크다운 파일로 저장합니다.
        
        Args:
            documents (List[Document]): 저장할 문서 리스트
            original_file_path (str): 원본 파일 경로
            
        Returns:
            List[str]: 저장된 파일들의 경로 리스트
        """
        saved_paths = []
        for i, doc in enumerate(documents):
            base_name = os.path.splitext(os.path.basename(original_file_path))[0]
            file_name = f"{base_name}_part_{i+1}.md"
            save_path = os.path.join(self.save_dir, file_name)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(doc.page_content)
                
            saved_paths.append(save_path)
            
        print(f"총 {len(saved_paths)}개의 문서가 저장되었습니다.")
        return saved_paths

# 기본 저장 관리자 인스턴스 생성
default_saver = DocumentSaver() 