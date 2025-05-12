
"""
교통 데이터 시각화 모듈
작성일: 2025-05-12
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ..config import get_config, REPORT_DIR

logger = logging.getLogger(__name__)

class TrafficPlotGenerator:
    """교통 데이터 시각화를 관리하는 클래스"""
    
    def __init__(self):
        """
        교통 데이터 시각화 생성기를 초기화합니다.
        """
        self.config = get_config("visualization")
        self.theme = self.config["theme"]
        self.color_scheme = self.config["color_scheme"]
        self.default_width = self.config["default_width"]
        self.default_height = self.config["default_height"]
        self.report_dir = REPORT_DIR
        self.plot_dir = os.path.join(self.report_dir, "plots")
        os.makedirs(self.plot_dir, exist_ok=True)
    
    def generate_speed_trend_plot(self, df: pd.DataFrame, period: str = "daily", 
                                  save_path: Optional[str] = None) -> str:
        """
        속도 추세 그래프를 생성합니다.
        
        Args:
            df (pd.DataFrame): 교통 데이터
            period (str): 기간 유형 (daily, weekly, monthly)
            save_path (Optional[str]): 저장 경로
            
        Returns:
            str: 저장된 파일 경로
        """
        if df.empty:
            logger.warning("시각화할 데이터가 없습니다.")
            return ""
        
        if 'DATE' not in df.columns and 'STAT_DAY' in df.columns:
            df['DATE'] = pd.to_datetime(df['STAT_DAY'], format='%Y%m%d')
        
        if period == "daily":
            if 'STAT_HOUR' in df.columns and 'SPD' in df.columns:
                speed_by_hour = df.groupby('STAT_HOUR')['SPD'].mean().reset_index()
                
                fig = px.line(
                    speed_by_hour, 
                    x='STAT_HOUR', 
                    y='SPD',
                    title='시간별 평균 속도',
                    labels={'STAT_HOUR': '시간', 'SPD': '평균 속도 (km/h)'},
                    color_discrete_sequence=px.colors.qualitative.Plotly,
                    width=self.default_width,
                    height=self.default_height
                )
                
                fig.update_layout(
                    template='plotly_white',
                    xaxis=dict(tickmode='linear', dtick=1),
                    yaxis=dict(title='평균 속도 (km/h)'),
                    hovermode='x unified'
                )
                
                fig.add_vrect(
                    x0=7, x1=9,
                    fillcolor="rgba(255, 0, 0, 0.1)", opacity=0.5,
                    layer="below", line_width=0,
                    annotation_text="아침 첨두",
                    annotation_position="top left"
                )
                
                fig.add_vrect(
                    x0=17, x1=19,
                    fillcolor="rgba(255, 0, 0, 0.1)", opacity=0.5,
                    layer="below", line_width=0,
                    annotation_text="저녁 첨두",
                    annotation_position="top left"
                )
        
        elif period == "weekly":
            if 'STAT_WEEKDAY' in df.columns and 'SPD' in df.columns:
                weekday_map = {
                    '1': '월요일', '2': '화요일', '3': '수요일', '4': '목요일',
                    '5': '금요일', '6': '토요일', '7': '일요일'
                }
                
                df['WEEKDAY_NAME'] = df['STAT_WEEKDAY'].astype(str).map(weekday_map)
                speed_by_weekday = df.groupby('WEEKDAY_NAME')['SPD'].mean().reset_index()
                
                weekday_order = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
                speed_by_weekday['WEEKDAY_ORDER'] = speed_by_weekday['WEEKDAY_NAME'].map(
                    {day: i for i, day in enumerate(weekday_order)}
                )
                speed_by_weekday = speed_by_weekday.sort_values('WEEKDAY_ORDER')
                
                fig = px.bar(
                    speed_by_weekday, 
                    x='WEEKDAY_NAME', 
                    y='SPD',
                    title='요일별 평균 속도',
                    labels={'WEEKDAY_NAME': '요일', 'SPD': '평균 속도 (km/h)'},
                    color='SPD',
                    color_continuous_scale=self.color_scheme,
                    width=self.default_width,
                    height=self.default_height
                )
                
                fig.update_layout(
                    template='plotly_white',
                    yaxis=dict(title='평균 속도 (km/h)'),
                    coloraxis_showscale=False,
                    hovermode='x unified'
                )
        
        elif period == "monthly":
            if 'DATE' in df.columns and 'SPD' in df.columns:
                speed_by_date = df.groupby('DATE')['SPD'].mean().reset_index()
                
                fig = px.line(
                    speed_by_date, 
                    x='DATE', 
                    y='SPD',
                    title='일별 평균 속도 추세',
                    labels={'DATE': '날짜', 'SPD': '평균 속도 (km/h)'},
                    color_discrete_sequence=px.colors.qualitative.Plotly,
                    width=self.default_width,
                    height=self.default_height
                )
                
                fig.update_layout(
                    template='plotly_white',
                    yaxis=dict(title='평균 속도 (km/h)'),
                    hovermode='x unified'
                )
                
                for date in speed_by_date['DATE']:
                    if date.weekday() >= 5:  # 5: 토요일, 6: 일요일
                        fig.add_vrect(
                            x0=date, x1=date + pd.Timedelta(days=1),
                            fillcolor="rgba(0, 255, 0, 0.1)", opacity=0.5,
                            layer="below", line_width=0
                        )
        
        else:
            logger.warning(f"지원하지 않는 기간 유형입니다: {period}")
            return ""
        
        if save_path is None:
            save_path = os.path.join(self.plot_dir, f"speed_trend_{period}.html")
        
        fig.write_html(save_path)
        logger.info(f"속도 추세 그래프를 저장했습니다: {save_path}")
        
        img_path = save_path.replace(".html", ".png")
        fig.write_image(img_path)
        
        return save_path
    
    def generate_congestion_heatmap(self, df: pd.DataFrame, period: str = "daily", 
                                    save_path: Optional[str] = None) -> str:
        """
        정체 히트맵을 생성합니다.
        
        Args:
            df (pd.DataFrame): 교통 데이터
            period (str): 기간 유형 (daily, weekly, monthly)
            save_path (Optional[str]): 저장 경로
            
        Returns:
            str: 저장된 파일 경로
        """
        if df.empty:
            logger.warning("시각화할 데이터가 없습니다.")
            return ""
        
        if 'CONGESTION_RATIO' not in df.columns and 'SPD' in df.columns:
            free_flow_speed = 80
            df['CONGESTION_RATIO'] = (1 - (df['SPD'] / free_flow_speed)).clip(0, 1) * 100
        
        if period == "daily":
            if 'STAT_HOUR' in df.columns and 'LINK_ID' in df.columns and 'CONGESTION_RATIO' in df.columns:
                congestion_pivot = df.pivot_table(
                    values='CONGESTION_RATIO', 
                    index='LINK_ID', 
                    columns='STAT_HOUR',
                    aggfunc='mean'
                ).fillna(0)
                
                top_links = congestion_pivot.mean(axis=1).sort_values(ascending=False).head(20).index
                congestion_pivot = congestion_pivot.loc[top_links]
                
                fig = px.imshow(
                    congestion_pivot,
                    title='시간별 링크 정체율 히트맵',
                    labels=dict(x="시간", y="링크 ID", color="정체율 (%)"),
                    x=congestion_pivot.columns,
                    y=congestion_pivot.index,
                    color_continuous_scale='Reds',
                    width=self.default_width,
                    height=self.default_height
                )
                
                fig.update_layout(
                    template='plotly_white',
                    xaxis=dict(tickmode='linear', dtick=1),
                    coloraxis_colorbar=dict(title="정체율 (%)"),
                    hovermode='closest'
                )
        
        elif period == "weekly":
            if 'STAT_WEEKDAY' in df.columns and 'STAT_HOUR' in df.columns and 'CONGESTION_RATIO' in df.columns:
                weekday_map = {
                    '1': '월요일', '2': '화요일', '3': '수요일', '4': '목요일',
                    '5': '금요일', '6': '토요일', '7': '일요일'
                }
                
                df['WEEKDAY_NAME'] = df['STAT_WEEKDAY'].astype(str).map(weekday_map)
                
                congestion_pivot = df.pivot_table(
                    values='CONGESTION_RATIO', 
                    index='WEEKDAY_NAME', 
                    columns='STAT_HOUR',
                    aggfunc='mean'
                ).fillna(0)
                
                weekday_order = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
                congestion_pivot = congestion_pivot.reindex(weekday_order)
                
                fig = px.imshow(
                    congestion_pivot,
                    title='요일별 시간대 정체율 히트맵',
                    labels=dict(x="시간", y="요일", color="정체율 (%)"),
                    x=congestion_pivot.columns,
                    y=congestion_pivot.index,
                    color_continuous_scale='Reds',
                    width=self.default_width,
                    height=self.default_height
                )
                
                fig.update_layout(
                    template='plotly_white',
                    xaxis=dict(tickmode='linear', dtick=1),
                    coloraxis_colorbar=dict(title="정체율 (%)"),
                    hovermode='closest'
                )
        
        elif period == "monthly":
            if 'DATE' in df.columns and 'STAT_HOUR' in df.columns and 'CONGESTION_RATIO' in df.columns:
                df['DATE_STR'] = df['DATE'].dt.strftime('%m-%d')
                
                congestion_pivot = df.pivot_table(
                    values='CONGESTION_RATIO', 
                    index='DATE_STR', 
                    columns='STAT_HOUR',
                    aggfunc='mean'
                ).fillna(0)
                
                fig = px.imshow(
                    congestion_pivot,
                    title='일별 시간대 정체율 히트맵',
                    labels=dict(x="시간", y="날짜", color="정체율 (%)"),
                    x=congestion_pivot.columns,
                    y=congestion_pivot.index,
                    color_continuous_scale='Reds',
                    width=self.default_width,
                    height=self.default_height
                )
                
                fig.update_layout(
                    template='plotly_white',
                    xaxis=dict(tickmode='linear', dtick=1),
                    coloraxis_colorbar=dict(title="정체율 (%)"),
                    hovermode='closest'
                )
        
        else:
            logger.warning(f"지원하지 않는 기간 유형입니다: {period}")
            return ""
        
        if save_path is None:
            save_path = os.path.join(self.plot_dir, f"congestion_heatmap_{period}.html")
        
        fig.write_html(save_path)
        logger.info(f"정체 히트맵을 저장했습니다: {save_path}")
        
        img_path = save_path.replace(".html", ".png")
        fig.write_image(img_path)
        
        return save_path
    
    def generate_traffic_status_pie(self, df: pd.DataFrame, 
                                   save_path: Optional[str] = None) -> str:
        """
        교통 상태 파이 차트를 생성합니다.
        
        Args:
            df (pd.DataFrame): 교통 데이터
            save_path (Optional[str]): 저장 경로
            
        Returns:
            str: 저장된 파일 경로
        """
        if df.empty:
            logger.warning("시각화할 데이터가 없습니다.")
            return ""
        
        if 'TRAFFIC_STATUS' not in df.columns and 'SPD' in df.columns:
            df['TRAFFIC_STATUS'] = 'NORMAL'
            df.loc[df['SPD'] < 30, 'TRAFFIC_STATUS'] = 'CONGESTED'
            df.loc[df['SPD'] < 10, 'TRAFFIC_STATUS'] = 'SEVERELY_CONGESTED'
            df.loc[df['SPD'] > 80, 'TRAFFIC_STATUS'] = 'FREE_FLOW'
        
        if 'TRAFFIC_STATUS' in df.columns:
            status_counts = df['TRAFFIC_STATUS'].value_counts()
            
            status_map = {
                'FREE_FLOW': '원활',
                'NORMAL': '정상',
                'CONGESTED': '정체',
                'SEVERELY_CONGESTED': '심각한 정체'
            }
            
            status_counts.index = status_counts.index.map(lambda x: status_map.get(x, x))
            
            color_map = {
                '원활': 'green',
                '정상': 'blue',
                '정체': 'orange',
                '심각한 정체': 'red'
            }
            
            colors = [color_map.get(status, 'gray') for status in status_counts.index]
            
            fig = go.Figure(data=[go.Pie(
                labels=status_counts.index,
                values=status_counts.values,
                hole=.3,
                marker_colors=colors
            )])
            
            fig.update_layout(
                title='교통 상태 분포',
                template='plotly_white',
                width=self.default_width,
                height=self.default_height,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.1,
                    xanchor="center",
                    x=0.5
                )
            )
            
            if save_path is None:
                save_path = os.path.join(self.plot_dir, "traffic_status_pie.html")
            
            fig.write_html(save_path)
            logger.info(f"교통 상태 파이 차트를 저장했습니다: {save_path}")
            
            img_path = save_path.replace(".html", ".png")
            fig.write_image(img_path)
            
            return save_path
        
        logger.warning("교통 상태 정보가 없습니다.")
        return ""
    
    def generate_volume_speed_scatter(self, df: pd.DataFrame, 
                                     save_path: Optional[str] = None) -> str:
        """
        교통량-속도 산점도를 생성합니다.
        
        Args:
            df (pd.DataFrame): 교통 데이터
            save_path (Optional[str]): 저장 경로
            
        Returns:
            str: 저장된 파일 경로
        """
        if df.empty:
            logger.warning("시각화할 데이터가 없습니다.")
            return ""
        
        if 'VOL' in df.columns and 'SPD' in df.columns:
            if 'TIME_PERIOD' not in df.columns and 'STAT_HOUR' in df.columns:
                df['TIME_PERIOD'] = 'NON_PEAK'
                df.loc[(df['STAT_HOUR'].astype(int) >= 7) & (df['STAT_HOUR'].astype(int) <= 9), 'TIME_PERIOD'] = 'MORNING_PEAK'
                df.loc[(df['STAT_HOUR'].astype(int) >= 17) & (df['STAT_HOUR'].astype(int) <= 19), 'TIME_PERIOD'] = 'EVENING_PEAK'
            
            if 'TIME_PERIOD' in df.columns:
                period_map = {
                    'MORNING_PEAK': '아침 첨두',
                    'EVENING_PEAK': '저녁 첨두',
                    'NON_PEAK': '비첨두'
                }
                
                df['TIME_PERIOD_KR'] = df['TIME_PERIOD'].map(period_map)
                
                fig = px.scatter(
                    df.sample(min(5000, len(df))),  # 데이터가 너무 많으면 샘플링
                    x='VOL',
                    y='SPD',
                    color='TIME_PERIOD_KR',
                    title='교통량-속도 관계',
                    labels={'VOL': '교통량', 'SPD': '속도 (km/h)', 'TIME_PERIOD_KR': '시간대'},
                    color_discrete_map={
                        '아침 첨두': 'red',
                        '저녁 첨두': 'orange',
                        '비첨두': 'blue'
                    },
                    width=self.default_width,
                    height=self.default_height
                )
            else:
                fig = px.scatter(
                    df.sample(min(5000, len(df))),  # 데이터가 너무 많으면 샘플링
                    x='VOL',
                    y='SPD',
                    title='교통량-속도 관계',
                    labels={'VOL': '교통량', 'SPD': '속도 (km/h)'},
                    color_discrete_sequence=px.colors.qualitative.Plotly,
                    width=self.default_width,
                    height=self.default_height
                )
            
            fig.update_layout(
                template='plotly_white',
                xaxis=dict(title='교통량'),
                yaxis=dict(title='속도 (km/h)'),
                hovermode='closest'
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df['VOL'].sort_values(),
                    y=df['VOL'].sort_values().map(lambda x: max(80 - 0.1 * x, 10)),
                    mode='lines',
                    name='추세선',
                    line=dict(color='black', dash='dash')
                )
            )
            
            if save_path is None:
                save_path = os.path.join(self.plot_dir, "volume_speed_scatter.html")
            
            fig.write_html(save_path)
            logger.info(f"교통량-속도 산점도를 저장했습니다: {save_path}")
            
            img_path = save_path.replace(".html", ".png")
            fig.write_image(img_path)
            
            return save_path
        
        logger.warning("교통량 또는 속도 정보가 없습니다.")
        return ""
    
    def generate_dashboard(self, df: pd.DataFrame, period: str = "daily",
                          save_path: Optional[str] = None) -> str:
        """
        종합 대시보드를 생성합니다.
        
        Args:
            df (pd.DataFrame): 교통 데이터
            period (str): 기간 유형 (daily, weekly, monthly)
            save_path (Optional[str]): 저장 경로
            
        Returns:
            str: 저장된 파일 경로
        """
        if df.empty:
            logger.warning("시각화할 데이터가 없습니다.")
            return ""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '시간별 평균 속도', '교통 상태 분포',
                '시간별 교통량', '교통량-속도 관계'
            ),
            specs=[
                [{"type": "scatter"}, {"type": "pie"}],
                [{"type": "bar"}, {"type": "scatter"}]
            ]
        )
        
        if 'STAT_HOUR' in df.columns and 'SPD' in df.columns:
            speed_by_hour = df.groupby('STAT_HOUR')['SPD'].mean().reset_index()
            
            fig.add_trace(
                go.Scatter(
                    x=speed_by_hour['STAT_HOUR'],
                    y=speed_by_hour['SPD'],
                    mode='lines+markers',
                    name='평균 속도',
                    line=dict(color='blue')
                ),
                row=1, col=1
            )
        
        if 'TRAFFIC_STATUS' not in df.columns and 'SPD' in df.columns:
            df['TRAFFIC_STATUS'] = 'NORMAL'
            df.loc[df['SPD'] < 30, 'TRAFFIC_STATUS'] = 'CONGESTED'
            df.loc[df['SPD'] < 10, 'TRAFFIC_STATUS'] = 'SEVERELY_CONGESTED'
            df.loc[df['SPD'] > 80, 'TRAFFIC_STATUS'] = 'FREE_FLOW'
        
        if 'TRAFFIC_STATUS' in df.columns:
            status_counts = df['TRAFFIC_STATUS'].value_counts()
            
            status_map = {
                'FREE_FLOW': '원활',
                'NORMAL': '정상',
                'CONGESTED': '정체',
                'SEVERELY_CONGESTED': '심각한 정체'
            }
            
            status_counts.index = status_counts.index.map(lambda x: status_map.get(x, x))
            
            color_map = {
                '원활': 'green',
                '정상': 'blue',
                '정체': 'orange',
                '심각한 정체': 'red'
            }
            
            colors = [color_map.get(status, 'gray') for status in status_counts.index]
            
            fig.add_trace(
                go.Pie(
                    labels=status_counts.index,
                    values=status_counts.values,
                    marker_colors=colors,
                    name='교통 상태'
                ),
                row=1, col=2
            )
        
        if 'STAT_HOUR' in df.columns and 'VOL' in df.columns:
            vol_by_hour = df.groupby('STAT_HOUR')['VOL'].mean().reset_index()
            
            fig.add_trace(
                go.Bar(
                    x=vol_by_hour['STAT_HOUR'],
                    y=vol_by_hour['VOL'],
                    name='평균 교통량',
                    marker_color='orange'
                ),
                row=2, col=1
            )
        
        if 'VOL' in df.columns and 'SPD' in df.columns:
            sample_df = df.sample(min(1000, len(df)))
            
            fig.add_trace(
                go.Scatter(
                    x=sample_df['VOL'],
                    y=sample_df['SPD'],
                    mode='markers',
                    name='교통량-속도',
                    marker=dict(
                        color=sample_df['VOL'],
                        colorscale='Viridis',
                        showscale=False
                    )
                ),
                row=2, col=2
            )
        
        title_map = {
            "daily": "일일 교통 대시보드",
            "weekly": "주간 교통 대시보드",
            "monthly": "월간 교통 대시보드"
        }
        
        fig.update_layout(
            title=title_map.get(period, "교통 대시보드"),
            template='plotly_white',
            height=800,
            width=1200,
            showlegend=False,
            hovermode='closest'
        )
        
        fig.update_xaxes(title_text="시간", row=1, col=1)
        fig.update_xaxes(title_text="시간", row=2, col=1)
        fig.update_xaxes(title_text="교통량", row=2, col=2)
        
        fig.update_yaxes(title_text="평균 속도 (km/h)", row=1, col=1)
        fig.update_yaxes(title_text="평균 교통량", row=2, col=1)
        fig.update_yaxes(title_text="속도 (km/h)", row=2, col=2)
        
        if save_path is None:
            save_path = os.path.join(self.plot_dir, f"dashboard_{period}.html")
        
        fig.write_html(save_path)
        logger.info(f"종합 대시보드를 저장했습니다: {save_path}")
        
        img_path = save_path.replace(".html", ".png")
        fig.write_image(img_path)
        
        return save_path
