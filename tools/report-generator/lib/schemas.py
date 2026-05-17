"""共享数据 schema。

变化点(相对上一版):
- ReportSection.content 不再是 string,改成 discriminated union(按 content_type 分发)
- 新增 6 种 content type: markdown / budget_tiers / timeline / checklist / cards / qa
- 每个 content 类型有自己的 Pydantic 模型,前端可按 type 字段 route 到组件
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ---------- 公共 ----------

Platform = Literal["xhs", "douyin"]
TimeWindow = Literal["6m", "1y", "2y", "unlimited"]


class Post(BaseModel):
    """一条社交帖子。所有爬虫统一返回这个格式。"""

    id: str  # 全局唯一,建议 f"{platform}_{native_id}"
    platform: Platform
    url: str
    title: str
    author: str
    likes: int = 0
    comments_count: int = 0
    content: str = ""
    cover: str | None = None
    publish_time: str | None = None  # ISO-8601,用于时效性过滤
    top_comments: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    """Report.evidence 里的一条,给前端渲染参考卡片用。"""

    platform: Platform
    url: str
    title: str
    author: str
    likes: int
    snippet: str
    cover: str | None = None


# ---------- ReportSection.content 的 6 种形态 ----------


class MarkdownContent(BaseModel):
    type: Literal["markdown"] = "markdown"
    text: str


class BudgetTier(BaseModel):
    name: str  # "入门" / "进阶" / "顶配"
    price_range: str  # "¥300-800"
    items: list[str] = Field(default_factory=list)  # 代表装备/配置
    note: str = ""  # 这一档的核心建议


class BudgetTiersContent(BaseModel):
    type: Literal["budget_tiers"] = "budget_tiers"
    tiers: list[BudgetTier]


class TimelineEntry(BaseModel):
    label: str  # "1 周" / "1 个月" / "进门"
    title: str  # 这阶段达到什么 / 这步做什么
    detail: str  # 描述


class TimelineContent(BaseModel):
    type: Literal["timeline"] = "timeline"
    entries: list[TimelineEntry]


class ChecklistItem(BaseModel):
    title: str
    detail: str = ""


class ChecklistContent(BaseModel):
    type: Literal["checklist"] = "checklist"
    items: list[ChecklistItem]


class Card(BaseModel):
    title: str
    description: str
    meta: str = ""  # 副信息:地址 / 价格 / 推荐预算 等
    url: str | None = None


class CardsContent(BaseModel):
    type: Literal["cards"] = "cards"
    cards: list[Card]


class QAItem(BaseModel):
    q: str
    a: str


class QAContent(BaseModel):
    type: Literal["qa"] = "qa"
    items: list[QAItem]


SectionContent = Annotated[
    MarkdownContent
    | BudgetTiersContent
    | TimelineContent
    | ChecklistContent
    | CardsContent
    | QAContent,
    Field(discriminator="type"),
]

ContentType = Literal["markdown", "budget_tiers", "timeline", "checklist", "cards", "qa"]


# ---------- Report ----------


class ReportSection(BaseModel):
    id: str  # 对应模板里的 section.id
    title: str
    content: SectionContent
    citations: list[str] = Field(default_factory=list)  # Post.id 列表
    video_refs: list[str] = Field(default_factory=list)  # VideoRef.id 列表


class VideoRef(BaseModel):
    """抖音视频引用,给 ReportSection.video_refs 解析用。"""

    id: str  # "douyin_<aweme_id>"
    url: str
    title: str
    author: str
    likes: int
    cover: str | None = None
    publish_time: str | None = None


class Report(BaseModel):
    hobby_id: str
    hobby_name: str
    category: str
    neon_color: str
    sections: list[ReportSection]
    evidence: dict[str, Evidence]
    videos: dict[str, VideoRef] = Field(default_factory=dict)
