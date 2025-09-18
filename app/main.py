# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import routes
from app.symbol_store import load_symbol_store_if_empty
from app.embedding_index import build_index

app = FastAPI(
    title="SignalZero Local Node",
    description="Local symbolic API runtime for SignalZero",
    version="0.1.0"
)

# CORS Middleware (adjust for deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include route definitions from app.routes
app.include_router(routes.router)

# Optional: root health check
@app.get("/")
def read_root():
    return {"status": "SignalZero Local Node Live"}

@app.on_event("startup")
async def startup_event():
    load_symbol_store_if_empty()
    build_index()