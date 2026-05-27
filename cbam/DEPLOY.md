# Deploying to DigitalOcean App Platform

The repo ships with a ready-made spec at `.do/app.yaml`. This document walks
through the one-time setup. From then on, every push to `master` redeploys.

## Cost & sizing

Spec uses `apps-s-1vcpu-0.5gb` — DigitalOcean's basic plan, **≈ $5/month**.
Resize via the App Platform console if you outgrow it.

## One-time setup

### Option A — DO console (no CLI needed)

1. Sign in to <https://cloud.digitalocean.com/apps>.
2. **Create App → GitHub → `egrilmez/mezo1`**, branch `master`.
3. When the wizard asks "Edit your app spec", upload or paste `.do/app.yaml`
   from this repo (or skip and accept the auto-detected service, then edit
   it to match the spec).
4. **Environment variables** step: set `OPENAI_API_KEY` to your real key.
   The spec declares the slot as `SECRET` with no value, so DO will prompt
   for it.
5. Create resources. First build takes ~3 minutes.
6. Once deployed, the app is at `https://<your-app>-<hash>.ondigitalocean.app`.

### Option B — `doctl` (CLI)

```bash
# Install doctl: https://docs.digitalocean.com/reference/doctl/how-to/install/
doctl auth init
doctl apps create --spec .do/app.yaml
# After creation, set the secret:
APP_ID=$(doctl apps list --format ID,Spec.Name --no-header | awk '/cbam-reporting-tool/ {print $1}')
doctl apps update "$APP_ID" --spec .do/app.yaml
# Set the OpenAI key via the console (doctl doesn't accept secret values
# inline; the spec only declares the slot).
```

## What the spec does

| Setting | Value | Why |
| --- | --- | --- |
| `source_dir` | `/cbam` | App lives in a subdirectory of the repo. |
| `environment_slug` | `python` | DO's Python buildpack installs `cbam/requirements.txt`. |
| `run_command` | `uvicorn backend.main:app --host 0.0.0.0 --port 8080` | Production server (no `--reload`, unlike `run.sh`). |
| `http_port` | `8080` | Matches the uvicorn bind port. |
| `health_check.http_path` | `/api/health` | Returns 200 as long as the app is up. |
| `OPENAI_API_KEY` | `SECRET`, no value | You set the real value in the DO console. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Override here if you want a different model. |
| `deploy_on_push: true` | — | Every push to `master` rebuilds automatically. |

## Verifying the deploy

```bash
APP_URL=https://<your-app>.ondigitalocean.app
curl -s "$APP_URL/api/health"
# {"ok":true,"openai_configured":true}   ← key is set
```

Then open `$APP_URL` in a browser to use the UI.

## Known gotchas

- **Goods registry is in-memory.** App Platform restarts the container on
  every deploy / scale event, wiping the registry. For real use, swap the
  in-memory dict in `backend/main.py` for DO Managed Postgres or KV.
- **CORS is open (`*`).** Tighten `allow_origins` in `backend/main.py`
  before exposing this to anything sensitive.
- **No auth.** Add Basic Auth or an OAuth proxy before sharing the URL.
- **First request after idle can be slow** if you scale to zero (basic
  plan keeps one instance hot, so this only applies on bigger plans).
