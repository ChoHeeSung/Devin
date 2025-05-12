import nbformat as nbf

# 새로운 노트북 생성
nb = nbf.v4.new_notebook()

# 마크다운 셀 생성
markdown_text = """# 첫 번째 주피터 노트북

이 노트북은 Python 프로그래밍을 위한 기본 템플릿입니다.

## 사용 방법
- 각 셀은 `Shift + Enter`로 실행할 수 있습니다.
- 마크다운 셀은 `M`키로, 코드 셀은 `Y`키로 변환할 수 있습니다.
- 새로운 셀은 `A`(위에 추가) 또는 `B`(아래에 추가)키로 생성할 수 있습니다."""

code1_text = """# Python 버전 확인
import sys
print(f"Python 버전: {sys.version}")

# 현재 작업 디렉토리 확인
import os
print(f"현재 작업 디렉토리: {os.getcwd()}")"""

code2_text = """# 데이터 분석 및 과학 계산 라이브러리
import numpy as np
import pandas as pd

# 시각화 라이브러리
import matplotlib.pyplot as plt
%matplotlib inline"""

# 셀 생성
markdown_cell = nbf.v4.new_markdown_cell(markdown_text)
code_cell1 = nbf.v4.new_code_cell(code1_text)
code_cell2 = nbf.v4.new_code_cell(code2_text)

# 노트북에 셀 추가
nb.cells.extend([markdown_cell, code_cell1, code_cell2])

# 노트북 파일 저장
with open('notebooks/first_notebook.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f) 