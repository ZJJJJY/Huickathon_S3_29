"""Xiaohongshu crawler.

Strategy (following MediaCrawler media_platform/xhs/):
  MediaCrawler signs X-S/X-T/X-S-Common with the xhshow library and calls
  https://edith.xiaohongshu.com JSON APIs directly. That signing flow is heavy.

  We reuse MediaCrawler's URLs and field mappings, but let the page itself sign:
  - Playwright opens https://www.xiaohongshu.com/search_result?keyword=...
  - The page JS fires /api/sns/web/v1/search/notes with a valid signature
  - page.on("response") captures the JSON we need
  - For details we open /explore/{note_id}?xsec_token=...
    and capture /api/sns/web/v1/feed and /api/sns/web/v2/comment/page

Field mapping (matches MediaCrawler):
  search items[i]:
    id              -> note_id (also used for url)
    xsec_token      -> needed for detail/comment APIs
    note_card.display_title           -> title
    note_card.user.nickname           -> author
    note_card.interact_info.liked_count    -> likes ("1.2w" allowed)
    note_card.interact_info.comment_count  -> comments_count
    note_card.cover.url_default       -> cover
  feed items[0].note_card:
    desc            -> content
    time (ms)       -> publish_time
  comments[i]:
    content         -> text
    like_count      -> sort key
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from .base import BaseCrawler, TimeWindow, run_login_cli, time_window_to_days


def _parse_count(v: Any) -> int:
    """xhs like/comment counts can be '1.2w' / '999+' / int. Normalise to int."""
    if isinstance(v, int):
        return v
    if v is None:
        return 0
    s = str(v).strip().replace(",", "").replace("+", "")
    if not s:
        return 0
    try:
        if s.endswith("w") or s.endswith("W"):
            return int(float(s[:-1]) * 10_000)
        # Chinese-wide chars, handled by ord check
        last = s[-1]
        if ord(last) == 0x4E07:  # wan
            return int(float(s[:-1]) * 10_000)
        if ord(last) == 0x4EBF:  # yi
            return int(float(s[:-1]) * 100_000_000)
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def _ts_ms_to_iso(ts: Any) -> str | None:
    if not ts:
        return None
    try:
        n = int(ts)
        if n > 10_000_000_000:
            n //= 1000
        return datetime.fromtimestamp(n, tz=timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None


class XhsCrawler(BaseCrawler):
    PLATFORM = "xhs"
    LOGIN_URL = "https://www.xiaohongshu.com"
    LOGGED_IN_SELECTOR = "xpath=//a[contains(@href, '/user/profile/')]"

    SEARCH_API = "/api/sns/web/v1/search/notes"
    FEED_API = "/api/sns/web/v1/feed"
    COMMENT_API = "/api/sns/web/v2/comment/page"
    QRCODE_API = "/api/sns/web/v1/login/qrcode/create"

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)
        self._token_cache: dict[str, dict[str, str]] = {}

    async def is_logged_in(self) -> bool:
        """实际探针: 监听 search/notes vs login/qrcode 谁先到。

        DOM 检查不可靠 —— xhs 在 session 过期后仍保留 profile 链接，
        只有调搜索接口时才会弹二维码浮层。
        """
        return await self._probe_search_login(timeout_s=15)

    async def _probe_search_login(self, timeout_s: float = 15) -> bool:
        """打开搜索页一次，看 search/notes 是否带 items 返回。返回 True/False。"""
        page = self.page
        notes_seen = asyncio.Event()
        qrcode_seen = asyncio.Event()

        async def on_response(resp):
            if self.SEARCH_API in resp.url:
                try:
                    data = await resp.json()
                    if (data.get("data") or {}).get("items"):
                        notes_seen.set()
                except Exception:
                    pass
            elif self.QRCODE_API in resp.url:
                qrcode_seen.set()

        page.on("response", on_response)
        try:
            try:
                await page.goto(
                    "https://www.xiaohongshu.com/search_result?keyword=test&type=51",
                    wait_until="domcontentloaded",
                )
            except Exception:
                return False
            elapsed = 0.0
            while elapsed < timeout_s:
                if notes_seen.is_set():
                    return True
                if qrcode_seen.is_set():
                    return False
                await asyncio.sleep(0.5)
                elapsed += 0.5
            return False
        finally:
            page.remove_listener("response", on_response)

    async def login_interactive(self):
        """覆盖父类: 打开搜索页一次, 长窗口监听 search/notes 是否真返回数据。

        每次探针重新 goto 会刷新二维码, 用户来不及扫;
        所以这里只 navigate 一次, 然后等监听器命中。
        """
        if self.headless:
            raise RuntimeError("login_interactive 需要 headless=False")

        page = self.page
        notes_seen = asyncio.Event()
        last_qrcode_at = 0.0

        async def on_response(resp):
            nonlocal last_qrcode_at
            if self.SEARCH_API in resp.url:
                try:
                    data = await resp.json()
                    if (data.get("data") or {}).get("items"):
                        notes_seen.set()
                except Exception:
                    pass
            elif self.QRCODE_API in resp.url:
                last_qrcode_at = asyncio.get_event_loop().time()

        page.on("response", on_response)
        try:
            print(f"[{self.PLATFORM}] 打开搜索页, 请扫描浮层里的二维码…")
            await page.goto(
                "https://www.xiaohongshu.com/search_result?keyword=test&type=51",
                wait_until="domcontentloaded",
            )
            # 长窗口轮询: 最多 8 分钟
            timeout_s = 480
            elapsed = 0.0
            tick = 0
            while elapsed < timeout_s:
                if notes_seen.is_set():
                    break
                await asyncio.sleep(2)
                elapsed += 2
                tick += 1
                if tick % 5 == 0:
                    print(f"[{self.PLATFORM}] 等待扫码… ({int(elapsed)}s/{timeout_s}s)")
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
        notes_future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def on_response(resp):
            if notes_future.done():
                return
            if self.SEARCH_API not in resp.url:
                return
            try:
                data = await resp.json()
            except Exception:
                return
            items = (data.get("data") or {}).get("items") or []
            if items:
                notes_future.set_result(items)

        page.on("response", on_response)
        url = (
            f"https://www.xiaohongshu.com/search_result?"
            f"keyword={quote(keyword)}&source=web_search_result_notes"
            f"&sort=popularity_descending&type=51"
        )
        await page.goto(url, wait_until="domcontentloaded")
        try:
            items = await asyncio.wait_for(notes_future, timeout=20)
        except asyncio.TimeoutError:
            items = []
        finally:
            page.remove_listener("response", on_response)

        items = [
            it for it in items
            if it.get("model_type") not in ("rec_query", "hot_query")
            and (it.get("note_card") or {}).get("display_title") is not None
        ]

        def likes_of(it: dict) -> int:
            nc = it.get("note_card") or {}
            return _parse_count((nc.get("interact_info") or {}).get("liked_count"))

        items.sort(key=likes_of, reverse=True)
        items = items[: limit * 2]

        days = time_window_to_days(time_window)
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=days) if days else None
        )

        out: list[dict] = []
        for it in items:
            if len(out) >= limit:
                break
            note_id = it.get("id") or (it.get("note_card") or {}).get("note_id")
            xsec_token = it.get("xsec_token") or ""
            xsec_source = it.get("xsec_source") or "pc_search"
            if not note_id:
                continue
            self._token_cache[note_id] = {
                "xsec_token": xsec_token,
                "xsec_source": xsec_source,
            }

            nc = it.get("note_card") or {}
            user = nc.get("user") or {}
            interact = nc.get("interact_info") or {}
            cover = (
                (nc.get("cover") or {}).get("url_default")
                or (nc.get("cover") or {}).get("url")
            )

            detail = await self._get_note_detail(note_id, xsec_token, xsec_source)
            content = detail.get("desc") or nc.get("display_title") or ""
            publish_iso = _ts_ms_to_iso(detail.get("time"))

            if cutoff and publish_iso:
                try:
                    if datetime.fromisoformat(publish_iso) < cutoff:
                        continue
                except ValueError:
                    pass

            out.append({
                "id": note_id,
                "url": (
                    f"https://www.xiaohongshu.com/explore/{note_id}"
                    f"?xsec_token={xsec_token}&xsec_source={xsec_source}"
                ),
                "title": nc.get("display_title") or "",
                "author": user.get("nickname") or user.get("nick_name") or "",
                "likes": _parse_count(interact.get("liked_count")),
                "comments_count": _parse_count(interact.get("comment_count")),
                "content": content,
                "cover": cover,
                "publish_time": publish_iso,
                "top_comments": [],
            })

        return out

    async def _get_note_detail(
        self, note_id: str, xsec_token: str, xsec_source: str
    ) -> dict:
        page = self.page
        feed_future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def on_response(resp):
            if feed_future.done():
                return
            if self.FEED_API not in resp.url:
                return
            try:
                data = await resp.json()
            except Exception:
                return
            items = (data.get("data") or {}).get("items") or []
            if items:
                feed_future.set_result(items[0].get("note_card") or {})

        page.on("response", on_response)
        try:
            url = (
                f"https://www.xiaohongshu.com/explore/{note_id}"
                f"?xsec_token={xsec_token}&xsec_source={xsec_source or 'pc_search'}"
            )
            await page.goto(url, wait_until="domcontentloaded")
            try:
                return await asyncio.wait_for(feed_future, timeout=10)
            except asyncio.TimeoutError:
                # fallback: parse window.__INITIAL_STATE__
                try:
                    html = await page.content()
                    m = re.search(
                        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>",
                        html, re.DOTALL,
                    )
                    if m:
                        state = json.loads(m.group(1).replace("undefined", "null"))
                        note = (
                            (state.get("note") or {}).get("noteDetailMap") or {}
                        ).get(note_id, {}).get("note") or {}
                        return note
                except Exception:
                    pass
                return {}
        finally:
            page.remove_listener("response", on_response)

    async def get_comments(
        self, post_id: str, limit: int = 20, url: str | None = None
    ) -> list[str]:
        """拿一篇笔记的热评。

        - 推荐传 url(整段含 xsec_token 的完整 explore url),最稳
        - 不传 url 时回退到 _token_cache 拼 URL(只在 search 之后同进程内可用)
        """
        page = self.page
        if url is None:
            token_info = self._token_cache.get(post_id, {})
            xsec_token = token_info.get("xsec_token", "")
            xsec_source = token_info.get("xsec_source", "pc_search")
            url = (
                f"https://www.xiaohongshu.com/explore/{post_id}"
                f"?xsec_token={xsec_token}&xsec_source={xsec_source}"
            )

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
            cs = (data.get("data") or {}).get("comments") or []
            all_comments.extend(cs)
            if len(all_comments) >= limit or not (data.get("data") or {}).get("has_more"):
                future.set_result(None)

        page.on("response", on_response)
        try:
            await page.goto(url, wait_until="domcontentloaded")
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
            key=lambda c: _parse_count(c.get("like_count")), reverse=True
        )
        texts: list[str] = []
        for c in all_comments[:limit]:
            t = (c.get("content") or "").strip()
            if t:
                texts.append(t)
        return texts


if __name__ == "__main__":
    run_login_cli(XhsCrawler)
