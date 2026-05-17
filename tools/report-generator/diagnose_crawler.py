"""诊断 xhs/douyin 搜索为什么返回空。

跑法:
    cd tools/report-generator
    uv run python diagnose_crawler.py xhs "吉他 入门"
    uv run python diagnose_crawler.py douyin "吉他 入门"

会做的事:
1. 用 headless=False 起 Playwright，加载 cookie
2. 检查是否登录 (LOGGED_IN_SELECTOR)
3. 打开搜索页，把所有命中的 XHR url + 状态 + 响应大小打印出来
4. 同时把 search 主接口 (XhsCrawler.SEARCH_API / DouyinCrawler.SEARCH_API) 命中时的
   原始 JSON dump 到 cache/diagnose_<platform>.json
浏览器会停在搜索页 30s，方便人工观察 / 处理弹窗。
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import quote

from crawlers.base import BaseCrawler, COOKIE_DIR
from crawlers.xhs import XhsCrawler
from crawlers.douyin import DouyinCrawler

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def make_url(platform: str, keyword: str) -> str:
    if platform == "xhs":
        return (
            f"https://www.xiaohongshu.com/search_result?"
            f"keyword={quote(keyword)}&source=web_search_result_notes"
            f"&sort=popularity_descending&type=51"
        )
    if platform == "douyin":
        return f"https://www.douyin.com/search/{quote(keyword)}?type=general"
    raise ValueError(platform)


def target_api(platform: str) -> str:
    return XhsCrawler.SEARCH_API if platform == "xhs" else DouyinCrawler.SEARCH_API


async def diagnose(platform: str, keyword: str):
    cls = XhsCrawler if platform == "xhs" else DouyinCrawler
    crawler: BaseCrawler = cls(headless=False)
    await crawler.start()
    page = crawler.page

    print(f"\n=== {platform} cookie file: {crawler.cookie_file} (exists={crawler.cookie_file.exists()}) ===")
    print(f"[step] 检查登录态…")
    try:
        ok = await crawler.is_logged_in()
        print(f"[result] is_logged_in = {ok}")
    except Exception as e:
        print(f"[result] is_logged_in raised: {e}")
        ok = False

    if not ok:
        print(
            "[hint] 未登录或 cookie 过期。运行:\n"
            f"  uv run python -m crawlers.{platform} --login\n"
            "扫码后再回来跑这个脚本。"
        )

    print(f"\n[step] 打开搜索页 keyword={keyword!r}")
    target = target_api(platform)
    raw_dump = []

    async def on_response(resp):
        url = resp.url
        if "xiaohongshu.com" not in url and "douyin.com" not in url:
            return
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        if "json" not in ct and "javascript" not in ct:
            return
        marker = "  *HIT*" if target in url else ""
        print(f"[xhr] {resp.status} {url[:140]}{marker}")
        if target in url:
            try:
                data = await resp.json()
                raw_dump.append({"url": url, "status": resp.status, "data": data})
            except Exception as e:
                print(f"[xhr] body parse failed: {e}")

    page.on("response", on_response)

    try:
        url = make_url(platform, keyword)
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(15)  # 让页面 JS 跑完，等 XHR
    finally:
        page.remove_listener("response", on_response)

    out = CACHE_DIR / f"diagnose_{platform}.json"
    out.write_text(json.dumps(raw_dump, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[result] 命中目标 API {len(raw_dump)} 次，dump -> {out}")
    if raw_dump:
        first = raw_dump[0]["data"]
        items = (first.get("data") or {}).get("items") if platform == "xhs" else (first.get("data") or [])
        print(f"[result] items count = {len(items) if items else 0}")

    print("\n[step] 浏览器停留 30s，可以人工观察是否被风控/登录墙挡住…")
    await asyncio.sleep(30)
    await crawler.close()


def main():
    if len(sys.argv) < 3:
        print("用法: uv run python diagnose_crawler.py <xhs|douyin> <keyword>")
        sys.exit(1)
    platform = sys.argv[1]
    keyword = sys.argv[2]
    asyncio.run(diagnose(platform, keyword))


if __name__ == "__main__":
    main()
