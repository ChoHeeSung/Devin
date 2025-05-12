# Python 프로젝트

이 프로젝트는 Anaconda 가상환경이 설정된 기본 프로젝트 템플릿입니다.

## 환경 설정

### 필수 요구사항
- Anaconda3 또는 Miniconda3
- Python 3.12

### 가상환경 설정

1. 환경 생성 및 활성화
```bash
# 환경 생성
conda env create -f environment.yml

# 환경 활성화
conda activate ai_example
```

2. 환경 업데이트 (필요시)
```bash
conda env update -f environment.yml --prune
```

## 자동 환경 설정

프로젝트 루트 디렉토리에서 다음 명령어를 실행하여 자동으로 환경을 설정할 수 있습니다:

```bash
source activate_env.sh
```

## 개발 도구

이 프로젝트는 다음과 같은 개발 도구들을 포함하고 있습니다:

- pytest: 테스트 프레임워크
- black: 코드 포매터
- isort: import 문 정렬
- mypy: 정적 타입 검사
- python-dotenv: 환경 변수 관리
- jupyter: 주피터 노트북
- notebook: 웹 기반 노트북 인터페이스
- ipykernel: 주피터 커널

## 프로젝트 구조
```
.
├── README.md
├── environment.yml
├── activate_env.sh
├── create_notebook.py
├── notebooks/
│ ├── first_notebook.ipynb
│ └── test.ipynb
└── .vscode/
└── settings.json
```


## Jupyter Notebook 사용

프로젝트에는 기본 주피터 노트북 템플릿이 포함되어 있습니다:

- `notebooks/first_notebook.ipynb`: 기본 데이터 분석 환경이 설정된 노트북
- `notebooks/test.ipynb`: 테스트용 노트북

새로운 노트북 생성은 `create_notebook.py` 스크립트를 통해 가능합니다:
```bash
python create_notebook.py
```

## 유용한 명령어

```bash
# 현재 환경 확인
conda info --envs

# 설치된 패키지 목록 확인
conda list

# 환경 제거
conda env remove -n ai_example

# Jupyter Notebook 실행
jupyter notebook
```

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.