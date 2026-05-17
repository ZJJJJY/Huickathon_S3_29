"""对已有报告补跑抖音视频引用（Stage 3 only）。

用法:
    uv run python fill_section_videos.py --hobby guitar --show
    uv run python fill_section_videos.py --hobby guitar --section budget --show
    uv run python fill_section_videos.py --all --show
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent.parent
HOBBIES_JSON = PROJECT_ROOT / "src" / "data" / "hobbies.json"
REPORTS_DIR = PROJECT_ROOT / "src" / "data" / "reports"

from crawlers.douyin import DouyinCrawler
from lib.schemas import Report, VideoRef

# 每个 section_id 对应的搜索关键词模板（{hobby} 被替换为中文爱好名）
SECTION_QUERY_TEMPLATES: dict[str, str] = {
    "intro":          "{hobby} 是什么 入门介绍",
    "budget":         "{hobby} 多少钱 购买推荐",
    "learning_curve": "{hobby} 怎么学 新手教程",
    "resources":      "{hobby} 教程 学习资源",
    "milestone":      "{hobby} 新手 第一次",
    "qa":             "{hobby} 新手 常见问题",
    # 其他通用 fallback
    "gear":           "{hobby} 装备 推荐",
    "community":      "{hobby} 打卡 一起玩",
    "cost":           "{hobby} 费用 价格",
    "beginner":       "{hobby} 新手 入门",
    "scene":          "{hobby} 体验 打卡",
    "tips":           "{hobby} 技巧 干货",
}

DOUYIN_LIMIT = 3               # 每次取前 N 条候选，选 likes 最高的 1 条
INTER_QUERY_SLEEP = (30.0, 50.0)   # section 间隔
INTER_HOBBY_SLEEP = (90.0, 150.0)  # hobby 间隔（更长，避免跨 hobby 风控）


def load_all_hobby_ids() -> list[str]:
    groups = json.loads(HOBBIES_JSON.read_text(encoding="utf-8"))
    return [h["id"] for g in groups for h in g["hobbies"]]


async def jitter_sleep(rng: tuple[float, float], label: str = "") -> None:
    s = random.uniform(*rng)
    if label:
        print(f"  · {label} {s:.0f}s ...")
    await asyncio.sleep(s)


async def fill_one(
    douyin: DouyinCrawler,
    hobby_id: str,
    only_section: str | None = None,
) -> int:
    """填充单个 hobby 的视频引用，返回新增视频数。"""
    report_path = REPORTS_DIR / f"{hobby_id}.json"
    if not report_path.exists():
        print(f"  · 报告不存在，跳过")
        return 0

    raw = json.loads(report_path.read_text(encoding="utf-8"))
    report = Report.model_validate(raw)

    hobby_name = report.hobby_name
    sections_to_run = [
        s for s in report.sections
        if (only_section is None or s.id == only_section)
        and not s.video_refs
    ]

    if not sections_to_run:
        print(f"  · 所有 section 已有视频，跳过")
        return 0

    print(f"  待填充: {[s.id for s in sections_to_run]}")
    added = 0

    for idx, sec in enumerate(sections_to_run):
        if idx > 0:
            await jitter_sleep(INTER_QUERY_SLEEP, "section 间隔")

        tmpl = SECTION_QUERY_TEMPLATES.get(sec.id, "{hobby} " + sec.title)
        query = tmpl.format(hobby=hobby_name)
        print(f"\n  [{sec.id}] 搜索: 「{query}」")

        try:
            items = await douyin.search(
                keyword=query, limit=DOUYIN_LIMIT, time_window="unlimited"
            )
        except Exception as e:
            print(f"    ✗ 搜索异常: {e}")
            continue

        if not items:
            print(f"    · 0 条 — 触发风控，稍后用 --hobby {hobby_id} --section {sec.id} 重试")
            continue

        chosen = items[0]
        vid_id = f"douyin_{chosen['id']}"
        print(f"    ✓ {vid_id}  likes={chosen.get('likes')}  {str(chosen.get('title',''))[:40]}")

        report.videos[vid_id] = VideoRef(
            id=vid_id,
            url=chosen["url"],
            title=chosen.get("title", "") or "",
            author=chosen.get("author", "") or "",
            likes=int(chosen.get("likes") or 0),
            cover=chosen.get("cover"),
            publish_time=chosen.get("publish_time"),
        )
        sec.video_refs = [vid_id]
        added += 1

    report_path.write_text(
        json.dumps(report.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  ✓ 保存 ({added} 条新视频)")
    return added


async def run_all(headless: bool) -> None:
    hobby_ids = load_all_hobby_ids()

    # 过滤掉已全部填完的
    pending = []
    for hid in hobby_ids:
        f = REPORTS_DIR / f"{hid}.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        needs = any(not s.get("video_refs") for s in r.get("sections", []))
        if needs:
            pending.append(hid)

    print(f"待处理 hobby: {len(pending)} 个")
    print(f"  {pending}\n")

    async with DouyinCrawler(headless=headless) as douyin:
        if not await douyin.is_logged_in():
            raise SystemExit("Douyin 未登录，先跑: uv run python -m crawlers.douyin --login")

        total_added = 0
        for i, hid in enumerate(pending):
            print(f"\n{'='*50}")
            print(f"[{i+1}/{len(pending)}] {hid}")
            if i > 0:
                await jitter_sleep(INTER_HOBBY_SLEEP, "hobby 间隔")
            added = await fill_one(douyin, hid)
            total_added += added

    print(f"\n{'='*50}")
    print(f"全部完成，共新增 {total_added} 条视频引用")


async def run_single(hobby_id: str, headless: bool, only_section: str | None) -> None:
    async with DouyinCrawler(headless=headless) as douyin:
        if not await douyin.is_logged_in():
            raise SystemExit("Douyin 未登录，先跑: uv run python -m crawlers.douyin --login")
        await fill_one(douyin, hobby_id, only_section)


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hobby", help="单个 hobby_id，例如 guitar")
    group.add_argument("--all", action="store_true", help="跑所有缺视频的 hobby")
    parser.add_argument("--section", help="（配合 --hobby）只跑指定 section")
    parser.add_argument("--show", action="store_true", help="显示浏览器窗口（必须，headless 会被拦截）")
    args = parser.parse_args()

    if args.all:
        asyncio.run(run_all(headless=not args.show))
    else:
        asyncio.run(run_single(args.hobby, headless=not args.show, only_section=args.section))


if __name__ == "__main__":
    main()
