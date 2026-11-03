---
title: MCP — 助手的门面(front door)，以及作为 OAuth 授权服务器的 treg
status: shipped
sources:
  - src/treg/application/auth.py
  - src/treg/mcp.py
  - src/treg/domain/identity/health.py
  - src/treg/domain/identity/mcp_oauth.py
  - src/treg/domain/identity/session.py
  - src/treg/domain/identity/access.py
  - src/treg/domain/identity/api_keys.py
  - src/treg/alembic/versions/0082_oauth_sso_provenance.py
  - src/treg/routers/api_keys.py
  - src/treg/routers/auth.py
  - src/treg/web/claude-connector.html
  - src/treg/web/connect-demo.html
  - tests/test_mcp.py
  - tests/test_mcp_oauth.py
  - tests/test_mcp_directory.py
  - tests/test_marketplace_call.py
related:
  - architecture/auth-secrets.md
  - architecture/proxy-model.md
  - architecture/money.md
  - interface/api.md
---

同一个授权服务器还服务一个非 MCP 客户端，「treg for Sheets」（`treg-sheets`）：它自己的资源（`<public_url>/table`）与 scope、一个属于个人而非一个团队的授权，以及一个只在该 table 路由上被接受的令牌。参见 [table](table.md)。

当一个团队要求企业级 SSO 时，常规登录同意无法为该团队创建一个授权。SSO 同意被限定到它自己的团队，包括逐次调用选择团队的 Sheets 请求。`OAuthCode.sso_org_id` 与 `OAuthGrant.sso_org_id` 通过换码与刷新保留那个证明；访问令牌通过内部身份桥把它传给 `require_member`。强制前创建的授权没有这种证明，并会在使用与刷新时停止在被强制团队上工作。一个 SSO 限定作用域的授权无法被移到另一个团队。

# MCP

## 反馈(Feedback)

团队 `/mcp/` 暴露 `feedback(category, message, call_ids?, endpoint_id?)`，使用四值类别枚举与共享 HTTP 入口。这是 treg 上一个增量、非破坏性的写入，而非上游调用。它要求既有的传输身份，且不花费余额。它还暴露 `review(call_id, usefulness, reason?)` 作为一个非破坏性、非幂等的本地写入，被中继到 `/reviews`，使用共享的有用性(usefulness)枚举与描述。邀请采样与提示优先级见 [feedback](feedback.md)。`/mcp/v2/` 两个工具都不注册，因此它绝不渲染 `/call/` 决定的 review 或 feedback 邀请（`_SurfacePolicy.invites`）；`/call/` 仍像对 OpenAI 的客户端那样决定并记录它。

## 托管的 bearer 密钥(Managed bearer keys)

`/mcp/` 与 `/mcp/v2/` 都接受一个活跃的托管密钥作为直接 bearer。MCP 工具把那个 bearer 传给普通 API，因此禁用与吊销在下次工具调用时生效。传输仍可在校验一个非 OAuth bearer 之前列出静态工具 schema；这不授予数据或调用访问。一个七天的 `scp=bootstrap` 登录令牌不是一个团队 bearer，且无法调用任一 MCP 表面；`treg mcp install` 在写入任何客户端配置之前拒绝它。改用团队 Default、Additional 或 Agent 密钥。

MCP OAuth 访问与刷新令牌仍是带类型的、短生命周期的桥接凭据，拥有独立的 V1 与 V2 受众(audience)。它们不通过 `ApiKey` 行解析，也不使用默认密钥控制。这保持 OAuth 刷新与受众隔离不变。

## 供应商授权补救(Provider authorization remediation)

两个调用适配器都使用共享的 [Org 并发守卫](org-concurrency.md)。它们的结构化结果保留 HTTP `Retry-After` 为 `retry_after`，包括团队媒体适配器，因此 MCP 客户端可以在不访问内部 HTTP 响应头的情况下重试一个并发拒绝。

供应商 OAuth 仍是一个人类浏览器动作。一个目录调用预检可以返回一个结构化的 HTTP 428 body，带有缺失或过期的授权、能力(capability)、范围(scopes)、精确的 CLI 命令，以及安全的 dashboard 动作。团队 MCP `call` 工具与目录 MCP `catalog_call_read` 或 `catalog_call_write` 保留那个 body。agent 可以告诉人类要授权什么，并在同意后重试同一个端点。任何 MCP 响应都不包含凭据。

treg 中其他一切都通过 CLI 或 HTTP 调用到达。这些是一个 **助手(assistant)** 进来的门：ChatGPT、Claude、Claude Code、Cursor，或任何说 Model Context Protocol 的东西。两者使用同一部署、数据库与强制层：

- `/mcp/` 是团队 MCP 表面。它保留其目录、团队工具与导入技能行为。
- `/mcp/v2/` 是仅目录的 Claude directory 表面。它无法列出或调用任意团队拥有的工具，包括一个名字匹配某目录端点的团队工具。

## V2 为何存在(Why V2 exists)

团队 `/mcp/` 必须保留其通用 `call` 工具，因为既有用户把它用于目录端点、团队拥有的工具与导入的技能。treg 无法可靠地分类一个任意私有工具的副作用，因此那个表面无法在不破坏既有契约的情况下给 Claude 一个精确的读对写的安全信号。

V2 保持 `/mcp/` 不变，并暴露一个更窄的 directory 边界。它只接受精选的目录 id，并按目录中存储的 HTTP 方法拆分调用。Claude 因此可以对待 GET、HEAD 与 OPTIONS 为读，并对 POST、PUT、PATCH 与 DELETE 请求批准。两个表面仍使用相同的内部凭据、策略、计量、审计与中继机制。

两个版本标签描述不同的东西。`/mcp/v2/` 是 Treg 的第二个 MCP 传输表面。**Connector release V1** 是提交到 Claude directory 的第一个产品发布。

`NormalizeDirectoryMCPPath` 使 `/mcp/v2` 与 `/mcp/v2/` 成为同一个 V2 资源。这是必需的，因为一个真实的 Claude 自定义 connector 流程去掉了尾部斜杠。没有归一化，请求可能落到团队 `/mcp` 挂载点并收到错误的 OAuth 资源身份。

## Claude connector 特性开关(feature flag)

`TREG_CLAUDE_CONNECTOR_ENABLED` 默认 `false`。为 false 时，V2 不挂载、其 lifespan 不启动、V2 资源元数据与新 V2 授权被拒绝，且仅目录调用路由返回 404。团队 `/mcp/` 表面不依赖这个开关。

## MCP 表面维护契约(MCP surface maintenance contract)

两个公开表面有不同的契约，但它们不能有共享行为的不同实现。

| 领域 | 必须保持共享 | 有意的差异 |
|---|---|---|
| 目录搜索 | 加载、排名、价格视图、近似匹配(near misses)，以及 HTTP 使用的同一进程观察缓存与刷新 Task | 下次调用指引与事件源；V2 在其隐藏平台上丢弃行 |
| 端点详情 | `/catalog/endpoints/{id}` 路由与错误形态 | 客户端归属；V2 在其隐藏平台上拒绝一个端点 |
| 调用 | 请求组装、凭据、策略、限制、幂等、中继、错误、计量、审计 | 团队 MCP 接受团队工具；V2 只接受目录 id、拆分读/写方法、拒绝其隐藏平台且不显示邀请 |
| 余额 | 团队选择、授权标签、余额路由、错误形态 | 客户端归属 |
| 目录请求 | `/tool-requests`、限流、字段限制、调用方 IP | 事件源与客户端归属 |
| 传输 | 主机检查、压缩、缓存头、eager auth、静态能力 | V2 有独立的受众、元数据路径、scope 标记与 Claude 浏览器源 |
| 生命周期 | 传输工厂与 `mcp_lifespan` | V2 挂载与 lifespan 依赖其特性开关 |

`_SurfacePolicy` 包含可以在共享工具行为内部不同的那一小撮值。公开工具注册保持分离，因为它们的名字、描述、输入 schema 与安全注解是公开契约。`build_mcp_app` 拒绝一个命名了不同表面的服务器与 OAuth 资源版本对。

当任一 MCP 表面或共享 MCP 代码变化时，审查两个表面。测试必须比较共享行为，也必须证明所列差异。除非新的 directory 审查批准一个契约变更，否则保持这些 V2 属性固定：

- `/mcp/v2/` 是稳定 URL，且 `/mcp/v2` 解析到同一资源。
- 工具列表有 directory 清单提交时那六个工具：`catalog_search`、`catalog_get`、`catalog_call_read`、`catalog_call_write`、`balance`、`catalog_request`。添加一个工具会改变清单；通过一个重新提交来做，而非顺带做。
- V2 不列出、描述或调用图像、视频、语音或音乐生成（`_DIRECTORY_HIDDEN_PLATFORMS`）：清单声明服务器不使用 AI 模型生成图像、视频或音频。团队 `/mcp/` 保留它们。
- V2 只接受目录 id。它不列出或调用任意团队工具或透传路径。
- 读与写调用保持分离，且它们的注解匹配其方法类别。
- V1 与 V2 OAuth 受众不交叉。
- 特性开关控制 V2 挂载、元数据、新授权、调用路由与 lifespan。
- V2 directory 标题、描述、schema、注解与中性审查文案保持受测。每个工具在 `annotations.title` 中重复其精确的展示标题；Anthropic 的提交门户独立于顶层工具标题验证注解标题。

`tests/test_mcp.py` 保护团队 MCP 行为。`tests/test_mcp_directory.py` 保护 V2 表面，并以相同输入调用两个公开 URL 来比较搜索结果与价格、端点详情、余额、目录调用结果、错误、仅目录提示与客户端归属。`tests/test_marketplace_call.py` 证明仅目录 API 路由无法被同名团队工具遮蔽。如果只审查了一个相关的 MCP 测试文件，变更就是不完整的。

## 团队 MCP 在 `/mcp/`

| 工具 | 工作 |
|---|---|
| `catalog_search` | 按你想 **做** 什么查找端点，带价格；在实验的 `v2` 模式下给出判定与该页上的工作（[search-experiment](search-experiment.md)） |
| `catalog_get` | 一个端点的完整信息：参数、成本、可靠性、兄弟供应商（路由计划在路由行上，如 CLI） |
| `call` | 按 id 的一个目录端点，或团队的自己工具的 `<tool-name>/<path>` |
| `call_media` | 同一 `/call/` 路径用于音频端点，作为原生 `AudioContent` 加上结构化调用/成本元数据返回 |
| `resources_list` | 调用统一的供应商资源 API；Fish 语音列表在有 BYOK 时使用已连接的 Fish 账户，否则使用活跃团队的平台语音 |
| `balance` | 团队的预付费余额 |
| `my_tools` | 团队注册的、无需持有密钥即可调用的工具 |
| `feedback` | 提交一个私有问题报告或建议 |
| `catalog_request` | 提交目录 **缺失** 的东西——下一步添加什么的需求信号 |
| `hub_create` | 以调用方团队名义发布一个 hub 工具（由其他工具组成的 maker 工具） |
| `hub_update` | 发布调用方团队拥有的 hub 工具的新版本 |
| `hub_mine` | 调用方团队的 hub 工具，带状态、价格与检查判定 |

三个 `hub_*` 工具只存在于 `/mcp/`，注册在与本表其余部分相同的服务器对象上；`_HubToolsGate`（一个 `tools/list` 中间件）隐藏它们，除非设置了 `TREG_HUB_ENABLED`，且当 `TREG_HUB_TEAMS`/`TREG_HUB_USERS` 也限制它时，调用方解析到一个列出的团队或邮件（`_hub_reader`，缓存一分钟）。`catalog_search` 也按分数合并调用方可见的已列出 hub 工具，标记为 `kind: "hub"`，且 `call` 接受一个 hub 工具 id（`<team-slug>.<name>[@N]`），它不是目录 id 或 `<tool>/<path>`，把输入作为 JSON body POST 出去。`/mcp/v2/` 从不注册这些工具（它们在 `directory_mcp` 中缺失），因此上面的 V2 工具计数不受影响。运行时见 [the tool hub](hub.md)。

刻意不是一个供应商一个工具。一个含数千端点的目录被暴露为数千个 MCP 工具会把客户端的工具列表淹没，并在目录每次增长时强制重新连接。`catalog_search` 加上 `call` 覆盖全部，并保持同样大小。

## 固定表面 — 无变更订阅(No change subscriptions)

MCP 表面在运行时是静态的。每周目录刷新改变 `catalog_search` 与 `catalog_get` 返回的 **数据**；它们不改变 `tools/list`。treg 也不发布任何工具、提示或资源变更事件。因此 `server/discover` 通告 `tools.listChanged=false`、`prompts.listChanged=false`、`resources.listChanged=false` 与 `resources.subscribe=false`，且 `subscriptions/listen` 以 `METHOD_NOT_FOUND` 被拒。

MCP SDK 2.0 安装了 `subscriptions/listen` 并从其存在派生全部四个标志，没有公开的构造函数开关来禁用它。`_StaticSurfaceCapabilities` 通过 SDK 的公开服务器中间件接缝修正这两种行为：它重写 discover 结果并否决 listen。它刻意不变异 SDK 的私有处理器注册表。这防止客户端打开永不提供有用工作的空闲 SSE 流。

`call` 被注解为 **破坏性 + 开放世界 + 非幂等**，这看起来悲观，直到你注意到 treg 不对上游建模：它中继到别人的 API，无法知道那个端点是否计费、写入或删除。声称其他情况会是一个被当作事实的猜测。`feedback`、`review` 与 `catalog_request` 是其他非读取。它们是无害的写入（treg 自身的一行，无上游、无花费），因此它们是非破坏性的；在团队 MCP 上它们是开放世界，因为它们的文本离开调用方账户前往 treg 团队（一个 review 的理由可能被引用在公开目录页上），这正是 Codex 插件 review 读取那个提示的方式。OpenAI 的客户端（`openai-mcp/` 用于 ChatGPT 与其插件审查器、`codex-mcp-client/` 用于 Codex，按 User-Agent）根本不被提供 `review`：`_OpenAIClientGate` 把它从 `tools/list` 与指令中的 review 句移除，且调用结果不为它们携带 review 或 feedback 邀请，因为那个 review 把 agent 发起的评分读作分析收集。其他客户端保留两者。`catalog_request` 中继到 `POST /tool-requests`，因此限流与字段上限集中在一处。像每个进程内调用一样，它携带调用方的地址，由 `_bearer` 解析（``client_ip.py``，绝不会是客户端写的 `X-Forwarded-For`）；否则每个 MCP 调用方会共享一个限流桶。`catalog_search` 的零结果提示指名它，因此一个刚搜索却一无所获的 agent 可以在同一会话中提交那个缺口——且那个未命中本身被记录为 `SearchMiss` 行（`audit.record_search_miss`，在团队 MCP 上是 `source="mcp"`，在 V2 上是 `source="claude-connector"`）：这个工具在进程内读取目录，因此 HTTP 路由自己的未命中日志永远看不到一个 MCP agent 的空搜索。两个 MCP 搜索工具也接收调用方的 `Context`：当 `search_experiment` 不为 `off` 时，搜索经过 [discovery 实验](search-experiment.md)，它可能提供一个被判定或交错的页面，并记录一个带调用方团队与邮件的 `SearchLog` 行——HTTP 路由是匿名的，不属于它。

## 进程内，而非走网络(In-process, not over the network)

工具通过针对我们自己 app 的 `httpx.ASGITransport` 到达 treg 的其余部分——一个真实的请求经过真实的路由，没有 socket。这很重要，因为强制规则（deny 规则、capability 固定、每成员工具访问、凭据阶梯、计量）活在那些路由中。一条「直接读数据库」的第二路径会是其中每一个的第二实现，悄无声息地漂移。进程内客户端为团队 MCP 盖戳 `X-Treg-Client: mcp`、为 V2 盖戳 `X-Treg-Client: claude-connector`（归属，绝非门控），因此每个 MCP 表面可与未报告的 CLI 流量及另一个 MCP 表面区分开。它还作为 `_bearer` 读取的那样转发工具调用背后的主机：`X-Treg-Mcp-Client`（`clientInfo.name`）与 `X-Treg-Mcp-User-Agent`（入站 User-Agent），在两个 MCP 表面上。`tool_called` 与 `call_intake_failed` 把它们记录为 `mcp_client` 与 `mcp_user_agent`，且只有当 `X-Treg-Client` 命名一个 MCP 表面时才如此，因此一个直接的 `/call/` 无法伪装成 MCP 主机。无状态传输不保留 `initialize`，因此 `clientInfo` 只在 2026-07-28+ 的请求上已知，它在每个请求上携带它；较旧的客户端按 User-Agent 区分。内部请求保留 httpx 自己的 User-Agent，因为那是自己的密钥上游看到的，且 relay 在到达上游前丢弃每个 `x-treg-*` 头。

目录是唯一的例外：直接读 `catalog_store`，它已经在内存中解析，因此一个搜索在约一毫秒内回答。那是一个 **速度** 选择，而非权限选择。

## `call` 说出了 CLI 说的每一种请求形态

`params` 保留它原有的基于方法的角色（GET 上的查询字符串，POST 上的 JSON body）。显式槽位用于那个角色无法表达的形态，镜像 `treg call` 的标志——每个都是因为一个真实端点需要它才被添加：

- `query` — **总是** 查询字符串。一个团队工具列表保留重复的键默认（`?tag=a&tag=b`，dict 会折叠它）；一个目录数组遵循其显式的端点默认 `input.queryArrayEncoding`（`json`、`comma` 或 `repeated`）。因此 Meta Ad Library 收到 `ad_reached_countries=["US"]` 作为一个 JSON 值；一个未声明的端点发送重复的键。与 POST 上的 `body` 可组合——Bright Data 数据集形态（`?dataset_id=…` + 数组 body）没有它就无法经 MCP 调用。
- `body` — **总是** body。对象/数组 → JSON；一个 **字符串** 按 `content_type` 命名它原样(raw)发送（当它解析为 JSON 时被嗅探为 `application/json`——CLI 的规则）。一个 body 意味着 POST。
- `headers` — 额外上游头（`login-customer-id` 是典型需求）。treg 自己的 auth/路由头从 relay 中过滤；被注入的凭据总是在服务端获胜。
- 一个透传 URL 内的内联 `?a=b` 被抽出并合并——httpx 在传入 `params=` 时静默 **丢弃** URL 的查询字符串，与 `cmd_call` 守卫的陷阱相同。
- 声称与显式槽位同位置的 `params` 被响亮地拒绝，绝不合并。
- **查询值按线缆(WIRE)拼写，而非按 Python 拼写。** `str(True)` 是 `"True"`，任何记录布尔值的上游都会拒绝（`{"rule": "boolean"}`）。调用方没做错什么——JSON 布尔值是 MCP 客户端发送的东西——因此转换是我们的：`true`/`false`、嵌套值作为紧凑 JSON（绝不单引号 `repr`），且 `None` 完全省略，因为那正是「无值」在 HTTP 上的含义。它在花费金钱的地方咬得最狠：在 thecompaniesapi 上 `simplified=true` 是 **免费** 预览模式，因此被篡改的标志悄然把调用方推到了付费路径上。
- 多部分文件上传保持 CLI-only（`treg call --upload`）——MCP 调用方不持有文件。
- `call` 解析团队的方式与 `balance` 相同（在花费任何东西之前 `_resolve_org`）：一个多团队身份令牌曾因 `/call` 原始的 `choose an org (send X-Treg-Org)` 400 而弹开——一个 MCP 调用方无法据此行动的 header 提示；现在它得到固定的/活跃团队，或指名团队们的友好错误。

## `call` 接受 `idempotency_key`

可选的，且它是调用方的。在重复一个答案从未到达的调用时传递同一个 key：treg 重放存储的响应，不到达供应商，且不计费，结果上带 `replayed: true`。该 key 变成一个 `Idempotency-Key` 头，且头值是 ASCII：一个 ASCII key 原样传输，一个非 ASCII 的按 UTF-8 百分号编码（当超出存储长度时取整个 key 的摘要），因此同一个 key 总是映射到同一个头（`_header_idempotency_key`）。

## 请求构建工具拒绝未声明参数

SDK 的参数模型忽略一个工具未声明的键。对于 `call`、`call_media`、`catalog_call_read` 与 `catalog_call_write`，一个被丢弃的键是一个错误请求（`data` 而非 `body` 发送了一个空 POST），因此 `_UnknownCallArguments`（两个表面上的 `tools/call` 中间件）在发送任何东西之前拒绝它，并指名被接受的参数。广告的 schema 不变。

## `call` 说出 overflow 中继何时服务了它

`/call/` 在 `X-Treg-Served-Via` 中披露一个被中继的回答；MCP 客户端永远看不到头，因此 `_call_impl` 把它提升为结果上的 `served_via`，带一行命名中继与已耗尽供应商的 `hint`（`cost_usd` 于是中继的真实价格，而非目录的直接价格）。两个表面共享该实现，因此 `/mcp/` 与 `/mcp/v2/` 说法相同。`catalog_get` 出于同样原因携带 `overflow_price_usd` / `overflow_price_unit` / `overflow_via`——在调用前告诉人类的那个价格包括中继可能计费的价格（`architecture/money.md` § Overflow money）。

它存在是因为该特性是为 agent 构建的，而 MCP 是 agent 路径。没有它，整个东西从它为之构建的表面无法到达。

刻意 **不** 由服务端基于端点与参数派生，那曾被提议又被拒绝：一小时内的两次相同搜索是新工作，treg 无法把它与重试区分开，且服务端发明的 key 会悄然服务陈旧数据。因此工具描述把它的文字花在 **何时** 使用它上，因为那正是错误会付出代价的地方。为不同请求重用被拒绝而非回答，因此失败是响亮的。

完整推理、存储规则与并发守卫见 `architecture/money.md`。

## 输出 schema：每个字段可选且可空(Output schemas: every field optional AND nullable)

每个工具声明它返回什么（ChatGPT 的 connector 审查会问；一个必须猜测字段名的模型会猜）。两条规则，都是吃了苦头学到的：

**每个字段可选**（`total=False`）。SDK 在输出时验证一个严格 schema，因此一个必需字段会把第一个 `{"error": "not authenticated"}` 变成不透明的工具失败，而非可恢复的拒绝。

**每个字段可空**（`| None`）——不只是携带数据 null 的那些（一个无描述的工具、一个无价格的端点）。SDK 通过 TypedDict 派生的 pydantic 模型序列化每个响应，而那个 dump 把每个 **缺失** 的键填入 `structuredContent` 中的 `null`。因此一个从不提及 `next` 的响应仍发出 `"next": null`，而一个针对广告的 `type: string` 验证的严格客户端以 -32602 拒绝整个回答。在它被抓住之前，同一天到了两份独立的字段报告（issue #93 与一个在 X 上的）；FastMCP 自己的客户端是宽松的，因此本地从没触发过。测试套件现在用 `jsonschema` 扮演严格客户端，针对广告的 schema 验证真实的 `structuredContent`。

一个真实负载形态各异的字段是 `Any`，而非联合：`call.body` 中继供应商发送的任何东西，且 `catalog_get.example_response` 对多数端点是 dict，但对响应是记录列表的供应商（`brightdata datasets`）是 ARRAY——把它打为 `dict` 会让服务器自己的出站验证拒绝整个目录条目。

## 响应在源端 gzip 压缩 — 边缘必须无事可做(Responses are gzip-compressed at the origin — the edge must find nothing to do)

托管服务位于一个托管的边缘(edge)之后，该边缘可以在输出时 Brotli 压缩大响应。至少一个真实的客户端栈（httpx + brotlicffi，issue #93）在对那个输出解码中途死掉，然后挂到它自己的超时，在数秒上游回答之后的数分钟。

第一个修复是 `Cache-Control: no-store, no-transform`（``NoTransformResponses`` 包装器，最外层，因此 401 挑战也携带它）——源端标准的「不要重新编码」（RFC 9111）。**托管边缘忽略它**（issue #100：生产中 `content-encoding: br` 与那个头并肩到达）。那个头保留，因为它正确且免费，但真正生效的修复不同：MCP app 压缩它自己的响应（`build_mcp_app` 内的 `GZipMiddleware`，≥1KB）。边缘只压缩到达时未压缩的东西——一个已经携带 `Content-Encoding: gzip` 的响应直接通过——且 gzip 经 zlib 在每个主流客户端上解码，完全绕过了 brotli 解码器。只有一个接受 br-但不接受-gzip 的客户端（没有主流栈这么做）仍会遇上边缘的 Brotli。

部署后检查，任何这个路径变化时：一个大的已认证 `catalog_get` 经 `/mcp/`，带 `Accept-Encoding: br, gzip`，必须回来 `content-encoding: gzip`，而非 `br`。

## 认证：eager，每个请求(Authentication: eager, every request)

`RequireAuthForProtectedTools` 以 **401** 与 `WWW-Authenticate: Bearer scope="…" resource_metadata="…"` 头回答 **任何** 无凭据的 MCP 请求。那个头是重点——一个在 200 内的友好错误告诉人类发生了什么，告诉程序什么都没有。挑战位于传输之前，因为一个工具函数既不能设状态码也不能设头。

**Eager，而非 lazy——一个刻意的反转。** 第一版把 `initialize` 与 `tools/list` 留开放，以便客户端在认证前浏览。但每个 treg 工具都需要 auth，因此匿名无东西可浏览，且开放的握手有真实成本：一个客户端（Claude Code、Cursor）`initialize` 了、得到 200、显示 **「✓ Connected」**，且从不提示——已连接但不可用，那个「登录」只在之后作为工具结果中的散文浮现。MCP 规范的规范流程改为在会话继续之前挑战客户端的 **第一个** 请求，使 OAuth 先行运行（Stripe/Subframe/AuthKit MCP 服务器都这么做；FastMCP 把一个无 401 的 `initialize` 当作 bug 跟踪）。因此挑战现在对每个 **带 id 的 JSON-RPC 请求** 触发——`initialize`、`tools/list`、`tools/call`。只有 **通知**（无 id、不期望响应）与 **`ping`**（存活）无凭据通过；`.well-known/*` 发现是独立的 GET 路由，未触动——那 **正是** 客户端需要的发现。任何 **非 POST** 请求（包括一个 GET 探测）以同样方式被挑战（缺失或失效令牌），否则以 **405** `Allow: POST` 拒绝：传输是无状态的，因此 SDK 的独立 GET 流没有会话可承载任何东西，且放过一个 GET 会让一个用 GET 探测的客户端等待 keep-alive ping 而非 401。受保护资源元数据也服务于尾部斜杠路径，即 RFC 9728 从 `/mcp/` 与 `/mcp/v2/` 派生的，因为一些客户端在发现期间不跟随重定向。

挑战还携带 `scope`（规范 SHOULD），因此客户端预先请求最小权限 scope。

中间件判断两种情况，而非一种。**无凭据** → 上面的普通挑战。**一个失效的访问令牌**——一个 *声称* 是我们 OAuth 访问令牌的 bearer（`looks_like_access_token` 读取未验证 payload 的 `typ`）但在 `read_access_token` 处失败（过期、坏签名、错误受众）→ 带 **`error="invalid_token"`** 的 401（RFC 6750 §3.1）。那个错误码是 OAuth 客户端运行其刷新授权所依据的；没有它，一个过期的令牌畅通无阻地到达工具在 200 中的友好散文，而 Claude Code 以「requires re-authorization」放弃，而非静默刷新。访问令牌验证是无状态的（HMAC + 过期），因此传输能负担它。留在中间件之外的是任何需要 **数据库** 的东西：一个每 org 或身份令牌（Codex env-var 路径）通过，有效与否，交由工具在下游验证——它的持有者没有刷新授权可运行，且在这里判断它会把第二个认证实现放在第一个之前。

传输自己的 DNS-rebinding 主机检查（421）与 Origin 检查（403）位于 *这个* 中间件 **之后**，因此一个带坏主机或 Origin 的已凭据请求仍被它们拒绝——auth 不掩盖传输守卫。

`RequireAuthForProtectedTools` 只缓冲 POST body 到足以对该请求分类。它随后重放被消费的请求消息，并把每个之后的 `receive()` 调用委托给原始的 ASGI 通道；它绝不制造 `http.disconnect`。那个区别对 MCP 2026-07-28 `subscriptions/listen` 是承重(load-bearing)的，它在 treg 停止通告那个未使用方法之前暴露了这个 bug，且对任何其他长响应也是：一个合成的 disconnect 取消活跃的下游工作。如果客户端在中间件读取 body 时真地断开，每个观察到的部分 body 消息与真实的 disconnect 都被原样重放，不发明完成。

# treg 作为授权服务器(treg as an authorization server)

在别处 treg 作为 **客户端** 说 OAuth（`oauth.py` 用 GitHub 登录、连接一个供应商账户）。这里它是 **签发** 令牌的东西。不同方向，不同模块。

`routers.auth` 拥有 OAuth HTTP 翻译与同意渲染。`application.auth` 排序客户端注册、授权、换码、刷新轮换/重放响应、吊销与授权团队变更；它打开每个会话并拥有每个提交。身份叶子在 `domain.identity.mcp_oauth` 中拥有令牌/资源验证与授权族原语。它的客户端元数据获取惰性导入 `health`，且 `domain.identity.health` 别名根凭据-网络-安全模块，因此两个路径保留一个模块对象与 monkeypatch 目标。

## `aud` 声明承载重量(The `aud` claim carries the weight)

规范要求客户端在 authorize 与 token 请求上发送 `resource=<该 mcp url>`，服务器把它拷贝进令牌的受众。不检查它，一个用户授予 *另一个* MCP 服务器的令牌会在这里工作——他们同意的是那个服务器，而非 treg，而我们会为它花费他们的余额。

`read_access_token` 因此把 `expected_audience` 作为一个 **无默认值的必需参数**。一个测试断言不带它调用会抛错，而非默认到宽松。

`/oauth/authorize` 也预先拒绝一个我们不服务的 `resource`。接受一个会铸造一个有效、格式良好且悄然无用的令牌——那个失败随后在第一次工具调用时以「not signed in」浮现，把读者指向认证，而问题其实是受众。

V2 通告 `treg:directory` 作为一个回退资源标记。托管的 Claude 可以在省略 RFC 8707 `resource` 参数的同时保留 V2 挑战 scope。那种情况下，`_effective_mcp_resource` 选择 V2 受众。一个显式的 resource 总是获胜，且所有其他请求保留 V1 默认。

**每个 MCP 版本有自己的受众集合。** `mcp_resource_audiences(version)` 包含配置的 `public_url` 加上该版本的 `Settings.public_host_aliases`。这是对称的，因此一个授权在主机变更或回滚时存活。主机与尾部斜杠别名可以在 V1 内部或 V2 内部归一化，但它们绝不跨版本。一个 V1 令牌在 `/mcp/v2/` 上失败，一个 V2 令牌在 `/mcp/` 上失败。

一个授权在其生命周期内保留其同意的受众，因为刷新重新签发 `row.resource`。`read_access_token_any` 针对所选版本验证，`_same_mcp_resource` 仅当两值都解析到该版本时才接受别名，且 `normalize_resource()` 在每个存储、铸造与比较点治愈斜杠拼写。

## 两扇门进，一行出(Two doors in, one row out)

`OAuthClient` 持有两类客户端：

- **DCR** (RFC 7591) — `POST /oauth/register`。Claude Code 与多数客户端。
- **CIMD** — `client_id` **就是** 我们获取的 https URL。ChatGPT 用的就是它。

支持其一而不支持另一会锁掉整个一族客户端，且那是一类会隐藏的缺口：你用来测试的客户端恰好是不需要另一路径的那个。

CIMD 获取被围栏(fenced)了，因为 URL 是调用方选的：仅 https、不跟随重定向、连接时一个公开地址、5s 超时、64KB 上限，复用 `health.safe_webhook_url` 与 `health.host_is_public` 而非第二份副本。文档还必须 **声明它自己的 URL**，否则托管在任何地方的文档可以断言别人的 client_id 并继承他们的同意。

`redirect_uris` 按 **精确** 匹配，绝不按前缀——`https://good.test/cb.evil` 以注册值开头，且一个注册主机下的开放重定向把一个草率的页面变成被偷的码。

## 同意屏幕是安全边界(The consent screen is the security boundary)

它是人类看到他们授予了什么的唯一地方，因此它用文字说出来——*这会花费团队的余额*、*使用你的团队注册的密钥，而看不到它们*——而非列出 scope。当一个客户端自己注册时它发出警告，因为 DCR 是开放的，任何人可以带着任何名字到达。

它携带 **团队选择器**，且每个选项显示那个团队的余额。一个客户端从哪个团队花费是在这里一次性决定的：一个在多个团队中的人被询问，而非被猜测。显示余额不是装饰——选一个 $0.00 团队是这个屏幕存在要防止的失败，且在余额被加入之前发生过。

### …但之后选择必须保持可见且可逆(but the choice must stay visible and reversible afterwards)

「一次性决定」变成了 **不可见且永久**，那个组合在 CLI 与 OAuth 客户端使用不同身份时导致了针对错误团队的花费。agent 中没有任何东西能把一个看似合理的 slug 与预期的团队区分开。修复的两半：

- **`balance` 与 `my_tools` 标记授权**：`team_name`（仅 slug 无法做健全检查）与 `identity`——授权所属的账户，通常是不同的那一关。如果授权命名了一个该 identity 自己的 `/orgs` 不列出的团队，答案就直说。提示的 *如何移动它* 那一半只为一个真实的 OAuth 调用方添加：一个 header 令牌携带它自己的团队，且 `treg mcp grants` 会为它什么都列不出。
- **团队可以在不重新同意的情况下被移动。** 它活在刷新族的 `OAuthGrant` 权威行（`current_org_id`）上，而非只在签发的访问令牌内，因此 `GET /oauth/grants` + `POST /oauth/grants/{family}/team`（`treg mcp grants`、`treg mcp use-team`）是一个在下次刷新拾取的行的更新，在访问令牌的一小时内。两边都有守卫：只有授权自己的用户可移动它，且只到他们所属的一个团队——一个授权绝不可到达比同意屏幕本会提供的更远。一个 *刷新* 仍不能改变团队；那不是第二次选择机会，是做出第一次选择的人一个刻意动作。

  审查中发现的生命周期规则：

  - **家族权威与令牌来源分离。** `OAuthGrant.current_org_id` 是 `_family_org` 那一个可变答案，列出与刷新读取。``OAuthRefresh.org_id`` 在签发后永不改变：因此一个已退休令牌的重放针对那个令牌实际命名的团队被审计，而非一个家族后来移到的团队。`OAuthGrant.granted_at` 同样是同意时间，因此常规轮换无法让一个旧的授权看起来是新授予的。残留窗口是一个已经为旧团队铸造的访问令牌，最多持续 `ACCESS_TTL_SECONDS`；未来的轮换读取家族行，因此一个与移动竞争的刷新无法回退它。
  - **Live 意味着未退休且未过期**（`_refresh_is_live`）无处不在：刷新、授权列出与团队移动。一个过期的家族被从 `GET /oauth/grants` 省略，且无法被移动。
  - **一个授权随它同意所基于的成员资格而死。** 刷新检查了用户与 org 仍存在，从不检查用户仍 *在* 其中。与此同时调用被拒绝（`require_member` 每次重新解析成员资格），但授权继续铸造令牌，且如果成员资格曾被恢复，会在没有新同意的情况下复活。
  - **一个滚动部署无法让一个无权威的家族搁浅(strand)。** A35 是一个启动快照；一个新实例运行它之后，旧实例仍只能签发 `OAuthRefresh`。`_ensure_grant` 在刷新、列出与团队移动之前，从最旧的刷新令牌重建缺失的行。它可移植的 upsert 容忍并发修复，且 `granted_at` 保留最旧行的同意时间，而非后来的修复或轮换时间。
  - **删除一个家族历史上的任何团队都会吊销整个家族。** `cascade_delete_org`（位于 `domain/governance/teams.py`）通过 `OAuthGrant.current_org_id` 与不可变的 `OAuthRefresh.org_id` 两者收集家族 id。否则删除一个前团队会抹掉识别一个重放的退休行，同时留下目的地团队下一个活跃令牌。
  - **「不是你的团队」与「无此团队」回答相同**（404）。被区分开的话，该路由会向任何已登录账户报告一个任意 slug 是否在 treg 上存在。

批准是一个 POST（一个授予访问的 GET 可能被任何能导航的页面触发），同源(same-origin)，且该页继承 `X-Frame-Options: DENY`。

`Origin: null` 只 **在** `Sec-Fetch-Site` 佐证它时才被接受。一个浏览器在某些重定向链之后报告一个不透明(opaque) origin——一个经由登录弹跳到达的同意页——且把它当作跨站会让批准间歇性失败。

## 码与刷新(Codes and refresh)

授权码是一次性且 **在验证前删除**，而非标记：检查期间持有一个会留下一个窗口，两个兑换都读到它。与 `ledger.reserve` 中条件 UPDATE 同样的推理——让数据库仲裁。

刷新令牌轮换，且退休的行被 **保留**，因此一个重放可被识别。一个被删除的令牌只看起来未知；一个退休的则说有人用了一个已经被花费的凭据。到那时，一个在丢弃响应后重试的客户端与一个拿着副本的小偷无法区分，因此整个 `family_id` 被吊销。以那种方式错只花费一次登录；以另一种方式错花费某人的余额。

保留的行也保留不可变的签发时团队来源。可变的团队选择与稳定的同意时间每家族活一次于 `OAuthGrant`；启动迁移 A35 从最旧的既有刷新令牌回填那一行，且 `_ensure_grant` 对滚动部署窗口期间旧二进制创建的家族执行同样的重建。

## 令牌是被交换的，而非转发的(Tokens are exchanged, not forwarded)

`_internal_auth` 验证一个 OAuth 访问令牌，并把它作为一个短生命周期（120s）、带类型 `aud=identity` 的令牌向前呈现给它所命名的用户，钉到授权上的 org。它显式的过期被强制，即使正常的复制身份密钥没有过期。那把 OAuth 留在 `mcp.py` 内部，而非教 `require_member` 第三种令牌类型，且它意味着 `_resolve_org` 必须尊重固定的团队，而非重新派生它。对于一个原生身份 bearer，`_internal_auth` 使用 `read_identity_claims` 来暴露签名的团队固定；它绝不把一个带类型的浏览器会话解释为 bearer。

两者都是通过运行整个流程而非测试各个片段发现的：`_oauth_claims` 完美地验证令牌，而每个工具仍转发原始 bearer 并得到「not signed in」。

## 授权中途的登录(Sign-in mid-authorization)

一个访问 `/oauth/authorize` 的已登出访问者把目的地停放在一个短生命周期的 HttpOnly cookie 中，并被重定向到 `/?signin=oauth`。dashboard 用通用的连接文案打开既有的登录模态框，从可见 URL 移除查询参数，且不创建沙箱会话。该查询参数只是一个 UI 提示；它不含 OAuth 请求数据。Google、GitHub 与邮件码登录都恢复被停放的授权请求：社交回调落在 `/app`，邮件码门重新加载 `/`，即模态框打开的地方；两者一旦登录就恢复。cookie 存储一个相对路径且只尊重 `/oauth/authorize`，因此它不能变成一个通用的「登录后把我送到任何地方」原语。

## `/connect-demo`

一个假装是别人 app 并运行整个流程的页面——注册、同意弹窗、令牌交换、工具调用。它只使用公开端点；从 treg 的域提供服务不给它任何东西。`TREG_CONNECT_DEMO_ENABLED` 门控该页面与其回调，默认 `false`，因此生产应返回 404。本地开发脚本启用它；staging 可以显式启用它用于测试。浏览器在标签页局部会话存储中为演示持有可用令牌，但可见日志只显示 `[received]` 且从不显示令牌前缀。断开连接会吊销授权并清除存储的令牌。该页面存在是因为 agent 客户端内部的失败表现为一个耸肩，且它立刻证明了自己：它发现浏览器被彻底拒绝（「*」不是 SDK origin 检查中的通配符）且同意在 `Origin: null` 上间歇性失败。

## 这里刻意没有的东西(What is deliberately NOT here)

- **没有每供应商 MCP 工具。** 见上。
- **没有路由或故障转移。** treg 发布事实并调用它被告知的东西；agent 选择。
- **没有强制规则的第二个副本。** 一切都经过 API 自己的路由。

## 认证 MCP 服务器的两种方式：OAuth，或一个头(Two ways to authenticate the MCP server: OAuth, or a header)

OAuth（上）是点击连接路径。还有一个 **无头(headless)** 路径，且它是安装器使用的默认：一个 **团队固定的令牌作为 `Authorization: Bearer` 头**。`treg mcp install`（`mcp_install.py`，`treg skill bootstrap` 的兄弟）用那个头把服务器注册进每个受支持的 agent——Claude Code 经它自己的 `claude mcp add --scope user`（用户全局，而非默认项目 scope；它拥有自己的格式并对令牌做脱敏），Cursor 与 opencode 经它们文档化的 JSON（`~/.cursor/mcp.json`、`~/.config/opencode/opencode.json`），Codex 作为一个 `~/.codex/config.toml` 中的 `[mcp_servers.treg]` 表，带内联 `http_headers` 映射。标准库没有 TOML 写入器，因此 `_write_toml_agent` 把任何之前的 `[mcp_servers.treg]` 表作为文本切掉，追加一个新表，且只在 `tomllib` 把它解析回恰好我们的条目时才落地文件。Hermes（yaml）与 OpenClaw 是 **报告，而非写入**——它们的格式无法从轻量 CLI 安全表达（yaml 是仅服务器依赖），因此我们打印精确的手动步骤。

**Codex 必须内联获得令牌，绝不经 `bearer_token_env_var`。** 旧的手动步骤说「在它的环境中设 TREG_TOKEN」；一个用户的 agent 正是这么做了，Codex app 在没有那个变量的情况下重启，treg 回答 401 且 Codex 静默丢弃每个 treg 工具。然后 agent 经 Codex 自己的浏览器驱动 dashboard，并在一个 $0.13 的工作上花费了用户的每日 Codex 额度。在 codex-cli 0.144 上实况验证：`http_headers = { "Authorization" = "Bearer …" }` 加载工具；一个 `X-Treg-Token` 头 **不**（MCP 表面回答 401 并启动 OAuth）。

该命令 **在写入任何东西之前针对 `/auth/me` 验证令牌**——与 `treg login --token` 运行的同一检查。吃了苦头学到的：没有它，一个垃圾令牌会静默扇出到机器上的每个 agent，并在数天后作为某代理尝试调用时的每供应商「invalid token」错误浮现——目录读取仍工作（它们不在下游验证令牌），这让它看起来像供应商中断而非设置问题。相关垃圾是测试套件自己的 dummy：`install_mcp(only=[])` 把一个空列表读作「无过滤」并每次套件运行都把 `Bearer K` 写入开发者的真实配置——`only=[]` 现在意味着 *无*，且测试隔离 HOME。

在那验证之前，安装器也识别签名的 `scp=bootstrap` 提示并无写入地退出。服务器仍具权威性——本地解码不授予任何东西——但这给出一个清晰的设置错误，而非安装一个无法识别计费团队的凭据。MCP OAuth 访问/刷新流程不变；它们内部的 120 秒桥接身份仍是一个独立的带类型路径。

为何一个头能工作，即使 treg 通告 OAuth：一个客户端只在 **401** 时回退到 OAuth 发现，而 treg 对一个有效头返回 **200**——针对 Claude Code 验证过，它否则偏好 OAuth（issue #59467）。决定性因素是「服务器是否对一个有效头返回 200」，而非「它是否通告 OAuth」；AgentKey 行为相同。该令牌是 dashboard 的 org 烘焙「API key」（见 [dashboard](../interface/dashboard.md)），因此它携带团队且不需要第二个头。`curl {BASE}/install.sh | sh -s -- --token <key>` 一次性运行整个过程——安装、登录、`treg mcp install`。

## 经 MCP 的调用方标签(Caller tags over MCP)

目录调用工具也暴露一个可选的 `authorization_method`。MCP 把那个显式参数映射到 treg 内部的 `X-Treg-Authorization-Method` 路由头；调用方提供的头不能覆盖它，且该头不被中继到供应商。

通用 `call` 表面接受可选的 `form` 标量字段与 base64 `uploads`，在内部请求前上限为 30 MiB，因此多部分语音创建不改变既有的 JSON 调用契约。只有团队 `/mcp/` 注册 `call_media` 与 `resources_list`；`/mcp/v2/` 两者都没有。原生音频从不经 JSON/文本解码通过。

`X-Treg-Meta`（见 [money](money.md)）在 `mcp.call()` 中从 MCP **传输** 读取并转发到内部请求，与 `catalog_request` 转发 `X-Forwarded-For` 的方式相同。它刻意 **不是** 一个工具参数：一个被要求传递客户 id 的模型会在某处链中省略它，且一个你无法核对(reconcile)的计费数字比没有数字更糟。`x-treg-meta` 因此也在 `call` 工具的额外头过滤器中，因此一个模型提供的值绝不能与传输的值矛盾。

一个代理 MCP 的构建者在他们自己的 HTTP 客户端上每个会话设置一次该头；模型从不看到它。
