# Use an official lightweight Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create the data directory for the ChromaDB volume
RUN mkdir -p /app/data

# Make the startup script executable
RUN chmod +x start.sh

# Launch both the API and the UI
CMD ["./start.sh"]