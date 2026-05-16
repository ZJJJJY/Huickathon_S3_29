"""小红书爬虫。

核心实现照 MediaCrawler 的 media_platform/xhs/ 模块借鉴。
签名思路:在 Playwright 打开的页面里通过 page.evaluate 调用页面 JS 签名函数,
不在 Python 复刻加密算法。
"""
from __future__ import annotations

from .base import BaseCrawler, TimeWindow, run_login_cli


class XhsCrawler(BaseCrawler):
    PLATFORM = "xhs"
    LOGIN_URL = "https://www.xiaohongshu.com"
    # TODO(MediaCrawler): 确认登录后稳定出现的 selector
    LOGGED_IN_SELECTOR = ".user-info"  # 占位

    async def search(
        self,
        keyword: str,
        limit: int = 15,
        time_window: TimeWindow = "unlimited",
    ) -> list[dict]:
        """按关键词搜索笔记,按热度排序,返回最多 limit 条。

        返回 schema 见 lib/schemas.Post:
        {id, url, title, author, likes, comments_count, content, cover, publish_time, top_comments}

        TODO(MediaCrawler): 抄 media_platform/xhs/core.py 的 search_posts_by_keyword:
        1. 调搜索接口 /api/sns/web/v1/search/notes,参数 keyword/page/page_size/sort_type=popularity_descending
        2. 用 page.evaluate 注入签名函数,给请求加 x-s / x-t headers
        3. 解析返回 items,映射到统一格式
        4. 对每条结果走详情接口拿完整正文(搜索接口只给摘要)
        5. 按 publish_time 过滤 time_window(unlimited 不过滤)
        6. 按 likes 排序,取 top limit
        """
        raise NotImplementedError("照 MediaCrawler xhs.core 填这里")

    async def get_comments(self, post_id: str, limit: int = 20) -> list[str]:
        """拿一条笔记的热门评论,返回纯文本列表。

        TODO(MediaCrawler): 抄 xhs/core.py 的 get_note_all_comments,
        按 like_count 排序,取 top N,只返回 content 字段列表。
        """
        raise NotImplementedError("照 MediaCrawler xhs.core 填这里")


if __name__ == "__main__":
    run_login_cli(XhsCrawler)
