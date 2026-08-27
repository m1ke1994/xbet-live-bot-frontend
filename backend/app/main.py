from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .browser.manager import BrowserManager
from .config import get_settings
from .routes.browser import create_browser_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

settings = get_settings()
browser_manager = BrowserManager(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await browser_manager.close()


app = FastAPI(
    title="XBET visible browser backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_browser_router(browser_manager, settings))


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
