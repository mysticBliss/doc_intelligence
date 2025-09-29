# Use an official Python runtime as a parent image
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy dependency-related files first to leverage Docker layer caching
COPY ui-requirements.txt .

# Install any needed packages specified in ui-requirements.txt
RUN pip install --no-cache-dir -r ui-requirements.txt

# Create directory for Gradio temporary files
RUN mkdir -p /tmp/gradio

# Copy the UI application code to the working directory
COPY app_ui.py .

# Command to run the application
CMD ["python", "app_ui.py"]