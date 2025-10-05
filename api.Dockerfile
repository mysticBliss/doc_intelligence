FROM python:3.12

WORKDIR /app

ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y tesseract-ocr poppler-utils && rm -rf /var/lib/apt/lists/*

COPY api-requirements.txt .

RUN pip install --no-cache-dir -r api-requirements.txt

COPY ./src ./src

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]