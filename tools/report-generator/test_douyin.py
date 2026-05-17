"""Quick smoke-test: is_logged_in + search("健身") on Douyin."""
import asyncio
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from crawlers.douyin import DouyinCrawler


async def main():
    async with DouyinCrawler(headless=False) as c:
        print("检查登录状态…")
        logged = await c.is_logged_in()
        print(f"logged_in = {logged}")
        if not logged:
            print("未登录，请先运行:  python crawlers/douyin.py --login")
            return

        print("\n搜索「健身」…")
        posts = await c.search("健身", limit=5, time_window="unlimited")
        print(f"拿到 {len(posts)} 条结果")
        for p in posts:
            print(
                f"  [{p['likes']:>6} 赞] {p['author']}: {p['title'][:40]}"
                f"  ({p['publish_time']})"
            )



asyncio.run(main())
