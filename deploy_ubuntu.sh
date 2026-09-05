#!/bin/bash

# Detect local IP address of Ubuntu Server
SERVER_IP=$(hostname -I | awk '{print $1}')
export SERVER_API_URL="http://${SERVER_IP}:8000"

echo "🚀 Deploying AeroSplit AI on Ubuntu Server..."
echo "📍 Server IP Detected: ${SERVER_IP}"
echo "🔗 Frontend will connect to Backend API at: ${SERVER_API_URL}"

# 1. Install Docker & Docker Compose if missing
if ! command -v docker &> /dev/null
then
    echo "📦 Docker not found. Installing Docker and Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose-v2
    sudo systemctl enable --now docker
    sudo usermod -aG docker $USER
fi

# 2. Open firewall ports (UFW)
if command -v ufw &> /dev/null; then
    echo "🛡️ Opening UFW firewall ports 3000 and 8000..."
    sudo ufw allow 3000/tcp
    sudo ufw allow 8000/tcp
fi

# 3. Build and launch containers
echo "🔨 Building and launching containers..."
docker compose build --build-arg NEXT_PUBLIC_API_URL=${SERVER_API_URL} --no-cache
docker compose up -d

echo "=========================================================="
echo "🎉 AeroSplit AI is live and accessible across your network!"
echo "🌐 Access from any browser/desktop at:"
echo "   http://${SERVER_IP}:3000"
echo "=========================================================="
