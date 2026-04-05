from __future__ import annotations

import builtins
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from topinvoice.config import Config
from topinvoice.errors import ScrapingError
from topinvoice.models import Period
from topinvoice.scraping import (
    BrowserContextLike,
    BrowserLike,
    ChromiumLike,
    DownloadContextLike,
    DownloadLike,
    GuestSageScraper,
    KeyboardLike,
    LocatorLike,
    PageLike,
    PlaywrightContextManagerLike,
    PlaywrightLike,
    click_dropdown_option,
    click_first,
    ensure_playwright_available,
    export_csv,
    fill_first,
    first_visible,
    get_playwright_error_type,
    launch_browser,
    login_if_needed,
    open_monthly_report_section,
    select_month_tab,
    select_value_by_label,
)

MONTHLY_REPORT_SELECTOR = (
    "xpath=//*[normalize-space()='Monthly report']/ancestor::div"
    "[.//*[contains(normalize-space(), 'Export to CSV')]][1]"
)


class FakePlaywrightError(Exception):
    pass


class FakeElement:
    def __init__(self, *, fail_wait: bool = False, fail_click: bool = False, fail_fill: bool = False) -> None:
        self.fail_wait = fail_wait
        self.fail_click = fail_click
        self.fail_fill = fail_fill
        self.filled_value: str | None = None
        self.selected_label: str | None = None
        self.scrolled = False

    def wait_for(self, *, state: str, timeout: int) -> None:
        del state, timeout
        if self.fail_wait:
            raise FakePlaywrightError("wait failed")

    def fill(self, value: str) -> None:
        if self.fail_fill:
            raise FakePlaywrightError("fill failed")
        self.filled_value = value

    def press(self, key: str) -> None:
        del key

    def click(self) -> None:
        if self.fail_click:
            raise FakePlaywrightError("click failed")

    def select_option(self, *, label: str) -> None:
        self.selected_label = label

    def scroll_into_view_if_needed(self) -> None:
        self.scrolled = True


class FakeLocator(LocatorLike):
    def __init__(self, elements: list[FakeElement] | None = None) -> None:
        self.elements = [FakeElement()] if elements is None else elements
        self.first = self

    def count(self) -> int:
        return len(self.elements)

    def nth(self, index: int) -> FakeElement:
        return self.elements[index]

    def wait_for(self, *, state: str, timeout: int) -> None:
        self.nth(0).wait_for(state=state, timeout=timeout)

    def fill(self, value: str) -> None:
        self.nth(0).fill(value)

    def click(self) -> None:
        self.nth(0).click()

    def press(self, key: str) -> None:
        self.nth(0).press(key)

    def select_option(self, *, label: str) -> None:
        self.nth(0).select_option(label=label)

    def scroll_into_view_if_needed(self) -> None:
        self.nth(0).scroll_into_view_if_needed()

    def get_by_role(self, role: str, name: str, exact: bool = False) -> FakeLocator:
        del role, name, exact
        return self

    def get_by_text(self, text: str, exact: bool = False) -> FakeLocator:
        del text, exact
        return self

    def locator(self, selector: str) -> FakeLocator:
        del selector
        return self


class FakeDownload(DownloadLike):
    def __init__(self) -> None:
        self.saved_path: str | None = None

    def save_as(self, path: str) -> None:
        self.saved_path = path


class FakeDownloadContext(DownloadContextLike):
    def __init__(self) -> None:
        self.value = FakeDownload()

    def __enter__(self) -> FakeDownloadContext:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback


class FakeKeyboard(KeyboardLike):
    def __init__(self) -> None:
        self.keys: list[str] = []

    def press(self, key: str) -> None:
        self.keys.append(key)


class FakePage(PageLike):
    def __init__(self, locators: dict[str, FakeLocator] | None = None, password_count: int = 1) -> None:
        self.locators = locators or {}
        self.password_count = password_count
        self.keyboard = FakeKeyboard()
        self.goto_calls: list[str] = []
        self.load_state_calls = 0
        self.timeout_waits: list[int] = []
        self.url = "https://extranet.guestsage.com/auth/login?returnTo=%2Fapartment-owner%2Fmy-schedule"

    def locator(self, selector: str) -> FakeLocator:
        if selector == "input[type='password']":
            return FakeLocator([FakeElement() for _ in range(self.password_count)])
        return self.locators.get(selector, FakeLocator())

    def get_by_role(self, role: str, name: str, exact: bool = False) -> FakeLocator:
        del exact
        return self.locators.get(f"role:{role}:{name}", FakeLocator())

    def goto(self, url: str, wait_until: str) -> None:
        del wait_until
        self.goto_calls.append(url)
        self.url = url

    def wait_for_load_state(self, state: str, timeout: int) -> None:
        del state, timeout
        self.load_state_calls += 1

    def wait_for_timeout(self, timeout: int) -> None:
        self.timeout_waits.append(timeout)

    def expect_download(self, timeout: int) -> FakeDownloadContext:
        del timeout
        return FakeDownloadContext()

    def set_default_timeout(self, timeout: int) -> None:
        del timeout


class FakeContext(BrowserContextLike):
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.closed = False

    def new_page(self) -> FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeBrowser(BrowserLike):
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.closed = False
        self.context = FakeContext(page)

    def new_context(self, *, accept_downloads: bool) -> FakeContext:
        assert accept_downloads is True
        return self.context

    def close(self) -> None:
        self.closed = True


class FakeChromium(ChromiumLike):
    def __init__(self, browser: FakeBrowser, failures: list[str] | None = None) -> None:
        self.browser = browser
        self.failures = failures or []
        self.calls: list[dict[str, object]] = []

    def launch(self, **kwargs: object) -> FakeBrowser:
        self.calls.append(kwargs)
        if self.failures:
            failure = self.failures.pop(0)
            raise FakePlaywrightError(failure)
        return self.browser


class FakePlaywright(PlaywrightLike):
    def __init__(self, browser: FakeBrowser, failures: list[str] | None = None) -> None:
        self.chromium = FakeChromium(browser, failures)


class FakePlaywrightContext(PlaywrightContextManagerLike):
    def __init__(self, playwright: FakePlaywright) -> None:
        self.playwright = playwright

    def __enter__(self) -> FakePlaywright:
        return self.playwright

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback


def install_fake_playwright_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("topinvoice.scraping.get_playwright_error_type", lambda: FakePlaywrightError)


def test_ensure_playwright_available_raises_when_dependency_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("playwright"):
            raise ModuleNotFoundError(name)
        importer = cast(Callable[..., object], original_import)
        return importer(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ScrapingError, match="Playwright is not installed"):
        ensure_playwright_available()


def test_first_visible_returns_first_available_element(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    locator = FakeLocator([FakeElement(fail_wait=True), FakeElement()])

    assert isinstance(first_visible(locator, 3000), FakeElement)


def test_first_visible_raises_when_all_elements_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    locator = FakeLocator([FakeElement(fail_wait=True)])

    with pytest.raises(ScrapingError, match="No visible element found"):
        first_visible(locator, 3000)


def test_fill_first_and_click_first(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    field = FakeElement()
    button = FakeElement()
    page = FakePage(
        {
            "field": FakeLocator([field]),
            "button": FakeLocator([button]),
        },
    )

    fill_first(page, ("field",), "value", 3000, "field")
    click_first(page, ("button",), 3000, "button")

    assert field.filled_value == "value"


def test_fill_first_raises_when_no_selector_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage({"field": FakeLocator([FakeElement(fail_wait=True)])})

    with pytest.raises(ScrapingError, match="Could not find field"):
        fill_first(page, ("field",), "value", 3000, "field")


def test_click_first_raises_when_no_selector_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage({"button": FakeLocator([FakeElement(fail_wait=True)])})

    with pytest.raises(ScrapingError, match="Could not click button"):
        click_first(page, ("button",), 3000, "button")


def test_login_if_needed_skips_when_not_on_login_screen(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage(password_count=0)

    login_if_needed(page, Config("login", "password"), 3000)

    assert len(page.goto_calls) == 1


def test_login_if_needed_fills_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage(
        {
            "input[placeholder='Email']": FakeLocator([FakeElement()]),
            "input[placeholder='Password']": FakeLocator([FakeElement()]),
            "button[type='submit']": FakeLocator([FakeElement()]),
        },
    )

    login_if_needed(page, Config("login", "password"), 3000)

    assert len(page.goto_calls) == 2


def test_login_if_needed_falls_back_to_enter_when_click_does_not_submit(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    password_field = FakeElement()
    page = FakePage(
        {
            "input[placeholder='Email']": FakeLocator([FakeElement()]),
            "input[placeholder='Password']": FakeLocator([password_field]),
            "input[name='password']": FakeLocator([password_field]),
            "button[type='submit']": FakeLocator([FakeElement()]),
        },
    )
    page.goto = lambda url, wait_until: page.goto_calls.append(url)  # type: ignore[method-assign]

    login_if_needed(page, Config("login", "password"), 3000)

    assert len(page.goto_calls) == 2


def test_click_dropdown_option_success_and_error(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage()

    click_dropdown_option(page, "Option", 3000)

    broken_page = FakePage(
        {
            "role:option:Option": FakeLocator([FakeElement(fail_wait=True)]),
            "xpath=//*[@role='option' and normalize-space()='Option']": FakeLocator([FakeElement(fail_wait=True)]),
            "xpath=//*[self::li or self::div or self::span][normalize-space()='Option']": FakeLocator(
                [FakeElement(fail_wait=True)],
            ),
        },
    )

    with pytest.raises(ScrapingError, match="Could not select dropdown option"):
        click_dropdown_option(broken_page, "Option", 3000)


def test_select_value_by_label_uses_native_select(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    native_element = FakeElement()
    page = FakePage(
        {
            "xpath=//*[normalize-space()='Year']/following::*[self::select][1]": FakeLocator([native_element]),
        },
    )

    select_value_by_label(page, "Year", "2026", 3000)

    assert native_element.selected_label == "2026"


def test_select_value_by_label_uses_dropdown_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    trigger_element = FakeElement()
    page = FakePage(
        {
            "xpath=//*[normalize-space()='Room type']/following::*[self::select][1]": FakeLocator(
                [FakeElement(fail_wait=True)],
            ),
            "xpath=//label[normalize-space()='Room type']/following::*[self::select][1]": FakeLocator(
                [FakeElement(fail_wait=True)],
            ),
            "xpath=//*[normalize-space()='Room type']/following-sibling::*[1]": FakeLocator([trigger_element]),
        },
    )

    select_value_by_label(page, "Room type", "Topolowa 15", 3000)

    assert trigger_element.scrolled is True


def test_select_value_by_label_raises_when_all_paths_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage(
        {
            "xpath=//*[normalize-space()='Year']/following::*[self::select][1]": FakeLocator(
                [FakeElement(fail_wait=True)],
            ),
            "xpath=//label[normalize-space()='Year']/following::*[self::select][1]": FakeLocator(
                [FakeElement(fail_wait=True)],
            ),
            "xpath=//*[normalize-space()='Year']/following-sibling::*[1]": FakeLocator([FakeElement(fail_wait=True)]),
            "xpath=//*[normalize-space()='Year']/parent::*/*[last()]": FakeLocator([FakeElement(fail_wait=True)]),
            "xpath=//*[normalize-space()='Year']/following::*[@role='combobox'][1]": FakeLocator(
                [FakeElement(fail_wait=True)],
            ),
            "xpath=//*[normalize-space()='Year']/following::*[self::button or self::input][1]": FakeLocator(
                [FakeElement(fail_wait=True)],
            ),
        },
    )

    with pytest.raises(ScrapingError, match="Could not set Year"):
        select_value_by_label(page, "Year", "2026", 3000)
    assert page.keyboard.keys == ["Escape", "Escape", "Escape", "Escape"]


def test_open_monthly_report_section_and_select_month_tab(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    section_locator = FakeLocator([FakeElement()])
    page = FakePage(
        {
            MONTHLY_REPORT_SELECTOR: section_locator,
        },
    )

    section = open_monthly_report_section(page, 3000)
    assert section is section_locator

    select_month_tab(page, "Mar", 3000)
    assert page.timeout_waits == [800]


def test_select_month_tab_raises_when_all_candidates_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    broken_section = FakeLocator([FakeElement()])
    page = FakePage(
        {
            MONTHLY_REPORT_SELECTOR: broken_section,
        },
    )

    monkeypatch.setattr(
        FakeLocator,
        "get_by_role",
        lambda self, role, name, exact=False: FakeLocator([FakeElement(fail_wait=True)]),
    )
    monkeypatch.setattr(
        FakeLocator,
        "get_by_text",
        lambda self, text, exact=False: FakeLocator([FakeElement(fail_wait=True)]),
    )
    monkeypatch.setattr(
        FakeLocator,
        "locator",
        lambda self, selector: FakeLocator([FakeElement(fail_wait=True)]),
    )

    with pytest.raises(ScrapingError, match="Could not select month tab"):
        select_month_tab(page, "Mar", 3000)


def test_export_csv_saves_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage(
        {
            MONTHLY_REPORT_SELECTOR: FakeLocator(),
        },
    )

    csv_path = export_csv(page, Period(2026, 3), tmp_path, 3000)

    assert csv_path == tmp_path / "guestsage-monthly-report-2026-03.csv"


def test_launch_browser_prefers_local_chrome(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage()
    browser = FakeBrowser(page)
    playwright = FakePlaywright(browser)
    monkeypatch.setattr("topinvoice.scraping.CHROME_EXECUTABLE_CANDIDATES", (Path(__file__),))

    launched_browser = launch_browser(playwright, headless=True)

    assert launched_browser is browser
    assert playwright.chromium.calls[0]["headless"] is True


def test_launch_browser_falls_back_and_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage()
    browser = FakeBrowser(page)
    playwright = FakePlaywright(browser, failures=["local", "channel", "default"])
    monkeypatch.setattr("topinvoice.scraping.CHROME_EXECUTABLE_CANDIDATES", (Path(__file__),))

    with pytest.raises(ScrapingError, match="Could not launch a browser"):
        launch_browser(playwright, headless=False)


def test_launch_browser_skips_missing_local_executables(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage()
    browser = FakeBrowser(page)
    playwright = FakePlaywright(browser, failures=["channel"])
    monkeypatch.setattr("topinvoice.scraping.CHROME_EXECUTABLE_CANDIDATES", (Path("/missing-browser"),))

    launched_browser = launch_browser(playwright, headless=False)

    assert launched_browser is browser


def test_ensure_playwright_available_success() -> None:
    assert callable(ensure_playwright_available())


def test_get_playwright_error_type_success() -> None:
    error_type = get_playwright_error_type()

    assert issubclass(error_type, Exception)


def test_get_playwright_error_type_raises_when_dependency_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("playwright"):
            raise ModuleNotFoundError(name)
        importer = cast(Callable[..., object], original_import)
        return importer(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ScrapingError, match="Playwright is not installed"):
        import topinvoice.scraping as scraping

        scraping.get_playwright_error_type()


def test_guestsage_scraper_orchestrates_browser_flow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    install_fake_playwright_error(monkeypatch)
    page = FakePage({"text=Monthly report": FakeLocator()})
    browser = FakeBrowser(page)
    playwright = FakePlaywright(browser)
    monkeypatch.setattr(
        "topinvoice.scraping.ensure_playwright_available",
        lambda: (lambda: FakePlaywrightContext(playwright)),
    )
    monkeypatch.setattr("topinvoice.scraping.login_if_needed", lambda page, credentials, timeout_ms: None)
    monkeypatch.setattr("topinvoice.scraping.select_value_by_label", lambda page, label, option, timeout_ms: None)
    monkeypatch.setattr("topinvoice.scraping.select_month_tab", lambda page, month_label, timeout_ms: None)
    monkeypatch.setattr(
        "topinvoice.scraping.export_csv",
        lambda page, period, downloads_dir, timeout_ms: downloads_dir / "report.csv",
    )

    scraper = GuestSageScraper()
    result = scraper.export_monthly_report(
        period=Period(2026, 3),
        downloads_dir=tmp_path,
        config=Config("login", "password"),
        headless=True,
        timeout_ms=3000,
    )

    assert result == tmp_path / "report.csv"
    assert browser.closed is True
    assert browser.context.closed is True
