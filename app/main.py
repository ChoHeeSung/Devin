from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import tempfile
import shutil
from typing import Dict, Any
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType

app = FastAPI(title="PDF to Markdown 변환기")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    메인 페이지 렌더링
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/convert-pdf")
async def convert_pdf_to_markdown(file: UploadFile = File(...)):
    """
    PDF 파일을 마크다운 형식으로 변환합니다.
    
    Args:
        file: 변환할 PDF 파일
        
    Returns:
        마크다운 내용을 포함하는 Dict
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 지원됩니다")
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        loader = DoclingLoader(
            file_path=temp_file_path,
            export_type=ExportType.MARKDOWN,
        )
        
        documents = loader.load()
        
        markdown_content = ""
        for doc in documents:
            markdown_content += doc.page_content + "\n\n"
        
        return {
            "filename": file.filename,
            "markdown_content": markdown_content
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 처리 중 오류 발생: {str(e)}")
    
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
