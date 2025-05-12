from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import tempfile
import shutil
import json
import time
import asyncio
from typing import Dict, Any, List, Optional
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType

app = FastAPI(title="PDF to Markdown 변환기")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

conversion_tasks = {}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    메인 페이지 렌더링
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/convert-pdf")
async def convert_pdf_to_markdown(file: UploadFile = File(), background_tasks: BackgroundTasks = BackgroundTasks()):
    """
    PDF 파일을 마크다운 형식으로 변환합니다.
    
    Args:
        file: 변환할 PDF 파일
        background_tasks: 백그라운드 작업 객체
        
    Returns:
        작업 ID를 포함하는 Dict
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 지원됩니다")
    
    task_id = f"task_{int(time.time())}"
    
    conversion_tasks[task_id] = {
        "status": "준비 중",
        "progress": 0,
        "logs": ["PDF 변환 작업이 시작되었습니다."],
        "result": None,
        "error": None,
        "filename": file.filename
    }
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    background_tasks.add_task(
        process_pdf_in_background,
        task_id=task_id,
        file_path=temp_file_path,
        temp_dir=temp_dir
    )
    
    return {"task_id": task_id}

async def process_pdf_in_background(task_id: str, file_path: str, temp_dir: str):
    """
    백그라운드에서 PDF 파일을 마크다운으로 변환하는 함수
    
    Args:
        task_id: 작업 ID
        file_path: PDF 파일 경로
        temp_dir: 임시 디렉토리 경로
    """
    try:
        conversion_tasks[task_id]["status"] = "파일 로딩 중"
        conversion_tasks[task_id]["progress"] = 10
        conversion_tasks[task_id]["logs"].append("PDF 파일을 로딩하는 중입니다...")
        await asyncio.sleep(0.5)  # 상태 업데이트가 클라이언트에 전달될 시간 확보
        
        loader = DoclingLoader(
            file_path=file_path,
            export_type=ExportType.MARKDOWN,
        )
        
        conversion_tasks[task_id]["status"] = "PDF 처리 중"
        conversion_tasks[task_id]["progress"] = 30
        conversion_tasks[task_id]["logs"].append("PDF 내용을 분석하는 중입니다...")
        await asyncio.sleep(0.5)
        
        documents = loader.load()
        
        conversion_tasks[task_id]["status"] = "마크다운 생성 중"
        conversion_tasks[task_id]["progress"] = 70
        conversion_tasks[task_id]["logs"].append("마크다운으로 변환하는 중입니다...")
        await asyncio.sleep(0.5)
        
        markdown_content = ""
        total_docs = len(documents)
        
        for i, doc in enumerate(documents):
            markdown_content += doc.page_content + "\n\n"
            
            progress = 70 + int((i + 1) / total_docs * 25)
            conversion_tasks[task_id]["progress"] = progress
            conversion_tasks[task_id]["logs"].append(f"페이지 {i+1}/{total_docs} 처리 완료")
            await asyncio.sleep(0.1)
        
        conversion_tasks[task_id]["status"] = "완료"
        conversion_tasks[task_id]["progress"] = 100
        conversion_tasks[task_id]["result"] = markdown_content
        conversion_tasks[task_id]["logs"].append("PDF 변환이 완료되었습니다.")
        
    except Exception as e:
        error_msg = f"PDF 처리 중 오류 발생: {str(e)}"
        conversion_tasks[task_id]["status"] = "오류"
        conversion_tasks[task_id]["error"] = error_msg
        conversion_tasks[task_id]["logs"].append(error_msg)
    
    finally:
        try:
            shutil.rmtree(temp_dir)
            conversion_tasks[task_id]["logs"].append("임시 파일이 정리되었습니다.")
        except:
            pass

@app.get("/conversion-status/{task_id}")
async def get_conversion_status(task_id: str):
    """
    변환 작업의 현재 상태를 반환합니다.
    
    Args:
        task_id: 작업 ID
        
    Returns:
        작업 상태 정보
    """
    if task_id not in conversion_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    return conversion_tasks[task_id]

@app.get("/stream-conversion-progress/{task_id}")
async def stream_conversion_progress(task_id: str):
    """
    Server-Sent Events를 사용하여 변환 진행 상황을 스트리밍합니다.
    
    Args:
        task_id: 작업 ID
        
    Returns:
        SSE 스트림
    """
    if task_id not in conversion_tasks:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    async def event_generator():
        last_progress = -1
        last_status = ""
        last_log_count = 0
        
        while True:
            task = conversion_tasks[task_id]
            current_progress = task["progress"]
            current_status = task["status"]
            current_log_count = len(task["logs"])
            
            if (current_progress != last_progress or 
                current_status != last_status or 
                current_log_count != last_log_count):
                
                event_data = {
                    "progress": current_progress,
                    "status": current_status,
                    "logs": task["logs"]
                }
                
                if current_status == "완료" and task["result"]:
                    event_data["result"] = task["result"]
                
                if current_status == "오류" and task["error"]:
                    event_data["error"] = task["error"]
                
                yield f"data: {json.dumps(event_data)}\n\n"
                
                last_progress = current_progress
                last_status = current_status
                last_log_count = current_log_count
                
                if current_status in ["완료", "오류"]:
                    break
            
            await asyncio.sleep(0.5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
