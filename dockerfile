# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Set the working directory in the container
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy only the app code (no assets)
COPY app/ /app/app/

# Expose port 8000 for the FastAPI app
EXPOSE 8000

# Default command (overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]