FROM nikolaik/python-nodejs:python3.13-nodejs24

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python packages globally
RUN pip install --upgrade pip && \
    pip install requests python-dotenv nodeenv websockets asyncua packaging

# Environment variables
ENV IS_DOCKER=true
ENV PYTHONUNBUFFERED=1

# Copy project files
COPY . .

# Install additional requirements if present
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Make setup script executable
RUN chmod +x setup_project.py

EXPOSE 3000 8001

# Default command
CMD ["python", "setup_project.py", "--force_full"]