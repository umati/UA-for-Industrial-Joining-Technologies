# Use official Node.js image with Python pre-installed
FROM node:22-slim

# Install Python and required tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv curl && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    IS_DOCKER=true \
    PATH="/app/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy package files and install JS dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Ensure permissions (optional, useful in CI/CD or Linux host environments)
RUN chmod +x setup_project.py

# Expose ports for live server and WebSocket server
EXPOSE 3000 8001

# Run the setup script (handles Python venv and servers)
CMD ["python3", "setup_project.py"]
