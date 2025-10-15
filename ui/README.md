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

The app listens on [http://localhost:5173](http://localhost:5173) by default.

## Production build

Create an optimized production build:

```bash
npm run build
```

Preview the production build locally:

```bash
npm run preview
```

## Project structure

- `src/` – React components, pages, hooks, and styles for the UI
- `index.html` – Single-page application entry point used by Vite
- `tailwind.config.js` and `postcss.config.cjs` – Tailwind CSS configuration

## Notes

- The current implementation uses mock symbol data located in `src/data/sampleSymbols.js`.
- The inference console is a stub and will be implemented in a future iteration.
