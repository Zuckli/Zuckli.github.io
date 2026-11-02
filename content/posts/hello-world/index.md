---
title: "开张：一套能长期用下去的写作流水线"
date: 2026-11-02T10:00:00+08:00
draft: false
tags: ["写作", "hugo", "工作流"]
categories: ["博客"]
description: "这个站怎么运转：写什么、写在哪、按一个键之后发生了什么。"
summary: "从 Obsidian 里的一行 Markdown，到 CDN 上的一个静态页面，中间只有两个动作：提交、构建。"
comments: true
ShowToc: true
math: true
---

## 为什么先定流水线

工具选型会变，流水线不该变。我给自己定的约束只有三条：

1. **内容必须是纯文本**，十年后随便哪个编辑器都能打开；
2. **发布只需要一个动作**，不是"打开后台 → 复制粘贴 → 点发布 → 修格式"；
3. **不能有数据库**，没有要备份、要升级、要被扫描的东西。

对应的实现就是：Markdown 放 Git 里，Hugo 在构建时把它编译成 HTML，产物交给 CDN。

## 一次发布的完整路径

```text
content/posts/<slug>/index.md   ← Obsidian 里写
        │  git push
        ▼
GitHub Actions                   ← hugo --gc --minify
        │  public/  (纯静态)
        ▼
Cloudflare Workers 静态资源      ← 全球边缘节点
        │
        ▼
你的浏览器
```

构建耗时和文章数量基本是线性关系：

$$
T(n) = a + b \cdot n
$$

其中 $a$ 是固定开销（读模板、处理资源管线），$b$ 是每篇文章的渲染成本。这个站现在 $n=3$，$T \approx 0.1\text{s}$；就算写到 500 篇，也还是"按下回车就完了"的量级。

## 写作目录长这样

```bash
content/
└── posts/
    ├── _index.md
    ├── hello-world/
    │   ├── index.md        # 正文
    │   └── cover.png       # 这篇的图，跟正文放一起
    └── static-blog-architecture/
        └── index.md
```

图片和正文放在同一个目录（Hugo 叫 page bundle），好处是删文章的时候不会留下孤儿图片，也不用维护图床。引用时直接写相对路径：

```markdown
![示意图](cover.png)
```

## 每天会用到的三条命令

```bash
npm run dev       # 本地预览，改文件自动刷新
npm run build     # 生成 public/ 并用 pagefind 建搜索索引
npm run deploy    # 构建 + 推到 Cloudflare（CI 里跑就省了这步）
```

写新文章：

```bash
hugo new content posts/我的新文章/index.md
```

## 这套东西的边界

它不适合需要登录、需要实时数据、需要评论审核后台的场景——那些直接上框架 + 数据库更省事。个人博客的内容形态是"写完就不怎么改的长文本"，静态化是最省心的答案。

下一篇会拆一个我最近翻过的站点，看看同样的思路在别人手里是怎么落地的。