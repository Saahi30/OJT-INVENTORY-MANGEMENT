# Deployment Guide
## FastAPI Inventory Reservation Service

This guide covers multiple deployment options, from free platforms to production-ready solutions.

---

## Table of Contents

1. [Quick Deploy Options (Free)](#quick-deploy-options-free)
   - [Render.com](#rendercom-recommended-free)
   - [Railway.app](#railwayapp-free-tier)
   - [Fly.io](#flyio-free-tier)
2. [Production Deployment](#production-deployment)
   - [Docker Deployment](#docker-deployment)
   - [VPS Deployment](#vps-deployment)
3. [Database Setup](#database-setup)
4. [Environment Configuration](#environment-configuration)
5. [Post-Deployment](#post-deployment)

---

## Quick Deploy Options (Free)

### Render.com (Recommended - Free)

**Pros:** Free tier, PostgreSQL included, easy setup, automatic HTTPS

#### Step 1: Prepare for Deployment

1. **Create `Procfile`** (for Render):
```bash
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile
```

2. **Update `requirements.txt`** (ensure all dependencies are listed):
```txt
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sqlalchemy>=2.0.36
asyncpg>=0.30.0
aiosqlite>=0.20.0
alembic>=1.14.0
pydantic>=2.10.0
pydantic-settings>=2.6.0
python-dotenv>=1.0.1
pytest>=8.3.0
pytest-asyncio>=0.24.0
httpx>=0.28.0
requests>=2.32.0
rich>=13.8.0
click>=8.1.8
greenlet>=3.1.0
```

#### Step 2: Deploy on Render

1. **Sign up** at [render.com](https://render.com) (free account)

2. **Create a New Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Or use "Public Git repository" and paste your repo URL

3. **Configure the Service:**
   - **Name:** `inventory-reservation-service`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (or paid for production)

4. **Add PostgreSQL Database:**
   - Click "New +" → "PostgreSQL"
   - Name: `inventory-db`
   - Plan: Free (or paid)
   - **Copy the Internal Database URL** (you'll need this)

5. **Set Environment Variables:**
   In your Web Service settings, add:
   ```
   DATABASE_URL=<paste the PostgreSQL Internal Database URL>
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   ```

6. **Deploy:**
   - Click "Create Web Service"
   - Render will build and deploy automatically
   - Wait 5-10 minutes for first deployment

7. **Access Your App:**
   - Your app will be available at: `https://inventory-reservation-service.onrender.com`
   - API docs: `https://inventory-reservation-service.onrender.com/docs`

#### Step 3: Initialize Database

After deployment, you need to create the database tables:

**Option A: Using Render Shell**
1. Go to your Web Service → "Shell"
2. Run:
```bash
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

**Option B: Using Python Script**
Create a file `init_db.py`:
```python
import asyncio
from app.database import init_db

if __name__ == "__main__":
    asyncio.run(init_db())
```

Then run it in Render Shell:
```bash
python init_db.py
```

---

### Railway.app (Free Tier)

**Pros:** Free tier, PostgreSQL included, easy setup

#### Steps:

1. **Sign up** at [railway.app](https://railway.app)

2. **Create New Project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo" (or upload code)

3. **Add PostgreSQL:**
   - Click "+ New" → "Database" → "PostgreSQL"
   - Railway automatically creates the database

4. **Configure Environment:**
   - Railway auto-detects Python
   - Add environment variable:
     ```
     DATABASE_URL=${{Postgres.DATABASE_URL}}
     ```
   - Railway automatically injects the database URL

5. **Deploy:**
   - Railway auto-deploys on git push
   - Or click "Deploy Now"

6. **Initialize Database:**
   - Use Railway CLI or web terminal:
   ```bash
   python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
   ```

7. **Access:**
   - Railway provides a URL like: `https://your-app.up.railway.app`

---

### Fly.io (Free Tier)

**Pros:** Free tier, global edge locations, fast

#### Steps:

1. **Install Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Sign up:**
   ```bash
   fly auth signup
   ```

3. **Create `fly.toml`:**
   ```bash
   fly launch
   ```
   Follow the prompts.

4. **Add PostgreSQL:**
   ```bash
   fly postgres create --name inventory-db
   fly postgres attach inventory-db
   ```

5. **Deploy:**
   ```bash
   fly deploy
   ```

6. **Initialize Database:**
   ```bash
   fly ssh console
   python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
   ```

---

## Production Deployment

### Docker Deployment

#### Step 1: Create Dockerfile

Create `Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Step 2: Create .dockerignore

Create `.dockerignore`:
```
venv/
__pycache__/
*.pyc
.env
.git
.gitignore
*.md
.pytest_cache/
```

#### Step 3: Build and Run

```bash
# Build image
docker build -t inventory-service .

# Run container
docker run -d \
  --name inventory-app \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname \
  inventory-service
```

#### Step 4: Deploy to Cloud

**Option A: Docker Hub + Any Cloud Provider**
1. Push to Docker Hub:
   ```bash
   docker tag inventory-service yourusername/inventory-service
   docker push yourusername/inventory-service
   ```
2. Deploy on any cloud provider that supports Docker

**Option B: AWS ECS/Fargate**
- Use AWS ECS with Fargate
- Create task definition with your Docker image
- Set up load balancer

**Option C: Google Cloud Run**
```bash
gcloud run deploy inventory-service \
  --image gcr.io/PROJECT_ID/inventory-service \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

### VPS Deployment

For deployment on a VPS (DigitalOcean, Linode, AWS EC2, etc.):

#### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install python3.12 python3.12-venv python3-pip -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Nginx (for reverse proxy)
sudo apt install nginx -y
```

#### Step 2: Setup Application

```bash
# Clone your repository
git clone <your-repo-url> /opt/inventory-service
cd /opt/inventory-service

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 3: Setup PostgreSQL

```bash
# Create database and user
sudo -u postgres psql
```

In PostgreSQL:
```sql
CREATE DATABASE inventory_db;
CREATE USER inventory_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;
\q
```

#### Step 4: Configure Environment

```bash
# Create .env file
nano /opt/inventory-service/.env
```

Add:
```
DATABASE_URL=postgresql+asyncpg://inventory_user:your_secure_password@localhost:5432/inventory_db
ENVIRONMENT=production
LOG_LEVEL=INFO
```

#### Step 5: Initialize Database

```bash
cd /opt/inventory-service
source venv/bin/activate
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

#### Step 6: Setup Systemd Service

Create `/etc/systemd/system/inventory-service.service`:
```ini
[Unit]
Description=Inventory Reservation Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/inventory-service
Environment="PATH=/opt/inventory-service/venv/bin"
ExecStart=/opt/inventory-service/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable inventory-service
sudo systemctl start inventory-service
sudo systemctl status inventory-service
```

#### Step 7: Setup Nginx Reverse Proxy

Create `/etc/nginx/sites-available/inventory-service`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/inventory-service /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 8: Setup SSL (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

## Database Setup

### For Cloud Deployments

Most platforms (Render, Railway, Fly.io) provide managed PostgreSQL. Just:
1. Create the database service
2. Use the provided connection string
3. Initialize tables (see initialization steps above)

### For Self-Hosted

**PostgreSQL Setup:**
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb inventory_db

# Create user
sudo -u postgres psql
CREATE USER inventory_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;
\q
```

**Initialize Tables:**
```python
# Run this once after deployment
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

---

## Environment Configuration

### Required Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Optional Environment Variables

```bash
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
EXPIRY_CHECK_INTERVAL_SECONDS=60
OPTIMISTIC_MAX_RETRIES=3
PESSIMISTIC_LOCK_TIMEOUT_SECONDS=30
```

---

## Post-Deployment

### 1. Verify Deployment

```bash
# Health check
curl https://your-app-url.com/health

# API docs
# Open: https://your-app-url.com/docs
```

### 2. Test Endpoints

```bash
# Create a product
curl -X POST "https://your-app-url.com/api/v1/skus" \
  -H "Content-Type: application/json" \
  -d '{
    "sku_code": "TEST-001",
    "name": "Test Product",
    "initial_qty": 100
  }'

# Check availability
curl "https://your-app-url.com/api/v1/inventory/availability"
```

### 3. Monitor Logs

**Render:**
- Go to your service → "Logs" tab

**Railway:**
- Go to your service → "Deployments" → View logs

**VPS:**
```bash
sudo journalctl -u inventory-service -f
```

### 4. Update CLI to Use Production URL

Update `cli.py`:
```python
API_BASE_URL = "https://your-app-url.com"  # Change from localhost
```

Or use environment variable:
```python
import os
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
```

---

## How Users Access Your Service

### Option 1: API Access (Direct)

Users can access your API directly:

**Base URL:** `https://your-app-url.com`

**Endpoints:**
- API Docs: `https://your-app-url.com/docs`
- Health: `https://your-app-url.com/health`
- Create Product: `POST https://your-app-url.com/api/v1/skus`
- Create Hold: `POST https://your-app-url.com/api/v1/inventory/holds`
- Check Availability: `GET https://your-app-url.com/api/v1/inventory/availability`

**Example using curl:**
```bash
curl -X POST "https://your-app-url.com/api/v1/inventory/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "client_token": "user-token-123",
    "items": [{"sku_id": "uuid-here", "qty": 5}],
    "expires_in_seconds": 300,
    "strategy": "optimistic"
  }'
```

### Option 2: CLI Tool

Users can download and use your CLI:

1. **Clone repository:**
   ```bash
   git clone <your-repo-url>
   cd OJT-INVENTORY-MANGEMENT
   ```

2. **Setup:**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure API URL:**
   ```bash
   export API_BASE_URL=https://your-app-url.com
   # Or edit cli.py to change default
   ```

4. **Use CLI:**
   ```bash
   ./startservice
   ```

### Option 3: Web Interface (Future)

You could build a simple web frontend using:
- React/Vue.js
- HTML + JavaScript
- Or use FastAPI's built-in form support

---

## Recommended Deployment Path

### For Demo/Presentation:
**Use Render.com** - Free, easy, fast setup

### For Production:
**Use Railway.app or Fly.io** - Better performance, more reliable

### For Learning/Full Control:
**Use VPS (DigitalOcean, Linode)** - Learn server management

---

## Quick Start: Render.com (Recommended)

1. **Create `Procfile`:**
   ```bash
   echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile
   ```

2. **Push to GitHub** (if not already)

3. **Go to render.com** → New Web Service → Connect GitHub

4. **Add PostgreSQL** → New PostgreSQL

5. **Set Environment Variable:**
   ```
   DATABASE_URL=<from PostgreSQL service>
   ```

6. **Deploy** → Wait 5-10 minutes

7. **Initialize Database:**
   - Go to Shell → Run initialization command

8. **Access:** `https://your-app.onrender.com/docs`

---

## Troubleshooting

### Database Connection Issues
- Check `DATABASE_URL` format
- Ensure database is accessible
- Check firewall rules

### Port Issues
- Use `$PORT` environment variable (Render, Railway)
- Or hardcode port 8000 (VPS)

### Import Errors
- Ensure all dependencies in `requirements.txt`
- Check Python version (3.12)

### Slow First Request
- Normal on free tiers (cold starts)
- Consider paid tier for production

---

## Security Checklist

- [ ] Use strong database passwords
- [ ] Enable HTTPS (automatic on most platforms)
- [ ] Set `ENVIRONMENT=production`
- [ ] Review and restrict CORS if needed
- [ ] Use environment variables for secrets
- [ ] Enable database backups
- [ ] Monitor logs for errors
- [ ] Set up rate limiting (future enhancement)

---

## Next Steps

1. **Choose a deployment platform**
2. **Follow the steps for that platform**
3. **Test your deployed API**
4. **Share the URL with users**
5. **Monitor and maintain**

Good luck with deployment! 🚀

