# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy the rest of your project code into the container
COPY . .

# Expose port 8000 for the FastAPI app
EXPOSE 8000

# Set the default command to run your FastAPI application.
# You might change this in docker-compose for the worker service.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
