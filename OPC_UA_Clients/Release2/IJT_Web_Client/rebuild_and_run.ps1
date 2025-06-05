
# PowerShell script to rebuild and run the Docker container

# Stop and remove the existing container
Write-Output "Stopping and removing existing container..."
docker stop ijt_web_client
docker rm ijt_web_client

# Remove the existing image
Write-Output "Removing existing Docker image..."
docker rmi ijt_web_client

# Rebuild the Docker image without cache
Write-Output "Rebuilding Docker image..."
docker build --no-cache -t ijt_web_client .

# Check if the build was successful
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed. Exiting script."
    exit $LASTEXITCODE
}

# Run the Docker container
Write-Output "Running Docker container..."
docker run --name ijt_web_client -d -p 3000:3000 ijt_web_client

# Check if the container started successfully
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to start Docker container. Exiting script."
    exit $LASTEXITCODE
}

# Follow the container logs
Write-Output "Following Docker container logs..."
docker logs -f ijt_web_client
