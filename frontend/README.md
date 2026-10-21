# FoodVerse AI frontend

## Requirements

- Node.js 18 or newer
- The FoodVerse backend running at `http://127.0.0.1:8000`

## Run locally

```sh
cd frontend
npm install
cp .env.example .env
npm run dev
```

Vite proxies `/api` requests to the local backend, so the default empty
`VITE_API_BASE_URL` works without a CORS configuration change. To use a
different API origin, set `VITE_API_BASE_URL` in `.env`. Restart Vite after
changing environment values.

Run `npm run build` to produce the production bundle and `npm test` to run the
frontend tests.
