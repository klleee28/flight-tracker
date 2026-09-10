#!/bin/bash

# Ensure script runs from the repository root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "🚀 AeroSplit AI - Automated Ubuntu Deployment Engine"
echo "=========================================================="

# 1. Pull latest updates automatically from GitHub
if command -v git &> /dev/null && [ -d ".git" ]; then
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
    echo "📥 Checking and pulling latest code from GitHub (branch: ${BRANCH})..."
    
    # Stash any untracked or permission changes so git pull always succeeds cleanly
    git stash 2>/dev/null || true
    
    if git pull origin "$BRANCH"; then
        echo "✅ Successfully updated to latest commit: $(git rev-parse --short HEAD)"
        echo "   Commit message: $(git log -1 --pretty=%B | head -n 1)"
    else
        echo "⚠️ git pull encountered an issue. Continuing with current local files."
    fi
    chmod +x deploy_ubuntu.sh 2>/dev/null || true
else
    echo "ℹ️ Not a git repository or git command missing. Skipping git pull."
fi

echo ""

# 2. Detect Public IP and Local IP
PUBLIC_IP=$(curl -s4 --max-time 4 https://ifconfig.me 2>/dev/null || curl -s4 --max-time 4 https://api.ipify.org 2>/dev/null || echo "")
LOCAL_IP=$(hostname -I | awk '{print $1}')
SERVER_IP="${PUBLIC_IP:-$LOCAL_IP}"
export SERVER_API_URL="http://${SERVER_IP}:8000"

echo "📍 Public IP Detected: ${PUBLIC_IP:-None (Local/Private only)}"
echo "📍 Local/Internal IP:  ${LOCAL_IP}"
echo "🔗 Internal API Proxy: Transparent routing via Next.js (No CORS or NAT loopback issues)"

# 3. Install Docker & Docker Compose if missing
if ! command -v docker &> /dev/null; then
    echo "📦 Docker not found. Installing Docker and Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose-v2
    sudo systemctl enable --now docker
    sudo usermod -aG docker $USER
fi

# Detect whether sudo is required for docker in current session
DOCKER_CMD="docker"
if ! docker info &> /dev/null; then
    DOCKER_CMD="sudo docker"
fi

# 4. Open firewall ports (UFW & iptables)
if command -v ufw &> /dev/null; then
    echo "🛡️ Configuring UFW firewall ports 3000 and 8000..."
    sudo ufw allow 3000/tcp
    sudo ufw allow 8000/tcp
fi

# Handle Oracle Cloud / RedHat style iptables rules if present
sudo iptables -I INPUT 1 -p tcp --dport 3000 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 1 -p tcp --dport 8000 -j ACCEPT 2>/dev/null || true

# 5. Build and launch containers
echo "🔨 Building and launching containers with ${DOCKER_CMD} (clean build & recreate)..."
if ! $DOCKER_CMD compose up -d --build --force-recreate; then
    echo "❌ Docker build or launch failed. Please review the error log above."
    exit 1
fi

# 4. Verification
echo ""
echo "🔍 Checking container status:"
$DOCKER_CMD compose ps

RUNNING_COUNT=$($DOCKER_CMD compose ps --status running -q 2>/dev/null | wc -l)
if [ "$RUNNING_COUNT" -eq 0 ]; then
    echo "❌ Containers failed to start. View logs with: ${DOCKER_CMD} compose logs"
    exit 1
fi

echo ""
echo "=========================================================="
echo "🎉 AeroSplit AI is live!"
if [ -n "$PUBLIC_IP" ]; then
    echo "🌐 Access from outside network (Public IP):"
    echo "   👉 http://${PUBLIC_IP}:3000"
fi
echo "🏠 Access from same local network / Wi-Fi (LAN IP):"
echo "   👉 http://${LOCAL_IP}:3000"
echo "⚡ Backend Swagger Docs / Direct API:"
echo "   👉 http://${LOCAL_IP}:8000/docs"
echo "=========================================================="
echo "💡 TIP: All API requests (/api/*) are automatically proxied"
echo "   through Next.js on port 3000. It works everywhere seamlessly!"
echo "=========================================================="
