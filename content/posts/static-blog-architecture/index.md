---
title: "拆一个博客：peanut996.com 给的三个启发"
date: 2026-10-28T21:30:00+08:00
draft: false
tags: ["架构", "静态站点", "hugo"]
categories: ["拆解"]
description: "一个从 2019 年活到现在的个人博客，技术栈换过一次，但骨架一直没变。"
summary: "Hugo + hugo-paper + Vercel + Cloudflare DNS，评论挂在 GitHub Issues 上。判断依据全在响应头和 HTML 里。"
comments: true
ShowToc: true
---

## 结论

| 环节 | 用什么 |
| --- | --- |
| 生成器 | Hugo 0.118.2（`meta generator` 直接写着） |
| 主题 | hugo-paper，Tailwind 3，作者自己加了 KaTeX 和评论 |
| 托管 | Vercel，`server: Vercel` + `x-vercel-cache: HIT` |
| DNS | Cloudflare，只解析不代理（响应里没有 `cf-ray`） |
| 评论 | Gitalk，数据落在 GitHub Issues 仓库里 |
| 图片 | 跟正文同目录的 page bundle |

## 启发一：静态站点的"可拆解性"是种资产

这套站没有任何需要读源码才能理解的东西。打开 DevTools，响应头告诉你托管商，`<meta name=generator>` 告诉你版本，页脚告诉你主题，`<script>` 里的 `repo:"blog-comment"` 告诉你评论存在哪。

对比之下，一个 Next.js + 自建 API 的博客，你要判断它怎么部署的，只能去猜。**能被一眼拆穿的架构，通常也更容易被接手和迁移**——这是选择简单方案时容易被忽略的收益。

## 启发二：内容分栏比主题重要

那个站不止一条时间线，它按用途分了四个 section：

- `/posts/`：正式文章，41 篇；
- `/daily/`：每日记录，98 篇，`Task / Note / Read` 三段式；
- `/read/`：读书笔记，27 篇，URL 直接是微信读书的 bookId；
- `/notes/`：技术长文，4 篇，带子目录。

首页只用 `mainSections = ["posts"]` 展示正式文章，其余栏目靠 URL 或单独入口进入。**这种"一个站点多种节奏"的结构，比任何主题配色都更影响你愿不愿意持续写。**

## 启发三：评论系统是最容易腐烂的一环

它用的是 Gitalk——把每篇文章映射成一个 GitHub Issue，评论就是 issue 里的回复。这个方案 2020 年就已经被 GitHub 的 OAuth 变更打到过一次（作者当年还专门写了篇修复记录），现在页面上仍然能看到明文写着的 `clientSecret`。

同类方案里，现在的默认答案是 **Giscus**：同样是 GitHub 承载，但走 Discussions，权限模型更干净，也不需要把 secret 放进前端。这个站用的就是 Giscus，配置在 `hugo.toml` 里。

## 迁移到自己的站要改什么

如果照着这套骨架搭，只有三处值得替换：

1. Gitalk → Giscus；
2. 前端 `auto-render` 渲染公式 → 保留也行，但版本要锁死并加 SRI（KaTeX 一年几个小版本，未锁版本的 CDN 引用是定时炸弹）；
3. `hugo-paper` 的主题快照已经落后上游两年，要么 pin 一个 commit，要么换维护更活跃的主题。

其余部分——Hugo、静态产物、CDN、Cloudflare 解析——照抄没有问题，这些是这套架构里最不容易过期的部分。