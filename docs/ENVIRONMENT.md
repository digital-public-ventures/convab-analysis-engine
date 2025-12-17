# Environment Setup Guide

**Purpose**: Document system dependencies, toolchain requirements, and platform-specific setup instructions.

**Last Updated**: 2025-12-17

---

## Table of Contents

- [System Requirements](#system-requirements)
- [Required Tools](#required-tools)
- [Platform-Specific Setup](#platform-specific-setup)
- [Installation Guide](#installation-guide)
- [Environment Variables](#environment-variables)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

- **OS**: macOS 11+, Ubuntu 20.04+, Windows 10+ (WSL2)
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 10 GB free space

### Recommended Requirements

- **OS**: macOS 13+, Ubuntu 22.04+, Windows 11 (WSL2)
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Disk**: 20+ GB free space (SSD preferred)

---

## Required Tools

### Core Tools

**Git** (version control)

- Minimum: 2.30+
- Recommended: 2.40+
- Install: https://git-scm.com/downloads

**Make** (build automation)

- Minimum: 3.81+
- Recommended: 4.0+
- Included on macOS/Linux, install via WSL on Windows

### Language/Framework Specific

Choose the tools relevant to your project:

**Python Projects**

- Python: 3.8+ (Recommended: 3.11+)
- pip: Latest
- virtualenv or venv

**Node.js Projects**

- Node.js: 16+ (Recommended: 20 LTS)
- npm: 8+ (or yarn 3+, pnpm 8+)

**Go Projects**

- Go: 1.19+ (Recommended: 1.21+)

**Rust Projects**

- Rust: 1.70+ (Recommended: Latest stable)
- Cargo: Included with Rust

**Java Projects**

- JDK: 11+ (Recommended: 17 LTS or 21 LTS)
- Maven: 3.6+ or Gradle: 7.0+

### Development Tools

**Code Editor** (choose one):

- VS Code: https://code.visualstudio.com/
- Cursor: https://cursor.sh/
- IntelliJ IDEA / PyCharm / WebStorm: https://www.jetbrains.com/
- Vim/Neovim with LSP

**Docker** (optional, for containerized development):

- Docker Desktop: 4.0+
- Docker Compose: 2.0+
- Install: https://www.docker.com/products/docker-desktop

### Optional Tools

**Database Clients**:

- PostgreSQL: `psql` or pgAdmin
- MySQL: `mysql` or MySQL Workbench
- MongoDB: `mongosh` or MongoDB Compass
- Redis: `redis-cli` or RedisInsight

**API Testing**:

- curl (command line)
- Postman or Insomnia (GUI)
- HTTPie (modern curl alternative)

**Cloud CLI Tools** (if deploying to cloud):

- AWS CLI: https://aws.amazon.com/cli/
- Google Cloud SDK: https://cloud.google.com/sdk
- Azure CLI: https://docs.microsoft.com/cli/azure/

---

## Platform-Specific Setup

### macOS

**Install Homebrew** (package manager):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Install development tools**:

```bash
# Command Line Tools (includes git, make)
xcode-select --install

# Language runtimes (examples)
brew install python@3.11
brew install node@20
brew install go
brew install rust

# Databases (if needed)
brew install postgresql@15
brew install redis
brew install mongodb-community

# Development tools
brew install docker
brew install visual-studio-code
```

**Shell setup** (zsh is default):

```bash
# Add to ~/.zshrc
export PATH="/usr/local/bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"

# Python (if installed via Homebrew)
export PATH="/usr/local/opt/python@3.11/bin:$PATH"

# Node (if using nvm)
export NVM_DIR="$HOME/.nvm"
[ -s "/usr/local/opt/nvm/nvm.sh" ] && \. "/usr/local/opt/nvm/nvm.sh"
```

### Linux (Ubuntu/Debian)

**Update package lists**:

```bash
sudo apt update
```

**Install build essentials**:

```bash
sudo apt install -y build-essential git make curl wget
```

**Install language runtimes**:

```bash
# Python
sudo apt install -y python3.11 python3-pip python3-venv

# Node.js (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Go
wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc

# Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Install databases**:

```bash
# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Redis
sudo apt install -y redis-server

# MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org
```

**Install Docker**:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect
```

### Windows (WSL2)

**Install WSL2**:

```powershell
# In PowerShell (as Administrator)
wsl --install
# Restart computer
# Set up Ubuntu user account
```

**Update and install tools** (in WSL):

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git make curl wget

# Follow Linux instructions above for language runtimes
```

**Docker Desktop for Windows**:

- Download: https://www.docker.com/products/docker-desktop
- Enable WSL2 integration in Docker Desktop settings

**VS Code with WSL**:

- Install VS Code on Windows
- Install "Remote - WSL" extension
- Open WSL directory: `code .` in WSL terminal

---

## Installation Guide

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/jimmoffet/cfpb-exploration.git
cd cfpb-exploration

# 2. Check environment
make doctor

# 3. Install dependencies
make setup

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Run tests
make test

# 6. Start development server
make run
```

### Detailed Setup

**Python Projects**:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Install pre-commit hooks
pre-commit install
```

**Node.js Projects**:

```bash
# Install dependencies
npm install

# Or with yarn
yarn install

# Or with pnpm
pnpm install

# Install development tools
npm install -D eslint prettier typescript

# Build project
npm run build
```

**Go Projects**:

```bash
# Download dependencies
go mod download

# Install development tools
go install golang.org/x/tools/gopls@latest
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# Build project
go build -o bin/cfpb-exploration ./cmd/cfpb-exploration
```

**Docker-based Setup**:

```bash
# Build containers
docker compose build

# Start services
docker compose up -d

# Run commands in container
docker compose exec app bash
```

---

## Environment Variables

### Required Variables

Create `.env` from `.env.example`:

```bash
# Copy template
cp .env.example .env

# Edit with your values
vim .env
```

**Example `.env.example`**:

```bash
# Application
NODE_ENV=development
PORT=3000
LOG_LEVEL=debug

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379

# External Services
API_KEY=your_api_key_here
STRIPE_SECRET_KEY=sk_test_...
SENDGRID_API_KEY=SG...

# Security
JWT_SECRET=generate_random_secret_here
SESSION_SECRET=another_random_secret

# Feature Flags
ENABLE_FEATURE_X=false
```

### Generating Secrets

```bash
# Generate random secret (32 bytes)
openssl rand -base64 32

# Or using Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Or using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

### Loading Environment Variables

**Python**:

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load from .env file

DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY")
```

**Node.js**:

```javascript
require('dotenv').config();

const DATABASE_URL = process.env.DATABASE_URL;
const API_KEY = process.env.API_KEY;
```

**Go**:

```go
import "github.com/joho/godotenv"

func init() {
    godotenv.Load()
}

databaseURL := os.Getenv("DATABASE_URL")
apiKey := os.Getenv("API_KEY")
```

---

## Verification

### Check Installation

Run `make doctor` to verify your environment:

```bash
make doctor
```

Expected output:

```
🏥 Checking development environment...

→ Checking for git...
  ✓ git found: git version 2.40.0

→ Checking for python3...
  ✓ python3 found: Python 3.11.5

→ Checking for node...
  ✓ node found: v20.10.0

→ Checking for docker...
  ✓ docker found: Docker version 24.0.6

✓ Environment check complete
```

### Manual Verification

**Git**:

```bash
git --version
# Expected: git version 2.30+
```

**Python**:

```bash
python3 --version
# Expected: Python 3.8+

pip3 --version
# Expected: pip 20.0+
```

**Node.js**:

```bash
node --version
# Expected: v16.0+

npm --version
# Expected: 8.0+
```

**Docker**:

```bash
docker --version
# Expected: Docker version 20.10+

docker compose version
# Expected: Docker Compose version 2.0+
```

---

## Troubleshooting

### Common Issues

#### Command Not Found

**Problem**: `command not found: python3`

**Solution**:

```bash
# macOS
brew install python@3.11

# Linux
sudo apt install python3.11

# Windows WSL
sudo apt install python3
```

#### Permission Denied

**Problem**: `Permission denied` when running scripts

**Solution**:

```bash
# Make script executable
chmod +x script.sh

# Or run with explicit interpreter
bash script.sh
python3 script.py
```

#### Port Already in Use

**Problem**: `Error: listen EADDRINUSE: address already in use :::3000`

**Solution**:

```bash
# Find process using port
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
PORT=3001 npm start
```

#### SSL Certificate Errors

**Problem**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solution**:

```bash
# macOS: Install certificates
/Applications/Python\ 3.11/Install\ Certificates.command

# Ubuntu: Update CA certificates
sudo apt install ca-certificates
sudo update-ca-certificates

# Use environment variable (temporary workaround)
export NODE_TLS_REJECT_UNAUTHORIZED=0  # Node.js
export PYTHONHTTPSVERIFY=0  # Python (NOT recommended for production)
```

#### Docker Issues

**Problem**: `Cannot connect to the Docker daemon`

**Solution**:

```bash
# macOS: Start Docker Desktop

# Linux: Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Windows WSL: Enable WSL integration in Docker Desktop
```

### Getting Help

If you encounter issues not covered here:

1. Check project-specific documentation in `docs/`
2. Search closed issues on GitHub
3. Ask in project chat/forum
4. Create new issue with:
   - OS and version
   - Tool versions (`make doctor` output)
   - Error message
   - Steps to reproduce

---

## See Also

- [Quick Start Guide](QUICK_START.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [Agent Operations](AGENT_OPERATIONS.md)
- [Observability Guide](OBSERVABILITY.md)
