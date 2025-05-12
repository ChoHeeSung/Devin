
"""
교통 보고서 생성 및 시각화 Agent 메인 모듈
작성일: 2025-05-12
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd

from config import get_config, REPORT_DIR, DATA_DIR, LOG_DIR
from database.oracle_connector import OracleConnector
from data_processing.data_loader import TrafficDataLoader
from data_processing.data_preprocessor import TrafficDataPreprocessor
from visualization.plot_generator import TrafficPlotGenerator
from report_generation.report_generator import TrafficReportGenerator
from llm_integration.llm_config import TrafficLLMProcessor
from memory_management.memory_manager import TrafficMemoryManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f"traffic_report_{datetime.now().strftime('%Y%m%d')}.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TrafficReportAgent:
    """교통 보고서 생성 및 시각화 Agent"""
    
    def __init__(self):
        """
        교통 보고서 Agent를 초기화합니다.
        """
        logger.info("교통 보고서 Agent를 초기화합니다.")
        
        self.db_connector = OracleConnector()
        self.data_loader = TrafficDataLoader()
        self.preprocessor = TrafficDataPreprocessor()
        self.plot_generator = TrafficPlotGenerator()
        self.report_generator = TrafficReportGenerator()
        self.llm_processor = TrafficLLMProcessor()
        self.memory_manager = TrafficMemoryManager()
    
    def process_natural_language_request(self, query: str) -> Dict[str, Any]:
        """
        자연어 요청을 처리합니다.
        
        Args:
            query (str): 사용자 자연어 요청
            
        Returns:
            Dict[str, Any]: 처리 결과
        """
        logger.info(f"자연어 요청을 처리합니다: {query}")
        
        query_info = self.llm_processor.process_query(query)
        
        report_type = query_info.get("report_type", "daily")
        
        date_range = query_info.get("date_range", {})
        
        region = query_info.get("region", "전체")
        
        sections = query_info.get("sections", [])
        
        additional_info = query_info.get("additional_info", "")
        
        result = self.generate_report(
            report_type=report_type,
            date_range=date_range,
            region=region,
            sections=sections,
            additional_info=additional_info
        )
        
        return {
            "query": query,
            "query_info": query_info,
            "result": result
        }
    
    def generate_report(self, report_type: str, date_range: Dict[str, str],
                       region: str = "전체", sections: List[str] = [],
                       additional_info: str = "") -> Dict[str, Any]:
        """
        보고서를 생성합니다.
        
        Args:
            report_type (str): 보고서 유형 (daily, weekly, monthly, custom)
            date_range (Dict[str, str]): 날짜 범위
            region (str): 지역
            sections (List[str]): 포함할 섹션 목록
            additional_info (str): 추가 정보
            
        Returns:
            Dict[str, Any]: 생성된 보고서 정보
        """
        logger.info(f"{report_type} 보고서 생성을 시작합니다.")
        
        df = self._load_data_for_report(report_type, date_range)
        
        if df.empty:
            logger.warning("보고서를 생성할 데이터가 없습니다.")
            return {"error": "데이터가 없습니다."}
        
        processed_df = self.preprocessor.preprocess_data(df)
        
        stats = self.preprocessor.calculate_statistics(processed_df)
        
        report_files = {}
        metadata = {
            "report_type": report_type,
            "date_range": date_range,
            "region": region,
            "sections": sections,
            "additional_info": additional_info,
            "stats": stats
        }
        
        if report_type == "daily":
            date = date_range.get("start_date", datetime.now().strftime("%Y%m%d"))
            
            llm_content = self.llm_processor.generate_report_content(
                report_type=report_type,
                df=processed_df,
                date_info={"date": date},
                stats=stats
            )
            
            report_files = self.report_generator.generate_daily_report(
                df=processed_df,
                date=date,
                llm_summary=llm_content
            )
        
        elif report_type == "weekly":
            start_date = date_range.get("start_date", "")
            end_date = date_range.get("end_date", "")
            
            weekday_stats = {}
            weekday_names = {
                '1': 'monday', '2': 'tuesday', '3': 'wednesday', 
                '4': 'thursday', '5': 'friday', '6': 'saturday', '7': 'sunday'
            }
            
            for weekday, name in weekday_names.items():
                if 'STAT_WEEKDAY' in processed_df.columns:
                    weekday_df = processed_df[processed_df['STAT_WEEKDAY'] == weekday]
                    if not weekday_df.empty:
                        weekday_stats[name] = self.preprocessor.calculate_statistics(weekday_df)
            
            llm_content = self.llm_processor.generate_report_content(
                report_type=report_type,
                df=processed_df,
                date_info={"start_date": start_date, "end_date": end_date},
                stats=stats,
                weekday_stats=weekday_stats
            )
            
            report_files = self.report_generator.generate_weekly_report(
                df=processed_df,
                start_date=start_date,
                end_date=end_date,
                llm_summary=llm_content
            )
        
        elif report_type == "monthly":
            if "start_date" in date_range:
                year_month = date_range["start_date"][:6]
            else:
                today = datetime.now()
                first_day_of_month = datetime(today.year, today.month, 1)
                last_month = first_day_of_month - timedelta(days=1)
                year_month = last_month.strftime("%Y%m")
            
            weekly_stats = []
            
            if 'DATE' in processed_df.columns:
                year = int(year_month[:4])
                month = int(year_month[4:])
                first_day = datetime(year, month, 1)
                
                if month == 12:
                    last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    last_day = datetime(year, month + 1, 1) - timedelta(days=1)
                
                current_date = first_day
                while current_date <= last_day:
                    week_start = current_date - timedelta(days=current_date.weekday())
                    week_end = week_start + timedelta(days=6)
                    
                    week_df = processed_df[(processed_df['DATE'] >= week_start) & (processed_df['DATE'] <= week_end)]
                    
                    if not week_df.empty:
                        week_stats = self.preprocessor.calculate_statistics(week_df)
                        weekly_stats.append({
                            "start_date": week_start.strftime("%Y년 %m월 %d일"),
                            "end_date": week_end.strftime("%Y년 %m월 %d일"),
                            **week_stats
                        })
                    
                    current_date = week_end + timedelta(days=1)
            
            llm_content = self.llm_processor.generate_report_content(
                report_type=report_type,
                df=processed_df,
                date_info={"year_month": year_month},
                stats=stats,
                weekly_stats=weekly_stats
            )
            
            report_files = self.report_generator.generate_monthly_report(
                df=processed_df,
                year_month=year_month,
                llm_summary=llm_content
            )
        
        elif report_type == "custom":
            start_date = date_range.get("start_date", "")
            end_date = date_range.get("end_date", "")
            
            title = f"사용자 정의 교통 보고서: {region}"
            
            if not sections:
                sections = ["summary", "traffic_analysis", "congestion_analysis", "recommendations"]
            
            llm_content = {}
            for section in sections:
                llm_content[section] = f"{section} 내용입니다. {additional_info}"
            
            report_files = self.report_generator.generate_custom_report(
                df=processed_df,
                title=title,
                start_date=start_date,
                end_date=end_date,
                sections=sections,
                llm_content=llm_content
            )
        
        else:
            logger.warning(f"지원하지 않는 보고서 유형입니다: {report_type}")
            return {"error": f"지원하지 않는 보고서 유형입니다: {report_type}"}
        
        report_id = self.memory_manager.store_report(
            report_type=report_type,
            report_files=report_files,
            metadata=metadata
        )
        
        logger.info(f"보고서 생성을 완료했습니다: {report_id}")
        
        return {
            "report_id": report_id,
            "report_files": report_files,
            "metadata": metadata
        }
    
    def _load_data_for_report(self, report_type: str, date_range: Dict[str, str]) -> pd.DataFrame:
        """
        보고서에 필요한 데이터를 로드합니다.
        
        Args:
            report_type (str): 보고서 유형 (daily, weekly, monthly, custom)
            date_range (Dict[str, str]): 날짜 범위
            
        Returns:
            pd.DataFrame: 로드된 데이터
        """
        if report_type == "daily":
            date = date_range.get("start_date", None)
            return self.data_loader.load_daily_data(date)
        
        elif report_type == "weekly":
            end_date = date_range.get("end_date", None)
            return self.data_loader.load_weekly_data(end_date)
        
        elif report_type == "monthly":
            if "start_date" in date_range:
                year_month = date_range["start_date"][:6]
            else:
                year_month = None
            return self.data_loader.load_monthly_data(year_month)
        
        elif report_type == "custom":
            start_date = date_range.get("start_date", "")
            end_date = date_range.get("end_date", "")
            
            if start_date and end_date:
                return self.data_loader.load_custom_period_data(start_date, end_date)
            else:
                logger.warning("사용자 정의 보고서에 필요한 날짜 범위가 없습니다.")
                return pd.DataFrame()
        
        else:
            logger.warning(f"지원하지 않는 보고서 유형입니다: {report_type}")
            return pd.DataFrame()
    
    def store_feedback(self, report_id: str, rating: int, comment: str = "") -> bool:
        """
        사용자 피드백을 저장합니다.
        
        Args:
            report_id (str): 보고서 ID
            rating (int): 평점 (1-5)
            comment (str): 코멘트
            
        Returns:
            bool: 성공 여부
        """
        feedback = {
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.memory_manager.store_feedback(report_id, feedback)
    
    def apply_feedback_improvements(self) -> Dict[str, Any]:
        """
        피드백을 기반으로 개선 사항을 적용합니다.
        
        Returns:
            Dict[str, Any]: 개선 적용 결과
        """
        return self.memory_manager.apply_feedback_improvements()
    
    def search_reports(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        보고서를 검색합니다.
        
        Args:
            query (Dict[str, Any]): 검색 쿼리
            
        Returns:
            List[Dict[str, Any]]: 검색 결과
        """
        return self.memory_manager.search_reports(query)
    
    def get_report(self, report_id: str) -> Dict[str, Any]:
        """
        보고서 정보를 조회합니다.
        
        Args:
            report_id (str): 보고서 ID
            
        Returns:
            Dict[str, Any]: 보고서 정보
        """
        return self.memory_manager.get_report(report_id)


def parse_args():
    """
    명령행 인수를 파싱합니다.
    
    Returns:
        argparse.Namespace: 파싱된 인수
    """
    parser = argparse.ArgumentParser(description="교통 보고서 생성 및 시각화 Agent")
    
    subparsers = parser.add_subparsers(dest="command", help="명령")
    
    query_parser = subparsers.add_parser("query", help="자연어 요청 처리")
    query_parser.add_argument("text", help="자연어 요청 텍스트")
    
    report_parser = subparsers.add_parser("report", help="보고서 생성")
    report_parser.add_argument("--type", choices=["daily", "weekly", "monthly", "custom"], default="daily", help="보고서 유형")
    report_parser.add_argument("--start-date", help="시작 날짜 (YYYYMMDD)")
    report_parser.add_argument("--end-date", help="종료 날짜 (YYYYMMDD)")
    report_parser.add_argument("--region", default="전체", help="지역")
    
    feedback_parser = subparsers.add_parser("feedback", help="피드백 저장")
    feedback_parser.add_argument("report_id", help="보고서 ID")
    feedback_parser.add_argument("--rating", type=int, choices=range(1, 6), required=True, help="평점 (1-5)")
    feedback_parser.add_argument("--comment", default="", help="코멘트")
    
    search_parser = subparsers.add_parser("search", help="보고서 검색")
    search_parser.add_argument("--type", choices=["daily", "weekly", "monthly", "custom"], help="보고서 유형")
    search_parser.add_argument("--start-date", help="시작 날짜 (YYYYMMDD)")
    search_parser.add_argument("--end-date", help="종료 날짜 (YYYYMMDD)")
    search_parser.add_argument("--region", help="지역")
    
    subparsers.add_parser("improve", help="피드백 기반 개선 사항 적용")
    
    return parser.parse_args()


def main():
    """
    메인 함수
    """
    args = parse_args()
    
    agent = TrafficReportAgent()
    
    if args.command == "query":
        result = agent.process_natural_language_request(args.text)
        print(f"처리 결과: {result}")
    
    elif args.command == "report":
        date_range = {}
        if args.start_date:
            date_range["start_date"] = args.start_date
        if args.end_date:
            date_range["end_date"] = args.end_date
        
        result = agent.generate_report(
            report_type=args.type,
            date_range=date_range,
            region=args.region
        )
        print(f"보고서 생성 결과: {result}")
    
    elif args.command == "feedback":
        result = agent.store_feedback(
            report_id=args.report_id,
            rating=args.rating,
            comment=args.comment
        )
        print(f"피드백 저장 결과: {result}")
    
    elif args.command == "search":
        query = {}
        if args.type:
            query["type"] = args.type
        
        if args.start_date or args.end_date:
            query["date_range"] = {}
            if args.start_date:
                query["date_range"]["start_date"] = args.start_date
            if args.end_date:
                query["date_range"]["end_date"] = args.end_date
        
        if args.region:
            query["region"] = args.region
        
        results = agent.search_reports(query)
        print(f"검색 결과: {results}")
    
    elif args.command == "improve":
        result = agent.apply_feedback_improvements()
        print(f"개선 사항 적용 결과: {result}")
    
    else:
        print("명령을 지정해주세요. 도움말을 보려면 --help 옵션을 사용하세요.")


if __name__ == "__main__":
    main()
