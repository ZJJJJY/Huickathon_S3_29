# 三分钟热度 (Three-Minute Spark)

Mobile-first Web 应用，帮用户在产生爱好冲动的瞬间快速判断「值不值得开始」。

## 设计文档

- [`design_minimal.md`](./design_minimal.md) — 最小设计决策
- [`architecture_minimal.md`](./architecture_minimal.md) — 开发文档与目录规范

## 本地开发

```bash
npm install
npm run dev
# 访问 http://localhost:3000
```

> 沙箱环境无法访问 npm registry，请在本地机器上执行 `npm install`。

## 技术栈

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS（已配置霓虹主题色 token）
- Framer Motion（动画）
- lucide-react（图标）

## 目录结构

代码全部位于 `src/`：

```
src/
├── app/                # Next.js App Router 页面
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── components/         # 复用组件
├── lib/
│   ├── theme.ts        # 霓虹色 token + 分类配置
│   └── types.ts        # 共享 TS 类型
├── data/               # 静态 JSON 数据（hobbies.json + reports/）
└── scripts/            # 离线预跑脚本
```
