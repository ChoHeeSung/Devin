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

app = FastAPI(title="PDF to Markdown Converter")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render the main page
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/convert-pdf")
async def convert_pdf_to_markdown(file: UploadFile = File(...)):
    """
    Convert a PDF file to Markdown format.
    
    Args:
        file: The PDF file to convert
        
    Returns:
        Dict containing the markdown content
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
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
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
