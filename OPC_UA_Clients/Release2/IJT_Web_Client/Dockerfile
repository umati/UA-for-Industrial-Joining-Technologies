# Use a minimal Python base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    IS_DOCKER=true \
    PATH="/app/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Ensure setup script is executable
RUN chmod +x setup_project.py

# Expose ports for HTTP and WebSocket servers
EXPOSE 3000 8001

# Run the setup script with full setup
CMD ["python", "setup_project.py", "--force_full"]