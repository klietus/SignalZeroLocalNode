# Signal Zero UI

This package contains a Vite-powered React application that provides the Signal Zero symbol browser and the future inference console.

## Prerequisites

- Node.js 18 or later
- npm 9 or later

## Installation

```bash
cd ui
npm install
```

## Development

Run the development server with hot reloading:

```bash
npm run dev
```

The app listens on [http://localhost:5173](http://localhost:5173) by default and proxies API
requests to the FastAPI service at [http://localhost:8000](http://localhost:8000). If your API
is hosted elsewhere, set `VITE_API_BASE_URL` in a `.env` file inside the `ui/` directory.

To automatically open a browser when running locally, set `VITE_DEV_SERVER_OPEN=true` in your
environment (for example by adding it to `.env`). The Docker development container disables this
behavior to avoid `xdg-open` errors in headless environments.

### Docker Compose workflow

The repository includes a `ui` service that runs the dev server alongside the API. Bring both
services up together so the proxy can reach FastAPI:

```bash
docker compose up web ui
```

The `ui` container respects the same `VITE_API_BASE_URL` configuration when present and uses the
internal proxy target configured via `VITE_DEV_PROXY_TARGET` (defaults to the `web` service).

## Project structure

- `src/` – React components, pages, hooks, and styles for the UI
- `index.html` – Single-page application entry point used by Vite
- `tailwind.config.js` and `postcss.config.cjs` – Tailwind CSS configuration

## Notes

- Symbol search runs against the running Signal Zero API (`/symbols` and `/symbol/{id}`
  endpoints).
- The inference console is a stub and will be implemented in a future iteration.
