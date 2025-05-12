#!/bin/bash

# 스크립트에 실행 권한 부여가 필요합니다
# chmod +x activate_env.sh

# 현재 경로의 프로젝트 이름을 기반으로 환경 이름 설정
PROJECT_NAME="ai_example"

# conda 환경 존재 여부 확인
if conda env list | grep -q "$PROJECT_NAME"; then
    echo "🔄 Updating conda environment..."
    conda env update -f environment.yml
else
    echo "🆕 Creating new conda environment..."
    conda env create -f environment.yml
fi

# 환경 활성화
conda activate "$PROJECT_NAME"

# VS Code가 설치되어 있다면 Python 인터프리터 설정
if command -v code >/dev/null 2>&1; then
    # .vscode 디렉토리가 없다면 생성
    mkdir -p .vscode
    
    # settings.json 생성 또는 업데이트
    cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "$CONDA_PREFIX/bin/python",
    "python.terminal.activateEnvironment": true,
    "jupyter.notebookFileRoot": "\${workspaceFolder}"
}
EOF
fi

echo "✨ Environment setup complete!"
echo "📍 Using Python at: $(which python)"
echo "📦 Python version: $(python --version)" 