FROM python:3.11-slim

# Create app directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run script
ENTRYPOINT ["python3", "immich-smart-albums.py"] 