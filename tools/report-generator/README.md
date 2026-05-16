# 三分钟热度 · 离线报告生成工具

爬小红书 / 抖音帖子作为素材，让 Claude agent 用 function calling 生成结构化报告 JSON。

**这是开发期工具，不参与运行时。** 产物写入 `../../src/data/reports/<hobby_id>.json`，由 Next.js 静态读取。

---

## 1. 安装

需要 Python 3.11+。推荐用 [uv](https://github.com/astral-sh/uv)。

```bash
cd tools/report-generator
uv sync
uv run playwright install chromium
```

不用 uv 的话：

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .
playwright install chromium
```

## 2. 配置

复制 `.env.example` 到 `.env` 并填入 Anthropic API key：

```bash
cp .env.example .env
# 编辑 .env，填 ANTHROPIC_API_KEY=sk-...
```

## 3. 首次扫码登录

每个平台首次跑要扫码一次，cookie 会持久化到 `.cookies/`：

```bash
uv run python -m crawlers.xhs --login
uv run python -m crawlers.douyin --login
```

浏览器会弹出来，手机扫码即可。完成后 cookie 自动保存，后续跑不再需要登录。

## 4. 跑

```bash
# 单个爱好
uv run python generate_reports.py --hobby guitar

# 全量（读 ../../src/data/hobbies.json）
uv run python generate_reports.py --all

# dry-run（不调 Claude，只爬取存原始数据）
uv run python generate_reports.py --hobby guitar --no-llm
```

产物：
- `../../src/data/reports/<hobby_id>.json` — 最终报告（commit）
- `cache/<hobby_id>.raw.json` — 爬取的原始帖子（不 commit）

## 5. 目录

```
tools/report-generator/
├── pyproject.toml
├── .env.example
├── README.md
├── generate_reports.py          # 主入口
├── tools.py                     # Claude function tool 定义 + dispatch
├── lib/
│   ├── schemas.py               # Pydantic: Post, Report
│   └── agent.py                 # agent loop helper
├── crawlers/
│   ├── base.py                  # Playwright + cookie 持久化基类
│   ├── xhs.py                   # 小红书
│   └── douyin.py                # 抖音
├── .cookies/                    # gitignored
└── cache/                       # gitignored，原始爬取数据
```

## 6. 实现状态

爬虫核心逻辑（搜索 endpoint、签名生成、字段解析）按 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 借鉴。当前 `crawlers/xhs.py` 和 `douyin.py` 的关键方法标了 `# TODO(MediaCrawler)` —— 照着仓库的对应模块填即可。
