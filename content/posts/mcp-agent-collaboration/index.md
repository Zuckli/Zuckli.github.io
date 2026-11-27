---
title: "MCP 正在变成 Agent 协作协议：Skills、Tasks、Elicitation 与文件传输"
date: 2026-11-28T01:44:15+08:00
draft: false
tags: ["架构", "工作流", "阅读"]
categories: ["拆解"]
description: "拆解 Skills over MCP、Tasks、Elicitation 与 File Uploads 的协议机制，以及它们如何把 MCP 从工具连接层扩展成 Agent 协作层。"
summary: "一个 MCP Server 过去主要回答“能调用什么”，现在还可以提供做事方法、保存长任务状态、在执行中请求用户输入，并绕开模型上下文传输文件。本文解释这四项能力怎样工作，以及组合之后的工程价值。"
comments: true
ShowToc: true
math: false
---

接入一个 MCP Server，并不等于接入了它背后的专业能力。

假设某家公司已经提供查询订单、创建退款和发送邮件的工具。模型能看见工具名和参数，却仍可能不知道：退款前该核对哪些记录，超过多少金额需要人工批准，异常订单应按什么顺序排查。开发者可以把这些规则塞进系统提示词，用户也可以每次重新解释，但两种做法都很难随服务一起更新。

Anthropic 在 2026 年 11 月 24 日发布的这组更新，补的正是工具之外的协作能力：Skills over MCP 进入公开测试，Tasks 与 Elicitation 在 Claude 和 Claude Code 中正式发布，File Uploads 则将在近期逐步推出。[1]

我更关注的不是功能数量，而是 MCP Server 的职责变了。它不再只提供一组动作，还可以携带领域方法、管理执行过程、请求人的决定，并直接交换文件。MCP 因而不只是“模型怎样调用系统”，也开始描述“模型怎样与一个外部执行者合作”。

## 新能力补上了工具调用的四块空白

MCP 原有的 Tools、Resources 和 Prompts 并没有消失。新扩展处理的是它们不擅长表达的部分。

| 能力 | 回答的问题 | 关键机制 |
| --- | --- | --- |
| Tools | 系统能执行什么动作 | 工具描述、参数 Schema、调用结果 |
| Resources | 模型可以读取什么上下文 | 可寻址资源与按需读取 |
| Skills over MCP | 怎样用这些能力完成一类工作 | Skill 发现、文件读取、按需加载 |
| Tasks | 长时间执行进行到哪一步 | 持久任务句柄、状态轮询、延迟取回结果 |
| Elicitation | 执行途中需要用户决定什么 | 结构化表单或外部 URL 交互 |
| File Uploads | 大文件怎样进出工具 | 内联或带外传输，字节不进入模型上下文 |

这四项能力分别处理方法、时间、交互和数据。它们可以独立使用，但只有放在一起，才覆盖了一次真实工作的完整生命周期。

## Skills over MCP：把做事方法和工具一起交付

工具描述适合说明“这个接口接受什么参数”，不适合装下一整套业务流程。即使开发者勉强写进去，所有用户也会在连接时背上同样长的说明，而且工具一多，相关规则很容易被淹没。

Skills over MCP 把流程知识放进独立的 Skill。一个 Skill 是一个目录，至少包含带 `name` 和 `description` 的 `SKILL.md`，还可以带参考资料、脚本、示例和模板。扩展本身没有重新发明 Skill 格式，而是把 Agent Skills 规范绑定到 MCP 的发现与资源读取机制上。[2]

一次典型加载过程是这样的：

1. Server 在 `server/discover` 中声明 `resources` 能力和 `io.modelcontextprotocol/skills` 扩展。
2. Client 通过 `skills/list` 获取 Skill 列表，通过 `skills/get` 取得单个 Skill 的清单、元数据和文件摘要。
3. 模型先根据名称与描述判断相关性，只有需要时才读取 `SKILL.md` 和辅助文件。
4. Skill 中的文件映射为 MCP Resources，通常使用 `skill://<skill-path>/<file-path>` 形式的 URI，再由 `resources/read` 读取。[2]

这里有一个容易漏掉的边界：调用 `resources/read` 读到一段 Markdown，并不等于激活 Skill。Host 要把读取结果送进自己的 Skill 加载流程，校验内容并执行必要的用户批准，然后才能把指令放入模型上下文。[2]

这也是“按需加载”真正节省上下文的原因。元数据先用于选择，完整指令在命中后加载，辅助文件继续按需读取。它解决的不是网络下载量，而是模型每一轮需要携带多少信息。

知识与工具随 Server 一起更新，也减少了版本错配。服务端改变退款流程时，可以同时更新工具约束和操作手册，用户不必另外寻找一份匹配版本的 Skill。不过，远程 Skill 本质上仍是会影响模型行为的指令。规范明确要求 Host 把它视为不可信输入，标注来源；涉及本机代码执行时，还需要独立的逐 Skill 用户批准。[2]

所以 Skills over MCP 不是“让 Server 接管模型”。它提供的是一条可发现、可更新、带激活边界的知识分发通道。

## Tasks：把一次阻塞调用改成可恢复的状态机

很多工作无法在普通请求的超时时间内完成，例如批量处理、深度调研、CI 流水线，甚至另一套完整的 Agent 循环。让连接一直等待，会占用客户端和服务端资源；中途断线后，调用方还可能连结果是否已经产生都无法确认。

Tasks 把“调用结果”与“执行过程”分开。Client 在请求能力中声明支持 `io.modelcontextprotocol/tasks`，Server 也声明同一扩展。是否把某次 `tools/call` 转成任务，由 Server 按请求决定，Client 不需要为每个工具预先选择同步或异步模式。[3]

需要长任务时，Server 不再直接返回最终结果，而是返回 `CreateTaskResult`：

- `resultType: "task"` 让 Client 明确区分任务句柄与普通工具结果；
- `taskId` 是 Server 生成的持久身份；
- 初始状态、`ttlMs` 和建议的 `pollIntervalMs` 告诉 Client 怎样跟踪任务；
- 任务必须在响应发出前持久创建，避免 Client 拿到一个实际上不存在的句柄。[3]

随后，Client 用 `tasks/get` 轮询状态。状态包括 `working`、`input_required`、`completed`、`failed` 和 `cancelled`；终态中可以携带最终结果或错误。需要取消时使用 `tasks/cancel`，需要补充输入时则通过 `tasks/update` 提交响应。[3]

这个设计的价值不只是“不阻塞”。持久 `taskId` 让 Client 在断线或重启后继续查询同一个任务，状态字段让进度可以展示给用户，TTL 则给结果保留和清理提供了明确边界。Claude 因而能把长工作交给 Server，同时继续处理其他事情，最后再取回结果。ZoomInfo 已经用它执行更深的账户与联系人调研。[1][3]

Tasks 并没有替开发者实现可靠执行系统。任务怎样调度、崩溃后怎样恢复、业务操作怎样保证幂等，仍由 Server 负责。协议标准化的是任务身份、状态和结果取回方式。把返回 `taskId` 当成“任务一定不会丢”，就超出了它能保证的范围。

## Elicitation：让 Server 在执行途中向人要一个决定

工具开始执行后，经常才发现缺少一项不能靠猜测补齐的信息：是否接受一笔费用，是否删除生产数据，是否授权访问第三方账户。传统做法是让模型先问，再重新组织一次工具调用；现在 Server 可以在处理流程中明确提出输入请求。

Elicitation 提供两种模式。[4]

Form 模式用于普通结构化信息。Server 给出说明和受限的 JSON Schema，Client 渲染表单并在发送前校验。为了降低不同客户端的界面实现成本，Schema 主要支持扁平对象中的字符串、数字、布尔值和枚举，不追求表达任意嵌套数据。用户可以检查、修改、拒绝或取消，而不是让模型替用户默认接受。

URL 模式用于密码、访问令牌、支付凭证等敏感交互。Server 提供一个 URL，Client 显示目标域名并取得用户同意，用户在外部页面完成认证、授权或支付。除 URL 本身外，交互数据不暴露给 MCP Client，自然也不会进入模型上下文。它也不能替代 MCP 自身的客户端授权，两者解决的是不同问题。[4]

Elicitation 与 Tasks 可以嵌套。长任务需要输入时进入 `input_required`，`tasks/get` 的响应通过 `inputRequests` 带回请求；Client 收集答案后调用 `tasks/update`，再继续观察任务，直到终态。这样，“等待人”也成为任务状态的一部分，而不是一条脱离执行过程的聊天记录。[3][4]

安全边界仍然不能省略。Client 必须显示是哪个 Server 在请求信息，Server 也必须在执行时重新验证权限。对于 URL 模式，Server 还要确认打开链接并完成授权的人，就是最初触发请求的用户，否则可能产生授权错绑和钓鱼风险。[4]

## File Uploads：模型需要文件内容，不需要接管文件字节

把 PDF、表格或图片直接塞进对话，会同时带来三个问题：文件字节占用上下文，大文件编码成本高，JSON-RPC 消息也不适合承担所有二进制传输。

File Uploads 扩展提供内联和带外两种路径。小文件可以随工具调用内联发送；大文件则先由 Client 在 `tools/call` 中提供文件元数据，例如名称、MIME 类型和大小。Server 可以据此拒绝文件，或者返回一个上传目标。Client 把字节上传到目标后，再用不变的参数重试工具调用。[5]

带外路径的重点是：文件字节既不进入模型上下文，也不进入 JSON-RPC 消息。模型看到的是文件描述、工具结果或后续提取出的内容，实际传输由 Client 与目标端点完成。Server 要返回文件时，也可以在工具结果的 `_meta` 中列出下载目标，让 Client 另行取回。[5]

这条分工很适合文档处理。Server 可以接收完整财报，执行解析、校验和批处理，再只把异常项、统计结果和报告入口交回模型。上下文窗口继续承担理解与判断，不再兼职文件传输协议。

文件能力同样需要明确授权。Host 在发送文件前必须取得用户批准；下载内容也可能包含针对模型的提示注入或危险文件，不能把“来自 MCP Server”当成安全证明。[5]

还要区分产品发布节奏与规范成熟度。原文说 File Uploads 即将在 Claude 和 Claude Code 中逐步推出，但其协议仓库目前仍明确标为实验扩展，尚未成为正式 MCP 规范，后续可能出现不兼容变化。今天设计实现时，能力检测和回退路径不是可选项。[1][5]

## 四项机制怎样拼成一次完整工作

下面用“上传财报并按公司规则生成分析报告”串起整个流程。这个例子不依赖某一家供应商，重点是每一步由谁负责。

| 阶段 | 协议动作 | 责任方与结果 |
| --- | --- | --- |
| 选择方法 | `skills/list`、`skills/get`、`resources/read` | Client 发现相关 Skill，校验并按需加载公司分析流程 |
| 上传文件 | `tools/call` 携带元数据，取得 `UploadTarget` 后重试 | Client 在带外通道上传字节，模型只保留必要的文件描述 |
| 启动任务 | Server 返回 `CreateTaskResult` | Server 持久创建任务，Client 获得 `taskId`、TTL 和轮询建议 |
| 跟踪进度 | Client 调用 `tasks/get` | Client 读取 `working` 等状态，无需保持最初的调用连接 |
| 请求决定 | 任务进入 `input_required`，返回 `inputRequests` | Client 展示付费或发布确认，用户可以接受、拒绝或取消 |
| 恢复执行 | Client 调用 `tasks/update` | Server 获得 `inputResponses`，从中断点继续处理 |
| 交付结果 | `tasks/get` 返回 `completed` | Client 取得分析结果和下载入口，再向用户交付报告 |

这段流程里，模型没有记住所有业务规则，没有一直占着连接等待，也没有替用户作出敏感决定，更没有亲手搬运整份文件。它负责理解目标、选择合适的 Skill、组织调用和解释结果。Host 负责权限、界面与传输，Server 负责领域流程和实际执行。

这比单独增加几个工具更接近真实协作。一个能干活的合作方，不仅要会执行命令，还应带来方法、交代进度、知道何时询问，并能交接工作材料。

## 对 MCP Server 开发者的实际启发

第一，不要把 Skill 写成更长的工具说明。工具说明应描述动作与参数，Skill 应描述跨调用的流程、顺序、质量标准和异常处理。两者版本关联，但职责不同。

第二，不要只把异步函数包装成 `taskId`。至少要确定持久化位置、TTL、轮询间隔、取消语义、断线恢复和最终结果保留时间。若业务有重复执行风险，还要单独设计幂等键。

第三，把需要人承担的决定放回协议。费用、删除、发布和第三方授权应由 Server 明确提出，由 Client 展示，由用户作出选择。模型转述“用户大概同意了”不能成为执行依据。

第四，让文件走文件通道，让模型接收完成任务所需的最小信息。文件引用不等于内容理解，Server 仍要返回可核对的解析结果、错误和来源位置。

最后，按能力协商设计兼容路径。Skills over MCP 的产品支持仍在公开测试，File Uploads 还是实验扩展；一个兼容 Client 不应假设所有 Server 和用户端都具备同一组能力。[1][2][5]

这组更新真正标准化的是协作中的四种信息：方法、状态、决定和字节。下次评审一个 MCP Server，除了问“暴露了多少工具”，更值得问的是：它能否交付自己的专业流程，能否让长工作可恢复，能否在关键时刻把人找回来，以及能否不污染上下文地交换材料。

## Sources

[1] https://claude.com/resources/articles/skills-over-mcp-tasks-and-more — MCP servers can now ship skills, run tasks, and more with Claude
[2] https://modelcontextprotocol.io/extensions/skills/overview — MCP Skills extension
[3] https://modelcontextprotocol.io/extensions/tasks/overview — MCP Tasks extension
[4] https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation — MCP Elicitation
[5] https://github.com/modelcontextprotocol/experimental-ext-file-uploads — Experimental MCP File Uploads extension
