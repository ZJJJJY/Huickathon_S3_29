"""模板加载、prompt 拼装、报告校验。

模板文件位于 ../templates/<category>.json。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from lib.schemas import (
    BudgetTiersContent,
    CardsContent,
    ChecklistContent,
    ContentType,
    MarkdownContent,
    QAContent,
    ReportSection,
    TimelineContent,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


# ---------- 模板 schema ----------


class SectionSpec(BaseModel):
    id: str
    title: str
    content_type: ContentType
    prompt_hint: str


class SearchStrategy(BaseModel):
    platform_quota: dict[Literal["xhs", "douyin"], int]
    keyword_templates: list[str]


class CategoryTemplate(BaseModel):
    category: str
    label: str
    sections: list[SectionSpec]
    search_strategy: SearchStrategy

    def section_by_id(self, sid: str) -> SectionSpec | None:
        return next((s for s in self.sections if s.id == sid), None)

    @property
    def required_section_ids(self) -> list[str]:
        return [s.id for s in self.sections]


def load_template(category: str) -> CategoryTemplate:
    path = TEMPLATES_DIR / f"{category}.json"
    if not path.exists():
        raise FileNotFoundError(f"模板不存在: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return CategoryTemplate.model_validate(raw)


# ---------- prompt 拼装 ----------


# 每种 content_type 对应的 JSON 结构样例,塞进 prompt 帮模型理解
_CONTENT_TYPE_EXAMPLES: dict[ContentType, str] = {
    "markdown": '{ "type": "markdown", "text": "一段 markdown 文本..." }',
    "budget_tiers": (
        '{ "type": "budget_tiers", "tiers": ['
        '{ "name": "入门", "price_range": "¥300-800", '
        '"items": ["民谣吉他 (Yamaha F310)", "调音器", "拨片"], '
        '"note": "够弹流行歌副歌" }'
        "] }"
    ),
    "timeline": (
        '{ "type": "timeline", "entries": ['
        '{ "label": "1 周", "title": "认识 6 根弦", '
        '"detail": "学会调音 + 按基本和弦 C/G/Am/F" }'
        "] }"
    ),
    "checklist": (
        '{ "type": "checklist", "items": ['
        '{ "title": "出发前查天气", "detail": "重点看风力和降水概率" }'
        "] }"
    ),
    "cards": (
        '{ "type": "cards", "cards": ['
        '{ "title": "南山滑雪场", "description": "北京最近的雪场,新手道多", '
        '"meta": "北京 · 冬季 11-3 月 · ¥200/天", "url": null }'
        "] }"
    ),
    "qa": (
        '{ "type": "qa", "items": ['
        '{ "q": "一个人能玩吗?", "a": "可以,大多数店都有拼场..." }'
        "] }"
    ),
}


def build_report_prompt(
    template: CategoryTemplate,
    hobby_name: str,
    posts_pool_json: str,
) -> str:
    """拼装第二阶段的 prompt:基于素材池产出结构化 sections。"""

    sections_spec_lines = []
    for s in template.sections:
        example = _CONTENT_TYPE_EXAMPLES[s.content_type]
        sections_spec_lines.append(
            f'- id="{s.id}"  title="{s.title}"  content_type="{s.content_type}"\n'
            f"  指引: {s.prompt_hint}\n"
            f"  content 形态: {example}"
        )
    sections_spec = "\n".join(sections_spec_lines)

    return f"""为爱好「{hobby_name}」生成入坑决策报告。

# 任务
基于下方素材池,严格按指定结构产出 JSON。

# 严格约束
1. sections 数组必须**完整包含且只包含**下列 {len(template.sections)} 个 section,顺序一致:
{sections_spec}

2. 每个 section 的 content 必须严格匹配对应 content_type 的 JSON 结构(见上方示例)。
3. 每个 section 的 citations 必须列出至少 2 条素材 id(从素材池里挑),最多 5 条。
4. 内容**必须**基于素材池,不得编造。
   如某段内容没有素材支持,宁可写得简短一些。
5. 每个 section 加一个 `video_query` 字段,值是字符串或 null:
   - 想给这个 section 配抖音视频参考时,填一个适合搜索抖音的中文短关键词
     (2-6 字,通常包含 hobby 名,例如 "吉他 入门"、"陶艺 教程"、"露营 装备")
   - 不需要视频参考的 section(纯文字介绍 / Q&A 等)填 null
   - 总数无强制上限,但建议挑最该配视频的几个 section,空 query 直接 null
6. 直接输出 JSON,不要任何 markdown 包裹和解释。

# 输出 schema
{{
  "sections": [
    {{
      "id": "<section id>",
      "title": "<section title>",
      "content": {{ "type": "<content_type>", ... }},
      "citations": ["<post_id>", ...],
      "video_query": "<keyword>" | null
    }}
  ]
}}

# 素材池
{posts_pool_json}
"""


# ---------- 校验 ----------


class ValidationReport(BaseModel):
    ok: bool
    missing_ids: list[str] = Field(default_factory=list)
    extra_ids: list[str] = Field(default_factory=list)
    wrong_content_type: list[tuple[str, str, str]] = Field(default_factory=list)
    # (section_id, expected_type, got_type)
    pydantic_errors: list[str] = Field(default_factory=list)


def validate_report_payload(
    payload: dict[str, Any], template: CategoryTemplate
) -> tuple[list[ReportSection], ValidationReport, dict[str, str | None]]:
    """把 LLM 输出的 dict 校验成 list[ReportSection]。

    返回 (sections, report, video_queries)。
    - sections: list[ReportSection]
    - report.ok 为 False 时不要采用 sections
    - video_queries: section_id -> 该 section 的 video_query (LLM 提的抖音关键词,
      stage 3 用完就丢,不在 ReportSection 字段里)
    """
    report = ValidationReport(ok=True)
    raw_sections = payload.get("sections", [])
    if not isinstance(raw_sections, list):
        report.ok = False
        report.pydantic_errors.append("sections 不是数组")
        return [], report, {}

    got_ids = [s.get("id", "") for s in raw_sections]
    required = template.required_section_ids

    missing = [i for i in required if i not in got_ids]
    extra = [i for i in got_ids if i not in required]
    if missing:
        report.missing_ids = missing
        report.ok = False
    if extra:
        report.extra_ids = extra
        report.ok = False

    # content_type 匹配
    for raw in raw_sections:
        sid = raw.get("id", "")
        spec = template.section_by_id(sid)
        if spec is None:
            continue  # 已在 extra 里报过
        got_type = raw.get("content", {}).get("type")
        if got_type != spec.content_type:
            report.wrong_content_type.append((sid, spec.content_type, got_type or "<missing>"))
            report.ok = False

    # 抽出 video_query 并从 raw 里移除(ReportSection 不认这个字段)
    video_queries: dict[str, str | None] = {}
    cleaned: list[dict] = []
    for raw in raw_sections:
        sid = raw.get("id", "")
        vq = raw.get("video_query")
        if isinstance(vq, str) and vq.strip():
            video_queries[sid] = vq.strip()
        else:
            video_queries[sid] = None
        cleaned.append({k: v for k, v in raw.items() if k != "video_query"})

    # Pydantic 校验
    sections: list[ReportSection] = []
    for raw in cleaned:
        try:
            sections.append(ReportSection.model_validate(raw))
        except ValidationError as e:
            report.pydantic_errors.append(f"section {raw.get('id', '?')}: {e}")
            report.ok = False

    return sections, report, video_queries


def retry_prompt_suffix(v: ValidationReport) -> str:
    """生成 retry 时附加的提示,告诉模型上一轮错在哪。"""
    lines = ["上一次输出有问题,请严格修正后重新输出完整 JSON:"]
    if v.missing_ids:
        lines.append(f"- 缺失 section: {v.missing_ids}")
    if v.extra_ids:
        lines.append(f"- 多余 section(不应出现): {v.extra_ids}")
    for sid, expected, got in v.wrong_content_type:
        lines.append(f"- section '{sid}' 的 content.type 应为 '{expected}',实际为 '{got}'")
    for e in v.pydantic_errors[:3]:
        lines.append(f"- 字段错误: {e[:200]}")
    return "\n".join(lines)


# ---------- 工具:把素材池序列化给 prompt ----------


def posts_pool_to_prompt(posts: list[Any], max_content_chars: int = 600) -> str:
    """posts 是 list[Post],序列化成 JSON 字符串塞进 prompt。"""
    pool = []
    for p in posts:
        d = p.model_dump() if hasattr(p, "model_dump") else dict(p)
        d["content"] = (d.get("content") or "")[:max_content_chars]
        d["top_comments"] = (d.get("top_comments") or [])[:5]
        # 砍掉 cover URL 等 LLM 用不到的字段
        d.pop("cover", None)
        pool.append(d)
    return json.dumps(pool, ensure_ascii=False, indent=2)
