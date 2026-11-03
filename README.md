# 李翔 · 工程笔记

个人博客。Hugo + PaperMod + Pagefind，纯静态，主站托管在 GitHub Pages，同一次构建再镜像到 Cloudflare Workers。

**线上地址：https://zuckli.github.io**（主站）
**镜像：https://lixiang-blog.lixiang22.workers.dev**（同一份产物，`canonical` 指向主站）

## 技术栈

| 层 | 选型 | 说明 |
| --- | --- | --- |
| 生成 | Hugo 0.169（extended） | 单二进制、毫秒级构建，无 Node 依赖 |
| 主题 | PaperMod（git submodule） | 暗色模式、TOC、代码高亮、归档、面包屑 |
| 公式 | KaTeX 0.19.1 | 只在 `math: true` 的文章里加载，版本锁死 + SRI |
| 搜索 | Pagefind 1.6 | 构建后生成静态索引，无后端 |
| 评论 | Giscus（GitHub Discussions） | 未配置时显示占位提示，不加载第三方脚本 |
| 托管 | GitHub Pages（主）+ Cloudflare Workers（镜像） | Pages 免费、根路径干净、自带 HTTPS；Workers 保留为备用入口 |
| CI | GitHub Actions | push 到 main 自动构建 + 部署 |

## 目录

```text
content/
  posts/            # 文章（page bundle：index.md + 图片同目录）
  about.md  archives.md  search.md
  tags/_index.md  categories/_index.md   # 分类页标题（默认是英文 Tags/Categories）
layouts/
  home.html                    # 首页：简介 + 精选 + 编号索引 + 标签 + 订阅
  _partials/home_info.html     # 首页简介：头像 + 文字的网格结构
  _partials/toc.html           # 目录：桌面右侧固定栏 + 移动端折叠块
  _partials/toc_tree.html      # 目录树递归（遍历 .Fragments.Headings）
  _partials/extend_post_content.html  # 文末：完、复制链接、相关文章
  _partials/extend_footer.html # 阅读进度、目录高亮、图片放大、⌘K
  _partials/extend_head.html   # KaTeX 注入
  _partials/comments.html      # Giscus
  _partials/breadcrumbs.html   # 面包屑（文本分隔符，不带悬空箭头）
  _partials/post_nav_links.html # 上一篇 / 下一篇
  search/pagefind.html         # 搜索页 + 常用标签
  _shortcodes/hugo-version.html
 404.html
assets/css/extended/01-custom.css   # 设计变量、基础排版、列表、代码块
assets/css/extended/02-editorial.css # 首页结构、目录栏、文末、阅读工具、打印
static/images/avatar.svg  static/favicon.svg
hugo.toml  wrangler.jsonc  package.json
```

## 样式与交互约定

- 颜色只有中性灰阶 + 一个强调色（`--accent`，墨蓝），浅色/暗色各一套变量，改色只改 `:root`。
- 层次用**细线 + 间距**建立：列表是带分隔线的行，不是卡片；页头/页脚/正文共用 704px 内容宽度。
- 元信息（日期、阅读时长、面包屑、页脚）统一等宽字体 + 等宽数字。
- 正文图片必须带宽高（`layouts/_markup/render-image.html`），避免懒加载高度塌陷。
- 文章封面只在正文页出现，列表页不放大图（`params.cover.hiddenInList`）。
- 目录只渲染一次数据：桌面固定栏（≥1200px）和移动端折叠块共用一个递归 partial，避免重复 `id="TableOfContents"`。
- 正文里的交互（进度条、目录高亮、图片放大、复制链接）全部在两处兜底：`prefers-reduced-motion` 与剪贴板不可用。
- 搜索快捷键：`⌘K` / `Ctrl+K` / `/`；`/search/?q=` 可直接带查询进入。

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

推到 `main` 即发布，`.github/workflows/deploy.yml` 一个 job 里做两件事：

1. `npm run build`（`HUGO_BASEURL` 由 Variable `SITE_URL` 决定，缺省 `https://zuckli.github.io/`）；
2. `actions/deploy-pages` 发到 GitHub Pages（主站），再用 `wrangler-action` 镜像到 Cloudflare Workers（`continue-on-error`，镜像挂了不影响主站）。

仓库名必须是 `<用户名>.github.io`（这里是 `Zuckli.github.io`），站点才会挂在**根路径** `https://zuckli.github.io/`；换名字会变成 `/<仓库名>/` 子路径，`hugo.toml` 的 `baseURL` 也得跟着带子路径。仓库必须是 **public**：免费账号的 Pages 不支持私有仓库（要 Pro）。

本地手动部署镜像（本机 wrangler 已用 OAuth 登录，账号 `lixiang22`）：

```bash
HUGO_BASEURL="https://zuckli.github.io/" npm run deploy
```

`static/_headers` 只对 Cloudflare 那份生效：`/assets/*` 一年 immutable，`/pagefind/*` 一周，HTML 保持 `max-age=0, must-revalidate`。GitHub Pages 不认这个文件（会原样当静态文件返回，无副作用）。

## 国内访问

- `github.io` 是主站，但它在国内的可达性不稳定（部分运营商 DNS 污染 / 阻断 GitHub 相关域），没自有域名时这是最现实的短板。
- `*.workers.dev` 在这台机器上可以打开，但 `cf-ray` 落在 SJC（美西），首字节约 1 秒——能访问，不快。镜像就是为这条退路留的。
- `workers.dev` 在部分国内网络（尤其移动）会被 DNS 污染 / SNI 阻断，给朋友发链接前先让对方试一次。
- 要稳定就换自有域名绑到 Cloudflare（延迟降到 150–300ms 量级），或整体迁到境内 OSS/COS + CDN（需备案）。构建产物不变，只换上传目标。

## 启用评论（Giscus）

**已配置完成**：评论仓库是 [Zuckli/blog-comments](https://github.com/Zuckli/blog-comments)（公开，已开 Discussions），分类用 `General`（Open 类型，访客也能新建 discussion），giscus app 已安装在该仓库上。`hugo.toml` 里存的是：

```toml
[params.comments.giscus]
  repo = "Zuckli/blog-comments"
  repoID = "R_kgDOVhOBJw"
  category = "General"
  categoryID = "DIC_kwDOVhOBJ84DKSG9"
```

换成别的仓库时：

1. 在 GitHub 上建一个公开仓库，开启 Discussions（`gh api -X PATCH repos/<owner>/<repo> -f has_discussions=true`）；
2. 安装 [giscus app](https://github.com/apps/giscus) 并授权该仓库；
3. 用 GraphQL 取 id：`gh api graphql -f query='{repository(owner:"<owner>",name:"<repo>"){id discussionCategories(first:20){nodes{id name}}}}'`；
4. 填进上面的配置。

评论区的配色跟随站点主题切换（`layouts/_partials/comments.html` 里给 iframe postMessage 同步），不依赖系统配色。

使用细节：

- 访客需要登录 GitHub 才能评论，评论内容就是该仓库 Discussions 里的帖子；
- 每个页面按 `pathname` 映射一个 discussion，**第一条评论发出时才创建**，所以新文章一开始显示“0 条评论”；
- 审核就是去 GitHub Discussions 里编辑/删除/锁定，没有额外后台。

## 已知取舍

- **RSS 会带上「关于」「搜索」两个页面**：PaperMod 的 `rss.xml` 只排除 `layout: search/archives`，而搜索页用了自定义 `layout: pagefind`。要改就覆盖 `layouts/rss.xml`，不值得为这个抄一份模板。
- **404 页面标题仍是英文**「404 Page not found」：标题由主题的 `head.html` 生成，改它要复制 200 行 partial，收益太低。正文是中文。
- **主题是 submodule**：升级要显式 `git submodule update --remote themes/PaperMod`，不会悄悄变。PaperMod 要求 Hugo ≥ 0.158，CI 里把 Hugo 版本钉死在 `0.169.0`。
- **`--baseURL` 由环境变量控制**：本地默认 `http://localhost:4321/`，CI 用 `SITE_URL`。site 的 canonical / sitemap / RSS 全依赖它，部署前务必确认。