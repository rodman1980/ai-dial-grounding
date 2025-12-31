---
title: Setup Guide
description: Comprehensive environment setup, dependency installation, and configuration instructions
version: 1.0.0
last_updated: 2025-12-31
related: [README.md, api.md, architecture.md]
tags: [setup, installation, configuration, docker, python]
---

# Setup Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Environment Management](#environment-management)
- [IDE Configuration](#ide-configuration)

## Prerequisites

### System Requirements

| Component | Minimum Version | Recommended | Notes |
|-----------|----------------|-------------|-------|
| Python | 3.11 | 3.11+ | Must support async/await |
| Docker | 20.10 | Latest | For User Service |
| Docker Compose | 2.0 | Latest | Container orchestration |
| RAM | 4 GB | 8 GB+ | For LLM operations |
| Disk Space | 2 GB | 5 GB+ | Vectorstores and models |

### Operating System Support

- ✅ **macOS**: 10.15+ (tested on Apple Silicon and Intel)
- ✅ **Linux**: Ubuntu 20.04+, Fedora 35+, Debian 11+
- ✅ **Windows**: Windows 10/11 with WSL2 (recommended) or native

### Required Software

1. **Python 3.11+**
   ```bash
   # Verify installation
   python --version
   # Should output: Python 3.11.x or higher
   ```

2. **Docker & Docker Compose**
   ```bash
   # Verify Docker
   docker --version
   # Should output: Docker version 20.x or higher
   
   # Verify Docker Compose
   docker-compose --version
   # Should output: docker-compose version 2.x or higher
   ```

3. **Git**
   ```bash
   git --version
   # Should output: git version 2.x or higher
   ```

### Access Requirements

- **EPAM VPN**: Required for DIAL API access
- **DIAL API Key**: Obtain from [EPAM Support Portal](https://support.epam.com/ess?id=sc_cat_item&table=sc_cat_item&sys_id=910603f1c3789e907509583bb001310c)

> **Important**: Without VPN and API key, you can explore code but cannot run LLM-dependent features.

---

## Quick Start

For experienced users who want to get running immediately:

```bash
# 1. Clone repository
git clone <repository-url>
cd ai-dial-grounding

# 2. Start User Service
docker-compose up -d

# 3. Create virtual environment
python -m venv dial_grounding
source dial_grounding/bin/activate  # macOS/Linux
# dial_grounding\Scripts\activate  # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure API key
export DIAL_API_KEY="your-api-key-here"  # macOS/Linux
# set DIAL_API_KEY=your-api-key-here     # Windows CMD

# 6. Verify setup
python -c "from task.user_client import UserClient; print('Success!')"

# 7. Run a demo
python -m task.t1.no_grounding
```

---

## Detailed Setup

### Step 1: Clone Repository

```bash
# Using HTTPS
git clone https://git.epam.com/path/to/ai-dial-grounding.git
cd ai-dial-grounding

# OR using SSH
git clone git@git.epam.com:path/to/ai-dial-grounding.git
cd ai-dial-grounding
```

**Verify structure**:
```bash
ls -la
# Should see: docker-compose.yml, requirements.txt, task/, etc.
```

---

### Step 2: Start User Service

The User Service provides mock user data via REST API.

#### Using Docker Compose (Recommended)

```bash
# Start service in detached mode
docker-compose up -d

# Verify container is running
docker-compose ps
# Should show: userservice (running)
```

**Configuration** (from [docker-compose.yml](../docker-compose.yml)):
```yaml
services:
  userservice:
    image: khshanovskyi/mockuserservice:latest
    ports:
      - "8041:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - GENERATE_USERS=true
      - USER_COUNT=1000  # Default: 1000 users
```

#### Health Check

```bash
# Test endpoint availability
curl http://localhost:8041/health

# Expected output:
# {"status":"healthy","service":"UserService",...}
```

#### Swagger UI

Open in browser: http://localhost:8041/docs

#### Service Management

```bash
# View logs
docker-compose logs -f userservice

# Stop service
docker-compose stop

# Restart service
docker-compose restart

# Remove service (data persists in ./data)
docker-compose down

# Remove service and data
docker-compose down -v
rm -rf ./data
```

---

### Step 3: Python Environment Setup

#### Create Virtual Environment

**Why?** Isolates project dependencies from system Python.

```bash
# Create virtualenv
python -m venv dial_grounding

# Activate (macOS/Linux)
source dial_grounding/bin/activate

# Activate (Windows CMD)
dial_grounding\Scripts\activate.bat

# Activate (Windows PowerShell)
dial_grounding\Scripts\Activate.ps1
```

**Verify activation**:
```bash
which python
# Should point to: /path/to/ai-dial-grounding/dial_grounding/bin/python
```

#### Upgrade pip

```bash
pip install --upgrade pip setuptools wheel
```

---

### Step 4: Install Dependencies

#### Core Dependencies

```bash
pip install -r requirements.txt
```

**Contents of [requirements.txt](../requirements.txt)**:
```
langchain-community==0.3.31
langchain-openai==1.0.2
langchain-chroma==1.0.0
faiss-cpu==1.12.0
requests>=2.28.0
```

#### Dependency Overview

| Package | Version | Purpose |
|---------|---------|---------|
| langchain-community | 0.3.31 | RAG framework, vectorstore integrations |
| langchain-openai | 1.0.2 | Azure OpenAI client wrappers |
| langchain-chroma | 1.0.0 | Chroma vectorstore integration |
| faiss-cpu | 1.12.0 | CPU-based vector similarity search |
| requests | 2.28.0+ | HTTP client for User Service API |

#### Optional Dependencies (Development)

```bash
# Linting and formatting
pip install black flake8 mypy

# Testing
pip install pytest pytest-asyncio

# Jupyter notebooks
pip install jupyter ipykernel
```

#### Verification

```bash
# Check installed packages
pip list | grep langchain

# Expected output:
# langchain-chroma       1.0.0
# langchain-community    0.3.31
# langchain-openai       1.0.2
```

---

### Step 5: Configure API Credentials

#### Obtain DIAL API Key

1. **Connect to EPAM VPN**
2. **Request API key**:
   - Visit: https://support.epam.com/ess?id=sc_cat_item&table=sc_cat_item&sys_id=910603f1c3789e907509583bb001310c
   - Follow instructions to obtain key
3. **Save key securely** (never commit to Git!)

#### Set Environment Variable

**Option 1: Terminal Session (Temporary)**

```bash
# macOS/Linux
export DIAL_API_KEY="your-actual-api-key-here"

# Windows CMD
set DIAL_API_KEY=your-actual-api-key-here

# Windows PowerShell
$env:DIAL_API_KEY="your-actual-api-key-here"
```

**Option 2: `.env` File (Persistent)**

Create a `.env` file in project root:

```bash
# .env
DIAL_API_KEY=your-actual-api-key-here
```

**Load with python-dotenv**:
```bash
pip install python-dotenv
```

Update [task/_constants.py](../task/_constants.py):
```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

DIAL_URL = 'https://ai-proxy.lab.epam.com'
API_KEY = os.getenv('DIAL_API_KEY', '')
```

**Option 3: Shell Profile (Permanent)**

Add to `~/.bashrc`, `~/.zshrc`, or `~/.bash_profile`:

```bash
export DIAL_API_KEY="your-actual-api-key-here"
```

Reload shell:
```bash
source ~/.zshrc  # or ~/.bashrc
```

#### Verification

```bash
# Check variable is set
echo $DIAL_API_KEY  # macOS/Linux
echo %DIAL_API_KEY%  # Windows CMD
echo $env:DIAL_API_KEY  # Windows PowerShell
```

---

## Configuration

### Project Configuration Files

#### 1. docker-compose.yml

Configure User Service behavior:

```yaml
environment:
  - USER_COUNT=1000      # Change number of generated users
  - GENERATE_USERS=true  # Auto-generate users on startup

volumes:
  - ./data:/app/data     # Persist user database
```

**Modify user count**:
```yaml
environment:
  - USER_COUNT=5000  # Generate 5000 users instead
```

#### 2. task/_constants.py

API endpoint configuration:

```python
import os

DIAL_URL = 'https://ai-proxy.lab.epam.com'
API_KEY = os.getenv('DIAL_API_KEY', '')

USER_SERVICE_ENDPOINT = "http://localhost:8041"
```

**For custom User Service port**:
```python
USER_SERVICE_ENDPOINT = os.getenv('USER_SERVICE_URL', "http://localhost:8041")
```

Then set:
```bash
export USER_SERVICE_URL="http://localhost:9000"
```

---

## Verification

### Step-by-Step Verification

#### 1. Verify Docker Service

```bash
# Check container status
docker ps | grep userservice

# Expected: Container running on port 8041
```

#### 2. Verify User Service API

```bash
# Health check
curl http://localhost:8041/health

# Fetch users
curl http://localhost:8041/v1/users | jq length
# Expected: 1000 (or your configured USER_COUNT)
```

#### 3. Verify Python Environment

```bash
# Ensure virtualenv is activated
which python
# Expected: /path/to/dial_grounding/bin/python

# Check Python version
python --version
# Expected: Python 3.11.x or higher
```

#### 4. Verify Dependencies

```bash
# Import test
python -c "import langchain_openai; print('LangChain OK')"
python -c "import faiss; print('FAISS OK')"
python -c "import chromadb; print('Chroma OK')"
```

#### 5. Verify UserClient

```bash
python << EOF
from task.user_client import UserClient
client = UserClient()
users = client.get_all_users()
print(f"Fetched {len(users)} users successfully!")
EOF
```

Expected output:
```
Get 1000 users successfully
Fetched 1000 users successfully!
```

#### 6. Verify API Key Configuration

```bash
python << EOF
from task._constants import API_KEY
if API_KEY:
    print(f"API key configured (length: {len(API_KEY)})")
else:
    print("⚠️  API key not set!")
EOF
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Docker Container Not Starting

**Symptoms**:
```bash
docker-compose up -d
# Error: Cannot start service userservice: port is already allocated
```

**Solution**:
```bash
# Check what's using port 8041
lsof -i :8041  # macOS/Linux
netstat -ano | findstr :8041  # Windows

# Change port in docker-compose.yml
ports:
  - "9000:8000"  # Use port 9000 instead

# Update USER_SERVICE_ENDPOINT in task/_constants.py
USER_SERVICE_ENDPOINT = "http://localhost:9000"
```

---

#### Issue 2: Python Version Mismatch

**Symptoms**:
```bash
python --version
# Python 3.9.x
```

**Solution**:
```bash
# Install Python 3.11 (macOS with Homebrew)
brew install python@3.11
python3.11 -m venv dial_grounding

# Install Python 3.11 (Ubuntu/Debian)
sudo apt update
sudo apt install python3.11 python3.11-venv
python3.11 -m venv dial_grounding

# Windows: Download from python.org
# https://www.python.org/downloads/
```

---

#### Issue 3: FAISS Installation Failure

**Symptoms**:
```bash
pip install faiss-cpu
# ERROR: Could not build wheels for faiss-cpu
```

**Solution A (Use conda)**:
```bash
conda install -c conda-forge faiss-cpu
```

**Solution B (Use pre-built wheels)**:
```bash
# Install from PyPI with specific version
pip install faiss-cpu==1.12.0 --no-cache-dir
```

**Solution C (macOS ARM64)**:
```bash
# Use architecture-specific installation
pip install faiss-cpu --extra-index-url https://pypi.org/simple
```

---

#### Issue 4: API Key Not Recognized

**Symptoms**:
```python
from task._constants import API_KEY
print(API_KEY)  # Outputs: empty string
```

**Solution**:
```bash
# 1. Check environment variable
echo $DIAL_API_KEY

# 2. If empty, set it again
export DIAL_API_KEY="your-key-here"

# 3. Verify in same terminal session
python -c "import os; print(os.getenv('DIAL_API_KEY'))"

# 4. If still empty, use .env file method (see Configuration section)
```

---

#### Issue 5: Chroma DB Persistence Issues

**Symptoms**:
```
chromadb.errors.ChromaError: Could not write to directory
```

**Solution**:
```bash
# Check permissions
ls -la data/vectorstores/t3/

# Fix permissions
chmod -R 755 data/vectorstores/

# Or delete and recreate
rm -rf data/vectorstores/t3/
python -m task.t3.in_out_grounding  # Will recreate
```

---

#### Issue 6: Connection Refused (User Service)

**Symptoms**:
```python
Exception: HTTP 500: Connection refused
```

**Solution**:
```bash
# 1. Check container is running
docker-compose ps

# 2. Restart container
docker-compose restart

# 3. Check logs
docker-compose logs userservice

# 4. Rebuild if needed
docker-compose down
docker-compose up -d --force-recreate
```

---

## Environment Management

### Managing Multiple Projects

Use `virtualenvwrapper` (optional but recommended):

```bash
# Install
pip install virtualenvwrapper

# Configure (add to ~/.bashrc or ~/.zshrc)
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

# Create environment
mkvirtualenv ai-grounding

# Activate
workon ai-grounding

# Deactivate
deactivate
```

### Freezing Dependencies

```bash
# Generate requirements with exact versions
pip freeze > requirements-lock.txt

# Install from lock file
pip install -r requirements-lock.txt
```

### Updating Dependencies

```bash
# Update specific package
pip install --upgrade langchain-openai

# Update all packages (use with caution)
pip list --outdated
pip install --upgrade $(pip list --outdated | awk 'NR>2 {print $1}')

# Regenerate requirements
pip freeze > requirements.txt
```

---

## IDE Configuration

### Visual Studio Code

#### Recommended Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "ms-azuretools.vscode-docker"
  ]
}
```

#### Python Interpreter

1. Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
2. Type "Python: Select Interpreter"
3. Choose: `./dial_grounding/bin/python`

#### settings.json

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/dial_grounding/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true
}
```

---

### PyCharm

1. **Open Project**: `File > Open` → Select `ai-dial-grounding` folder
2. **Configure Interpreter**:
   - `File > Settings > Project > Python Interpreter`
   - Click gear icon → `Add...`
   - Select `Existing environment`
   - Choose: `./dial_grounding/bin/python`
3. **Mark directories**:
   - Right-click `task/` → `Mark Directory as > Sources Root`

---

## Advanced Setup

### GPU Acceleration (Optional)

For faster embeddings, use GPU-enabled FAISS:

```bash
# Uninstall CPU version
pip uninstall faiss-cpu

# Install GPU version (requires CUDA)
pip install faiss-gpu

# Verify GPU usage
python -c "import faiss; print(faiss.get_num_gpus())"
```

### Custom Docker Build

Build User Service from source:

```bash
# Clone mock service repository
git clone <user-service-repo>
cd user-service

# Build image
docker build -t custom-userservice:latest .

# Update docker-compose.yml
# image: custom-userservice:latest

# Start
docker-compose up -d
```

---

## Next Steps

After successful setup:

1. **Explore Examples**: Run [task/t1/no_grounding.py](../task/t1/no_grounding.py)
2. **Read Architecture**: Review [Architecture Documentation](./architecture.md)
3. **Try Vector Search**: Experiment with [task/t2/Input_vector_based.py](../task/t2/Input_vector_based.py)
4. **Build Your Own**: Modify existing approaches or create new ones

---

## Related Documentation

- [Architecture](./architecture.md) - System design and patterns
- [API Reference](./api.md) - User Service API details
- [Testing Guide](./testing.md) - Running tests and validation

---

## Support

For setup issues:
- Check [Troubleshooting](#troubleshooting) section above
- Review Docker logs: `docker-compose logs`
- Verify prerequisites are met
- Contact project maintainers

---

**Setup Complete!** 🎉

Your environment is ready. Start with:
```bash
python -m task.t1.no_grounding
```
