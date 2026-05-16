"""离线报告生成主入口。模板驱动 + 平台硬配额 + 校验重试。

跑法:
    python generate_reports.py --hobby guitar     # 单个
    python generate_reports.py --all              # 全量
    python generate_reports.py --hobby guitar --no-llm  # 只爬不生成报告

流程:
1. 读 hobby + category 模板(决定 sections / search 策略 / 关键词模板)
2. 收集阶段: agent 用 search_xhs/search_douyin/get_comments 收集素材
   - prompt 里把 keyword_templates 作为「必搜」给 agent
   - agent 跑完后,代码做「平台硬配额」检查,缺的话用默认关键词补
3. 生成阶段: 把素材池作为强 context,要 Claude 输出严格匹配模板的 JSON
   - 校验失败 retry 一次,prompt 里附上具体错在哪
4. 落地: src/data/reports/<hobby_id>.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()  # 必须在 import lib.agent 之前,否则 ANTHROPIC_MODEL 读不到

from pydantic import ValidationError

from crawlers.base import TimeWindow
from lib.agent import AgentLoop, call_json
from lib.schemas import Evidence, Post, Report, ReportSection
from lib.templates import (
    CategoryTemplate,
    build_report_prompt,
    load_template,
    posts_pool_to_prompt,
    retry_prompt_suffix,
    validate_report_payload,
)
from tools import TOOLS_SCHEMA, Tools

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent.parent
HOBBIES_JSON = PROJECT_ROOT / "src" / "data" / "hobbies.json"
REPORTS_DIR = PROJECT_ROOT / "src" / "data" / "reports"
CACHE_DIR = ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


COLLECT_SYSTEM = """你是社交媒体素材采集 agent。给定一个爱好 + 必搜关键词模板,
你的任务是用提供的工具搜集 10-15 条高质量帖子作为后续报告的素材。

策略:
- 第一轮: 严格按提供的「必搜关键词」逐个搜索(小红书 + 抖音都覆盖)
- 第二轮: 看完结果后,如果发现某些重要角度还没素材,可以自由补充几次搜索
- 看到主题契合且高赞的帖子,调 get_comments 拿热评(评论区往往最真实)
- 不要重复搜同一关键词。素材足够后停止,输出一段简短总结(覆盖了哪些角度、收了多少条)。"""


def collect_prompt(hobby_name: str, template: CategoryTemplate, time_window: TimeWindow) -> str:
    kws = "\n".join(f"  - {k.format(hobby=hobby_name)}" for k in template.search_strategy.keyword_templates)
    quota = template.search_strategy.platform_quota
    tw_hint = "" if time_window == "unlimited" else f"\n- 时效性: 优先选近 {time_window} 内发布的内容(已配置爬虫层做过滤,你只需关注热度)"
    return f"""请为爱好「{hobby_name}」收集报告素材。

# 必搜关键词(第一轮)
请逐个调用搜索工具搜下列关键词。小红书和抖音都要覆盖。
{kws}

# 平台配额
- 小红书目标条数: {quota['xhs']}
- 抖音目标条数: {quota['douyin']}
- 优先选高赞 / 高评论数的帖子{tw_hint}

# 流程
1. 把上面的关键词,各调一次 search_xhs 和一次 search_douyin
2. 看完结果后,自由补充搜索(关键词可以更具体,如某个装备名、某种玩法)
3. 选最值得深挖的高赞 xhs 帖子,调 get_comments 拿热评 —— **xhs get_comments 整轮最多调用 3 次,超过会被工具层拒绝**
4. 最后输出一段简短总结(不是报告,只是说明覆盖了哪些角度)
"""


async def collect_evidence(
    tools: Tools, hobby_name: str, template: CategoryTemplate, time_window: TimeWindow
) -> list[Post]:
    """阶段 1: agent 收素材 + 硬配额兜底。"""
    loop = AgentLoop(
        tools_schema=TOOLS_SCHEMA,
        tool_dispatch=tools.dispatch(),
        system=COLLECT_SYSTEM,
    )
    await loop.run(collect_prompt(hobby_name, template, time_window))

    # 硬配额兜底: 检查每个平台条数,不够就用默认关键词补
    quota = template.search_strategy.platform_quota
    counts = tools.store.count_by_platform()
    for platform, target in quota.items():
        gap = target - counts.get(platform, 0)
        if gap <= 0:
            continue
        print(f"  配额不足: {platform} 还缺 {gap} 条,用默认关键词补搜")
        # 用第一个关键词模板再补一次
        kw = template.search_strategy.keyword_templates[0].format(hobby=hobby_name)
        fn = tools.search_xhs if platform == "xhs" else tools.search_douyin
        try:
            await fn(keyword=kw, limit=gap + 5)  # 多搜几条以防去重后还是不够
        except Exception as e:
            print(f"  补搜失败({platform}): {e}")

    return tools.store.all()


REPORT_SYSTEM = """你是基于素材生成结构化报告的助手。严格按 schema 输出 JSON,
不要编造素材里没有的内容。每个 section 必须 citations 引用至少 2 条素材的 id。"""


def build_report(
    hobby_id: str, hobby_meta: dict, template: CategoryTemplate, posts: list[Post]
) -> Report:
    """阶段 2: 把素材喂给 Claude,要它输出结构化 sections,带校验和 retry。"""
    if not posts:
        raise RuntimeError(f"{hobby_id} 没有任何素材,跳过")

    prompt = build_report_prompt(template, hobby_meta["name"], posts_pool_to_prompt(posts))

    # 第一次尝试
    payload = call_json(prompt, system=REPORT_SYSTEM)
    sections, vr = validate_report_payload(payload, template)

    if not vr.ok:
        # retry 一次,prompt 里附上具体错误
        print(f"  ⚠ 校验失败: missing={vr.missing_ids}, wrong_type={vr.wrong_content_type}")
        retry_prompt = prompt + "\n\n" + retry_prompt_suffix(vr)
        payload = call_json(retry_prompt, system=REPORT_SYSTEM)
        sections, vr = validate_report_payload(payload, template)

    if not vr.ok:
        raise RuntimeError(
            f"{hobby_id} 生成报告校验失败两次:\n"
            f"  missing={vr.missing_ids}\n"
            f"  extra={vr.extra_ids}\n"
            f"  wrong_type={vr.wrong_content_type}\n"
            f"  errors={vr.pydantic_errors}"
        )

    # 收集 citation id,组装 evidence
    cited: set[str] = set()
    for s in sections:
        cited.update(s.citations)

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
        if p.id in cited
    }

    return Report(
        hobby_id=hobby_id,
        hobby_name=hobby_meta["name"],
        category=hobby_meta["category"],
        neon_color=hobby_meta["neon_color"],
        sections=sections,
        evidence=evidence,
    )


def load_hobbies() -> dict[str, dict[str, Any]]:
    raw = json.loads(HOBBIES_JSON.read_text(encoding="utf-8"))
    flat: dict[str, dict[str, Any]] = {}
    for group in raw:
        for h in group["hobbies"]:
            flat[h["id"]] = {**h, "category": group["category"]}
    return flat


async def generate_one(hobby_id: str, hobby_meta: dict, no_llm: bool = False):
    print(f"\n=== {hobby_id} ({hobby_meta['name']}) ===")
    template = load_template(hobby_meta["category"])
    time_window: TimeWindow = hobby_meta.get("time_window", "unlimited")
    print(f"  category={hobby_meta['category']}  time_window={time_window}")

    async with Tools(time_window=time_window) as tools:
        posts = await collect_evidence(tools, hobby_meta["name"], template, time_window)

    raw_file = CACHE_DIR / f"{hobby_id}.raw.json"
    raw_file.write_text(
        json.dumps([p.model_dump() for p in posts], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  原始素材 {len(posts)} 条 -> {raw_file.relative_to(ROOT)}")

    if no_llm:
        print("  --no-llm,跳过报告生成")
        return

    report = build_report(hobby_id, hobby_meta, template, posts)
    out = REPORTS_DIR / f"{hobby_id}.json"
    out.write_text(
        json.dumps(report.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  报告 -> {out.relative_to(PROJECT_ROOT)}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hobby", help="hobby_id,例如 guitar")
    parser.add_argument("--all", action="store_true", help="跑全部")
    parser.add_argument("--no-llm", action="store_true", help="只爬取不调 Claude")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY") and not args.no_llm:
        raise SystemExit("ANTHROPIC_API_KEY 未设置(或加 --no-llm)")

    hobbies = load_hobbies()
    if args.all:
        targets = list(hobbies.keys())
    elif args.hobby:
        if args.hobby not in hobbies:
            raise SystemExit(f"未知 hobby: {args.hobby}。可选: {list(hobbies)}")
        targets = [args.hobby]
    else:
        raise SystemExit("用 --hobby <id> 或 --all")

    failures = []
    for hid in targets:
        try:
            await generate_one(hid, hobbies[hid], no_llm=args.no_llm)
        except (RuntimeError, ValidationError, NotImplementedError) as e:
            print(f"  ✗ {hid} 失败: {e}")
            failures.append(hid)

    if failures:
        print(f"\n失败列表: {failures}")


if __name__ == "__main__":
    asyncio.run(main())
