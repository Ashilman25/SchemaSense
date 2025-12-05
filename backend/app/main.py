import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import config, history, nl, schema, sql, db_provision

#python -m uvicorn app.main:app --reload

# Easiest for testing: Just run SQL commands directly:
    # docker exec schemasense-postgres psql -U schemasense -d schemasense -c "YOUR SQL HERE"

# Best for permanent data: Create a file like infra/sql/init-mydata.sql and restart the container. For large imports: Use pg_dump from your existing DB and import with:
    # docker exec -i schemasense-postgres psql -U schemasense -d schemasense < yourfile.sql


logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
)

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
app.include_router(db_provision.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

