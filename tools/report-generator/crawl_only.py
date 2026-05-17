"""纯爬虫脚本: 不调 LLM, 不走 agent。

对每个 hobby:
  1. 读 category 模板的 keyword_templates, 把 {hobby} 替换成 hobby name
  2. 每个关键词用 XhsCrawler.search 搜 limit=10, 用 hobby 自己的 time_window
  3. 4 个关键词的结果按 id 去重, 按 likes 降序, 取前 10
  4. 落盘 cache/<hobby_id>.raw.json (沿用 generate_reports.py 既有约定)

跑法:
    python crawl_only.py                 # 全量
    python crawl_only.py --hobby guitar  # 单个
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
from pathlib import Path
from typing import Any

from crawlers.xhs import XhsCrawler
from lib.schemas import Post
from lib.templates import load_template

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent.parent
HOBBIES_JSON = PROJECT_ROOT / "src" / "data" / "hobbies.json"
CACHE_DIR = ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)

PER_KEYWORD_LIMIT = 10
FINAL_LIMIT = 10

INTER_KEYWORD_SLEEP = (3.0, 6.0)
INTER_HOBBY_SLEEP = (8.0, 15.0)
MAX_CONSECUTIVE_FAILURES = 3


async def jitter_sleep(rng: tuple[float, float], label: str = "") -> None:
    s = random.uniform(*rng)
    if label:
        print(f"  · sleep {s:.1f}s ({label})")
    await asyncio.sleep(s)


def load_hobbies() -> dict[str, dict[str, Any]]:
    raw = json.loads(HOBBIES_JSON.read_text(encoding="utf-8"))
    flat: dict[str, dict[str, Any]] = {}
    for group in raw:
        for h in group["hobbies"]:
            flat[h["id"]] = {**h, "category": group["category"]}
    return flat


def item_to_post(it: dict) -> Post:
    return Post(
        id=f"xhs_{it['id']}",
        platform="xhs",
        url=it.get("url", ""),
        title=it.get("title", ""),
        author=it.get("author", ""),
        likes=int(it.get("likes") or 0),
        comments_count=int(it.get("comments_count") or 0),
        content=it.get("content", "") or "",
        cover=it.get("cover"),
        publish_time=it.get("publish_time"),
        top_comments=[],
    )


async def crawl_one(crawler: XhsCrawler, hobby_id: str, hobby_meta: dict) -> int:
    template = load_template(hobby_meta["category"])
    keywords = [
        kw.format(hobby=hobby_meta["name"])
        for kw in template.search_strategy.keyword_templates
    ]
    time_window = hobby_meta.get("time_window", "unlimited")

    print(f"\n=== {hobby_id} ({hobby_meta['name']}) | tw={time_window} ===")
    print(f"  关键词: {keywords}")

    by_id: dict[str, dict] = {}
    for idx, kw in enumerate(keywords):
        if idx > 0:
            await jitter_sleep(INTER_KEYWORD_SLEEP, "inter-keyword")
        try:
            items = await crawler.search(
                keyword=kw, limit=PER_KEYWORD_LIMIT, time_window=time_window
            )
        except Exception as e:
            print(f"  ✗ '{kw}' 搜索异常: {e}")
            continue
        n_new = 0
        for it in items:
            nid = it.get("id")
            if not nid:
                continue
            if nid in by_id:
                prev = by_id[nid]
                if int(it.get("likes") or 0) > int(prev.get("likes") or 0):
                    by_id[nid] = it
                continue
            by_id[nid] = it
            n_new += 1
        print(f"  '{kw}' -> {len(items)} 条 (新增 {n_new})")

    if not by_id:
        print(f"  skip: 0 results")
        return 0

    candidates = sorted(
        by_id.values(), key=lambda it: int(it.get("likes") or 0), reverse=True
    )[:FINAL_LIMIT]
    posts = [item_to_post(it) for it in candidates]

    out = CACHE_DIR / f"{hobby_id}.raw.json"
    out.write_text(
        json.dumps([p.model_dump() for p in posts], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tag = "" if len(posts) >= FINAL_LIMIT else f" (partial {len(posts)}/{FINAL_LIMIT})"
    print(f"  保存 {len(posts)} 条 -> {out.relative_to(ROOT)}{tag}")
    return len(posts)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hobby", help="hobby_id, 例如 guitar; 不传则全量")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--show", action="store_true", help="开浏览器窗口 debug")
    args = parser.parse_args()

    hobbies = load_hobbies()
    if args.hobby:
        if args.hobby not in hobbies:
            raise SystemExit(f"未知 hobby: {args.hobby}。可选: {list(hobbies)}")
        targets = [args.hobby]
    else:
        targets = list(hobbies.keys())

    headless = not args.show
    totals: dict[str, int] = {}
    consecutive_failures = 0
    aborted = False
    async with XhsCrawler(headless=headless) as crawler:
        if not await crawler.is_logged_in():
            raise SystemExit(
                "xhs 未登录。先跑: python -m crawlers.xhs --login"
            )
        for idx, hid in enumerate(targets):
            if idx > 0:
                await jitter_sleep(INTER_HOBBY_SLEEP, "inter-hobby")
            try:
                n = await crawl_one(crawler, hid, hobbies[hid])
            except Exception as e:
                print(f"  ✗ {hid} 失败: {e}")
                n = 0
            totals[hid] = n
            if n == 0:
                consecutive_failures += 1
                print(f"  · 连续失败计数: {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}")
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    print(
                        f"\n!!! 连续 {MAX_CONSECUTIVE_FAILURES} 个 hobby 0 条, "
                        f"疑似风控,中止后续 {len(targets) - idx - 1} 个 hobby"
                    )
                    aborted = True
                    break
            else:
                consecutive_failures = 0

    print("\n=== 汇总 ===")
    for hid, n in totals.items():
        print(f"  {hid}: {n}")
    not_run = [hid for hid in targets if hid not in totals]
    if not_run:
        print(f"\n未执行(因中止): {not_run}")
    skipped = [hid for hid, n in totals.items() if n == 0]
    if skipped:
        print(f"\n跳过(0 条): {skipped}")
    if aborted:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())
