# MCP 服务器的 OAuth —— 一个授权服务器，任意 MCP 客户端

**状态：已发布并在生产上线。** 按下面六步走完，每步在下一步之前都经审阅。验收测试通过 —— MCP SDK 自己的 OAuth 客户端驱动了整条流，没有任何 treg 特定的特例 —— 而且 ChatGPT 通过 CIMD 连接，发起了一次计费的调用并正确计费。参考文档：`docs/context/architecture/mcp-oauth.md`。

## 不是 ChatGPT 特性

MCP 授权规范不是 ChatGPT 的。任何实现了它的客户端 —— Claude Code、Claude Desktop、Cursor、下一个出来的什么 —— 都用同样的两份元数据文档、同样的 PKCE 流、同样的同意屏。**ChatGPT 是第一个消费者，不是设计目标。** 这样写，它也就成了 Codex 路径今天一个问题的答案：环境变量里的一个 bearer token 是一个用户手工复制的凭据，而这个用"打开一个链接、选一个团队、完事"替代它。

两个决策随之而来，现在都便宜、以后改起来别扭：

- **没有硬编码的回调 URI。** ChatGPT 的 `https://chatgpt.com/connector/oauth/{callback_id}` 是一个已注册客户端的回调，按客户端校验 —— 不是我们代码里的常量。
- **既支持动态客户端注册也支持 CIMD。** ChatGPT 偏好 CIMD；Claude Code 和大多数其他客户端用 DCR。只支持 CIMD 会悄悄把其他所有人锁在门外，而我们不会注意到，因为我们那一个测试客户端恰好不需要它。

## 为什么这不是可选项

ChatGPT 的 connector 表单恰好提供三个认证选择：**OAuth**、**No Auth**、**Mixed**。没有 bearer-token 选项。Codex 有一个（`codex mcp add --bearer-token-env-var`），这正是 Codex 那半今天能用、ChatGPT 那半不能的原因。

`No Auth` 不是这个产品的简化版，它是另一个产品。针对生产、无 token 验证过：

| 工具 | No Auth |
|---|---|
| `catalog_search`、`catalog_get` | 能用 —— 目录是公开的 |
| `call`、`balance`、`my_tools` | `{"error": "not authenticated"}` |

treg 是多租户的：每次调用都要回答是谁的余额付费、谁的 key 可用、谁的上限适用、写谁的审计行。token 就是回答那个的东西。没有它就没有调用方 —— 对审阅者不是，对任何装了插件的人也不是。把一个 token 放进 URL 会把这个团队的余额和这个团队的私有 key 交给目录里每个用户，那正是 treg 存在要避免的东西。

## 方向是新的

treg 已经会说 OAuth，但只是作为**客户端**：`oauth.py` 构建 PKCE challenge 来用 GitHub 和 Google 登录、并连接供应商账号。这里 treg 必须是**授权服务器** —— 发 token 的那个，而不是兑换 token 的那个。那个角色还不存在。

有两块确实能复用：

- `session.py` 铸造带 claims 和过期的 HMAC 签名 token（`make` / `read_claims`）。一个 access token 是带更多 claims 的同形态，所以签名机制已经写好并经审阅。
- 三个登录门（GitHub、Google、邮箱码）已经在浏览器里识别一个人。`authorize` 端点复用那个会话，而不是发明一个登录。

## 规范要求的

这些来自 MCP 授权规范，每个合规客户端都实现它。ChatGPT 专属那列只有它的回调 URI 和它偏好 CIMD —— 其他一切对它们所有都是共通的：

| 要求 | 细节 |
|---|---|
| 流 | OAuth 2.1 授权码 + **PKCE `S256`** |
| 受保护资源元数据 | MCP host 上的 `GET /.well-known/oauth-protected-resource` |
| 授权服务器元数据 | `GET /.well-known/oauth-authorization-server` |
| 客户端身份 | **CIMD** —— ChatGPT 发一个 HTTPS 元数据 URL 作为 `client_id`。声明 `client_id_metadata_document_supported: true`。**我们也加 DCR**，给那些用它的客户端 |
| 回调 URI | ChatGPT 的是 `https://chatgpt.com/connector/oauth/{callback_id}` —— 按客户端存储，绝不假设 |
| `resource` 参数 | ChatGPT 在 authorize **和** token 请求上追加 `resource=<我们的 mcp url>`；它**必须**被复制进 token 的 `aud` claim |
| 客户端认证 | `none`（公共客户端 + PKCE）或 `private_key_jwt` |

## 要建什么

### 0. 客户端注册 —— 两条路都进

`POST /oauth/register`（RFC 7591）给动态注册的客户端：它们发名字和回调 URI，我们存起来并返回一个 `client_id`。而 CIMD 给那些发一个 HTTPS 元数据 URL 作为自己 `client_id` 的客户端，我们去拉取并缓存。

任一种方式都是同一张表，所以下游一切 —— authorize、token、同意 —— 读一种形态，不在乎客户端是怎么来的。

### 1. 两份元数据文档

静态 JSON，无状态。`/.well-known/oauth-protected-resource` 命名规范资源（`https://treg.superdesign.dev/mcp/`），把 treg 指向它自己作为授权服务器，并列出 scopes。`/.well-known/oauth-authorization-server` 公布 authorize 和 token 端点、`code_challenge_methods_supported: ["S256"]`，以及 CIMD 支持。

### 2. `GET /oauth/authorize` —— 同意屏

复用浏览器会话。如果访客没登录，把他们送过既有的门再回来。然后显示一页：**这个 connector 可以代表哪个团队**行动，以及它将能做什么。

团队选择器不是装饰 —— 它是对一个真实问题的回答。一个人可以属于好几个团队，而 `balance` 在没有任何一个被标为活跃时不得不拒绝并询问。同意是那个选择真正属于的地方，由一个人做一次，而不是每次调用猜。

发出一个短生命的授权码，绑定到：用户、所选 org、`code_challenge`、`redirect_uri`，以及 `resource`。

### 3. `POST /oauth/token` —— 兑换

根据存储的 challenge 验证 PKCE verifier（`S256`）、回调 URI 匹配、且码未用过且未过期。码是**一次性**的 —— 兑换时删除，所以重放什么也得不到。

返回一个 access token，携带 `sub`（用户）、`org`（所选团队）、`aud`（逐字照抄的 `resource` 值）和过期时间，外加一个 refresh token。刷新很重要：一个一小时后死掉、无法恢复的 connector 是一张每用户每天的工单。

### 3b. 面向用户的链接

因为同意页是一个普通 URL，一个没有浏览器集成的客户端仍然能用它：打印链接，人打开它，批准，然后粘回一个短码 —— 和今天的 `treg login` 同形态。这让 Claude Code 和任何终端客户端无需我们特殊支持就能工作。

### 4. `mcp.py` 里的 token 接受

`_bearer()` 已经读 header。它多一个分支：如果 token 是一个 OAuth access token，验证签名，检查 `aud` 匹配我们自己的 MCP URL —— **拒绝一个为另一个 resource 铸造的 token 正是那个 claim 的全部意义** —— 并把 `sub`+`org` 解析到成员关系。既有的每 org 和身份 token 继续原样工作，所以 Codex 不受影响。

### 5. 存储

一张新表给授权码（短生命、一次性），一张给 refresh token（可撤销）。access token 像会话 cookie 一样保持无状态：签名的、自描述的、热路径上无查找。

## 可能出什么错，以及我会先去看哪

- **`aud` 处理错。** 如果我们接受一个受众是另一个资源的 token，一个为别人服务器发的 token 会在我们的上工作。这是测试套件里单个最重要的断言。
- **CIMD 拉取。** `client_id` 是一个我们去拉的 URL。从我们服务器拉一个攻击者提供的 URL 是请求伪造风险：必须是 HTTPS、必须带超时拉取、不重定向到私有地址，而且结果必须被缓存。
- **同意屏就是安全边界。** 这是唯一一个人看到他们在授予什么的地方。它必须直白点名团队和能力，而且绝不能能被嵌进一个 frame。
- **Refresh-token 轮换。** 用时轮换并检测复用；一个永远活的泄漏 refresh token 比一个短 access token 更糟。
- **蔓延进代理的作用域。** OAuth 决定*谁*在调用。它绝不能变成第二个决定*他们能调什么*的地方 —— 那留在 `_resolve_marketplace_call` 里，否则两份副本会漂移。

## 顺序，以及停在哪看

1. 元数据文档 + `mcp.py` 里的 `aud` 检查。还没发任何 token；这是拒绝错误 token 的那部分。
2. 客户端注册 —— DCR 和 CIMD 进一张表。
3. `authorize` + `token` 带 PKCE，码在数据库里，无 UI —— 由测试驱动。
4. 同意屏，含团队选择器。
5. Refresh token 和轮换。
6. **停下，连一个真实客户端。** 故意两个：ChatGPT（CIMD）和 Claude Code（DCR）。如果第二个需要在我方改代码，那设计就是错的，而这是学它最便宜的时刻。
7. 然后插件 manifest、demo 录制，以及提交的其他部分。

## 诚实的体量评估

这是几天，不是几小时 —— 流本身走得很熟，但它是新的安全面，而且测试套件必须有说服力，而不只是绿。Codex 路径全程继续工作且不需要其中任何东西，所以整个过程里都有一个可发布的产品。

敲定：这是一个**通用的 MCP 授权服务器**，不是 ChatGPT 集成。ChatGPT 是穿过它的第一个客户端，而"我们建得对不对"的验收测试是第二个客户端 —— Claude Code —— 不改动我方代码就能连接。
