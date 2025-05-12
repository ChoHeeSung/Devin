
"""
메모리 관리 모듈
작성일: 2025-05-12
"""

import os
import logging
import json
import shutil
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
import pandas as pd
from ..config import get_config, REPORT_DIR

logger = logging.getLogger(__name__)

class TrafficMemoryManager:
    """교통 보고서 메모리 관리를 담당하는 클래스"""
    
    def __init__(self):
        """
        메모리 관리자를 초기화합니다.
        """
        self.report_dir = REPORT_DIR
        self.memory_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory")
        self.report_index_file = os.path.join(self.memory_dir, "report_index.json")
        self.feedback_file = os.path.join(self.memory_dir, "user_feedback.json")
        
        os.makedirs(self.memory_dir, exist_ok=True)
        
        self._initialize_files()
    
    def _initialize_files(self):
        """
        인덱스 및 피드백 파일을 초기화합니다.
        """
        if not os.path.exists(self.report_index_file):
            with open(self.report_index_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            logger.info(f"보고서 인덱스 파일을 생성했습니다: {self.report_index_file}")
        
        if not os.path.exists(self.feedback_file):
            with open(self.feedback_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            logger.info(f"사용자 피드백 파일을 생성했습니다: {self.feedback_file}")
    
    def store_report(self, report_type: str, report_files: Dict[str, str], 
                    metadata: Dict[str, Any]) -> str:
        """
        생성된 보고서를 저장하고 인덱싱합니다.
        
        Args:
            report_type (str): 보고서 유형 (daily, weekly, monthly, custom)
            report_files (Dict[str, str]): 보고서 파일 경로 (markdown, pdf)
            metadata (Dict[str, Any]): 보고서 메타데이터
            
        Returns:
            str: 보고서 ID
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        report_id = f"{report_type}_{timestamp}"
        
        report_storage_dir = os.path.join(self.memory_dir, "reports", report_id)
        os.makedirs(report_storage_dir, exist_ok=True)
        
        stored_files = {}
        for file_type, file_path in report_files.items():
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                dest_path = os.path.join(report_storage_dir, filename)
                shutil.copy2(file_path, dest_path)
                stored_files[file_type] = dest_path
                logger.info(f"보고서 파일을 복사했습니다: {file_path} -> {dest_path}")
        
        metadata_file = os.path.join(report_storage_dir, "metadata.json")
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        report_entry = {
            "id": report_id,
            "type": report_type,
            "created_at": datetime.now().isoformat(),
            "files": stored_files,
            "metadata": metadata
        }
        
        with open(self.report_index_file, "r", encoding="utf-8") as f:
            report_index = json.load(f)
        
        report_index.append(report_entry)
        
        with open(self.report_index_file, "w", encoding="utf-8") as f:
            json.dump(report_index, f, ensure_ascii=False, indent=2)
        
        logger.info(f"보고서를 인덱싱했습니다: {report_id}")
        return report_id
    
    def store_feedback(self, report_id: str, feedback: Dict[str, Any]) -> bool:
        """
        사용자 피드백을 저장합니다.
        
        Args:
            report_id (str): 보고서 ID
            feedback (Dict[str, Any]): 사용자 피드백
            
        Returns:
            bool: 성공 여부
        """
        feedback_entry = {
            "id": f"feedback_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "report_id": report_id,
            "created_at": datetime.now().isoformat(),
            "content": feedback
        }
        
        with open(self.feedback_file, "r", encoding="utf-8") as f:
            feedback_list = json.load(f)
        
        feedback_list.append(feedback_entry)
        
        with open(self.feedback_file, "w", encoding="utf-8") as f:
            json.dump(feedback_list, f, ensure_ascii=False, indent=2)
        
        logger.info(f"사용자 피드백을 저장했습니다: {report_id}")
        return True
    
    def get_report(self, report_id: str) -> Dict[str, Any]:
        """
        보고서 정보를 조회합니다.
        
        Args:
            report_id (str): 보고서 ID
            
        Returns:
            Dict[str, Any]: 보고서 정보
        """
        with open(self.report_index_file, "r", encoding="utf-8") as f:
            report_index = json.load(f)
        
        for report in report_index:
            if report["id"] == report_id:
                return report
        
        logger.warning(f"보고서를 찾을 수 없습니다: {report_id}")
        return {}
    
    def search_reports(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        보고서를 검색합니다.
        
        Args:
            query (Dict[str, Any]): 검색 쿼리
            
        Returns:
            List[Dict[str, Any]]: 검색 결과
        """
        with open(self.report_index_file, "r", encoding="utf-8") as f:
            report_index = json.load(f)
        
        results = []
        
        for report in report_index:
            match = True
            
            if "type" in query and report["type"] != query["type"]:
                match = False
            
            if "date_range" in query:
                report_date = datetime.fromisoformat(report["created_at"]).date()
                
                if "start_date" in query["date_range"]:
                    start_date = datetime.strptime(query["date_range"]["start_date"], "%Y%m%d").date()
                    if report_date < start_date:
                        match = False
                
                if "end_date" in query["date_range"]:
                    end_date = datetime.strptime(query["date_range"]["end_date"], "%Y%m%d").date()
                    if report_date > end_date:
                        match = False
            
            if "region" in query and "metadata" in report and "region" in report["metadata"]:
                if report["metadata"]["region"] != query["region"]:
                    match = False
            
            if match:
                results.append(report)
        
        return results
    
    def get_feedback_for_report(self, report_id: str) -> List[Dict[str, Any]]:
        """
        특정 보고서에 대한 피드백을 조회합니다.
        
        Args:
            report_id (str): 보고서 ID
            
        Returns:
            List[Dict[str, Any]]: 피드백 목록
        """
        with open(self.feedback_file, "r", encoding="utf-8") as f:
            feedback_list = json.load(f)
        
        return [feedback for feedback in feedback_list if feedback["report_id"] == report_id]
    
    def analyze_feedback(self) -> Dict[str, Any]:
        """
        사용자 피드백을 분석합니다.
        
        Returns:
            Dict[str, Any]: 피드백 분석 결과
        """
        with open(self.feedback_file, "r", encoding="utf-8") as f:
            feedback_list = json.load(f)
        
        if not feedback_list:
            return {"message": "분석할 피드백이 없습니다."}
        
        feedback_data = []
        for feedback in feedback_list:
            if "content" in feedback and "rating" in feedback["content"]:
                feedback_data.append({
                    "report_id": feedback["report_id"],
                    "created_at": feedback["created_at"],
                    "rating": feedback["content"]["rating"],
                    "comment": feedback["content"].get("comment", "")
                })
        
        if not feedback_data:
            return {"message": "분석할 평점 데이터가 없습니다."}
        
        df = pd.DataFrame(feedback_data)
        df["created_at"] = pd.to_datetime(df["created_at"])
        
        avg_rating = df["rating"].mean()
        rating_counts = df["rating"].value_counts().to_dict()
        
        df["month"] = df["created_at"].dt.strftime("%Y-%m")
        monthly_ratings = df.groupby("month")["rating"].mean().to_dict()
        
        report_types = []
        for idx, row in df.iterrows():
            report = self.get_report(row["report_id"])
            report_type = report.get("type", "unknown") if report else "unknown"
            report_types.append(report_type)
        
        df["report_type"] = report_types
        type_ratings = df.groupby("report_type")["rating"].mean().to_dict()
        
        return {
            "average_rating": avg_rating,
            "rating_distribution": rating_counts,
            "monthly_trend": monthly_ratings,
            "report_type_ratings": type_ratings,
            "total_feedback_count": len(df),
            "recent_comments": df.sort_values("created_at", ascending=False).head(5)["comment"].tolist()
        }
    
    def apply_feedback_improvements(self) -> Dict[str, Any]:
        """
        피드백을 기반으로 개선 사항을 적용합니다.
        
        Returns:
            Dict[str, Any]: 개선 적용 결과
        """
        analysis = self.analyze_feedback()
        
        if "message" in analysis:
            return {"message": analysis["message"], "improvements": []}
        
        improvements = []
        
        if "report_type_ratings" in analysis:
            type_ratings = analysis["report_type_ratings"]
            for report_type, rating in type_ratings.items():
                if rating < 3.0:
                    improvements.append({
                        "target": f"{report_type} 보고서",
                        "issue": f"평균 평점이 낮습니다 ({rating:.1f}/5.0)",
                        "action": f"{report_type} 보고서 템플릿 및 내용 개선 필요"
                    })
        
        if "recent_comments" in analysis:
            for comment in analysis["recent_comments"]:
                if comment and len(comment) > 10:
                    if "시각화" in comment or "그래프" in comment or "차트" in comment:
                        improvements.append({
                            "target": "시각화",
                            "issue": "시각화 관련 피드백",
                            "action": "시각화 개선 필요",
                            "comment": comment
                        })
                    elif "내용" in comment or "분석" in comment or "설명" in comment:
                        improvements.append({
                            "target": "보고서 내용",
                            "issue": "내용 관련 피드백",
                            "action": "보고서 내용 개선 필요",
                            "comment": comment
                        })
        
        improvements_file = os.path.join(self.memory_dir, "improvements.json")
        with open(improvements_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis,
                "improvements": improvements
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"피드백 기반 개선 사항을 저장했습니다: {improvements_file}")
        
        return {
            "analysis": analysis,
            "improvements": improvements
        }
