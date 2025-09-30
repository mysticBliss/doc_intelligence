FROM python:3.12

WORKDIR /code

COPY api-requirements.txt .

# Force rebuild of dependencies
RUN pip install --no-cache-dir -r api-requirements.txt

COPY app/ ./app
COPY config/ ./config
COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]