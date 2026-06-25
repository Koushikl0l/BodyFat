# BodyFat API (Railway)

ONNX body-fat inference API for [MukitMoves](https://mukitmoves.com) `/BodyFat` page.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/analyze` | Analyze front/side photos + measurements |

## Deploy on Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select this repo: `Koushikl0l/BodyFat`
3. Add environment variables:

| Variable | Value |
|----------|-------|
| `BODYFAT_MODEL_PATH` | `models/bodyfat_student.onnx` |
| `ALLOWED_ORIGINS` | `https://mukitmoves.com,https://www.mukitmoves.com` |

4. Set **memory to at least 2 GB** (rembg + torch need RAM on first request)
5. Deploy → copy your Railway URL (e.g. `https://bodyfat-production.up.railway.app`)

## Connect to MukitMoves (shared hosting)

In the main MukitMoves site, edit `public/api/bodyfat-config.php`:

```php
'backend_url' => 'https://YOUR-RAILWAY-URL.up.railway.app',
```

The Hostinger site calls `/api/analyze` → PHP proxies to Railway.

## Verify

```bash
curl https://YOUR-RAILWAY-URL.up.railway.app/health
# {"status":"ok","backend":"onnx","model":"bodyfat_student.onnx"}
```

## Local dev

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export BODYFAT_MODEL_PATH=models/bodyfat_student.onnx
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000 for the standalone UI, or http://localhost:8000/health.
