"""FastAPI application definition and lifecycle hooks."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import routes
from app.embedding_index import build_index
from app.encryption import initialize_encryption

app = FastAPI(
    title="SignalZero Local Node",
    description="Local symbolic API runtime for SignalZero",
    version="0.1.0",
)

log.info("app.initialised", title=app.title, version=app.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)


@app.get("/")
def read_root() -> dict:
    log.debug("app.healthcheck")
    return {"status": "SignalZero Local Node Live"}


@app.on_event("startup")
async def startup_event() -> None:
    log.info("app.startup.begin")
    load_symbol_store_if_empty()
    build_index()
    initialize_encryption()

    log.info("app.startup.symbol_store_ready")
    build_index()
    log.info("app.startup.embedding_index_ready")
