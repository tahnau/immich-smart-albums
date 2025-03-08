FROM python:3.11-slim

# Create app directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY immich-smart-albums.py .
COPY immich-smart-albums.sh .
COPY filters/ ./filters/

# Create non-root user and set permissions
RUN useradd -m -r -u 1000 immich && \
    chmod +x immich-smart-albums.sh && \
    chown -R immich:immich /app

# Switch to non-root user
USER immich

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run script
ENTRYPOINT ["/app/immich-smart-albums.sh"] 