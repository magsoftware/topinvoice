from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, Self, cast

from topinvoice.config import Config
from topinvoice.errors import ScrapingError
from topinvoice.models import Period

SCHEDULE_URL = "https://extranet.guestsage.com/apartment-owner/my-schedule"
ROOM_TYPE = "Topolowa 15"
CHROME_EXECUTABLE_CANDIDATES = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
)
LOGIN_SELECTORS = (
    "input[placeholder='Email']",
    "input[type='email']",
    "input[name='email']",
    "input[name='login']",
    "input[autocomplete='username']",
    "input[placeholder*='mail' i]",
    "input[type='text']",
)
PASSWORD_SELECTORS = (
    "input[placeholder='Password']",
    "input[type='password']",
    "input[name='password']",
    "input[autocomplete='current-password']",
)
SUBMIT_SELECTORS = (
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('Login')",
    "button:has-text('Log in')",
    "button:has-text('Sign in')",
)


class ElementLike(Protocol):
    """Protocol describing element interactions used by the scraper."""

    def wait_for(self, *, state: str, timeout: int) -> None: ...

    def fill(self, value: str) -> None: ...

    def press(self, key: str) -> None: ...

    def click(self) -> None: ...

    def select_option(self, *, label: str) -> None: ...

    def scroll_into_view_if_needed(self) -> None: ...


class LocatorLike(ElementLike, Protocol):
    """Protocol describing locator operations used by the scraper."""

    first: Self

    def count(self) -> int: ...

    def nth(self, index: int) -> ElementLike: ...

    def get_by_role(self, role: str, name: str, exact: bool = False) -> Self: ...

    def get_by_text(self, text: str, exact: bool = False) -> Self: ...

    def locator(self, selector: str) -> Self: ...


class KeyboardLike(Protocol):
    """Protocol for keyboard interactions on the page."""

    def press(self, key: str) -> None: ...


class DownloadLike(Protocol):
    """Protocol for downloaded browser artifacts."""

    def save_as(self, path: str) -> None: ...


class DownloadContextLike(Protocol):
    """Protocol for Playwright download context managers."""

    value: DownloadLike

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool | None: ...


class PageLike(Protocol):
    """Protocol for the subset of page APIs used by the scraper."""

    keyboard: KeyboardLike
    url: str

    def locator(self, selector: str) -> LocatorLike: ...

    def get_by_role(self, role: str, name: str, exact: bool = False) -> LocatorLike: ...

    def goto(self, url: str, wait_until: str) -> None: ...

    def wait_for_load_state(self, state: str, timeout: int) -> None: ...

    def wait_for_timeout(self, timeout: int) -> None: ...

    def expect_download(self, timeout: int) -> DownloadContextLike: ...

    def set_default_timeout(self, timeout: int) -> None: ...


class BrowserContextLike(Protocol):
    """Protocol for browser contexts with download support."""

    def new_page(self) -> PageLike: ...

    def close(self) -> None: ...


class BrowserLike(Protocol):
    """Protocol for browser instances used by the scraper."""

    def new_context(self, *, accept_downloads: bool) -> BrowserContextLike: ...

    def close(self) -> None: ...


class ChromiumLike(Protocol):
    """Protocol for Chromium launcher access."""

    def launch(self, **kwargs: object) -> BrowserLike: ...


class PlaywrightLike(Protocol):
    """Protocol for the Playwright root object."""

    chromium: ChromiumLike


class PlaywrightContextManagerLike(Protocol):
    """Protocol for the `sync_playwright()` context manager."""

    def __enter__(self) -> PlaywrightLike: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool | None: ...


def get_playwright_error_type() -> type[Exception]:
    """Return the Playwright error type used for browser interaction failures.

    Returns:
        Playwright exception class.

    Raises:
        ScrapingError: If Playwright is not installed in the current
            environment.
    """
    try:
        from playwright.sync_api import Error as PlaywrightError
    except ModuleNotFoundError as error:
        raise ScrapingError("Playwright is not installed. Install project dependencies from pyproject.toml.") from error
    return PlaywrightError


def ensure_playwright_available() -> Callable[[], PlaywrightContextManagerLike]:
    """Return the synchronous Playwright context manager factory.

    Returns:
        Callable that creates a Playwright context manager.

    Raises:
        ScrapingError: If Playwright is not installed in the current
            environment.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as error:
        raise ScrapingError("Playwright is not installed. Install project dependencies from pyproject.toml.") from error

    return cast(Callable[[], PlaywrightContextManagerLike], sync_playwright)


def wait_for_first(locator: LocatorLike, timeout_ms: int) -> LocatorLike:
    """Wait for the first locator match to become visible.

    Args:
        locator: Locator to resolve.
        timeout_ms: Visibility timeout in milliseconds.

    Returns:
        Locator pointing at the first visible match.
    """
    target = locator.first
    target.wait_for(state="visible", timeout=timeout_ms)

    return target


def first_visible(locator: LocatorLike, timeout_ms: int) -> ElementLike:
    """Return the first visible element from a locator collection.

    Args:
        locator: Locator that may resolve to multiple candidates.
        timeout_ms: Visibility timeout in milliseconds.

    Returns:
        First visible element.

    Raises:
        ScrapingError: If no visible candidate can be found.
    """
    playwright_error = get_playwright_error_type()
    errors: list[str] = []
    for index in range(locator.count()):
        candidate = locator.nth(index)
        try:
            candidate.wait_for(state="visible", timeout=min(timeout_ms, 1500))
            return candidate
        except playwright_error as error:
            errors.append(f"#{index}: {error}")

    raise ScrapingError(f"No visible element found. {errors}")


def fill_first(page: PageLike, selectors: tuple[str, ...], value: str, timeout_ms: int, field_name: str) -> None:
    """Fill the first visible field that matches the provided selectors.

    Args:
        page: Browser page used for lookups.
        selectors: Candidate selectors checked in order.
        value: Value to type into the field.
        timeout_ms: Timeout in milliseconds.
        field_name: Human-readable field name used in error messages.

    Raises:
        ScrapingError: If no matching field can be filled.
    """
    playwright_error = get_playwright_error_type()
    errors: list[str] = []
    for selector in selectors:
        try:
            field = first_visible(page.locator(selector), min(timeout_ms, 4000))
            field.fill(value)
            return
        except (ScrapingError, playwright_error) as error:
            errors.append(f"{selector}: {error}")

    raise ScrapingError(f"Could not find {field_name}. Tried selectors: {errors}")


def click_first(page: PageLike, selectors: tuple[str, ...], timeout_ms: int, element_name: str) -> None:
    """Click the first visible element that matches the provided selectors.

    Args:
        page: Browser page used for lookups.
        selectors: Candidate selectors checked in order.
        timeout_ms: Timeout in milliseconds.
        element_name: Human-readable element name used in error messages.

    Raises:
        ScrapingError: If no matching element can be clicked.
    """
    playwright_error = get_playwright_error_type()
    errors: list[str] = []
    for selector in selectors:
        try:
            element = first_visible(page.locator(selector), min(timeout_ms, 4000))
            element.click()
            return
        except (ScrapingError, playwright_error) as error:
            errors.append(f"{selector}: {error}")

    raise ScrapingError(f"Could not click {element_name}. Tried selectors: {errors}")


def login_if_needed(page: PageLike, config: Config, timeout_ms: int) -> None:
    """Authenticate in GuestSage when the session is not already logged in.

    Args:
        page: Browser page used for the session.
        config: GuestSage credentials.
        timeout_ms: Timeout in milliseconds for page interactions.
    """
    page.goto(SCHEDULE_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=timeout_ms)
    if page.locator("input[type='password']").count() == 0:
        return

    fill_first(page, LOGIN_SELECTORS, config.login, timeout_ms, "login field")
    fill_first(page, PASSWORD_SELECTORS, config.password, timeout_ms, "password field")

    first_visible(page.locator("input[name='password']"), min(timeout_ms, 4000)).press("Enter")
    page.wait_for_timeout(3000)

    page.wait_for_load_state("networkidle", timeout=timeout_ms)
    page.goto(SCHEDULE_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=timeout_ms)


def click_dropdown_option(page: PageLike, option_text: str, timeout_ms: int) -> None:
    """Click a dropdown option by visible text.

    Args:
        page: Browser page used for lookups.
        option_text: Visible label of the option to select.
        timeout_ms: Timeout in milliseconds.

    Raises:
        ScrapingError: If the option cannot be found.
    """
    playwright_error = get_playwright_error_type()
    candidates = (
        page.get_by_role("option", name=option_text, exact=True),
        page.locator(f"xpath=//*[@role='option' and normalize-space()='{option_text}']"),
        page.locator(f"xpath=//*[self::li or self::div or self::span][normalize-space()='{option_text}']"),
    )
    for locator in candidates:
        try:
            wait_for_first(locator, min(timeout_ms, 2500)).click()
            return
        except playwright_error:
            continue

    raise ScrapingError(f"Could not select dropdown option: {option_text}")


def select_value_by_label(page: PageLike, label_text: str, option_text: str, timeout_ms: int) -> None:
    """Select a form value by locating its associated label.

    Args:
        page: Browser page used for lookups.
        label_text: Visible label text of the target field.
        option_text: Visible option text to select.
        timeout_ms: Timeout in milliseconds.

    Raises:
        ScrapingError: If the field or option cannot be selected.
    """
    playwright_error = get_playwright_error_type()
    native_selectors = (
        f"xpath=//*[normalize-space()='{label_text}']/following::*[self::select][1]",
        f"xpath=//label[normalize-space()='{label_text}']/following::*[self::select][1]",
    )
    for selector in native_selectors:
        try:
            wait_for_first(page.locator(selector), min(timeout_ms, 2000)).select_option(label=option_text)
            return
        except playwright_error:
            continue

    trigger_selectors = (
        f"xpath=//*[normalize-space()='{label_text}']/following-sibling::*[1]",
        f"xpath=//*[normalize-space()='{label_text}']/parent::*/*[last()]",
        f"xpath=//*[normalize-space()='{label_text}']/following::*[@role='combobox'][1]",
        f"xpath=//*[normalize-space()='{label_text}']/following::*[self::button or self::input][1]",
    )
    errors: list[str] = []
    for selector in trigger_selectors:
        try:
            trigger = wait_for_first(page.locator(selector), min(timeout_ms, 2500))
            trigger.scroll_into_view_if_needed()
            trigger.click()
            click_dropdown_option(page, option_text, timeout_ms)
            return
        except (ScrapingError, playwright_error) as error:
            errors.append(f"{selector}: {error}")
            page.keyboard.press("Escape")

    raise ScrapingError(f"Could not set {label_text} to {option_text}. Tried selectors: {errors}")


def open_monthly_report_section(page: PageLike, timeout_ms: int) -> LocatorLike:
    """Open or locate the monthly report section on the GuestSage page.

    Args:
        page: Browser page used for lookups.
        timeout_ms: Timeout in milliseconds.

    Returns:
        Locator pointing at the monthly report section.
    """
    section = page.locator(
        "xpath=//*[normalize-space()='Monthly report']/ancestor::div"
        "[.//*[contains(normalize-space(), 'Export to CSV')]][1]",
    )

    return wait_for_first(section, timeout_ms)


def select_month_tab(page: PageLike, month_label: str, timeout_ms: int) -> None:
    """Select the month tab inside the monthly report section.

    Args:
        page: Browser page used for lookups.
        month_label: GuestSage label for the target month.
        timeout_ms: Timeout in milliseconds.

    Raises:
        ScrapingError: If the month tab cannot be selected.
    """
    playwright_error = get_playwright_error_type()
    section = open_monthly_report_section(page, timeout_ms)
    candidates = (
        section.get_by_role("button", name=month_label, exact=True),
        section.get_by_text(month_label, exact=True),
        section.locator(f"xpath=.//*[self::button or self::div or self::span][normalize-space()='{month_label}']"),
    )
    for locator in candidates:
        try:
            wait_for_first(locator, min(timeout_ms, 2500)).click()
            page.wait_for_timeout(800)
            return
        except playwright_error:
            continue

    raise ScrapingError(f"Could not select month tab: {month_label}")


def export_csv(page: PageLike, period: Period, downloads_dir: Path, timeout_ms: int) -> Path:
    """Export the monthly CSV report to the requested directory.

    Args:
        page: Browser page used for the export action.
        period: Billing period being exported.
        downloads_dir: Output directory for the downloaded file.
        timeout_ms: Timeout in milliseconds.

    Returns:
        Path to the saved CSV file.
    """
    downloads_dir.mkdir(parents=True, exist_ok=True)
    section = open_monthly_report_section(page, timeout_ms)
    export_button = section.get_by_role("button", name="Export to CSV", exact=True).first
    target_path = downloads_dir / f"guestsage-monthly-report-{period.token}.csv"

    with page.expect_download(timeout=timeout_ms) as download_info:
        export_button.click()
    download_info.value.save_as(str(target_path))

    return target_path


def launch_browser(playwright: PlaywrightLike, headless: bool) -> BrowserLike:
    """Launch a browser suitable for Playwright scraping.

    Args:
        playwright: Playwright root object.
        headless: Whether the browser should run in headless mode.

    Returns:
        Running browser instance.

    Raises:
        ScrapingError: If no supported browser can be launched.
    """
    playwright_error = get_playwright_error_type()
    launch_errors: list[str] = []

    for executable_path in CHROME_EXECUTABLE_CANDIDATES:
        if not executable_path.exists():
            continue
        try:
            return playwright.chromium.launch(executable_path=str(executable_path), headless=headless)
        except playwright_error as error:
            launch_errors.append(f"{executable_path}: {error}")

    try:
        return playwright.chromium.launch(channel="chrome", headless=headless)
    except playwright_error as error:
        launch_errors.append(f"channel=chrome: {error}")

    try:
        return playwright.chromium.launch(headless=headless)
    except playwright_error as error:
        launch_errors.append(f"default chromium: {error}")
        raise ScrapingError(
            "Could not launch a browser. Tried local Chrome and Playwright browsers:\n" + "\n".join(launch_errors),
        ) from error


class GuestSageScraper:
    """Scraper implementation that downloads monthly reports from GuestSage."""

    def export_monthly_report(
        self,
        period: Period,
        downloads_dir: Path,
        config: Config,
        headless: bool,
        timeout_ms: int,
    ) -> Path:
        """Download the monthly GuestSage CSV report for a period.

        Args:
            period: Billing period to export.
            downloads_dir: Directory where the CSV should be saved.
            config: GuestSage credentials.
            headless: Whether the browser should run in headless mode.
            timeout_ms: Timeout in milliseconds for browser interactions.

        Returns:
            Path to the downloaded CSV file.
        """
        sync_playwright = ensure_playwright_available()
        with sync_playwright() as playwright:
            browser = launch_browser(playwright, headless)
            context = browser.new_context(accept_downloads=True)
            try:
                page = context.new_page()
                page.set_default_timeout(timeout_ms)
                login_if_needed(page, config, timeout_ms)
                page.goto(SCHEDULE_URL, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
                open_monthly_report_section(page, timeout_ms)
                select_value_by_label(page, "Room type", ROOM_TYPE, timeout_ms)
                select_value_by_label(page, "Year", str(period.year), timeout_ms)
                select_month_tab(page, period.month_label, timeout_ms)

                return export_csv(page, period, downloads_dir.expanduser(), timeout_ms)
            finally:
                context.close()
                browser.close()
