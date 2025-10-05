# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install Tesseract OCR
RUN apt-get update && apt-get install -y tesseract-ocr libmagic1 poppler-utils

WORKDIR /app

# Add src to python path
ENV PYTHONPATH "${PYTHONPATH}:/app/src"

# Copy the requirements file into the container at /app
COPY api-requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r api-requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run your app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]