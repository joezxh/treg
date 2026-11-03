# treg 的 MCP 服务器，以及发出它的插件

**状态：**探针已完成并丢弃；实现已批准但尚未开始。

目标是插件目录的流量。一个纯技能插件能获得那波流量，然后让访客去装一个 CLI —— 死胡同就是转化。一个 MCP 连接器**安装好那一刻就能用**，而且是唯一能触达 ChatGPT 的形态，因为那里根本没有终端。

不是一个供应商一个工具。目录保持为*数据*；MCP 服务器暴露的是**treg 自己的操作** —— 和 CLI 同样的少数几个。五个工具，而不是 2,600 个。

## 我首先在本机验证过的（codex-cli 0.145.0）

三个事实，每个都是证明而非读来的，因为它们决定了设计：

| 问题 | 答案 | 如何 |
|---|---|---|
| 一个插件能否声明一个**远程** MCP 服务器，还是只能声明一个 OpenAI 注册的 connector？ | **可以，远程可用** | 构建了一个一次性插件，其 `.mcp.json` 声明了一个 `url`；装好后，`codex mcp list` 显示该服务器已注册并启用 |
| 配置形态是什么？ | `{"<name>": {"url": …, "bearer_token_env_var": …}}` | `codex mcp add --url` 精确写入 `[mcp_servers.x] url/bearer_token_env_var` |
| 支持 OAuth，还是只有 bearer token？ | 两者 —— `codex mcp login <name>` 用 OAuth 认证 | `codex mcp login --help` |

以及塑造第二阶段的约束：OpenAI 自家的 `github` 与 `gmail` 插件用 `.app.json` 带一个 OpenAI 发放的 `connector_…` id。**那个 id 来自提交流程**，所以 ChatGPT 路径受审查限制，而 Codex 路径不受。

## 探针结果 —— 全部四个问题都在本机得到回答

一次性代码，已删除。它证明了：

**1. 它能挂载进 treg 的 FastAPI 应用 —— 但有个陷阱。** `app.mount()` **不会**运行被挂载应用的生命周期，而 streamable-HTTP 会话管理器在那里初始化它的任务组。每个请求都 500，报 `Task group is not initialized`。treg 的 `api.py` 已经有一个生命周期（数据库设置），所以真正的实现必须**组合**二者：

```python
mcp_app = mcp.streamable_http_app(streamable_http_path="/", stateless_http=True, json_response=True)

@asynccontextmanager
async def lifespan(app):
    async with mcp_app.router.lifespan_context(mcp_app):   # treg 自己的生命周期包裹它
        yield
```

在探针里而不是在 Render 上发现这一点，正是这次练习的整个意义。

**2. `stateless_http=True` 可用**，这一点比看上去更重要：生产在 Render 上，可能跑多于一个实例。基于会话的传输需要粘性路由才能可靠。Stateless 加 `json_response=True` 也跳过了 SSE 帧封装，速度就是从这里来的。

**3. 它很快。** 各自实测 12 次调用，针对真实的 2,590 端点目录：

| 调用 | p50 | min | max | 其中真实工作 |
|---|---|---|---|---|
| `tools/list` | 1.5 ms | — | — | — |
| `catalog_search("backlinks")` | **1.4 ms** | 1.0 | 1.9 | 0.18 ms |
| `catalog_search("work email")` | **2.1 ms** | 1.9 | 2.6 | 1.01 ms |
| `catalog_get(<id>)` | **1.4 ms** | 1.0 | 1.8 | — |

传输开销约 1.2 ms。目录在 import 时已经解析过一次，所以搜索是一次内存扫描。这里还不需要缓存。

**4. 一个工具能读到调用方的 bearer token** —— `Context.headers`，由 HTTP 传输填充。两种方式都验证了：有 token 时工具看到 `authorization`，无 token 时看到同样的头减去那个。组织隔离有东西可用来做键。

SDK 自己的 docstring 带着要遵守的警告：*"Headers are client-supplied input — never treat one as an identity assertion."* 该 token 必须在每次调用时针对数据库验证，完全像 HTTP API 那样。

**5. 从 Codex 端到端，这才是真正的测试。** 用 `codex mcp add --url` 注册探针，让 Codex 搜索反链端点。它调用了工具并以真实数据作答 —— 端点 id、供应商、`$0.02436` 每次调用，以及"不需要 API key" —— 一个 4 ms 的往返。

这就是那个"哇"：一个问题进去，一个带价格的答案出来，没有 key 也没有 CLI。

## 工具面

五个工具，每一个都镜像一个已经存在且经过测试的 CLI 命令：

| 工具 | 作用 | 镜像 |
|---|---|---|
| `catalog_search(query, limit)` | 按你想**做什么**找端点，带价格、供应商与实测可靠性 | `treg catalog search` |
| `catalog_get(endpoint_id)` | 单个端点：参数、价格、认证层级、能力兄弟、观测到的统计 | `treg catalog get` |
| `call(endpoint_id, params)` | 那个计量调用 —— treg 注入凭据，转发响应 | `treg call` |
| `balance()` | 团队的预付费余额与在途预留 | `treg balance` |
| `my_tools()` | 团队注册了什么：密钥、OAuth 连接、技能 | `treg tool list` |

**工具描述就是产品。** 它们是模型在判断 treg 是否相关时所读的东西，正如今天 `skill.md` 的 frontmatter。它们得到同样的用心。

`call` 把上游响应**逐字**返回，外加它花了多少。创始规则不变：treg 转发，绝不建模。

## 它在哪，以及它不能打破的规则

一个新模块，`src/treg/mcp.py`，挂载在既有 FastAPI 应用的 `/mcp`。一个部署，一个数据库，一套规则。

**它必须经由 `_resolve_marketplace_call`，而不是绕开它。** 组织隔离、余额预留、每天 $5 的平台上限、能力 pin 与拒绝规则都活在那条路径上。一个重新实现其中任何一项的第二入口，就是两者漂移、其中一项停止被强制执行的方式。具体来说：`call` 构造和 HTTP 代理同样的请求，并走同样的解析、预留与结算。

## 认证，分两个阶段

**阶段 1 —— Codex，今天可用。** 插件的 `.mcp.json` 声明 URL 和 `bearer_token_env_var: TREG_TOKEN`。用户导出一个按组织的 token。那是一个环境变量，而不是装一个 CLI 再登录 —— 而且按组织的 token 已经存在，带角色与审计。

**阶段 2 —— ChatGPT，需要 OAuth。** `codex mcp login` 显示 OAuth 受支持，且 MCP 的规范用的是 OAuth 2.1。treg 已经为 GitHub 和 Google 登录跑 OAuth，并有一个托管的连接流程，所以是有基础的 —— 但这是真正的新工作，也是 ChatGPT connector 所需要的。

阶段 1 可以发布并端到端测试。阶段 2 是公开提交所需要的。

## 插件包含什么

    plugin/
    ├── .codex-plugin/plugin.json     manifest + 上架文案（从归档分支复用）
    ├── .mcp.json                    远程服务器声明
    ├── skills/treg/                 保留 —— 由 src/treg/web/skill.md 生成
    └── assets/                      图标 + logo（已制作）

**两者都要**，正如 OpenAI 的 `github` 插件同时发布 `"skills"` 和 `"apps"`。连接器给模型操作；技能给模型判断力 —— 什么时候 treg 是对的，如何在供应商之间选择，在花钱前先说价格。只有工具会丢失全部这些。

## 风险与未决决策

- **`mcp` 2.0.0 依赖 `httpx2`**，而 treg 的 CLI 用 `httpx`。它只应属于 `[server]` extra —— 基础安装必须保持轻量 CLI。在采用 SDK 前需要检查冲突。
- **一个公开的 MCP 端点是新的攻击面。** 任何工作开始前必须拒绝未认证请求，且它需要自己的速率限制 —— 既有的按用户上限假设的是 HTTP API。
- **Streamable HTTP 是基于会话的**，这与 treg 无状态的请求/响应是不同的生命周期。在采用前值得先探针一下。
- **token 放在环境变量里**比 OAuth 弱：它待在用户的 shell profile 里。这是务实的阶段 1 答案，不是终点。
- **成本可见性。** 一个调用 `call` 的模型可能花真钱。工具描述必须说明价格，且 `catalog_get` 应该是 `call` 之前被鼓励的一步。

## 构建顺序

1. **探针** MCP SDK 对 FastAPI —— 传输、会话、依赖冲突。一次性。
2. **`src/treg/mcp.py`** 含五个工具，经由既有的强制执行路径路由。
3. **测试** —— 强制类的最要紧：错误组织的 token 什么都看不到，超上限的调用被拒绝，未定价的端点被拒绝，被 pin 的能力拒绝错误的供应商。
4. **部署**到开发机，把 Codex 指向它，真正地演练全部五个工具。
5. **打包**插件，从本地市场安装，在 `codex exec` 里验证。
6. **然后**才是提交 —— 带上 connector，那正是阶段 2 变得必需的地方。

在第 4 步之后停一下，打包前先看看它。那是工具面要么对模型读着顺、要么不顺的节点，而且那时改起来便宜得多。
