# Web App

Single-page map UI for:

- current snapshot (`/v1/line/{line_id}/snapshot`)
- per-tracker historical movement (`/v1/line/{line_id}/history`)
- optional measurement-density layer

In the self-hosted stack, Caddy serves the files and proxies `/api` to
FastAPI on the same HTTPS origin. FastAPI is not exposed directly.

## Run

Serve `web/` as static files (example with Python):

```bash
cd web
python -m http.server 8080
```

Then open `http://localhost:8080` and set API base URL to
`http://localhost:8000` for local development.
