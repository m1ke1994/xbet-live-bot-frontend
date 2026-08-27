from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from playwright.async_api import Locator, Page
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .selectors import (
    AUTHENTICATED_SELECTORS,
    LOGIN_BUTTON_SELECTORS,
    LOGIN_SUBMIT_SELECTORS,
    MANUAL_ACTION_SELECTORS,
    first_visible,
)


logger = logging.getLogger(__name__)
StatusCallback = Callable[[str], None]
VISUAL_DELAY_MS = 300
FORM_TIMEOUT_MS = 10_000
USERNAME_SELECTOR = "input#username"
PASSWORD_SELECTOR = 'input#username-password[type="password"]'


class LoginError(RuntimeError):
    """Raised when the login flow cannot safely continue."""


@dataclass(frozen=True, slots=True)
class LoginResult:
    status: str
    current_url: str
    title: str
    message: str | None = None


async def _result(page: Page, status: str, message: str | None = None) -> LoginResult:
    return LoginResult(status, page.url, await page.title(), message)


async def _first_visible_enabled(candidates: Sequence[Locator]) -> Locator | None:
    for collection in candidates:
        try:
            count = await collection.count()
        except PlaywrightError:
            continue
        for index in range(count):
            candidate = collection.nth(index)
            try:
                if await candidate.is_visible() and await candidate.is_enabled():
                    return candidate
            except PlaywrightError:
                continue
    return None


async def _find_login_opener(page: Page) -> Locator | None:
    semantic = await _first_visible_enabled(
        [
            page.get_by_role("button", name="Вход", exact=True),
            page.get_by_role("button", name="Войти", exact=True),
        ]
    )
    if semantic is not None:
        return semantic

    for caption_text in ("Вход", "Войти"):
        captions = page.get_by_text(caption_text, exact=True)
        try:
            count = await captions.count()
        except PlaywrightError:
            continue
        for index in range(count):
            caption = captions.nth(index)
            try:
                if not await caption.is_visible():
                    continue
                clickable_parent = caption.locator(
                    "xpath=ancestor-or-self::*[self::button or self::a "
                    "or @role='button' or (@tabindex and @tabindex != '-1')][1]"
                )
                if (
                    await clickable_parent.count()
                    and await clickable_parent.first.is_visible()
                    and await clickable_parent.first.is_enabled()
                ):
                    return clickable_parent.first
            except PlaywrightError:
                continue

    fallback = await first_visible(page, LOGIN_BUTTON_SELECTORS)
    if fallback is not None and await fallback.is_enabled():
        return fallback
    return None


async def _exact_form_fields(page: Page) -> tuple[Locator, Locator]:
    username = page.locator(USERNAME_SELECTOR).first
    password = page.locator(PASSWORD_SELECTOR).first
    try:
        await username.wait_for(state="visible", timeout=FORM_TIMEOUT_MS)
        await password.wait_for(state="visible", timeout=FORM_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise LoginError(
            "Форма входа открылась, но поля input#username и "
            "input#username-password[type=password] не стали видимыми. "
            "Chromium оставлен открытым для ручной проверки."
        ) from exc
    return username, password


async def _form_is_open(page: Page) -> bool:
    try:
        return await page.locator(USERNAME_SELECTOR).first.is_visible() and await page.locator(
            PASSWORD_SELECTOR
        ).first.is_visible()
    except PlaywrightError:
        return False


async def _authenticated_marker(page: Page) -> Locator | None:
    return await first_visible(page, AUTHENTICATED_SELECTORS)


async def open_login_form(page: Page, set_status: StatusCallback) -> LoginResult:
    if page.is_closed():
        raise LoginError("Окно Chromium закрыто. Сначала снова откройте браузер.")

    if await _form_is_open(page):
        set_status("LOGIN_FORM_OPENED")
        logger.info("Login form detected")
        return await _result(page, "LOGIN_FORM_OPENED")

    authenticated = await _authenticated_marker(page)
    if authenticated is not None:
        set_status("AUTHENTICATED")
        logger.info("Authenticated state detected")
        return await _result(page, "AUTHENTICATED")

    set_status("OPENING_LOGIN")
    logger.info("Opening login form")
    opener = await _find_login_opener(page)
    if opener is None:
        set_status("AUTH_STATE_UNKNOWN")
        return await _result(
            page,
            "AUTH_STATE_UNKNOWN",
            "Кнопка «Вход» и надёжный DOM-признак авторизации не найдены. Chromium оставлен открытым.",
        )

    await opener.click()
    await _exact_form_fields(page)
    set_status("LOGIN_FORM_OPENED")
    logger.info("Login form detected")
    return await _result(page, "LOGIN_FORM_OPENED")


async def fill_credentials(
    page: Page,
    login_value: str,
    password_value: str,
    set_status: StatusCallback,
) -> LoginResult:
    set_status("FILLING_CREDENTIALS")
    username, password = await _exact_form_fields(page)

    logger.info("Filling username")
    try:
        await username.fill(login_value)
    except PlaywrightError as exc:
        raise LoginError("Не удалось заполнить поле #username.") from exc
    await page.wait_for_timeout(VISUAL_DELAY_MS)
    if not await username.input_value():
        raise LoginError("Не удалось заполнить поле #username.")
    logger.info("Username filled")

    logger.info("Filling password")
    try:
        await password.fill(password_value)
    except PlaywrightError as exc:
        raise LoginError("Не удалось заполнить поле #username-password.") from exc
    await page.wait_for_timeout(VISUAL_DELAY_MS)
    if not bool(await password.input_value()):
        raise LoginError("Не удалось заполнить поле #username-password.")
    logger.info("Password filled")

    set_status("CREDENTIALS_FILLED")
    logger.info("Credentials filled")
    return await _result(page, "CREDENTIALS_FILLED")


async def _find_auth_container(page: Page) -> Locator | None:
    username = page.locator(USERNAME_SELECTOR).first
    form = username.locator("xpath=ancestor::form[1]")
    try:
        if (
            await form.count()
            and await form.first.is_visible()
            and await form.first.locator(PASSWORD_SELECTOR).count()
        ):
            return form.first

        common_ancestor = username.locator(
            "xpath=ancestor::*[descendant::input[@id='username-password' "
            "and @type='password']][1]"
        )
        if await common_ancestor.count() and await common_ancestor.first.is_visible():
            tag_name = await common_ancestor.first.evaluate("element => element.tagName")
            if tag_name not in {"BODY", "HTML"}:
                return common_ancestor.first
    except PlaywrightError:
        return None
    return None


async def _find_submit_button(container: Locator) -> Locator | None:
    semantic = await _first_visible_enabled(
        [
            container.locator('button[type="submit"]'),
            container.get_by_role("button", name="Вход", exact=True),
            container.get_by_role("button", name="Войти", exact=True),
        ]
    )
    if semantic is not None:
        return semantic

    # Fallback selectors are deliberately scoped to the auth container.
    fallback = await first_visible(container, LOGIN_SUBMIT_SELECTORS)
    if fallback is not None and await fallback.is_enabled():
        return fallback
    return None


async def _detect_post_submit_status(page: Page) -> str:
    for _ in range(20):
        if await first_visible(page, MANUAL_ACTION_SELECTORS):
            return "MANUAL_ACTION_REQUIRED"
        if await _authenticated_marker(page):
            return "AUTHENTICATED"
        await asyncio.sleep(0.25)
    return "LOGIN_SUBMITTED"


async def submit_login(page: Page, set_status: StatusCallback) -> LoginResult:
    set_status("SUBMITTING_LOGIN")
    await _exact_form_fields(page)
    container = await _find_auth_container(page)
    submit_button = await _find_submit_button(container) if container is not None else None
    if submit_button is None:
        set_status("CREDENTIALS_FILLED")
        return await _result(
            page,
            "CREDENTIALS_FILLED",
            "Логин и пароль заполнены. Кнопка подтверждения требует уточнения селектора.",
        )

    logger.info("Submitting login")
    await submit_button.click()
    await page.wait_for_timeout(VISUAL_DELAY_MS)
    set_status("LOGIN_SUBMITTED")
    logger.info("Login submitted")

    detected_status = await _detect_post_submit_status(page)
    set_status(detected_status)
    if detected_status == "MANUAL_ACTION_REQUIRED":
        logger.info("Manual action is required in the visible Chromium window")
    elif detected_status == "AUTHENTICATED":
        logger.info("Authenticated state detected")
    return await _result(page, detected_status)


async def login(
    page: Page,
    login_value: str,
    password_value: str,
    set_status: StatusCallback,
) -> LoginResult:
    opened = await open_login_form(page, set_status)
    if opened.status != "LOGIN_FORM_OPENED":
        return opened
    await fill_credentials(page, login_value, password_value, set_status)
    return await submit_login(page, set_status)


async def collect_auth_diagnostics(
    page: Page,
    stage: str,
    error_message: str,
    diagnostics_dir: Path,
) -> dict[str, Any]:
    """Collect safe DOM facts and a screenshot with credential fields masked."""
    username = page.locator(USERNAME_SELECTOR).first
    password = page.locator(PASSWORD_SELECTOR).first

    try:
        username_found = await username.count() > 0
    except PlaywrightError:
        username_found = False
    try:
        password_found = await password.count() > 0
    except PlaywrightError:
        password_found = False

    submit_found = False
    try:
        container = await _find_auth_container(page)
        if container is not None:
            submit_found = await _find_submit_button(container) is not None
    except PlaywrightError:
        pass

    screenshot: str | None = None
    try:
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        screenshot_path = diagnostics_dir / f"auth-error-{timestamp}.png"
        await page.screenshot(
            path=str(screenshot_path),
            full_page=True,
            mask=[username, password],
            animations="disabled",
        )
        screenshot = str(screenshot_path)
    except (OSError, PlaywrightError):
        logger.warning("Could not save masked authentication screenshot")

    return {
        "current_url": page.url,
        "stage": stage,
        "username_input_found": username_found,
        "password_input_found": password_found,
        "submit_button_found": submit_found,
        "screenshot": screenshot,
        "error": error_message,
    }
