from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Any

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..config import Settings
from .auth import (
    LoginResult,
    collect_auth_diagnostics,
    fill_credentials,
    login,
    open_login_form,
)


logger = logging.getLogger(__name__)


class BrowserStatus(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    OPENED = "OPENED"
    OPENING_LOGIN = "OPENING_LOGIN"
    LOGIN_FORM_OPENED = "LOGIN_FORM_OPENED"
    FILLING_CREDENTIALS = "FILLING_CREDENTIALS"
    CREDENTIALS_FILLED = "CREDENTIALS_FILLED"
    SUBMITTING_LOGIN = "SUBMITTING_LOGIN"
    LOGIN_SUBMITTED = "LOGIN_SUBMITTED"
    AUTHENTICATED = "AUTHENTICATED"
    AUTH_STATE_UNKNOWN = "AUTH_STATE_UNKNOWN"
    MANUAL_ACTION_REQUIRED = "MANUAL_ACTION_REQUIRED"
    ERROR = "ERROR"


class BrowserNotRunningError(RuntimeError):
    """Raised when a browser command requires an open Chromium context."""


class BrowserActionError(RuntimeError):
    def __init__(self, diagnostics: dict[str, Any]) -> None:
        super().__init__(str(diagnostics["error"]))
        self.diagnostics = diagnostics


class BrowserManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._lock = asyncio.Lock()
        self.status = BrowserStatus.STOPPED
        self.last_diagnostics: dict[str, Any] | None = None

    def _set_status(self, status: str | BrowserStatus) -> None:
        self.status = BrowserStatus(status)

    def _on_context_closed(self, _: BrowserContext) -> None:
        self._context = None
        self._page = None
        if self.status != BrowserStatus.ERROR:
            self.status = BrowserStatus.STOPPED

    def _current_open_page(self) -> Page | None:
        if self._page is not None and not self._page.is_closed():
            return self._page
        if self._context is None:
            return None
        for candidate in reversed(self._context.pages):
            if not candidate.is_closed():
                self._page = candidate
                return candidate
        return None

    async def _ensure_page(self) -> Page:
        page = self._current_open_page()
        if page is not None:
            return page
        if self._context is None:
            raise BrowserNotRunningError("Chromium не запущен. Сначала вызовите POST /api/browser/start.")
        try:
            self._page = await self._context.new_page()
        except PlaywrightError as exc:
            raise BrowserNotRunningError(
                "Окно Chromium закрыто. Сначала снова вызовите POST /api/browser/start."
            ) from exc
        return self._page

    async def _open_site(self, page: Page) -> None:
        logger.info("Opening site")
        await page.goto(self.settings.xbet_url, wait_until="domcontentloaded", timeout=60_000)
        try:
            await page.wait_for_load_state("load", timeout=30_000)
        except PlaywrightTimeoutError:
            logger.warning("Page load event timed out; continuing with the loaded DOM")
        await page.bring_to_front()
        self.status = BrowserStatus.OPENED

    async def _discard_stale_context(self) -> None:
        if self._context is None:
            return
        try:
            await self._context.close()
        except PlaywrightError:
            pass
        finally:
            self._context = None
            self._page = None

    async def start(self) -> dict[str, Any]:
        async with self._lock:
            page = self._current_open_page()
            if page is not None:
                await page.bring_to_front()
                return await self._state_unlocked()

            await self._discard_stale_context()
            self.status = BrowserStatus.STARTING
            logger.info("Browser starting")
            self.settings.profile_dir.mkdir(parents=True, exist_ok=True)

            try:
                if self._playwright is None:
                    self._playwright = await async_playwright().start()
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.settings.profile_dir),
                    headless=False,
                    slow_mo=self.settings.browser_slow_mo,
                )
                self._context.on("close", self._on_context_closed)
                self._page = self._current_open_page() or await self._context.new_page()
                await self._open_site(self._page)
                return await self._state_unlocked()
            except Exception:
                self.status = BrowserStatus.ERROR
                logger.exception("Could not start or open Chromium")
                # If Chromium did open, keep it visible so a navigation problem
                # can be inspected manually. A failed launch has no context and
                # its Playwright driver is cleaned up before the next retry.
                if self._context is None and self._playwright is not None:
                    try:
                        await self._playwright.stop()
                    finally:
                        self._playwright = None
                raise

    async def get_page(self) -> Page:
        async with self._lock:
            return await self._ensure_page()

    async def open_site(self) -> dict[str, Any]:
        async with self._lock:
            page = await self._ensure_page()
            await self._open_site(page)
            return await self._state_unlocked()

    async def open_login(self) -> LoginResult:
        async with self._lock:
            page = await self._ensure_page()
            if page.url == "about:blank":
                await self._open_site(page)
            self.last_diagnostics = None
            try:
                return await open_login_form(page, self._set_status)
            except Exception as exc:
                raise await self._auth_error(page, exc) from exc

    async def fill_login(self, login_value: str, password: str) -> LoginResult:
        async with self._lock:
            page = await self._ensure_page()
            self.last_diagnostics = None
            try:
                return await fill_credentials(
                    page,
                    login_value,
                    password,
                    self._set_status,
                )
            except Exception as exc:
                raise await self._auth_error(page, exc) from exc

    async def perform_login(self, login_value: str, password: str) -> LoginResult:
        async with self._lock:
            page = await self._ensure_page()
            if page.url == "about:blank":
                await self._open_site(page)
            self.last_diagnostics = None
            try:
                return await login(page, login_value, password, self._set_status)
            except Exception as exc:
                raise await self._auth_error(page, exc) from exc

    async def _auth_error(self, page: Page, exc: Exception) -> BrowserActionError:
        failed_stage = self.status.value
        safe_message = str(exc)
        for secret in (self.settings.xbet_login, self.settings.xbet_password):
            if secret:
                safe_message = safe_message.replace(secret, "[REDACTED]")
        diagnostics = await collect_auth_diagnostics(
            page,
            failed_stage,
            safe_message,
            self.settings.diagnostics_dir,
        )
        self.last_diagnostics = diagnostics
        self.status = BrowserStatus.ERROR
        return BrowserActionError(diagnostics)

    async def _state_unlocked(self) -> dict[str, Any]:
        page = self._current_open_page()
        if page is None:
            state = {
                "running": False,
                "current_url": None,
                "title": None,
                "status": self.status.value,
            }
            if self.last_diagnostics is not None:
                state["last_error"] = self.last_diagnostics
            return state
        try:
            title = await page.title()
        except PlaywrightError:
            title = None
        state = {
            "running": True,
            "current_url": page.url,
            "title": title,
            "status": self.status.value,
        }
        if self.last_diagnostics is not None:
            state["last_error"] = self.last_diagnostics
        return state

    async def get_state(self) -> dict[str, Any]:
        async with self._lock:
            return await self._state_unlocked()

    async def close(self) -> None:
        async with self._lock:
            context, playwright = self._context, self._playwright
            self._context = None
            self._page = None
            self._playwright = None
            try:
                if context is not None:
                    await context.close()
            except PlaywrightError:
                logger.exception("Error while closing BrowserContext")
            finally:
                if playwright is not None:
                    try:
                        await playwright.stop()
                    except PlaywrightError:
                        logger.exception("Error while stopping Playwright")
                self.status = BrowserStatus.STOPPED
                logger.info("Browser closed")
