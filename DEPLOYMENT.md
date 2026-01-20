# Railway Deployment Guide

This guide explains how to deploy Daňový Poradce Pro to Railway.

## Prerequisites

1. [Railway account](https://railway.app/)
2. [Railway CLI](https://docs.railway.app/develop/cli) (optional but recommended)
3. Git repository (GitHub recommended)

## Quick Deployment Steps

### Option A: Deploy via GitHub (Recommended)

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/your-username/danovy-poradce-pro.git
   git push -u origin main
   ```

2. **Create a new project on Railway**
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Deploy Backend Service**
   - Click "New Service" → "GitHub Repo"
   - Select the repository
   - Set root directory to `backend`
   - Railway will auto-detect the Dockerfile

4. **Deploy Frontend Service**
   - Click "New Service" → "GitHub Repo"
   - Select the same repository
   - Set root directory to `frontend`
   - Add build variable: `VITE_API_URL` = your backend URL

5. **Configure Environment Variables** (see below)

### Option B: Deploy via CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init

# Deploy backend
cd backend
railway up

# Deploy frontend
cd ../frontend
railway up
```

## Environment Variables

### Backend Variables (Required)

Set these in Railway Dashboard → Backend Service → Variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL URL (auto-set if using Railway PostgreSQL) | `postgresql://...` |
| `CORS_ORIGINS` | Allowed frontend origins | `["https://your-frontend.railway.app"]` |
| `DEBUG` | Debug mode | `false` |

### Backend Variables (Optional)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude AI API key |
| `APPSTORE_KEY_ID` | App Store Connect Key ID |
| `APPSTORE_ISSUER_ID` | App Store Connect Issuer ID |
| `DATABASE_ENCRYPTION_KEY` | SQLite encryption key |

### Frontend Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `https://your-backend.railway.app` |

## Adding PostgreSQL Database

For production, use PostgreSQL instead of SQLite:

1. In Railway Dashboard, click "New Service"
2. Select "Database" → "PostgreSQL"
3. Railway auto-creates `DATABASE_URL` variable
4. Link it to your backend service

## Custom Domain

1. Go to Service → Settings → Domains
2. Click "Generate Domain" or add custom domain
3. Update `CORS_ORIGINS` with new domain
4. Update frontend `VITE_API_URL` with backend domain

## Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│                   Railway                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  Frontend   │  │   Backend   │  │ Postgres│ │
│  │   (Nginx)   │→ │  (FastAPI)  │→ │   DB    │ │
│  │   :80       │  │   :8000     │  │  :5432  │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────┘
```

## Troubleshooting

### Build Fails

1. Check logs in Railway Dashboard
2. Ensure Dockerfile is correct
3. Verify all dependencies in `pyproject.toml` / `package.json`

### Backend Not Starting

1. Check `DATABASE_URL` is set correctly
2. Verify health check endpoint works: `/api/v1/system/health`
3. Check logs for Python errors

### Frontend Can't Connect to Backend

1. Verify `VITE_API_URL` points to correct backend URL
2. Check `CORS_ORIGINS` includes frontend domain
3. Ensure backend is running and healthy

### Database Connection Issues

1. If using SQLite: ensure `/app/data` directory exists
2. If using PostgreSQL: verify `DATABASE_URL` format
3. Check database service is running

## Costs

Railway pricing (as of 2025):
- **Hobby Plan**: $5/month credit (usually enough for small apps)
- **Pro Plan**: $20/month + usage

Typical usage for this app:
- Backend: ~$2-5/month
- Frontend: ~$1-2/month
- PostgreSQL: ~$5/month

## Monitoring

1. **Health Check**: `/api/v1/system/health`
2. **Logs**: Railway Dashboard → Service → Logs
3. **Metrics**: Railway Dashboard → Service → Metrics

## Updating the App

With GitHub integration, simply push to main:

```bash
git add .
git commit -m "Update feature X"
git push
```

Railway will auto-deploy on push.

## Rolling Back

1. Go to Railway Dashboard → Service → Deployments
2. Find the previous working deployment
3. Click "Redeploy"
