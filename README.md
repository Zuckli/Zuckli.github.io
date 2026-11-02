# 李想 · 工程笔记

个人博客。Hugo + PaperMod + Pagefind，纯静态，部署到 Cloudflare Workers 静态资源。

## 技术栈

| 层 | 选型 | 说明 |
| --- | --- | --- |
| 生成 | Hugo 0.169（extended） | 单二进制、毫秒级构建，无 Node 依赖 |
| 主题 | PaperMod（git submodule） | 暗色模式、TOC、代码高亮、归档、面包屑 |
| 公式 | KaTeX 0.19.1 | 只在 `math: true` 的文章里加载，版本锁死 + SRI |
| 搜索 | Pagefind 1.6 | 构建后生成静态索引，无后端 |
| 评论 | Giscus（GitHub Discussions） | 未配置时显示占位提示，不加载第三方脚本 |
| 托管 | Cloudflare Workers 静态资源 | 免费、无限带宽，`404.html` 直接生效 |
| CI | GitHub Actions | push 到 main 自动构建 + 部署 |

## 目录

```text
content/
  posts/            # 文章（page bundle：index.md + 图片同目录）
  about.md  archives.md  search.md
layouts/
  _partials/extend_head.html   # KaTeX 注入
  _partials/comments.html      # Giscus
  search/pagefind.html         # 搜索页
  _shortcodes/hugo-version.html
 404.html
assets/css/extended/01-custom.css   # 配色、首页头像网格、移动端点击区域
static/images/avatar.svg  static/favicon.svg
hugo.toml  wrangler.jsonc  package.json
```

## 本地开发

```bash
npm install          # 只装 pagefind + wrangler，Hugo 用 brew 装
npm run dev          # http://localhost:1313，改文件自动刷新
```

本地开发时搜索不可用（索引是构建产物），要验证搜索用：

```bash
npm run preview      # 构建 + 起静态服务器 http://localhost:4321
```

## 写新文章

```bash
hugo new content posts/文章标题/index.md
```

图片直接放进同一个目录，正文里写 `![](cover.png)`。需要公式时在 front matter 里把 `math: false` 改成 `true`。

## 部署

1. 推到 GitHub，仓库里建两个 secret：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`；
2. 建一个仓库 Variable `SITE_URL`，值是你的正式地址，**结尾要带 `/`**，例如 `https://blog.example.com/`；
3. Cloudflare 后台给域名加 `A` 记录指向 Workers 路由，或在 Worker 的 Triggers 里绑定自定义域。

手动部署：

```bash
export HUGO_BASEURL="https://blog.example.com/"
npm run deploy       # 构建 + wrangler deploy
```

## 启用评论（Giscus）

1. 在 GitHub 上建一个公开仓库（例如 `blog-comments`），开启 Discussions；
2. 安装 [giscus app](https://github.com/apps/giscus) 并授权该仓库；
3. 打开 [giscus.app](https://giscus.app)，填仓库名，复制生成的 `data-repo-id` 和 `data-category-id`；
4. 填进 `hugo.toml`：

```toml
[params.comments.giscus]
  repo = "你的用户名/blog-comments"
  repoID = "R_xxxxxxx"
  category = "Announcements"
  categoryID = "DIC_xxxxxxx"
```

## 已知取舍

- **RSS 会带上「关于」「搜索」两个页面**：PaperMod 的 `rss.xml` 只排除 `layout: search/archives`，而搜索页用了自定义 `layout: pagefind`。要改就覆盖 `layouts/rss.xml`，不值得为这个抄一份模板。
- **404 页面标题仍是英文**「404 Page not found」：标题由主题的 `head.html` 生成，改它要复制 200 行 partial，收益太低。正文是中文。
- **主题是 submodule**：升级要显式 `git submodule update --remote themes/PaperMod`，不会悄悄变。PaperMod 要求 Hugo ≥ 0.158，CI 里把 Hugo 版本钉死在 `0.169.0`。
- **`--baseURL` 由环境变量控制**：本地默认 `http://localhost:4321/`，CI 用 `SITE_URL`。site 的 canonical / sitemap / RSS 全依赖它，部署前务必确认。