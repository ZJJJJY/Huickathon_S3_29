"""爬虫基类:Playwright 启动 + cookie 持久化 + login 流程脚手架。

子类只需实现:
- LOGIN_URL: 用于扫码登录的页面
- LOGGED_IN_SELECTOR: 登录成功后才会出现的 CSS selector
- search(keyword, limit, time_window) / get_comments(post_id, limit) 业务方法

爬虫核心(搜索 endpoint、签名生成、字段映射)参考 MediaCrawler
对应模块:xhs 看 MediaCrawler/media_platform/xhs,douyin 看 douyin。
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import ClassVar, Literal

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

COOKIE_DIR = Path(__file__).resolve().parent.parent / ".cookies"
COOKIE_DIR.mkdir(exist_ok=True)

TimeWindow = Literal["6m", "1y", "2y", "unlimited"]


class BaseCrawler:
    PLATFORM: ClassVar[str] = "base"
    LOGIN_URL: ClassVar[str] = ""
    LOGGED_IN_SELECTOR: ClassVar[str] = ""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = None
        self._browser: Browser | None = None
        self._ctx: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def cookie_file(self) -> Path:
        return COOKIE_DIR / f"{self.PLATFORM}.json"

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def start(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        storage_state = str(self.cookie_file) if self.cookie_file.exists() else None
        self._ctx = await self._browser.new_context(storage_state=storage_state)
        self._page = await self._ctx.new_page()

    async def close(self):
        if self._ctx:
            await self._ctx.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    @property
    def page(self) -> Page:
        assert self._page is not None, "调 start() 或用 async with"
        return self._page

    async def is_logged_in(self) -> bool:
        if not self.LOGIN_URL or not self.LOGGED_IN_SELECTOR:
            return False
        await self.page.goto(self.LOGIN_URL)
        try:
            await self.page.wait_for_selector(self.LOGGED_IN_SELECTOR, timeout=5000)
            return True
        except Exception:
            return False

    async def login_interactive(self):
        if self.headless:
            raise RuntimeError("login_interactive 需要 headless=False")
        print(f"[{self.PLATFORM}] 打开登录页,请用 app 扫码...")
        await self.page.goto(self.LOGIN_URL)
        for _ in range(60):
            try:
                await self.page.wait_for_selector(self.LOGGED_IN_SELECTOR, timeout=5000)
                break
            except Exception:
                await asyncio.sleep(5)
                print(f"[{self.PLATFORM}] 等待扫码...")
        else:
            raise TimeoutError("登录超时(5 分钟)")
        assert self._ctx is not None
        await self._ctx.storage_state(path=str(self.cookie_file))
        print(f"[{self.PLATFORM}] cookie 已保存到 {self.cookie_file}")


def run_login_cli(crawler_cls: type[BaseCrawler]):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--login", action="store_true", help="弹出浏览器扫码登录")
    args = parser.parse_args()

    async def main():
        async with crawler_cls(headless=not args.login) as c:
            if args.login:
                await c.login_interactive()
            else:
                ok = await c.is_logged_in()
                print(f"{crawler_cls.PLATFORM} logged in: {ok}")

    asyncio.run(main())


# ---------- 时间窗口工具 ----------


def time_window_to_days(tw: TimeWindow) -> int | None:
    """`unlimited` 返回 None,其他返回天数。供 crawler 实现做时间过滤。"""
    return {"6m": 180, "1y": 365, "2y": 730, "unlimited": None}[tw]
