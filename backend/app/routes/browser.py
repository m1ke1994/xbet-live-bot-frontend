from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, HTTPException, status
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..browser.auth import LoginError, LoginResult
from ..browser.manager import BrowserActionError, BrowserManager, BrowserNotRunningError
from ..config import Settings


logger = logging.getLogger(__name__)


def _result_response(result: LoginResult) -> dict:
    response = {
        "ok": True,
        "status": result.status,
        "current_url": result.current_url,
        "title": result.title,
    }
    if result.message:
        response["message"] = result.message
    return response


async def _execute_auth_action(
    action: Callable[[], Awaitable[LoginResult]],
) -> dict:
    try:
        return _result_response(await action())
    except BrowserActionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.diagnostics,
        ) from exc
    except BrowserNotRunningError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LoginError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except PlaywrightTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                "Истекло время ожидания элемента формы. "
                "Chromium оставлен открытым для ручной проверки."
            ),
        ) from exc
    except PlaywrightError as exc:
        logger.exception("Playwright authentication error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка управления Chromium: {exc}",
        ) from exc


def create_browser_router(manager: BrowserManager, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/browser", tags=["browser"])

    @router.get("/config-check")
    async def config_check() -> dict:
        login_value = settings.xbet_login or ""
        password_value = settings.xbet_password or ""
        return {
            "url": settings.xbet_url,
            "login_loaded": bool(login_value),
            "login_last4": login_value[-4:] if login_value else None,
            "password_loaded": bool(password_value),
            "password_length": len(password_value),
        }

    @router.post("/start")
    async def start_browser() -> dict:
        try:
            browser_state = await manager.start()
            return {
                "ok": True,
                "status": browser_state["status"],
                "current_url": browser_state["current_url"],
            }
        except PlaywrightTimeoutError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Сайт не успел загрузиться. Chromium оставлен открытым для ручной проверки.",
            ) from exc
        except PlaywrightError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось запустить Chromium: {exc}",
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось запустить Chromium: {exc}",
            ) from exc

    @router.post("/open-login")
    async def open_login() -> dict:
        return await _execute_auth_action(manager.open_login)

    @router.post("/fill-login")
    async def fill_login() -> dict:
        if not settings.has_credentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="XBET_LOGIN и XBET_PASSWORD не заданы",
            )
        return await _execute_auth_action(
            lambda: manager.fill_login(
                settings.xbet_login or "",
                settings.xbet_password or "",
            )
        )

    @router.post("/login")
    async def submit_login() -> dict:
        if not settings.has_credentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="XBET_LOGIN и XBET_PASSWORD не заданы",
            )
        return await _execute_auth_action(
            lambda: manager.perform_login(
                settings.xbet_login or "",
                settings.xbet_password or "",
            )
        )

    @router.post("/full-login")
    async def full_login() -> dict:
        if not settings.has_credentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="XBET_LOGIN и XBET_PASSWORD не заданы",
            )
        return await _execute_auth_action(
            lambda: manager.perform_login(
                settings.xbet_login or "",
                settings.xbet_password or "",
            )
        )

    @router.get("/state")
    async def browser_state() -> dict:
        return await manager.get_state()

    @router.post("/stop")
    async def stop_browser() -> dict:
        await manager.close()
        return {"ok": True, "status": "CLOSED"}

    return router
