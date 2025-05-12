FROM python:3.12-slim

WORKDIR /app

# Install dependencies directly
RUN pip install fastapi uvicorn langchain-docling langchain-core python-multipart jinja2

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["python", "-m", "app.main"]
