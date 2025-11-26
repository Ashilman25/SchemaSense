from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import config, history, nl, schema, sql

#python -m uvicorn app.main:app --reload

settings = get_settings()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config.router)
app.include_router(schema.router)
app.include_router(sql.router)
app.include_router(nl.router)
app.include_router(history.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

