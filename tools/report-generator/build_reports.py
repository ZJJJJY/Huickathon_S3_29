"""Stage 2 + Stage 3: 基于已爬取的 xhs cache 生成结构化报告 + 抓抖音视频。

流水线:
  Stage 1 (前置)  crawl_only.py 已经把 10 条/hobby 的 xhs 帖子存到 cache/<id>.raw.json
  Stage 2 (本脚本) Claude 单次 call_json 读 cache,
                    输出 sections[] (含 content + citations + video_query)
                    —— 不再用 agent / get_comments,纯文本素材池
  Stage 3 (本脚本) 对每个 section.video_query 调 DouyinCrawler.search,挑 top1,
                    填回 section.video_refs 和 report.videos
  Stage 4 (本脚本) 落盘 src/data/reports/<id>.json

跑法:
    python build_reports.py --hobby guitar
    python build_reports.py --all
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv

load_dotenv(override=True)  # 必须在 import lib.agent 之前,否则 ANTHROPIC_MODEL 读不到

from pydantic import ValidationError

from crawlers.douyin import DouyinCrawler
from lib.agent import call_json
from lib.schemas import Evidence, Post, Report, ReportSection, VideoRef
from lib.templates import (
    build_report_prompt,
    load_template,
    posts_pool_to_prompt,
    retry_prompt_suffix,
    validate_report_payload,
)

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent.parent
HOBBIES_JSON = PROJECT_ROOT / "src" / "data" / "hobbies.json"
REPORTS_DIR = PROJECT_ROOT / "src" / "data" / "reports"
CACHE_DIR = ROOT / "cache"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DOUYIN_PER_QUERY = 2          # 每个 query 抓的候选数,从中挑 likes 最高的 1 条
INTER_QUERY_SLEEP = (3.0, 6.0)
INTER_HOBBY_SLEEP = (8.0, 15.0)


REPORT_SYSTEM = """你是基于素材生成结构化决策报告的助手。

你将拿到一组小红书帖子作为素材池。任务是按指定的 sections 结构产出 JSON 报告。
- 内容必须基于素材池,不得编造
- 每个 section 决定要不要配抖音参考视频:在该 section 输出里加 `video_query` 字段
  (字符串关键词或 null)
- 最终输出严格 JSON,不要 markdown 包裹"""


# ---------- 加载 ----------


def load_hobbies() -> dict[str, dict[str, Any]]:
    raw = json.loads(HOBBIES_JSON.read_text(encoding="utf-8"))
    flat: dict[str, dict[str, Any]] = {}
    for group in raw:
        for h in group["hobbies"]:
            flat[h["id"]] = {**h, "category": group["category"]}
    return flat


def load_cached_posts(hobby_id: str) -> list[Post]:
    f = CACHE_DIR / f"{hobby_id}.raw.json"
    if not f.exists():
        raise FileNotFoundError(f"cache 不存在: {f}, 先跑 crawl_only.py")
    raw = json.loads(f.read_text(encoding="utf-8"))
    return [Post.model_validate(r) for r in raw]


# ---------- Stage 2: 单次 call_json ----------


def stage2_generate_sections(
    hobby_meta: dict, posts: list[Post]
) -> tuple[list[ReportSection], dict[str, str | None]]:
    """单次 Claude 调用 + 校验/重试,返回 (sections, video_queries)。"""
    template = load_template(hobby_meta["category"])
    prompt = build_report_prompt(
        template, hobby_meta["name"], posts_pool_to_prompt(posts)
    )

    payload = _call_with_json_retry(prompt)
    sections, vr, video_queries = validate_report_payload(payload, template)

    if not vr.ok:
        print(f"  ⚠ 校验失败: missing={vr.missing_ids}, wrong_type={vr.wrong_content_type}")
        retry_prompt = prompt + "\n\n" + retry_prompt_suffix(vr)
        payload = _call_with_json_retry(retry_prompt)
        sections, vr, video_queries = validate_report_payload(payload, template)

    if not vr.ok:
        raise RuntimeError(
            f"{hobby_meta['name']} 报告生成校验失败两次:\n"
            f"  missing={vr.missing_ids}\n"
            f"  extra={vr.extra_ids}\n"
            f"  wrong_type={vr.wrong_content_type}\n"
            f"  errors={vr.pydantic_errors[:2]}"
        )

    return sections, video_queries


def _call_with_json_retry(prompt: str, max_retries: int = 2) -> dict:
    """call_json 但 JSONDecodeError 时附加严格提示再调一次。"""
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        p = prompt
        if attempt > 0 and last_err:
            p = (
                prompt
                + "\n\n上一次输出不是合法 JSON,具体错误:\n  "
                + str(last_err)
                + "\n请严格输出可被 json.loads 解析的 JSON,"
                "注意:\n"
                "  - 字符串里的双引号必须用 \\\" 转义\n"
                "  - 不要尾随逗号\n"
                "  - 不要 markdown 包裹"
            )
        try:
            return call_json(p, system=REPORT_SYSTEM)
        except json.JSONDecodeError as e:
            last_err = e
            print(f"  ⚠ JSON parse 失败 (attempt {attempt + 1}): {e}")
            if attempt == max_retries:
                raise
    # unreachable
    raise RuntimeError("unreachable")


# ---------- Stage 3: 抖音补视频 ----------


async def jitter_sleep(rng: tuple[float, float], label: str = "") -> None:
    s = random.uniform(*rng)
    if label:
        print(f"  · sleep {s:.1f}s ({label})")
    await asyncio.sleep(s)


async def stage3_fetch_videos(
    douyin: DouyinCrawler,
    sections: list[ReportSection],
    video_queries: dict[str, str | None],
    time_window: str,
) -> tuple[dict[str, VideoRef], list[ReportSection]]:
    """对每个 section.video_query 抓抖音 top1, 填回 section.video_refs。

    返回 (videos_dict, 更新后的 sections)。
    """
    videos: dict[str, VideoRef] = {}
    queries_run = 0

    for sec in sections:
        q = video_queries.get(sec.id)
        if not q:
            continue
        if queries_run > 0:
            await jitter_sleep(INTER_QUERY_SLEEP, "inter-query")
        queries_run += 1
        print(f"  · {sec.id} -> 搜抖音 '{q}' (tw={time_window})")

        try:
            items = await douyin.search(
                keyword=q, limit=DOUYIN_PER_QUERY, time_window=time_window
            )
        except Exception as e:
            print(f"    ✗ 搜索异常: {e}")
            continue

        if not items:
            print(f"    · 0 条")
            continue

        chosen = items[0]
        vid_id = f"douyin_{chosen['id']}"
        if vid_id not in videos:
            videos[vid_id] = VideoRef(
                id=vid_id,
                url=chosen["url"],
                title=chosen.get("title", "") or "",
                author=chosen.get("author", "") or "",
                likes=int(chosen.get("likes") or 0),
                cover=chosen.get("cover"),
                publish_time=chosen.get("publish_time"),
            )
        sec.video_refs = [vid_id]
        print(f"    ✓ {vid_id} likes={chosen.get('likes')} | {chosen.get('title', '')[:30]}")

    return videos, sections


# ---------- 主流程 ----------


async def build_one(
    douyin: DouyinCrawler | None,
    hobby_id: str,
    hobby_meta: dict,
    skip_existing: bool = True,
) -> bool:
    print(f"\n=== {hobby_id} ({hobby_meta['name']}) ===")
    out = REPORTS_DIR / f"{hobby_id}.json"
    if skip_existing and out.exists():
        print(f"  · 已存在 {out.relative_to(PROJECT_ROOT)},跳过")
        return True

    posts = load_cached_posts(hobby_id)
    print(f"  cache: {len(posts)} 条 xhs 帖子")

    # Stage 2 (纯 LLM,无网络)
    print(f"  [stage2] call_json 生成 sections + video_query")
    sections, video_queries = stage2_generate_sections(hobby_meta, posts)
    n_q = sum(1 for v in video_queries.values() if v)
    print(f"  [stage2] sections={len(sections)}, video_query 提了 {n_q} 个")

    # Stage 3
    videos: dict[str, VideoRef] = {}
    if douyin and n_q > 0:
        time_window = hobby_meta.get("time_window", "unlimited")
        print(f"  [stage3] 抓抖音视频")
        videos, sections = await stage3_fetch_videos(
            douyin, sections, video_queries, time_window
        )
        print(f"  [stage3] 抓到 {len(videos)} 条视频")
    elif n_q == 0:
        print(f"  [stage3] 跳过(LLM 没提任何 video_query)")
    else:
        print(f"  [stage3] 跳过(douyin 不可用)")

    # 组装 evidence (只保留被 cite 的 xhs)
    cited_post_ids: set[str] = set()
    for s in sections:
        cited_post_ids.update(s.citations)
    evidence = {
        p.id: Evidence(
            platform=p.platform,
            url=p.url,
            title=p.title,
            author=p.author,
            likes=p.likes,
            snippet=(p.content or "")[:200],
            cover=p.cover,
        )
        for p in posts
        if p.id in cited_post_ids
    }

    report = Report(
        hobby_id=hobby_id,
        hobby_name=hobby_meta["name"],
        category=hobby_meta["category"],
        neon_color=hobby_meta["neon_color"],
        sections=sections,
        evidence=evidence,
        videos=videos,
    )

    out = REPORTS_DIR / f"{hobby_id}.json"
    out.write_text(
        json.dumps(report.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  ✓ -> {out.relative_to(PROJECT_ROOT)}")
    return True


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hobby", help="hobby_id, 例如 guitar")
    parser.add_argument("--all", action="store_true", help="跑全部")
    parser.add_argument("--show", action="store_true", help="开浏览器窗口 debug")
    parser.add_argument("--no-douyin", action="store_true", help="跳过抖音 stage")
    parser.add_argument("--force", action="store_true", help="重新生成已存在的报告")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY 未设置")

    hobbies = load_hobbies()
    if args.all:
        targets = list(hobbies.keys())
    elif args.hobby:
        if args.hobby not in hobbies:
            raise SystemExit(f"未知 hobby: {args.hobby}。可选: {list(hobbies)}")
        targets = [args.hobby]
    else:
        raise SystemExit("用 --hobby <id> 或 --all")

    headless = not args.show
    failures: list[str] = []

    douyin: DouyinCrawler | None = None
    if not args.no_douyin:
        douyin = DouyinCrawler(headless=headless)
        await douyin.start()
        if not await douyin.is_logged_in():
            print("⚠ douyin 未登录, stage 3 全部跳过 (跑 python -m crawlers.douyin --login 重试)")
            await douyin.close()
            douyin = None

    try:
        for idx, hid in enumerate(targets):
            if idx > 0 and douyin:
                await jitter_sleep(INTER_HOBBY_SLEEP, "inter-hobby")
            try:
                await build_one(
                    douyin, hid, hobbies[hid], skip_existing=not args.force
                )
            except Exception as e:
                # 不让单个 hobby 异常(包括 anthropic quota)中止整轮
                print(f"  ✗ {hid} 失败: {type(e).__name__}: {e}")
                failures.append(hid)
    finally:
        if douyin:
            await douyin.close()

    if failures:
        print(f"\n失败: {failures}")


if __name__ == "__main__":
    asyncio.run(main())
