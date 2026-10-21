# Deployment guide

The backend and frontend deploy as separate services. Examples below use
Render/Railway for FastAPI and Vercel/Netlify for the static Vite app; equivalent
host settings are fine.

## Backend (Render or Railway)

1. Create a Python web service from the repository root.
2. Install dependencies with `pip install -r requirements.txt`.
3. Use this start command:

   ```sh
   uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```

4. Add secrets and settings in the host's environment-variable dashboard.
   Never commit credentials or copy them into frontend variables.
5. Set `CORS_ORIGINS` to the exact deployed frontend origin, for example
   `https://foodverse-demo.example`; do not use `*`.
6. Set `GROQ_API_KEY` only if live model calls are intended. Set
   `DEMO_MODE=true` for synthetic sample responses. Add `USDA_FDC_API_KEY`
   only when optional USDA lookup is desired.
7. Verify `GET https://<backend-host>/api/health` reports `status: "ok"`,
   `configured`, and the expected `demo` value.

`$PORT` is provided by Render/Railway. If a provider uses a different port
variable, adapt the command in its dashboard. Video analysis requires a
compatible OpenCV runtime and codec support; test that feature on the chosen
host.

## Frontend (Vercel or Netlify)

1. Create a static-site project with the repository's `frontend/` directory as
   the project root.
2. Set the build command to `npm ci && npm run build`.
3. Set the output directory to `dist`.
4. Set `VITE_API_BASE_URL` to the backend origin, e.g.
   `https://foodverse-api.example`. This is a build-time public URL, not a
   secret. Do not put Groq or USDA credentials in frontend environment
   settings.
5. Deploy and verify the browser can call the backend. The CORS allowlist must
   contain the exact scheme/host frontend origin.

The Vite `/api` proxy is for development only; production requests use
`VITE_API_BASE_URL`.

## Operations and limitations

- Profiles are stored in memory and reset on a backend restart or deployment.
- Free-tier hosts may sleep when idle; the first request after sleep can be
  delayed.
- Keep `DEMO_MODE=false` for real model calls and clearly distinguish that
  mode from synthetic samples in any presentation.
- Monitor provider quota and server logs without recording request bodies,
  profile fields, uploaded data, or credentials.
- Confirm platform file size, request timeout, Python-version, system-codec,
  and storage limits before enabling image/video analysis publicly.
