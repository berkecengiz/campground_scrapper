# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Install PostgreSQL dependencies
RUN apt-get update && apt-get install -y libpq-dev build-essential

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file to the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project to the container
COPY . .
ENV PYTHONPATH=/app/src

# Set environment variables to avoid Python bytecode files and log output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose the port your app will run on (e.g., 8000 for FastAPI)
EXPOSE 8000

# Set the default command to run the app
CMD ["python", "-m", "src.campground_scraper.main"]
