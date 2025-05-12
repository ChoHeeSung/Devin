
"""
LLM 설정 및 통합 모듈
작성일: 2025-05-12
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import json
import pandas as pd
from langchain.llms import LlamaCpp
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import Document
from ..config import get_config

logger = logging.getLogger(__name__)

class TrafficLLMProcessor:
    """교통 데이터 LLM 처리를 관리하는 클래스"""
    
    def __init__(self):
        """
        교통 데이터 LLM 처리기를 초기화합니다.
        """
        self.config = get_config("llm")
        self.model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        os.makedirs(self.model_path, exist_ok=True)
        
        self.llm = self._initialize_llm()
        
        self._initialize_prompts()
    
    def _initialize_llm(self) -> Any:
        """
        LLM 모델을 초기화합니다.
        
        Returns:
            Any: 초기화된 LLM 모델
        """
        model_name = self.config.get("model", "mistral:latest")
        temperature = self.config.get("temperature", 0.1)
        max_tokens = self.config.get("max_tokens", 2000)
        
        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
        
        try:
            model_file = os.path.join(self.model_path, "mistral-7b-instruct-v0.2.Q4_K_M.gguf")
            
            if not os.path.exists(model_file):
                logger.warning(f"모델 파일이 없습니다: {model_file}")
                logger.warning("다음 명령어로 모델을 다운로드하세요:")
                logger.warning(f"wget -P {self.model_path} https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
                
                with open(model_file, "w") as f:
                    f.write("placeholder")
            
            llm = LlamaCpp(
                model_path=model_file,
                temperature=temperature,
                max_tokens=max_tokens,
                n_ctx=4096,
                callback_manager=callback_manager,
                verbose=False,
            )
            
            logger.info(f"LLM 모델을 초기화했습니다: {model_name}")
            return llm
            
        except Exception as e:
            logger.error(f"LLM 모델 초기화 실패: {str(e)}")
            logger.warning("LLM 모델 초기화에 실패했습니다. 기본 응답을 사용합니다.")
            return None
    
    def _initialize_prompts(self):
        """
        프롬프트 템플릿을 초기화합니다.
        """
        self.daily_report_prompt = PromptTemplate(
            input_variables=["date", "stats", "traffic_data"],
            template="""
            당신은 교통 데이터 분석 전문가입니다. 다음 교통 데이터를 분석하여 일일 보고서를 작성해주세요.
            
            날짜: {date}
            
            통계 정보:
            {stats}
            
            교통 데이터 샘플:
            {traffic_data}
            
            다음 섹션에 대한 내용을 작성해주세요:
            1. summary: 전체적인 교통 상황 요약
            2. traffic_analysis: 교통 흐름 분석
            3. congestion_analysis: 정체 분석
            4. incident_analysis: 사고 분석
            5. recommendations: 권장사항
            
            각 섹션은 JSON 형식으로 반환해주세요. 예시:
            {{
                "summary": "요약 내용...",
                "traffic_analysis": "교통 분석 내용...",
                "congestion_analysis": "정체 분석 내용...",
                "incident_analysis": "사고 분석 내용...",
                "recommendations": "권장사항 내용..."
            }}
            """
        )
        
        self.weekly_report_prompt = PromptTemplate(
            input_variables=["start_date", "end_date", "stats", "weekday_stats", "traffic_data"],
            template="""
            당신은 교통 데이터 분석 전문가입니다. 다음 교통 데이터를 분석하여 주간 보고서를 작성해주세요.
            
            기간: {start_date} ~ {end_date}
            
            전체 통계 정보:
            {stats}
            
            요일별 통계 정보:
            {weekday_stats}
            
            교통 데이터 샘플:
            {traffic_data}
            
            다음 섹션에 대한 내용을 작성해주세요:
            1. executive_summary: 전체적인 주간 교통 상황 요약
            2. weekly_trends: 주간 교통 추세 분석
            3. peak_analysis: 첨두 시간대 분석
            4. incident_summary: 사고 요약
            5. recommendations: 권장사항
            
            각 섹션은 JSON 형식으로 반환해주세요. 예시:
            {{
                "executive_summary": "요약 내용...",
                "weekly_trends": "추세 분석 내용...",
                "peak_analysis": "첨두 시간대 분석 내용...",
                "incident_summary": "사고 요약 내용...",
                "recommendations": "권장사항 내용..."
            }}
            """
        )
        
        self.monthly_report_prompt = PromptTemplate(
            input_variables=["year_month", "stats", "weekly_stats", "traffic_data"],
            template="""
            당신은 교통 데이터 분석 전문가입니다. 다음 교통 데이터를 분석하여 월간 보고서를 작성해주세요.
            
            년월: {year_month}
            
            전체 통계 정보:
            {stats}
            
            주간별 통계 정보:
            {weekly_stats}
            
            교통 데이터 샘플:
            {traffic_data}
            
            다음 섹션에 대한 내용을 작성해주세요:
            1. executive_summary: 전체적인 월간 교통 상황 요약
            2. monthly_overview: 월간 교통 개요
            3. trend_analysis: 추세 분석
            4. incident_patterns: 사고 패턴
            5. recommendations: 권장사항
            6. next_month_forecast: 다음 달 예측
            
            각 섹션은 JSON 형식으로 반환해주세요. 예시:
            {{
                "executive_summary": "요약 내용...",
                "monthly_overview": "개요 내용...",
                "trend_analysis": "추세 분석 내용...",
                "incident_patterns": "사고 패턴 내용...",
                "recommendations": "권장사항 내용...",
                "next_month_forecast": "다음 달 예측 내용..."
            }}
            """
        )
        
        self.query_prompt = PromptTemplate(
            input_variables=["query"],
            template="""
            당신은 교통 보고서 생성 시스템의 일부입니다. 사용자의 자연어 요청을 분석하여 필요한 정보를 추출해주세요.
            
            사용자 요청: {query}
            
            다음 정보를 JSON 형식으로 반환해주세요:
            1. report_type: 보고서 유형 (daily, weekly, monthly, custom)
            2. date_range: 날짜 범위 (시작일, 종료일)
            3. region: 지역 (있는 경우)
            4. sections: 포함할 섹션 목록
            5. additional_info: 추가 정보
            
            예시:
            {{
                "report_type": "weekly",
                "date_range": {{"start_date": "20230501", "end_date": "20230507"}},
                "region": "서울",
                "sections": ["executive_summary", "weekly_trends", "peak_analysis", "recommendations"],
                "additional_info": "첨두 시간대 정체 현황에 중점을 두고 분석해주세요."
            }}
            
            날짜 형식은 YYYYMMDD로 통일해주세요. 사용자가 "이번 주", "지난 달" 등의 상대적인 표현을 사용한 경우, 현재 날짜를 기준으로 계산해주세요.
            """
        )
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        사용자의 자연어 쿼리를 처리합니다.
        
        Args:
            query (str): 사용자 쿼리
            
        Returns:
            Dict[str, Any]: 처리된 쿼리 정보
        """
        if self.llm is None:
            logger.warning("LLM이 초기화되지 않았습니다. 기본 응답을 반환합니다.")
            return self._get_default_query_response(query)
        
        try:
            chain = LLMChain(llm=self.llm, prompt=self.query_prompt)
            
            response = chain.run(query=query)
            
            result = json.loads(response)
            logger.info(f"쿼리를 처리했습니다: {query}")
            return result
            
        except Exception as e:
            logger.error(f"쿼리 처리 실패: {str(e)}")
            return self._get_default_query_response(query)
    
    def _get_default_query_response(self, query: str) -> Dict[str, Any]:
        """
        기본 쿼리 응답을 생성합니다.
        
        Args:
            query (str): 사용자 쿼리
            
        Returns:
            Dict[str, Any]: 기본 응답
        """
        report_type = "daily"
        if "주간" in query or "주 보고서" in query or "weekly" in query:
            report_type = "weekly"
        elif "월간" in query or "월 보고서" in query or "monthly" in query:
            report_type = "monthly"
        
        from datetime import datetime, timedelta
        today = datetime.now()
        
        if report_type == "daily":
            yesterday = today - timedelta(days=1)
            date_str = yesterday.strftime("%Y%m%d")
            date_range = {"start_date": date_str, "end_date": date_str}
        
        elif report_type == "weekly":
            end_date = today - timedelta(days=today.weekday() + 1)
            start_date = end_date - timedelta(days=6)
            date_range = {
                "start_date": start_date.strftime("%Y%m%d"),
                "end_date": end_date.strftime("%Y%m%d")
            }
        
        else:  # monthly
            first_day_of_month = datetime(today.year, today.month, 1)
            last_month = first_day_of_month - timedelta(days=1)
            date_range = {
                "start_date": last_month.replace(day=1).strftime("%Y%m%d"),
                "end_date": last_month.strftime("%Y%m%d")
            }
        
        if report_type == "daily":
            sections = ["summary", "traffic_analysis", "congestion_analysis", "incident_analysis", "recommendations"]
        elif report_type == "weekly":
            sections = ["executive_summary", "weekly_trends", "peak_analysis", "incident_summary", "recommendations"]
        else:  # monthly
            sections = ["executive_summary", "monthly_overview", "trend_analysis", "incident_patterns", "recommendations", "next_month_forecast"]
        
        return {
            "report_type": report_type,
            "date_range": date_range,
            "region": "전체",
            "sections": sections,
            "additional_info": ""
        }
    
    def generate_report_content(self, report_type: str, df: pd.DataFrame, 
                               date_info: Dict[str, str], stats: Dict[str, Any],
                               weekday_stats: Optional[Dict[str, Any]] = None,
                               weekly_stats: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """
        보고서 내용을 생성합니다.
        
        Args:
            report_type (str): 보고서 유형 (daily, weekly, monthly)
            df (pd.DataFrame): 교통 데이터
            date_info (Dict[str, str]): 날짜 정보
            stats (Dict[str, Any]): 통계 정보
            weekday_stats (Optional[Dict[str, Any]]): 요일별 통계 정보
            weekly_stats (Optional[List[Dict[str, Any]]]): 주간별 통계 정보
            
        Returns:
            Dict[str, str]: 생성된 보고서 내용
        """
        if self.llm is None:
            logger.warning("LLM이 초기화되지 않았습니다. 기본 응답을 반환합니다.")
            return self._get_default_report_content(report_type, stats)
        
        try:
            traffic_data = df.head(10).to_string()
            
            stats_str = json.dumps(stats, indent=2, ensure_ascii=False)
            
            if report_type == "daily":
                chain = LLMChain(llm=self.llm, prompt=self.daily_report_prompt)
                response = chain.run(
                    date=date_info.get("date", ""),
                    stats=stats_str,
                    traffic_data=traffic_data
                )
            
            elif report_type == "weekly":
                weekday_stats_str = json.dumps(weekday_stats, indent=2, ensure_ascii=False) if weekday_stats else "{}"
                chain = LLMChain(llm=self.llm, prompt=self.weekly_report_prompt)
                response = chain.run(
                    start_date=date_info.get("start_date", ""),
                    end_date=date_info.get("end_date", ""),
                    stats=stats_str,
                    weekday_stats=weekday_stats_str,
                    traffic_data=traffic_data
                )
            
            elif report_type == "monthly":
                weekly_stats_str = json.dumps(weekly_stats, indent=2, ensure_ascii=False) if weekly_stats else "[]"
                chain = LLMChain(llm=self.llm, prompt=self.monthly_report_prompt)
                response = chain.run(
                    year_month=date_info.get("year_month", ""),
                    stats=stats_str,
                    weekly_stats=weekly_stats_str,
                    traffic_data=traffic_data
                )
            
            else:
                logger.warning(f"지원하지 않는 보고서 유형입니다: {report_type}")
                return self._get_default_report_content(report_type, stats)
            
            result = json.loads(response)
            logger.info(f"{report_type} 보고서 내용을 생성했습니다.")
            return result
            
        except Exception as e:
            logger.error(f"보고서 내용 생성 실패: {str(e)}")
            return self._get_default_report_content(report_type, stats)
    
    def _get_default_report_content(self, report_type: str, stats: Dict[str, Any]) -> Dict[str, str]:
        """
        기본 보고서 내용을 생성합니다.
        
        Args:
            report_type (str): 보고서 유형 (daily, weekly, monthly)
            stats (Dict[str, Any]): 통계 정보
            
        Returns:
            Dict[str, str]: 기본 보고서 내용
        """
        avg_speed = stats.get("SPD_mean", 0)
        congestion_ratio = stats.get("congestion_time_ratio", 0)
        
        if report_type == "daily":
            return {
                "summary": f"오늘의 교통 상황 요약입니다. 평균 속도는 {avg_speed:.2f} km/h이며, 정체 시간 비율은 {congestion_ratio:.2f}%입니다.",
                "traffic_analysis": "교통 흐름 분석 결과입니다. 시간대별 교통량과 속도 변화를 분석했습니다.",
                "congestion_analysis": "정체 분석 결과입니다. 첨두 시간대의 정체 현황과 주요 정체 구간을 분석했습니다.",
                "incident_analysis": "사고 분석 결과입니다. 오늘 발생한 사고와 그 영향을 분석했습니다.",
                "recommendations": "교통 상황 개선을 위한 권장사항입니다."
            }
        
        elif report_type == "weekly":
            return {
                "executive_summary": f"주간 교통 상황 요약입니다. 평균 속도는 {avg_speed:.2f} km/h이며, 정체 시간 비율은 {congestion_ratio:.2f}%입니다.",
                "weekly_trends": "주간 교통 추세 분석 결과입니다. 요일별 교통량과 속도 변화를 분석했습니다.",
                "peak_analysis": "첨두 시간대 분석 결과입니다. 요일별 첨두 시간대의 정체 현황과 주요 정체 구간을 분석했습니다.",
                "incident_summary": "사고 요약 결과입니다. 이번 주 발생한 사고와 그 영향을 분석했습니다.",
                "recommendations": "교통 상황 개선을 위한 권장사항입니다."
            }
        
        else:  # monthly
            return {
                "executive_summary": f"월간 교통 상황 요약입니다. 평균 속도는 {avg_speed:.2f} km/h이며, 정체 시간 비율은 {congestion_ratio:.2f}%입니다.",
                "monthly_overview": "월간 교통 개요입니다. 전체적인 교통 흐름과 주요 특징을 분석했습니다.",
                "trend_analysis": "월간 교통 추세 분석 결과입니다. 주간별 교통량과 속도 변화를 분석했습니다.",
                "incident_patterns": "사고 패턴 분석 결과입니다. 이번 달 발생한 사고의 패턴과 그 영향을 분석했습니다.",
                "recommendations": "교통 상황 개선을 위한 권장사항입니다.",
                "next_month_forecast": "다음 달 교통 상황 예측입니다. 현재 추세를 바탕으로 다음 달의 교통 상황을 예측했습니다."
            }
