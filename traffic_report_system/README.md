# 자동 교통 보고서 생성 및 시각화 Agent

실시간 및 이력 교통 데이터를 기반으로 일간, 주간, 월간 교통 보고서를 자동 생성하고 이를 시각화하여 운영자에게 제공하는 로컬 실행 기반 LLM 자동화 Agent입니다.

## 프로젝트 개요

이 시스템은 고속도로 교통 데이터를 분석하여 다양한 형태의 보고서를 자동으로 생성하고, 주요 교통 지표를 시각화하여 제공합니다. 로컬 환경에서 실행 가능한 소형 언어 모델(LLM)을 활용하여 사용자의 자연어 요청을 처리하고, 사용자 피드백을 기반으로 지속적인 개선이 가능한 시스템입니다.

## 주요 기능

1. **데이터 연동 및 처리**
   - Oracle 데이터베이스에서 고속도로 교통 데이터 연동
   - 최신 데이터 자동 로딩 및 캐싱 기능
   - Z-score, IQR 등 다양한 방식의 이상치 처리
   - 보간법, 평균값 대체 등 결측치 처리 기능

2. **보고서 자동 생성**
   - 일일, 주간, 월간 단위 자동 보고서 생성
   - Markdown 및 PDF 포맷 지원
   - 템플릿 기반 보고서 생성으로 일관성 유지

3. **데이터 시각화**
   - 시간별 속도 추세 그래프
   - 정체 히트맵
   - 교통 상태 분포 파이 차트
   - 교통량-속도 관계 산점도
   - 종합 대시보드

4. **로컬 소형 언어 모델 활용**
   - Mistral 모델을 활용한 자연어 처리
   - 사용자 요청 분석 및 보고서 내용 생성
   - 예: "5월 첫째 주 서울 지역 교통 보고서 생성"

5. **메모리 관리 및 자기반영**
   - 생성된 보고서 인덱싱 및 검색 기능
   - 사용자 피드백 저장 및 분석
   - 피드백 기반 자동 개선 사항 도출

## 기술 스택

- **언어 및 프레임워크**: Python 3.12, LangChain
- **로컬 LLM 모델**: Mistral 7B
- **데이터베이스**: Oracle Database
- **시각화**: Plotly
- **데이터 처리**: Pandas, NumPy, SciPy
- **보고서 생성**: Markdown, Jinja2, WeasyPrint

## 설치 및 실행

1. 의존성 설치
```bash
pip install -r requirements.txt
```

2. Oracle DB 설정
```bash
# .env.example 파일을 .env로 복사하고 Oracle 접속 정보 설정
cp .env.example .env
# .env 파일을 편집하여 Oracle DB 연결 정보 입력
# 자세한 내용은 config.py 파일의 ORACLE_CONFIG 참조
```

3. LLM 모델 설정
```bash
# Mistral 모델 다운로드
mkdir -p models
wget -P models https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

4. 실행
```bash
# 자연어 요청 처리
python main.py query "5월 첫째 주 서울 지역 교통 보고서 생성해줘"

# 특정 유형의 보고서 생성
python main.py report --type daily --start-date 20230501
```

## 사용 방법

### 명령행 인터페이스

```bash
# 자연어 요청 처리
python main.py query "5월 첫째 주 서울 지역 교통 보고서 생성해줘"

# 특정 유형의 보고서 생성
python main.py report --type daily --start-date 20230501

# 보고서 검색
python main.py search --type weekly --start-date 20230501 --end-date 20230507

# 피드백 저장
python main.py feedback report_daily_20230501123456 --rating 4 --comment "시각화가 잘 되어 있습니다"

# 피드백 기반 개선 사항 적용
python main.py improve
```

### 프로그래밍 방식 사용

```python
from traffic_report_system.main import TrafficReportAgent

# Agent 초기화
agent = TrafficReportAgent()

# 자연어 요청 처리
result = agent.process_natural_language_request("5월 첫째 주 서울 지역 교통 보고서 생성해줘")

# 보고서 생성
report = agent.generate_report(
    report_type="weekly",
    date_range={"start_date": "20230501", "end_date": "20230507"},
    region="서울"
)
```

## 프로젝트 구조

```
traffic_report_system/
├── config.py                  # 시스템 설정
├── main.py                    # 메인 애플리케이션
├── requirements.txt           # 의존성 목록
├── .env.example               # 환경 변수 예시 파일
├── database/                  # 데이터베이스 연결
│   └── oracle_connector.py    # Oracle DB 연결
├── data_processing/           # 데이터 처리
│   ├── data_loader.py         # 데이터 로딩
│   └── data_preprocessor.py   # 데이터 전처리
├── visualization/             # 시각화
│   └── plot_generator.py      # 시각화 생성
├── report_generation/         # 보고서 생성
│   └── report_generator.py    # 보고서 생성
├── llm_integration/           # LLM 통합
│   └── llm_config.py          # LLM 설정
├── memory_management/         # 메모리 관리
│   └── memory_manager.py      # 메모리 관리
├── models/                    # LLM 모델 저장
├── data/                      # 데이터 저장
├── reports/                   # 생성된 보고서 저장
├── memory/                    # 메모리 저장
└── templates/                 # 보고서 템플릿
```

## 주요 클래스 및 모듈

- **TrafficReportAgent**: 전체 시스템을 관리하는 메인 클래스
- **OracleConnector**: Oracle 데이터베이스 연결 관리
- **TrafficDataLoader**: 교통 데이터 로딩 및 캐싱
- **TrafficDataPreprocessor**: 데이터 전처리 및 통계 계산
- **TrafficPlotGenerator**: 시각화 생성
- **TrafficReportGenerator**: 보고서 생성
- **TrafficLLMProcessor**: LLM 통합 및 자연어 처리
- **TrafficMemoryManager**: 메모리 관리 및 피드백 처리

## Oracle DB 설정 (TODO)

Oracle 데이터베이스 연결 정보는 `.env` 파일에 설정해야 합니다:

```
ORACLE_HOST=your_oracle_host
ORACLE_PORT=1521
ORACLE_SERVICE=your_oracle_service
ORACLE_USER=your_oracle_username
ORACLE_PASSWORD=your_oracle_password
```

이 설정은 `config.py` 파일의 `ORACLE_CONFIG` 딕셔너리에서 로드됩니다.
