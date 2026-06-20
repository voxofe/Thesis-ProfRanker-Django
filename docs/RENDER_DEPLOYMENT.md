# ProfRanker Production Rollout (Canonical Plan)

## Target Architecture

1. Frontend: Cloudflare Pages on profrankerapp.com
2. Backend API: Render web service on api.profrankerapp.com
3. Background jobs: Render worker + Render Redis
4. Database: Neon Postgres
5. File storage: Cloudflare R2

## Rollout Order (Use This Exact Order)

1. Prepare backend production config
2. Verify Neon is active and used by backend
3. Enable and verify R2 media storage
4. Deploy backend API + worker on Render
5. Deploy React frontend on Cloudflare Pages
6. Retire tunnels after 1-2 days stable runtime

## 1) Backend Production Config

Already in codebase:
- DJANGO_DEBUG is env-based
- DJANGO_SECRET_KEY is env-based
- WhiteNoise static handling is enabled
- Gunicorn is installed
- Optional S3/R2 storage is env-switched by USE_S3_MEDIA

Required runtime env vars on Render API:
- DJANGO_DEBUG=False
- DJANGO_SECRET_KEY=(generated secret)
- ALLOWED_HOSTS=api.profrankerapp.com,*.onrender.com
- CLIENT_URL=https://profrankerapp.com
- DATABASE_URL=(Neon connection string)
- REDIS_URL=(from Render Redis service)
- RQ_QUEUE_NAME=background
- USE_S3_MEDIA=True
- AWS_S3_ENDPOINT_URL=https://0aaeeedefed8b47bfee8b00934b48013.r2.cloudflarestorage.com
- AWS_ACCESS_KEY_ID=(R2 key)
- AWS_SECRET_ACCESS_KEY=(R2 secret)
- AWS_STORAGE_BUCKET_NAME=profranker-media
- AWS_S3_REGION_NAME=auto
- RESEND_API_KEY=(if email is enabled)
- OPENAI_API_KEY=(if AI features enabled)
- CRON_SECRET=(required)

Security env vars on Render API:
- SECURE_SSL_REDIRECT=True
- SECURE_HSTS_SECONDS=31536000
- SECURE_HSTS_INCLUDE_SUBDOMAINS=True
- SECURE_HSTS_PRELOAD=True
- SESSION_COOKIE_SECURE=True
- CSRF_COOKIE_SECURE=True

## 2) Neon Status

Neon is already working and should remain the source of truth.

Operational checks after deploy:
- Run migrations successfully
- Confirm API reads/writes expected data
- Confirm admin login and user login use Neon data

## 3) R2 Media Enablement

Backend is already coded for R2 via django-storages + boto3.

Production switch:
- USE_S3_MEDIA=True
- Ensure AWS_S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME are set

Important:
- Addressing style is path-style in settings and is required for R2

Validation:
- Upload from profile vault
- Replace existing file
- Download file
- Confirm object appears in R2 bucket

## 4) Render Deployment (API + Worker + Redis)

This repo now contains render.yaml at server/render.yaml with:
- profranker-api (web service)
- profranker-worker (worker service)
- profranker-redis (redis service)

Build/start behavior:
- API build runs build.sh (migrate + collectstatic)
- API starts gunicorn
- Worker starts through python app/services/rq_worker.py

Deploy steps:
1. Push repository changes
2. In Render, create Blueprint from this repo and set Blueprint Path to server/render.yaml
3. Render creates all three services from server/render.yaml
4. Fill all sync:false variables in API and worker
5. Redeploy API and worker

Worker note:
- Worker uses same DATABASE_URL and REDIS_URL as API
- Worker queue is background

## 5) Cloudflare Pages Deployment (Frontend)

Create Cloudflare Pages project from the same repo:
- Project root: client
- Build command: pnpm install && pnpm build
- Build output directory: build

Pages environment variable:
- REACT_APP_API_URL=https://api.profrankerapp.com

Then attach custom domain:
- profrankerapp.com
- Optional: www.profrankerapp.com

## 6) DNS Records

Cloudflare DNS should include:

API domain:
- Type: CNAME
- Name: api
- Target: profranker-api.onrender.com
- Proxy status: DNS only while validating, then proxied if desired

Frontend root domain:
- Managed by Cloudflare Pages custom domain setup flow

## 7) End-to-End Validation Checklist

Backend:
- API health endpoint responds
- Login/register works
- Submit application works
- Vault upload/replace/download works
- Admin pages work
- RQ worker consumes background jobs

Frontend:
- Loads on profrankerapp.com
- API calls go to api.profrankerapp.com
- Auth/session flows function in browser

Storage and data:
- New media files appear in R2
- Existing data is read from Neon

## 8) Secret Rotation Before Go-Live

Rotate before production cutover:
- Neon DB password / connection credentials
- R2 access key and secret key
- DJANGO_SECRET_KEY
- CRON_SECRET
- RESEND_API_KEY
- OPENAI_API_KEY (if used)

## 9) Cutover and Tunnel Retirement

1. Keep tunnels as rollback only for 1-2 days
2. Monitor API/worker logs and user flows
3. Disable cloudflared tunnels after stable window

## Notes

- Local R2 TLS issues do not block production validation on Render.
- Frontend is intentionally not hosted on Render in this plan.


