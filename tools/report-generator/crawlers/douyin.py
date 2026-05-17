"""Douyin crawler.

Strategy (following MediaCrawler media_platform/douyin/):
  MediaCrawler signs requests by calling libs/douyin.js via execjs to produce
  a_bogus, then httpx-calls https://www.douyin.com/aweme/v1/web/general/search/single/.
  That signing also depends on msToken from page.localStorage.xmst plus webid.

  We don't reproduce signing here. Playwright opens
  https://www.douyin.com/search/{kw}?type=general
  the page JS calls /aweme/v1/web/general/search/single/ with a valid signature,
  and page.on("response") captures the JSON we need.

Field mapping (matches MediaCrawler douyin/core.py search & client.py):
  search.data[i].aweme_info  (or aweme_mix_info.mix_items[0]):
    aweme_id                                -> id
    desc                                    -> title / content
    author.nickname                         -> author
    statistics.digg_count                   -> likes
    statistics.comment_count                -> comments_count
    video.cover.url_list[0]                 -> cover
    create_time (sec)                       -> publish_time
  comments[i] (/aweme/v1/web/comment/list/):
    text                                    -> content
    digg_count                              -> sort key

publish_time filter (PublishTimeType):
  6m -> 180 (native)
  1y, 2y -> 0 (not natively supported, post-filter via cutoff)
  unlimited -> 0
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from .base import BaseCrawler, TimeWindow, run_login_cli, time_window_to_days

_NATIVE_PUBLISH_TIME = {"6m": 180, "1y": 0, "2y": 0, "unlimited": 0}


def _ts_sec_to_iso(ts: Any) -> str | None:
    if not ts:
        return None
    try:
        n = int(ts)
        if n > 10_000_000_000:
            n //= 1000
        return datetime.fromtimestamp(n, tz=timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None


class DouyinCrawler(BaseCrawler):
    PLATFORM = "douyin"
    LOGIN_URL = "https://www.douyin.com"
    LOGGED_IN_SELECTOR = '[data-e2e="user-info"], [data-e2e="live-avatar"]'

    SEARCH_API = "/aweme/v1/web/general/search/single/"
    COMMENT_API = "/aweme/v1/web/comment/list/"

    async def is_logged_in(self) -> bool:
        """跑一次实际搜索探针：search/single 真返回 data 才算登录。

        localStorage.HasUserLogin / DOM selector 都不够稳定:
        - 新 context 加载旧 cookie 后这两者可能都拿不到值，但 cookie 实际有效
        - 反过来 DOM selector 也可能在未登录时短暂命中
        所以直接看搜索 API 是否吐数据。
        """
        return await self._probe_search_login(timeout_s=15)

    async def _probe_search_login(self, timeout_s: float = 15) -> bool:
        page = self.page
        ok_seen = asyncio.Event()

        async def on_response(resp):
            if self.SEARCH_API not in resp.url:
                return
            try:
                data = await resp.json()
            except Exception:
                return
            if data.get("data"):
                ok_seen.set()

        page.on("response", on_response)
        try:
            try:
                await page.goto(
                    "https://www.douyin.com/search/test?type=general",
                    wait_until="domcontentloaded",
                )
            except Exception:
                return False
            elapsed = 0.0
            while elapsed < timeout_s:
                if ok_seen.is_set():
                    return True
                await asyncio.sleep(0.5)
                elapsed += 0.5
            return False
        finally:
            page.remove_listener("response", on_response)

    async def login_interactive(self):
        """覆盖父类: 打开搜索页一次, 长窗口监听 search/single 是否真返回数据。

        每次探针重新 goto 会刷新二维码, 用户来不及扫;
        所以这里只 navigate 一次, 然后等监听器命中。
        """
        if self.headless:
            raise RuntimeError("login_interactive 需要 headless=False")

        page = self.page
        ok_seen = asyncio.Event()

        async def on_response(resp):
            if self.SEARCH_API not in resp.url:
                return
            try:
                data = await resp.json()
            except Exception:
                return
            if data.get("data"):
                ok_seen.set()

        page.on("response", on_response)
        try:
            print(f"[{self.PLATFORM}] 打开搜索页, 请扫码 / 完成验证…")
            await page.goto(
                "https://www.douyin.com/search/test?type=general",
                wait_until="domcontentloaded",
            )
            timeout_s = 480
            elapsed = 0.0
            tick = 0
            while elapsed < timeout_s:
                if ok_seen.is_set():
                    break
                await asyncio.sleep(2)
                elapsed += 2
                tick += 1
                if tick % 5 == 0:
                    print(f"[{self.PLATFORM}] 等待登录… ({int(elapsed)}s/{timeout_s}s)")
            else:
                raise TimeoutError("登录超时(8 分钟)")
        finally:
            page.remove_listener("response", on_response)

        assert self._ctx is not None
        await self._ctx.storage_state(path=str(self.cookie_file))
        print(f"[{self.PLATFORM}] cookie 已保存到 {self.cookie_file}")

    async def search(
        self,
        keyword: str,
        limit: int = 15,
        time_window: TimeWindow = "unlimited",
    ) -> list[dict]:
        page = self.page
        publish_time = _NATIVE_PUBLISH_TIME.get(time_window, 0)

        future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def on_response(resp):
            if future.done():
                return
            if self.SEARCH_API not in resp.url:
                return
            try:
                data = await resp.json()
            except Exception:
                return
            if data.get("data"):
                future.set_result(data.get("data") or [])

        page.on("response", on_response)
        url = (
            f"https://www.douyin.com/search/{quote(keyword)}"
            f"?type=general&publish_time={publish_time}&sort_type=0"
            f"&source=normal_search"
        )
        try:
            await page.goto(url, wait_until="domcontentloaded")
            try:
                items = await asyncio.wait_for(future, timeout=20)
            except asyncio.TimeoutError:
                items = []
        finally:
            page.remove_listener("response", on_response)

        awemes: list[dict] = []
        for post in items:
            aweme = post.get("aweme_info")
            if not aweme:
                mix = post.get("aweme_mix_info") or {}
                mix_items = mix.get("mix_items") or []
                aweme = mix_items[0] if mix_items else None
            if aweme:
                awemes.append(aweme)

        awemes.sort(
            key=lambda a: int((a.get("statistics") or {}).get("digg_count") or 0),
            reverse=True,
        )

        days = time_window_to_days(time_window)
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=days) if days else None
        )

        out: list[dict] = []
        for a in awemes:
            if len(out) >= limit:
                break
            aweme_id = a.get("aweme_id")
            if not aweme_id:
                continue
            author = a.get("author") or {}
            stats = a.get("statistics") or {}
            video = a.get("video") or {}
            cover_list = (video.get("cover") or {}).get("url_list") or []
            cover = cover_list[0] if cover_list else None
            publish_iso = _ts_sec_to_iso(a.get("create_time"))

            if cutoff and publish_iso:
                try:
                    if datetime.fromisoformat(publish_iso) < cutoff:
                        continue
                except ValueError:
                    pass

            desc = a.get("desc") or ""
            out.append({
                "id": aweme_id,
                "url": f"https://www.douyin.com/video/{aweme_id}",
                "title": desc[:60],
                "author": author.get("nickname") or "",
                "likes": int(stats.get("digg_count") or 0),
                "comments_count": int(stats.get("comment_count") or 0),
                "content": desc,
                "cover": cover,
                "publish_time": publish_iso,
                "top_comments": [],
            })

        return out

    async def get_comments(self, post_id: str, limit: int = 20) -> list[str]:
        page = self.page
        all_comments: list[dict] = []
        future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def on_response(resp):
            if future.done():
                return
            if self.COMMENT_API not in resp.url:
                return
            try:
                data = await resp.json()
            except Exception:
                return
            cs = data.get("comments") or []
            all_comments.extend(cs)
            if len(all_comments) >= limit or not data.get("has_more"):
                future.set_result(None)

        page.on("response", on_response)
        try:
            await page.goto(
                f"https://www.douyin.com/video/{post_id}",
                wait_until="domcontentloaded",
            )
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except Exception:
                pass
            try:
                await asyncio.wait_for(future, timeout=10)
            except asyncio.TimeoutError:
                pass
        finally:
            page.remove_listener("response", on_response)

        all_comments.sort(
            key=lambda c: int(c.get("digg_count") or 0), reverse=True
        )
        texts: list[str] = []
        for c in all_comments[:limit]:
            t = (c.get("text") or "").strip()
            if t:
                texts.append(t)
        return texts


if __name__ == "__main__":
    run_login_cli(DouyinCrawler)
