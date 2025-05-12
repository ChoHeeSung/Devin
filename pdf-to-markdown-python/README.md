# PDF to Markdown Converter

이 애플리케이션은 PDF 파일을 마크다운 형식으로 변환하는 웹 기반 도구입니다. 사용자는 웹 브라우저를 통해 PDF 파일을 업로드하고, 변환된 마크다운을 확인 및 다운로드할 수 있습니다.

## 기능

- PDF 파일 업로드
- PDF를 마크다운으로 자동 변환
- 변환된 마크다운 텍스트 표시
- 마크다운 파일 다운로드

## 기술 스택

- **백엔드 및 프론트엔드**: FastAPI (Python) + Jinja2 템플릿
- **컨테이너화**: Docker, docker-compose

## 설치 및 실행 방법

### 사전 요구사항

- Docker
- docker-compose

### Docker를 이용한 실행

1. 저장소 클론:
   ```bash
   git clone <repository-url>
   cd pdf-to-markdown-python
   ```

2. docker-compose로 애플리케이션 실행:
   ```bash
   docker-compose up -d
   ```

3. 웹 브라우저에서 다음 URL 접속:
   ```
   http://localhost:8000
   ```

### 로컬 개발 환경 설정 (Docker 없이)

1. Python 3.12 설치

2. Poetry 설치:
   ```bash
   pip install poetry
   ```

3. 의존성 설치:
   ```bash
   poetry install
   ```

4. 개발 서버 실행:
   ```bash
   python -m app.main
   ```

5. 웹 브라우저에서 다음 URL 접속:
   ```
   http://localhost:8000
   ```

## 사용 방법

1. 웹 브라우저에서 애플리케이션에 접속합니다.
2. "Upload PDF" 섹션에서 "Browse Files" 버튼을 클릭하여 PDF 파일을 선택합니다.
3. "Convert to Markdown" 버튼을 클릭합니다.
4. 변환이 완료되면 오른쪽 섹션에 마크다운 텍스트가 표시됩니다.
5. "Download Markdown" 버튼을 클릭하여 마크다운 파일을 다운로드할 수 있습니다.

## 문제 해결

- **서버 연결 오류**: Docker 컨테이너가 정상적으로 실행 중인지 확인하세요.
  ```bash
  docker-compose ps
  ```

- **변환 오류**: PDF 파일 변환 중 오류가 발생하면 PDF 파일이 손상되지 않았는지 확인하세요.

- **Docker 컨테이너 로그 확인**:
  ```bash
  docker-compose logs
  ```

## 라이선스

MIT 라이선스
