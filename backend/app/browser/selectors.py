from __future__ import annotations

import asyncio
from collections.abc import Sequence

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page


LOGIN_BUTTON_SELECTORS = [
    'button:has-text("Вход")',
    'a:has-text("Вход")',
    '[role="button"]:has-text("Вход")',
    'button:has-text("Войти")',
    'a:has-text("Войти")',
    '[role="button"]:has-text("Войти")',
    'button:has-text("Login")',
    'a:has-text("Login")',
]

LOGIN_INPUT_SELECTORS = [
    "input#username",
    'input[autocomplete="username"]',
    'input[placeholder="E-mail или ID"]',
    'input[name*="login" i]',
    'input[name*="phone" i]',
    'input[name*="email" i]',
    'input[type="tel"]',
    'input[placeholder*="телефон" i]',
    'input[placeholder*="логин" i]',
    'input[placeholder*="email" i]',
]

PASSWORD_INPUT_SELECTORS = [
    'input#username-password[type="password"]',
    'input[type="password"][autocomplete="current-password"]',
    'input[placeholder="Пароль"]',
    'input[type="password"]',
    'input[name*="password" i]',
    'input[placeholder*="парол" i]',
]

LOGIN_SUBMIT_SELECTORS = [
    'button[type="submit"]',
    'button:has-text("Вход")',
    '[role="button"]:has-text("Вход")',
    'button:has-text("Войти")',
    '[role="button"]:has-text("Войти")',
    'button:has-text("Login")',
    'button:has-text("Продолжить")',
]

AUTHENTICATED_SELECTORS = [
    'a[href*="logout" i]',
    'button:has-text("Выйти")',
    'button:has-text("Logout")',
]

MANUAL_ACTION_SELECTORS = [
    'iframe[src*="captcha" i]',
    '[class*="captcha" i]',
    '[id*="captcha" i]',
    'input[name*="captcha" i]',
    'input[name*="otp" i]',
    'input[autocomplete="one-time-code"]',
    'input[placeholder*="код подтверждения" i]',
    'input[placeholder*="sms" i]',
    'text=/captcha/i',
    'text=/капч/i',
    'text=/sms.{0,10}код/i',
    'text=/код.{0,20}(из sms|подтверждения)/i',
    'text=/дополнительн.{0,20}(провер|защит)/i',
]


async def first_visible(
    root: Page | Locator,
    selectors: Sequence[str],
    *,
    timeout_ms: int = 0,
    poll_interval: float = 0.2,
) -> Locator | None:
    """Return the first visible match, optionally polling until timeout."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_ms / 1000

    while True:
        for selector in selectors:
            try:
                candidate = root.locator(selector).first
                if await candidate.is_visible():
                    return candidate
            except PlaywrightError:
                # A fallback selector may not be valid for a particular DOM state.
                continue

        if loop.time() >= deadline:
            return None
        await asyncio.sleep(poll_interval)
