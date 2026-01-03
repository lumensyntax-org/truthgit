# TruthGit Deployment Guide

## Production Stack

| Component | Platform | URL |
|-----------|----------|-----|
| API | Railway | `https://truthgit-production.up.railway.app` |
| UI | Vercel | `https://www.truthgit.com` |

---

## Railway Deployment (API)

### Prerequisites

- Railway account
- GitHub repository connected to Railway
- API keys for validators (see Configuration)

### Setup

1. **Create Railway Project**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli

   # Login and link
   railway login
   railway link
   ```

2. **Configure Environment Variables**

   In Railway Dashboard → Variables, add:

   ```env
   # Required for Claude validator
   ANTHROPIC_API_KEY=sk-ant-api03-...

   # Required for Logos6 validator (Vertex AI)
   GOOGLE_CREDENTIALS_BASE64=<base64-encoded-service-account-json>

   # Optional: GPT validator
   OPENAI_API_KEY=sk-...
   ```

3. **Deploy**

   Railway auto-deploys on push to `main`. Manual deploy:
   ```bash
   railway up
   ```

### Files Required

- `requirements.txt` - Python dependencies
- `Procfile` - Start command:
  ```
  web: uvicorn truthgit.api.server:app --host 0.0.0.0 --port $PORT
  ```
- `pyproject.toml` - Package configuration

### Generate GCP Credentials Base64

```bash
# From service account JSON file
cat service-account.json | base64 -w 0 > credentials_base64.txt

# Copy the contents to Railway GOOGLE_CREDENTIALS_BASE64
```

---

## Vercel Deployment (UI)

The TruthGit UI is a Next.js app deployed on Vercel.

### Prerequisites

- Vercel account
- GitHub repository for UI

### Environment Variables

In Vercel Dashboard → Settings → Environment Variables:

```env
# API Connection
NEXT_PUBLIC_API_URL=https://truthgit-production.up.railway.app

# NextAuth Configuration
NEXTAUTH_URL=https://www.truthgit.com
NEXTAUTH_SECRET=<generated-secret>
AUTH_URL=https://www.truthgit.com

# GitHub OAuth
AUTH_GITHUB_ID=<github-oauth-app-client-id>
AUTH_GITHUB_SECRET=<github-oauth-app-client-secret>
```

### GitHub OAuth App Setup

1. Go to GitHub → Settings → Developer settings → OAuth Apps
2. Create new OAuth App:
   - Homepage URL: `https://www.truthgit.com`
   - Callback URL: `https://www.truthgit.com/api/auth/callback/github`
3. Copy Client ID and Secret to Vercel env vars

---

## Validators Configuration

### Claude (Anthropic)

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
```

Model: `claude-3-haiku-20240307`

### Logos6 (Vertex AI)

1. **Create GCP Service Account**
   ```bash
   # Create service account
   gcloud iam service-accounts create truthgit-api \
     --display-name="TruthGit API"

   # Grant Vertex AI permissions
   gcloud projects add-iam-policy-binding lumen-syntax \
     --member="serviceAccount:truthgit-api@lumen-syntax.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"

   # Generate key
   gcloud iam service-accounts keys create truthgit-sa.json \
     --iam-account=truthgit-api@lumen-syntax.iam.gserviceaccount.com
   ```

2. **Encode and Configure**
   ```bash
   # Encode to base64
   base64 -w 0 truthgit-sa.json > credentials.b64

   # Add to Railway
   # GOOGLE_CREDENTIALS_BASE64=<contents of credentials.b64>
   ```

### GPT (OpenAI)

```env
OPENAI_API_KEY=sk-...
```

Model: `gpt-4o-mini`

---

## Monitoring

### Health Check

```bash
curl https://truthgit-production.up.railway.app/
```

### Validator Status

```bash
curl https://truthgit-production.up.railway.app/api/debug/validators
```

### Test Verification

```bash
curl -X POST https://truthgit-production.up.railway.app/api/verify \
  -H "Content-Type: application/json" \
  -d '{"claim": "Water boils at 100°C", "domain": "physics"}'
```

---

## Troubleshooting

### Validators Returning 0 Confidence

1. Check validator debug endpoint
2. Verify API keys are set correctly
3. Check logs in Railway dashboard

### GCP Credentials Not Found

1. Ensure `GOOGLE_CREDENTIALS_BASE64` is set
2. Verify base64 encoding is correct (single line, no newlines)
3. Check service account has `roles/aiplatform.user`

### CI Failing

1. Run locally: `ruff check src/ && ruff format --check src/`
2. Run tests: `pytest tests/ -v`
3. Check build: `python -m build`

---

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`):

- **Lint**: `ruff check src/` and `ruff format --check src/`
- **Test**: pytest on Python 3.10, 3.11, 3.12
- **Build**: Package build verification

Railway auto-deploys on successful push to `main`.
