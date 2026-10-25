from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings, startup_problems
from app.db import init_db
from app.routes.extract import router

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


@asynccontextmanager
async def lifespan(_app: FastAPI):
    problems = startup_problems(get_settings())
    if problems:
        raise RuntimeError('Refusing to start: ' + '; '.join(problems))
    init_db()
    yield


_settings = get_settings()
app = FastAPI(title='CBP reference files', version='0.1.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_settings.cors_origins),
    allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type', 'X-Demo-User', 'X-Callback-Secret'],
)
app.include_router(router)


@app.get('/health')
def health() -> dict:
    return {'status': 'ok'}
