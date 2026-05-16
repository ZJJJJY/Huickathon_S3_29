"""把爬虫包成 Claude function tool。

变化点(相对上一版):
- search_xhs / search_douyin 增加 time_window 参数(由外层 hobby 配置决定,传给爬虫)
- 增加 search_posts(platform, ...) 兜底接口,方便硬配额补齐时直接调用
- PostStore 同前

agent 看到的是「轻量条目 + 唯一 id」,完整 Post 留在 Python 进程,
通过 id 反查,避免 context 爆炸。
"""
from __future__ import annotations

from typing import Any

from crawlers.base import TimeWindow
from crawlers.douyin import DouyinCrawler
from crawlers.xhs import XhsCrawler
from lib.schemas import Post

# --- 工具 schema(给 Claude 看) ---

TOOLS_SCHEMA: list[dict] = [
    {
        "name": "search_xhs",
        "description": (
            "搜索小红书笔记。按热度返回最匹配的若干条。"
            "用来收集某个爱好的真实玩家分享、避坑指南、入门教程。"
            "返回每条:{id, platform, title, author, likes, comments_count, snippet}。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词,如「吉他入门」「新手买琴避坑」",
                },
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 30},
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "search_douyin",
        "description": (
            "搜索抖音视频/图文。按热度返回最匹配的若干条。"
            "用来收集生动的体验类内容、达人推荐。"
            "返回字段同 search_xhs。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 30},
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "get_comments",
        "description": (
            "拿某条帖子的热评 top N。评论区经常比正文更真实,"
            "适合在 agent 觉得某条帖子重要、想深挖时调用。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "之前 search_* 返回的 id,例如 xhs_xxx 或 douyin_xxx",
                },
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["post_id"],
        },
    },
]


class PostStore:
    def __init__(self):
        self._by_id: dict[str, Post] = {}

    def put(self, posts: list[Post]):
        for p in posts:
            self._by_id[p.id] = p

    def get(self, post_id: str) -> Post | None:
        return self._by_id.get(post_id)

    def all(self) -> list[Post]:
        return list(self._by_id.values())

    def count_by_platform(self) -> dict[str, int]:
        out = {"xhs": 0, "douyin": 0}
        for p in self._by_id.values():
            out[p.platform] = out.get(p.platform, 0) + 1
        return out

    def slim_for_agent(self, posts: list[Post]) -> list[dict]:
        return [
            {
                "id": p.id,
                "platform": p.platform,
                "title": p.title,
                "author": p.author,
                "likes": p.likes,
                "comments_count": p.comments_count,
                "snippet": (p.content or "")[:120],
            }
            for p in posts
        ]


class Tools:
    """爬虫实例 + PostStore 包一起,给 agent loop 用。

    构造时传入 time_window(由当前正在跑的 hobby 决定),
    search_xhs / search_douyin 会带上这个 time_window 调爬虫。
    """

    def __init__(self, time_window: TimeWindow = "unlimited"):
        self.time_window = time_window
        self.xhs = XhsCrawler(headless=True)
        self.douyin = DouyinCrawler(headless=True)
        self.store = PostStore()

    async def __aenter__(self):
        await self.xhs.start()
        await self.douyin.start()
        return self

    async def __aexit__(self, *exc):
        await self.xhs.close()
        await self.douyin.close()

    async def search_xhs(self, keyword: str, limit: int = 10) -> list[dict]:
        raw = await self.xhs.search(keyword, limit=limit, time_window=self.time_window)
        posts = [_to_post("xhs", r) for r in raw]
        self.store.put(posts)
        return self.store.slim_for_agent(posts)

    async def search_douyin(self, keyword: str, limit: int = 10) -> list[dict]:
        raw = await self.douyin.search(keyword, limit=limit, time_window=self.time_window)
        posts = [_to_post("douyin", r) for r in raw]
        self.store.put(posts)
        return self.store.slim_for_agent(posts)

    async def get_comments(self, post_id: str, limit: int = 10) -> list[str]:
        post = self.store.get(post_id)
        if post is None:
            return [f"未找到 {post_id}"]
        crawler = self.xhs if post.platform == "xhs" else self.douyin
        native_id = post_id.split("_", 1)[1]
        comments = await crawler.get_comments(native_id, limit=limit)
        post.top_comments = comments
        return comments

    def dispatch(self) -> dict:
        return {
            "search_xhs": self.search_xhs,
            "search_douyin": self.search_douyin,
            "get_comments": self.get_comments,
        }


def _to_post(platform: str, raw: dict[str, Any]) -> Post:
    native_id = raw.get("id") or raw.get("note_id") or raw.get("aweme_id")
    if not native_id:
        raise ValueError(f"crawler 返回的 raw 缺 id: {raw}")
    return Post(
        id=f"{platform}_{native_id}",
        platform=platform,  # type: ignore[arg-type]
        url=raw.get("url", ""),
        title=raw.get("title", ""),
        author=raw.get("author", ""),
        likes=int(raw.get("likes", 0) or 0),
        comments_count=int(raw.get("comments_count", 0) or 0),
        content=raw.get("content", ""),
        cover=raw.get("cover"),
        publish_time=raw.get("publish_time"),
        top_comments=raw.get("top_comments", []) or [],
    )
