"""抖音爬虫。

核心实现照 MediaCrawler 的 media_platform/douyin/ 模块借鉴。
签名:Playwright 页面里调用 window.byted_acrawler.sign 或 a_bogus 生成器。
"""
from __future__ import annotations

from .base import BaseCrawler, TimeWindow, run_login_cli


class DouyinCrawler(BaseCrawler):
    PLATFORM = "douyin"
    LOGIN_URL = "https://www.douyin.com"
    LOGGED_IN_SELECTOR = '[data-e2e="user-info"]'  # 占位

    async def search(
        self,
        keyword: str,
        limit: int = 15,
        time_window: TimeWindow = "unlimited",
    ) -> list[dict]:
        """按关键词搜索视频/图文,按热度排序。

        TODO(MediaCrawler): 抄 media_platform/douyin/core.py 的搜索逻辑:
        1. 调 /aweme/v1/web/search/item/,参数 keyword/offset/count/sort_type=1(综合)
           publish_time 参数对应抖音原生时间过滤(0=不限/1=一天/7=一周/30=一月/180=半年/365=一年)
           我们的 time_window 映射: 6m->180, 1y->365, 2y->730(原生不支持,自己后处理), unlimited->0
        2. 注入签名 a_bogus / _signature
        3. 解析返回 aweme_list,映射到统一格式:
           - id 取 aweme_id
           - title 取 desc
           - likes 取 statistics.digg_count
           - comments_count 取 statistics.comment_count
           - content 取 desc(抖音没有正文字段,desc 既是标题又是描述)
           - cover 取 video.cover.url_list[0]
           - publish_time 取 create_time(unix 秒,转 ISO)
        4. 按 likes 排序取 top limit
        """
        raise NotImplementedError("照 MediaCrawler douyin.core 填这里")

    async def get_comments(self, post_id: str, limit: int = 20) -> list[str]:
        """拿一条视频的热门评论。

        TODO(MediaCrawler): 抄 douyin/core.py 的 get_aweme_all_comments,
        按 digg_count 排序,提取 text 字段返回。
        """
        raise NotImplementedError("照 MediaCrawler douyin.core 填这里")


if __name__ == "__main__":
    run_login_cli(DouyinCrawler)
