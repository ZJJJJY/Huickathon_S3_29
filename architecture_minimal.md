# 三分钟热度 · 最小开发文档 (architecture_minimal.md)

> 基于 `design_minimal.md` 的最小决策，落地为可直接动手的开发规范。
> 报告 JSON 字段结构留空，标记为 `ReportContent`，后续填充不影响其它模块。

---

## 1. 技术栈

| 层 | 选型 |
|---|---|
| 框架 | Next.js 14 (App Router) |
| 样式 | Tailwind CSS |
| 动画 | Framer Motion |
| 字体图标 | lucide-react |
| 后端 | Next.js API Routes (Node 20) |
| 数据 | 静态 JSON 文件（`/data/*.json`） |
| 部署 | Vercel |

不引入：数据库、Redux、登录、SSE、Serper/Tavily 等。

---

## 2. 项目目录

```
/
├── app/
│   ├── page.tsx                    # 落地页
│   ├── survey/page.tsx             # 问卷页
│   ├── pick/page.tsx               # 分类 + 爱好选择页
│   ├── report/[hobby]/page.tsx     # 报告页
│   └── api/
│       ├── hobbies/route.ts        # GET 全量爱好清单
│       ├── report/route.ts         # GET 单个爱好报告
│       └── random/route.ts         # GET 随机一个爱好
├── components/
│   ├── ui/                         # 通用 UI 原子组件
│   ├── HobbyCard.tsx
│   ├── CategorySection.tsx
│   ├── ReportSection.tsx
│   └── SurveyStep.tsx
├── data/
│   ├── hobbies.json                # 候选爱好清单（人工填）
│   └── reports/
│       ├── guitar.json             # 离线预跑产出
│       ├── ski.json
│       └── ...
├── scripts/
│   └── generate_reports.ts         # 离线预跑脚本（开发者本地跑）
├── lib/
│   ├── types.ts                    # 共享 TS 类型
│   └── theme.ts                    # 霓虹色彩 token
└── public/
```

---

## 3. 数据 Schema

### 3.1 `data/hobbies.json`

```ts
type HobbyCategory =
  | 'skill_growth'        // 技能成长型
  | 'physical'            // 体能体验型
  | 'crafting'            // 创作手工型
  | 'collecting'          // 收藏鉴赏型
  | 'outdoor'             // 自然户外型
  | 'social_competitive'; // 社交竞技型

interface HobbyMeta {
  id: string;             // 'guitar', 'ski'，与 reports/<id>.json 对应
  name: string;           // '吉他'
  emoji: string;          // '🎸'
  one_liner: string;      // 选爱好页卡片副标题
  neon_color: string;     // '#FF3EA5'，霓虹强调色
}

interface CategoryGroup {
  category: HobbyCategory;
  label: string;          // '技能成长型'
  hobbies: HobbyMeta[];   // 4–5 个
}

type HobbiesJSON = CategoryGroup[];
```

### 3.2 `data/reports/<hobby_id>.json`

```ts
interface Report {
  hobby_id: string;
  hobby_name: string;
  category: HobbyCategory;
  neon_color: string;
  content: ReportContent;   // 字段结构待定，先按黑盒 JSON 处理
}

type ReportContent = unknown;  // TODO: 后续定义后替换
```

### 3.3 问卷 Profile（前端 LocalStorage）

```ts
interface Profile {
  // 字段待定，先放占位
  [key: string]: string | number | undefined;
}
```

`Profile` 此版**不喂给在线 LLM**，仅在前端 LocalStorage 保存，可能在报告页头部展示「你在{城市}」之类。

---

## 4. API

所有接口都是纯静态读取，没有副作用。

### 4.1 `GET /api/hobbies`

返回所有分类和候选爱好。

**Response:** `HobbiesJSON`（见 3.1）

### 4.2 `GET /api/report?hobby=<id>`

返回单个爱好的预跑报告。

**Response:** `Report`（见 3.2）。找不到时返回 404。

### 4.3 `GET /api/random`

从全集里随机抽一个爱好的 id。

**Response:** `{ hobby_id: string }`

---

## 5. 页面

### 5.1 落地页 `/`

一句 slogan + 一个霓虹「开始」按钮 → 跳 `/survey`。

### 5.2 问卷页 `/survey`

题目暂未定。结构上预留多步切换（每题一屏 + 进度条 + 下一步），用 Framer Motion 做左右滑入。答案存 LocalStorage。完成后跳 `/pick`。

### 5.3 选爱好页 `/pick`

读 `/api/hobbies`，按 6 个分类分组渲染：

- 每组：分类标题（带分类色发光） + 卡片栅格（每行 2 个）
- 卡片：emoji + 名字 + one_liner，未选中态深色卡 + 细霓虹描边，hover/选中态边框亮起
- 入场动画：分类逐组淡入，卡片在组内 stagger 出现
- 顶部固定一个「🎲 随便来一个」按钮 → 调 `/api/random` → 跳 `/report/[id]`
- 点卡片 → 跳 `/report/[id]`

### 5.4 报告页 `/report/[hobby]`

读 `/api/report?hobby=...`：

- 顶部：爱好名 + 分类 tag + 霓虹色头图
- 中部：按 `ReportContent` 结构渲染（**报告结构定下来后再做**，先放一个通用 JSON pretty viewer 占位）
- 渐次入场动画营造「正在生成」感（实际是本地数据）
- 底部：「🎲 再来一个」按钮

---

## 6. 离线预跑脚本

`scripts/generate_reports.ts`：

输入：`data/hobbies.json` 的全集
处理：对每个 hobby，调用 Anthropic API + Web Search tool，生成 `Report`
输出：`data/reports/<hobby_id>.json`

由开发者本地一次性运行，产物 commit 进仓库。运行时**不会触发**。

```bash
# 大致用法
ANTHROPIC_API_KEY=xxx npx tsx scripts/generate_reports.ts
```

脚本细节（prompt、tool 定义、错误重试）在 `ReportContent` 结构确定后再实现。

---

## 7. 主题色 token

`lib/theme.ts`：

```ts
export const theme = {
  bg: '#0A0A0F',            // 主背景
  bgCard: '#13131A',        // 卡片背景
  text: '#F5F5F7',
  textMuted: '#8B8B95',
  category: {
    skill_growth:        '#3EE8FF',  // 青霓虹
    physical:            '#FF6B35',  // 橙霓虹
    crafting:            '#FFD23F',  // 黄霓虹
    collecting:          '#A855F7',  // 紫霓虹
    outdoor:             '#34D399',  // 绿霓虹
    social_competitive:  '#FF3EA5',  // 粉霓虹
  },
};
```

所有发光效果统一用 `box-shadow: 0 0 12px <color>` + 卡片描边 `border: 1px solid <color>` 实现，避免每个组件各搞各的。

---

## 8. 开发顺序建议

1. ✅ T1 项目初始化 + Tailwind + Framer Motion + 主题 token
2. T2 `data/hobbies.json` 字段定义 + 一份示例数据（每类 1 个先）
3. T3 三个 API 路由（读静态 JSON）
4. T4 落地页 + 选爱好页（含动画）—— **跳过问卷和报告**，先把视觉走通
5. T5 报告页占位（pretty JSON 渲染器）+ 跳转打通
6. T6 问卷页（待题目确定）
7. T7 报告结构定下来后：补 `ReportContent` 类型 + 报告页组件 + 离线脚本
8. T8 Vercel 部署

T1–T5 可以在报告结构未定的情况下并行推进，是最小可演示链路