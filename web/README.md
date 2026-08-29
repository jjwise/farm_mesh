# Web App

Single-page map UI for:

- a unified pod/tracker/valve/infrastructure map
- profile filters and node sorting
- current interpolated pod snapshots and a pod heat layer
- per-line historical movement
- basic-tracker position interval changes
- acknowledged valve open/close commands with bounded duration

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
