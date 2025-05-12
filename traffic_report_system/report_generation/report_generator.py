
"""
교통 보고서 생성 모듈
작성일: 2025-05-12
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd
import markdown
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
from ..config import get_config, REPORT_DIR
from ..data_processing.data_preprocessor import TrafficDataPreprocessor
from ..visualization.plot_generator import TrafficPlotGenerator

logger = logging.getLogger(__name__)

class TrafficReportGenerator:
    """교통 보고서 생성을 관리하는 클래스"""
    
    def __init__(self):
        """
        교통 보고서 생성기를 초기화합니다.
        """
        self.config = get_config("report")
        self.report_dir = REPORT_DIR
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.report_dir, exist_ok=True)
        
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        
        self.preprocessor = TrafficDataPreprocessor()
        self.plot_generator = TrafficPlotGenerator()
        
        self._create_default_templates()
    
    def _create_default_templates(self):
        """
        기본 보고서 템플릿을 생성합니다.
        """
        daily_template = """# 일일 교통 보고서: {{ date }}

{{ summary }}

{{ traffic_analysis }}

- 평균 속도: {{ stats.SPD_mean|round(2) }} km/h
- 최대 속도: {{ stats.SPD_max|round(2) }} km/h
- 최소 속도: {{ stats.SPD_min|round(2) }} km/h
- 평균 교통량: {{ stats.VOL_mean|round(2) }}
- 정체 시간 비율: {{ stats.congestion_time_ratio|round(2) }}%

{{ congestion_analysis }}

- 아침 첨두(07-09시) 평균 속도: {{ stats.SPD_mean_MORNING_PEAK|round(2) }} km/h
- 저녁 첨두(17-19시) 평균 속도: {{ stats.SPD_mean_EVENING_PEAK|round(2) }} km/h
- 비첨두 평균 속도: {{ stats.SPD_mean_NON_PEAK|round(2) }} km/h

{{ incident_analysis }}

{{ recommendations }}

![시간별 평균 속도]({{ plots.speed_trend }})
![정체 히트맵]({{ plots.congestion_heatmap }})
![교통 상태 분포]({{ plots.traffic_status_pie }})
![교통량-속도 관계]({{ plots.volume_speed_scatter }})
"""
        
        weekly_template = """# 주간 교통 보고서: {{ start_date }} ~ {{ end_date }}

{{ executive_summary }}

{{ weekly_trends }}

- 평균 속도: {{ stats.SPD_mean|round(2) }} km/h
- 최대 속도: {{ stats.SPD_max|round(2) }} km/h
- 최소 속도: {{ stats.SPD_min|round(2) }} km/h
- 평균 교통량: {{ stats.VOL_mean|round(2) }}
- 정체 시간 비율: {{ stats.congestion_time_ratio|round(2) }}%

{{ peak_analysis }}

- 월요일 아침 첨두 평균 속도: {{ weekday_stats.monday.SPD_mean_MORNING_PEAK|round(2) }} km/h
- 월요일 저녁 첨두 평균 속도: {{ weekday_stats.monday.SPD_mean_EVENING_PEAK|round(2) }} km/h
- 금요일 아침 첨두 평균 속도: {{ weekday_stats.friday.SPD_mean_MORNING_PEAK|round(2) }} km/h
- 금요일 저녁 첨두 평균 속도: {{ weekday_stats.friday.SPD_mean_EVENING_PEAK|round(2) }} km/h

{{ incident_summary }}

{{ recommendations }}

![요일별 평균 속도]({{ plots.speed_trend }})
![요일별 시간대 정체율]({{ plots.congestion_heatmap }})
![교통 상태 분포]({{ plots.traffic_status_pie }})
![교통량-속도 관계]({{ plots.volume_speed_scatter }})
"""
        
        monthly_template = """# 월간 교통 보고서: {{ year_month }}

{{ executive_summary }}

{{ monthly_overview }}

- 평균 속도: {{ stats.SPD_mean|round(2) }} km/h
- 최대 속도: {{ stats.SPD_max|round(2) }} km/h
- 최소 속도: {{ stats.SPD_min|round(2) }} km/h
- 평균 교통량: {{ stats.VOL_mean|round(2) }}
- 정체 시간 비율: {{ stats.congestion_time_ratio|round(2) }}%

{{ trend_analysis }}

{% for week in weekly_stats %}
- {{ week.start_date }} ~ {{ week.end_date }}: 평균 속도 {{ week.SPD_mean|round(2) }} km/h, 정체율 {{ week.congestion_time_ratio|round(2) }}%
{% endfor %}

{{ incident_patterns }}

{{ recommendations }}

{{ next_month_forecast }}

![일별 평균 속도 추세]({{ plots.speed_trend }})
![일별 시간대 정체율]({{ plots.congestion_heatmap }})
![교통 상태 분포]({{ plots.traffic_status_pie }})
![교통량-속도 관계]({{ plots.volume_speed_scatter }})
![월간 대시보드]({{ plots.dashboard }})
"""
        
        template_files = {
            "daily_report.md": daily_template,
            "weekly_report.md": weekly_template,
            "monthly_report.md": monthly_template
        }
        
        for filename, content in template_files.items():
            file_path = os.path.join(self.template_dir, filename)
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"템플릿 파일을 생성했습니다: {file_path}")
    
    def generate_daily_report(self, df: pd.DataFrame, date: str, 
                             llm_summary: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        일일 교통 보고서를 생성합니다.
        
        Args:
            df (pd.DataFrame): 교통 데이터
            date (str): 보고서 날짜 (YYYYMMDD)
            llm_summary (Optional[Dict[str, str]]): LLM이 생성한 요약 정보
            
        Returns:
            Dict[str, str]: 생성된 보고서 파일 경로
        """
        if df.empty:
            logger.warning("보고서를 생성할 데이터가 없습니다.")
            return {}
        
        processed_df = self.preprocessor.preprocess_data(df)
        
        stats = self.preprocessor.calculate_statistics(processed_df)
        
        plots = {
            "speed_trend": self.plot_generator.generate_speed_trend_plot(processed_df, "daily"),
            "congestion_heatmap": self.plot_generator.generate_congestion_heatmap(processed_df, "daily"),
            "traffic_status_pie": self.plot_generator.generate_traffic_status_pie(processed_df),
            "volume_speed_scatter": self.plot_generator.generate_volume_speed_scatter(processed_df),
            "dashboard": self.plot_generator.generate_dashboard(processed_df, "daily")
        }
        
        for key, path in plots.items():
            if path:
                plots[key] = os.path.relpath(path.replace(".html", ".png"), self.report_dir)
        
        date_obj = datetime.strptime(date, "%Y%m%d")
        formatted_date = date_obj.strftime("%Y년 %m월 %d일")
        
        if llm_summary is None:
            llm_summary = {
                "summary": f"{formatted_date}의 교통 상황에 대한 요약입니다. 이 날의 평균 속도는 {stats.get('SPD_mean', 0):.2f} km/h이며, 정체 시간 비율은 {stats.get('congestion_time_ratio', 0):.2f}%입니다.",
                "traffic_analysis": "교통 흐름 분석 결과입니다. 시간대별 교통량과 속도 변화를 분석했습니다.",
                "congestion_analysis": "정체 분석 결과입니다. 첨두 시간대의 정체 현황과 주요 정체 구간을 분석했습니다.",
                "incident_analysis": "사고 분석 결과입니다. 이 날 발생한 사고와 그 영향을 분석했습니다.",
                "recommendations": "교통 상황 개선을 위한 권장사항입니다."
            }
        
        template = self.env.get_template("daily_report.md")
        report_md = template.render(
            date=formatted_date,
            stats=stats,
            plots=plots,
            **llm_summary
        )
        
        md_path = os.path.join(self.report_dir, f"daily_report_{date}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        logger.info(f"일일 보고서 마크다운 파일을 생성했습니다: {md_path}")
        
        pdf_path = os.path.join(self.report_dir, f"daily_report_{date}.pdf")
        html = markdown.markdown(report_md, extensions=['tables', 'fenced_code'])
        
        for key, path in plots.items():
            if path:
                abs_path = os.path.join(self.report_dir, path)
                html = html.replace(f'src="{path}"', f'src="{abs_path}"')
        
        HTML(string=html).write_pdf(pdf_path)
        logger.info(f"일일 보고서 PDF 파일을 생성했습니다: {pdf_path}")
        
        return {
            "markdown": md_path,
            "pdf": pdf_path
        }
    
    def generate_weekly_report(self, df: pd.DataFrame, start_date: str, end_date: str,
                              llm_summary: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        주간 교통 보고서를 생성합니다.
        
        Args:
            df (pd.DataFrame): 교통 데이터
            start_date (str): 시작 날짜 (YYYYMMDD)
            end_date (str): 종료 날짜 (YYYYMMDD)
            llm_summary (Optional[Dict[str, str]]): LLM이 생성한 요약 정보
            
        Returns:
            Dict[str, str]: 생성된 보고서 파일 경로
        """
        if df.empty:
            logger.warning("보고서를 생성할 데이터가 없습니다.")
            return {}
        
        processed_df = self.preprocessor.preprocess_data(df)
        
        stats = self.preprocessor.calculate_statistics(processed_df)
        
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
        
        plots = {
            "speed_trend": self.plot_generator.generate_speed_trend_plot(processed_df, "weekly"),
            "congestion_heatmap": self.plot_generator.generate_congestion_heatmap(processed_df, "weekly"),
            "traffic_status_pie": self.plot_generator.generate_traffic_status_pie(processed_df),
            "volume_speed_scatter": self.plot_generator.generate_volume_speed_scatter(processed_df),
            "dashboard": self.plot_generator.generate_dashboard(processed_df, "weekly")
        }
        
        for key, path in plots.items():
            if path:
                plots[key] = os.path.relpath(path.replace(".html", ".png"), self.report_dir)
        
        start_date_obj = datetime.strptime(start_date, "%Y%m%d")
        end_date_obj = datetime.strptime(end_date, "%Y%m%d")
        formatted_start_date = start_date_obj.strftime("%Y년 %m월 %d일")
        formatted_end_date = end_date_obj.strftime("%Y년 %m월 %d일")
        
        if llm_summary is None:
            llm_summary = {
                "executive_summary": f"{formatted_start_date}부터 {formatted_end_date}까지의 주간 교통 상황에 대한 요약입니다. 이 기간의 평균 속도는 {stats.get('SPD_mean', 0):.2f} km/h이며, 정체 시간 비율은 {stats.get('congestion_time_ratio', 0):.2f}%입니다.",
                "weekly_trends": "주간 교통 추세 분석 결과입니다. 요일별 교통량과 속도 변화를 분석했습니다.",
                "peak_analysis": "첨두 시간대 분석 결과입니다. 요일별 첨두 시간대의 정체 현황과 주요 정체 구간을 분석했습니다.",
                "incident_summary": "사고 요약 결과입니다. 이 기간 발생한 사고와 그 영향을 분석했습니다.",
                "recommendations": "교통 상황 개선을 위한 권장사항입니다."
            }
        
        template = self.env.get_template("weekly_report.md")
        report_md = template.render(
            start_date=formatted_start_date,
            end_date=formatted_end_date,
            stats=stats,
            weekday_stats=weekday_stats,
            plots=plots,
            **llm_summary
        )
        
        md_path = os.path.join(self.report_dir, f"weekly_report_{start_date}_to_{end_date}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        logger.info(f"주간 보고서 마크다운 파일을 생성했습니다: {md_path}")
        
        pdf_path = os.path.join(self.report_dir, f"weekly_report_{start_date}_to_{end_date}.pdf")
        html = markdown.markdown(report_md, extensions=['tables', 'fenced_code'])
        
        for key, path in plots.items():
            if path:
                abs_path = os.path.join(self.report_dir, path)
                html = html.replace(f'src="{path}"', f'src="{abs_path}"')
        
        HTML(string=html).write_pdf(pdf_path)
        logger.info(f"주간 보고서 PDF 파일을 생성했습니다: {pdf_path}")
        
        return {
            "markdown": md_path,
            "pdf": pdf_path
        }
    
    def generate_monthly_report(self, df: pd.DataFrame, year_month: str,
                               llm_summary: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        월간 교통 보고서를 생성합니다.
        
        Args:
            df (pd.DataFrame): 교통 데이터
            year_month (str): 년월 (YYYYMM)
            llm_summary (Optional[Dict[str, str]]): LLM이 생성한 요약 정보
            
        Returns:
            Dict[str, str]: 생성된 보고서 파일 경로
        """
        if df.empty:
            logger.warning("보고서를 생성할 데이터가 없습니다.")
            return {}
        
        processed_df = self.preprocessor.preprocess_data(df)
        
        stats = self.preprocessor.calculate_statistics(processed_df)
        
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
        
        plots = {
            "speed_trend": self.plot_generator.generate_speed_trend_plot(processed_df, "monthly"),
            "congestion_heatmap": self.plot_generator.generate_congestion_heatmap(processed_df, "monthly"),
            "traffic_status_pie": self.plot_generator.generate_traffic_status_pie(processed_df),
            "volume_speed_scatter": self.plot_generator.generate_volume_speed_scatter(processed_df),
            "dashboard": self.plot_generator.generate_dashboard(processed_df, "monthly")
        }
        
        for key, path in plots.items():
            if path:
                plots[key] = os.path.relpath(path.replace(".html", ".png"), self.report_dir)
        
        year = year_month[:4]
        month = year_month[4:]
        formatted_year_month = f"{year}년 {month}월"
        
        if llm_summary is None:
            llm_summary = {
                "executive_summary": f"{formatted_year_month}의 월간 교통 상황에 대한 요약입니다. 이 기간의 평균 속도는 {stats.get('SPD_mean', 0):.2f} km/h이며, 정체 시간 비율은 {stats.get('congestion_time_ratio', 0):.2f}%입니다.",
                "monthly_overview": "월간 교통 개요입니다. 전체적인 교통 흐름과 주요 특징을 분석했습니다.",
                "trend_analysis": "월간 교통 추세 분석 결과입니다. 주간별 교통량과 속도 변화를 분석했습니다.",
                "incident_patterns": "사고 패턴 분석 결과입니다. 이 기간 발생한 사고의 패턴과 그 영향을 분석했습니다.",
                "recommendations": "교통 상황 개선을 위한 권장사항입니다.",
                "next_month_forecast": "다음 달 교통 상황 예측입니다. 현재 추세를 바탕으로 다음 달의 교통 상황을 예측했습니다."
            }
        
        template = self.env.get_template("monthly_report.md")
        report_md = template.render(
            year_month=formatted_year_month,
            stats=stats,
            weekly_stats=weekly_stats,
            plots=plots,
            **llm_summary
        )
        
        md_path = os.path.join(self.report_dir, f"monthly_report_{year_month}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        logger.info(f"월간 보고서 마크다운 파일을 생성했습니다: {md_path}")
        
        pdf_path = os.path.join(self.report_dir, f"monthly_report_{year_month}.pdf")
        html = markdown.markdown(report_md, extensions=['tables', 'fenced_code'])
        
        for key, path in plots.items():
            if path:
                abs_path = os.path.join(self.report_dir, path)
                html = html.replace(f'src="{path}"', f'src="{abs_path}"')
        
        HTML(string=html).write_pdf(pdf_path)
        logger.info(f"월간 보고서 PDF 파일을 생성했습니다: {pdf_path}")
        
        return {
            "markdown": md_path,
            "pdf": pdf_path
        }
    
    def generate_custom_report(self, df: pd.DataFrame, title: str, start_date: str, end_date: str,
                              sections: List[str], llm_content: Dict[str, str]) -> Dict[str, str]:
        """
        사용자 정의 교통 보고서를 생성합니다.
        
        Args:
            df (pd.DataFrame): 교통 데이터
            title (str): 보고서 제목
            start_date (str): 시작 날짜 (YYYYMMDD)
            end_date (str): 종료 날짜 (YYYYMMDD)
            sections (List[str]): 보고서 섹션 목록
            llm_content (Dict[str, str]): LLM이 생성한 섹션별 내용
            
        Returns:
            Dict[str, str]: 생성된 보고서 파일 경로
        """
        if df.empty:
            logger.warning("보고서를 생성할 데이터가 없습니다.")
            return {}
        
        processed_df = self.preprocessor.preprocess_data(df)
        
        stats = self.preprocessor.calculate_statistics(processed_df)
        
        plots = {
            "speed_trend": self.plot_generator.generate_speed_trend_plot(processed_df),
            "congestion_heatmap": self.plot_generator.generate_congestion_heatmap(processed_df),
            "traffic_status_pie": self.plot_generator.generate_traffic_status_pie(processed_df),
            "volume_speed_scatter": self.plot_generator.generate_volume_speed_scatter(processed_df),
            "dashboard": self.plot_generator.generate_dashboard(processed_df)
        }
        
        for key, path in plots.items():
            if path:
                plots[key] = os.path.relpath(path.replace(".html", ".png"), self.report_dir)
        
        start_date_obj = datetime.strptime(start_date, "%Y%m%d")
        end_date_obj = datetime.strptime(end_date, "%Y%m%d")
        formatted_start_date = start_date_obj.strftime("%Y년 %m월 %d일")
        formatted_end_date = end_date_obj.strftime("%Y년 %m월 %d일")
        
        report_md = f"# {title}: {formatted_start_date} ~ {formatted_end_date}\n\n"
        
        for section in sections:
            if section in llm_content:
                report_md += f"## {section}\n{llm_content[section]}\n\n"
        
        report_md += "## 주요 지표\n"
        report_md += f"- 평균 속도: {stats.get('SPD_mean', 0):.2f} km/h\n"
        report_md += f"- 최대 속도: {stats.get('SPD_max', 0):.2f} km/h\n"
        report_md += f"- 최소 속도: {stats.get('SPD_min', 0):.2f} km/h\n"
        report_md += f"- 평균 교통량: {stats.get('VOL_mean', 0):.2f}\n"
        report_md += f"- 정체 시간 비율: {stats.get('congestion_time_ratio', 0):.2f}%\n\n"
        
        report_md += "## 첨부 자료\n"
        for key, path in plots.items():
            if path:
                report_md += f"![{key}]({path})\n"
        
        filename = f"custom_report_{start_date}_to_{end_date}"
        
        md_path = os.path.join(self.report_dir, f"{filename}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        logger.info(f"사용자 정의 보고서 마크다운 파일을 생성했습니다: {md_path}")
        
        pdf_path = os.path.join(self.report_dir, f"{filename}.pdf")
        html = markdown.markdown(report_md, extensions=['tables', 'fenced_code'])
        
        for key, path in plots.items():
            if path:
                abs_path = os.path.join(self.report_dir, path)
                html = html.replace(f'src="{path}"', f'src="{abs_path}"')
        
        HTML(string=html).write_pdf(pdf_path)
        logger.info(f"사용자 정의 보고서 PDF 파일을 생성했습니다: {pdf_path}")
        
        return {
            "markdown": md_path,
            "pdf": pdf_path
        }
