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

## Project structure

- `src/` – React components, pages, hooks, and styles for the UI
- `index.html` – Single-page application entry point used by Vite
- `tailwind.config.js` and `postcss.config.cjs` – Tailwind CSS configuration

## Notes

- Symbol search runs against the running Signal Zero API (`/symbols` and `/symbol/{id}`
  endpoints).
- The inference console is a stub and will be implemented in a future iteration.
