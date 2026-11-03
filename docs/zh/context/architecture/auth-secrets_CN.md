---
title: 认证与密钥 — 注入器(injectors)、加密、OAuth 时效、健康检查
status: shipped
sources:
  - src/treg/infra/upstream/injectors.py
  - src/treg/infra/upstream/ssrf.py
  - src/treg/crypto.py
  - src/treg/oauth.py
  - src/treg/domain/connections/__init__.py
  - src/treg/domain/connections/authorization.py
  - src/treg/domain/connections/oauth_flow.py
  - src/treg/domain/connections/refresh.py
  - src/treg/infra/oauth_exchange.py
  - src/treg/infra/oauth_refresh.py
  - src/treg/oauth_providers.py
  - frontend/src/state/session.js
  - frontend/src/state/keys.js
  - frontend/src/pages/TeamPage.vue
  - src/treg/health.py
  - src/treg/application/connect.py
  - src/treg/alembic/versions/0051_context_dev_tool_host.py
  - src/treg/routers/connections.py
  - src/treg/routers/resources.py
  - src/treg/domain/tools/__init__.py
  - src/treg/domain/tools/bindings.py
  - src/treg/domain/tools/bundles.py
  - src/treg/domain/identity/api_keys.py
  - src/treg/domain/identity/access.py
  - src/treg/routers/api_keys.py
  - tests/test_api_keys.py
  - tests/test_oauth_refresh.py
  - tests/test_financialdatasets.py
  - tests/test_key_providers.py
  - src/treg/config.py
related:
  - architecture/proxy-model.md
  - architecture/data-model.md
  - interface/api.md
---

# 认证与密钥(Auth & secrets)

Fetchin 使用粘贴在 `https://api.fetchin.io` 的 `X-API-Key`。其免费的内部 `GET /api/v1/subscription` 探测会拒绝无效凭据，且即使在信用(credit)余额为零时也会接受有效账户。 `TREG_PLATFORM_KEY_FETCHINIO` 提供可选的共享绑定(binding)；「自有密钥优先」的阶梯保证团队的凭据不被计量(metered)。同一条免费路由还提供容量(capacity)数据，但不作为目录(catalog)工具对外暴露。

Tavily 使用粘贴在 `https://api.tavily.com` 的 Bearer 密钥。其免费的内部 `GET /usage` 探测会拒绝无效凭据，并同时校验团队自有与可选的平台凭据，且不把用量作为目录工具暴露。 `TREG_PLATFORM_KEY_TAVILY` 提供服务端持有的回退(fallback)；既有的「自有密钥优先」阶梯意味着团队密钥始终获胜并保持不被计量。公开能力面仅限于 Search、Extract、Map 和 Crawl。

Linkup 使用粘贴在 `https://api.linkup.so` 的 Bearer 密钥。其免费的内部 `GET /v1/credits/balance` 探测会校验已连接的密钥，并在不暴露账户余额作为目录工具的前提下提供容量证据。 `TREG_PLATFORM_KEY_LINKUP` 提供可选的共享绑定；团队自有密钥获胜并由 treg 保持不被计量。

Crawl4AI 使用粘贴在 `https://api.crawl4ai.com` 的 Bearer 密钥（`sk_live_…`）。免费的 `GET /v1/billing/balance` 会校验已连接的密钥（伪造密钥返回 401）并提供容量证据；它比每次调用的 `x-c4-balance` 头大约滞后一分钟。 `TREG_PLATFORM_KEY_CRAWL4AI` 提供可选的共享绑定；团队自有密钥获胜并由 treg 保持不被计量。

Spider 使用粘贴在 `https://api.spider.cloud` 的 Bearer 密钥。免费的内部 `GET /data/credits` 探测会校验已连接的密钥并提供容量证据。 `TREG_PLATFORM_KEY_SPIDERCLOUD` 提供可选的共享绑定；「自有密钥优先」阶梯让团队的凭据保持不被计量。只有计价的 Search 列表项可以使用共享密钥。

ScrapeGraphAI 使用粘贴在 `https://v2-api.scrapegraphai.com` 的原始 `SGAI-APIKEY` 头。其免费的内部 `GET /api/credits` 探测会拒绝无效凭据，并同时校验团队自有与可选的平台凭据，同时提供容量数据。 `TREG_PLATFORM_KEY_SCRAPEGRAPHAI` 提供服务端持有的回退；既有的「自有密钥优先」阶梯让团队的凭据保持不被计量。

Serper 使用粘贴在 `https://google.serper.dev` 的原始 `X-API-KEY` 头。其免费的内部 `GET /account` 探测会同时校验团队自有与可选的平台凭据，并提供余额与限流证据。 `CatalogTarget` 批准同一个凭据用于 `https://scrape.serper.dev`，不会扩大主机的范围。 `TREG_PLATFORM_KEY_SERPER` 提供服务端持有的回退；既有的「自有密钥优先」阶梯让团队的凭据保持不被计量。

`ADYNTEL` 是首个两个凭据都装在 JSON 请求体中的粘贴密钥供应商。主 `api_key` 与第二个 `email` 都是 `location: json` 的普通声明式绑定(binding)；relay 中没有任何 Adyntel 分支。Tier 4 读取 `TREG_PLATFORM_KEY_ADYNTEL` 与 `TREG_PLATFORM_EMAIL_ADYNTEL`，而团队连接存储其自有的一对凭据并保持不被计量。第一步连接只能收到密钥，因此供应商声明的 HTTP 422 探测结果会使其保持显式的「未校验」，直到 email 被添加；它绝不会从这条部分探测中被标记为已验证。JSON 注入需要一个 JSON 对象，只覆盖指定的顶层字段，拒绝重复的 object key，以 UTF-8 输出非 ASCII 文本，并在序列化后重新计算 Content-Length。它刻意不保证字节一致(byte-faithful)，不得用于会对原始 body 字节做签名或哈希的 API。没有 JSON 绑定的供应商保留既有的流式 body 路径。

`TRESTLEIQ` 使用粘贴的原始 `x-api-key` 头。其连接探测调用供应商自有的无效号码沙箱 fixture。类型化的 `probe_cost_micro=15000` 标记了首次付费密钥探测；连接对话框根据该字段渲染警告，而供应流程刻意把它从工具健康检查中省略，使后续健康检查不会再消耗团队的供应商钱包。 `TREG_PLATFORM_KEY_TRESTLEIQ` 提供可选的共享绑定；团队自有密钥仍然获胜。

`HLRLOOKUP` 复用了 Adyntel 的模式：`api_key` 与 `api_secret` 都是 `location: json` 绑定，且 relay 没有 HLR Lookup 分支。HLR Lookup 不会对原始 body 做签名或哈希，因此 JSON 重新序列化是安全的。免费的 `POST /apiv2/balance` 探测在任一半错误时返回 401，但对单独发送的密钥（无论是否有效）返回 400。因此第一步连接步骤以未校验方式存储团队密钥（声明 `probe_deferred_statuses=(400,)`），且添加 secret 后不会重新探测这对凭据：一对错误的团队凭据会在首次调用时表现为供应商未计费的 401。Tier 4 读取 `TREG_PLATFORM_KEY_HLRLOOKUP` 与 `TREG_PLATFORM_KEY_HLRLOOKUP_SECRET`（`platform_extra_setting`），因此团队自有的一对永远不会与 treg 的 secret 一起发送。

`LIMADATA` 使用粘贴的原始 `x-api-key` 头。其免费连接探测发送一个无效的空 web-search body：被指派的密钥返回 HTTP 400，伪造密钥返回 401。真实的本地连接流程接受前者、拒绝后者。 `TREG_PLATFORM_KEY_LIMADATA` 是独立的可选共享绑定；团队密钥仍然获胜并保持不被计量。

BounceBan 使用无 `Bearer` 前缀的粘贴原始 `Authorization` 头。免费的 `GET /v1/account` 探测以 HTTP 401 拒绝伪造密钥，并以 HTTP 200 接受所提供密钥（经由真实连接流程）。 `TREG_PLATFORM_KEY_BOUNCEBAN` 提供可选的共享绑定；团队密钥仍然获胜并保持不被计量。供应流程包含标准 API 工具及其显式的瀑布式(waterfall)主机伴随工具，且不暴露凭据。

ZeroBounce 使用标准的粘贴密钥流程，带一个 `api_key` 查询参数。其免费用量探测以 HTTP 403 拒绝坏密钥，以 HTTP 200 接受所提供密钥。该探测不使用余额路由，因为该路由可能对坏密钥也返回 HTTP 200 且 `Credits=-1`。 `TREG_PLATFORM_KEY_ZEROBOUNCE` 提供可选的共享绑定；团队密钥仍然获胜并保持不被计量。

`MOLTSETS` 是一个粘贴 Bearer 密钥的供应商，其免费 `POST /get_account` 探测会同时校验团队与可选的平台凭据。既有的「自有密钥优先」阶梯与部署允许名单(allow-list)均适用。

`SUMBLE` 使用标准的粘贴 Bearer 密钥路径与免费的 technology-search miss 探测；垃圾密钥拒绝已通过本地连接 API 验证。

`GETLEADSIO` 使用位于 `app.getleads.io` 的标准粘贴 Bearer 密钥路径。其免费公平使用(fair-use)探测以 401 拒绝坏密钥，并接受有效的零信用账户。同一条路由提供容量数据；它不是公开目录工具。

Financial Datasets 使用标准的粘贴密钥与平台密钥路径，带原始 `X-API-KEY` 头。 `OAuthProvider.probe_url` 指向最小实际的价格快照请求，且 `probe_path` 保持为空。因此绝对 URL 仅在连接期间校验粘贴的密钥；`_autoprovision_provider_tool` 不会为该供应商持久化一个周期性的健康检查。既有的 `probe_reject_statuses` 元数据拒绝除 `200` 与 `402` 之外的所有正常 HTTP 结果。于是，一个 `402` 证明凭据已被识别但其上游 Credits 账户为空，而 `429`、`500` 等无关失败无法校验密钥。该规则仅在连接校验期间适用：一次普通的数据调用仍会把 `402` 作为失败中继。没有新增任何共享连接逻辑、健康 schema，或 Financial-Datasets 专属的健康分支。它的 13 个发现(discovery)辅助函数声明通用的 `platform_auth: anonymous` 模式。当既无团队工具也无已存储的供应商密钥时，treg 以无注入凭据的方式调用那些已验证的公开路由。若调用方直接提供 `X-API-KEY`，忠实(faithful)的 relay 会保留它，Financial Datasets 即可对该密钥计费。

QuickEnrich 使用 `QUICKENRICH`，一个位于 `app.quickenrich.io` 的粘贴 Bearer 密钥。免费的 POST Contact Finder 探测以 HTTP 401 拒绝无效密钥，且不需要正的信用余额即可接受成功的探测。 `platform_key_quickenrich` 提供独立的服务端持有平台凭据。不需要 OAuth app 或特殊注入器。参见 [catalog](catalog.md) 中的 QuickEnrich 段落。

TinyFish 使用粘贴的 `X-API-Key`。其主 Agent 主机提供免费的 `/v1/wallet` 探测，而 `CatalogTarget` 为同一个凭据批准独立的 Search 与 Fetch 主机。该钱包属于连接/容量证据，而非公开工具。 `TREG_PLATFORM_KEY_TINYFISH` 提供可选的共享绑定；团队自有密钥保留优先且不曾被计量。

Tier 4 为 MiniMax、OpenRouter、Replicate、reAPI、PiAPI 与 TinyFish 设有显式的平台密钥槽位。web 与异步 cron 将它们作为环境密钥(env secrets)接收，worker 则构建与调用路径相同的平台绑定。密钥值从不复制到任务记录、日志或存档证据中。

## 托管的 treg API 密钥(Managed treg API keys)

treg API 密钥对调用方做认证(authenticate)；供应商密钥(secret)则对上游服务做授权(authorize)。这两类存储是分开的。新增的额外人类与 agent 密钥以 `treg_` 开头，只返回一次，且只以 SHA-256 哈希加一个安全前缀存储。带签名的身份密钥(signed identity key)不存储哈希；其稳定的 `default_human` 行控制该团队的成员资格。新的人类成员资格保留遗留的 `Membership.token_hash` 兼容字段为空，并返回一个钉在团队上的签名默认令牌(token)，因此它们不会制造一个 `legacy_human` 行。既有的非空哈希保留其已迁移的行。

认证先加载密钥，再加载实时成员资格。因此禁用(disable)与吊销(revoke)无需改变角色、访问、上限(cap)或计费数据即可生效。吊销是永久性的。轮换(rotation)使用条件行更新作为跨进程声明(claim)，随后吊销旧行并将其关联到一条新行。该声明同时把被吊销的前驱从默认清单中隐藏；其行、密钥事件与 Activity 快照仍可用于审计。竞争中的请求会收到 409，而不是创建另一个替换项或泄漏数据库错误。密钥审计表与 Activity 快照中不包含完整的 secret。

带签名的人类 Default 密钥是「替换行轮换」的例外。其控制行携带 `default_generation`；团队固定的令牌携带签名的 `kg` 声明。轮换会自增同一行并返回新派生的令牌，因此旧令牌以 `revoked key` 失败，而该用户其他团队的 Default 密钥、随机的额外密钥、agent 密钥与浏览器会话均不受影响。Default 密钥不可被吊销：禁用/启用是临时停止手段，轮换才是替换方式。新铸造的 Default 密钥还携带 `scp=team`；其签名的 `org` 对资源访问具有权威性，因此冲突的 `X-Treg-Org` 无法把一个团队的密钥重定向到另一个团队。无 org 的 `scp=bootstrap` 登录令牌是七天的新手引导凭证，而非托管的 API 密钥。

`last_used_at` 是近似的展示元数据。认证在 `api_keys.touch()` 调度一个尽力而为(best-effort)的后台更新之前提交其只读事务。进程与条件 UPDATE 都强制执行一个五分钟窗口，进程内 map 是有界的，且由单个写入者使用后台连接池。共享同一密钥的请求不会因对 `ApiKey` 行的写入而串行化。

每一个返回完整调用方凭据的响应都使用 `Cache-Control: no-store`。所有者与管理员可以列出、检查 Activity、禁用并启用另一个人类的密钥，以及吊销基于哈希的人类密钥。只有被指派的人类可以轮换 Default 或额外的个人密钥。管理员可以重命名、轮换、吊销并隐藏 agent 密钥。

`MILLIONVERIFIER` 是一个粘贴密钥的 Enrichment 供应商。自有密钥与平台绑定都向 `https://api.millionverifier.com` 的查询中注入 `api`。其免费的 `/api/v3/credits` 探测对垃圾密钥返回 HTTP 200 且 `error: apikey_not_found`；`token_reject_field="error"` 拒绝该 body，同时允许有效的零信用账户。 `platform_key_millionverifier` 读取 `TREG_PLATFORM_KEY_MILLIONVERIFIER`；平台访问还需要既有的允许名单。

## Instagram 授权方法(Instagram grant methods) (2026-09-01)

Instagram 是一个拥有两种显式协议配置的供应商。默认的 `instagram-login` 配置使用独立的 Instagram app 凭据、逗号分隔的 `instagram_business_*` 范围(scope)、用于换码(code exchange)的 `api.instagram.com`，以及用于调用的 `graph.instagram.com`。它把短期令牌交换为可续期(refreshable)的长期令牌，并把通用刷新协议存储到加密 blob 中。可选的 `facebook-page` 配置使用既有的 Meta app、Facebook Login、Page 发现，以及一个派生的 Page 令牌。这些授权是独立的 `Secret` 行。端点矩阵与设置契约见 [instagram-oauth](instagram-oauth.md)。

可复用的多方法规则位于 `domain/connections/authorization.py`：能力(capability)归属、遗留方法推断、方法专属配置、端点-方法选择，以及范围翻译。 `oauth_providers.py` 提供注册表数据，并保留委托给这些领域(domain)规则的兼容方法。初始令牌交换是 `infra/oauth_exchange.py` 中的基础设施适配器；`oauth.py` 仅是兼容门面(facade)。

`authorization_method` 同时存储在 `PendingOAuth` 与 `Secret` 上。既有的 Instagram 行被回填为 `facebook-page`。回调(callback)在关闭数据库会话之后执行令牌与所需身份请求。所需身份的缺失会产生 `setup_required` 且没有工具。其细节来自所选供应商配置的 `identity_missing_detail`，因此共享回调中没有任何 Instagram 专属代码。遗留授权推断也处处使用 `OAuthProvider.authorization_method_name()`；共享调用与重连代码不会重复供应商 id。

难点在于：匹配真实 skill 使用的每一种凭据形态、保持其加密、并保持 OAuth 令牌存活，而代理(proxy)永远不按形态分叉(branch)。

## 注入器 — 接缝(seam) (`infra/upstream/injectors.py`)

代理调用 `inject(headers, params, binding, secret, json_body=...)`，它通过 `INJECTORS` 注册表（由 `@register(name)` 装饰器填充）按 `binding["injector"]` 分派。四种形态、两种机制：
- **放置一个字符串：** `env_injector`、`cli_auth_injector` → `_place()` 把 `binding["format"]`（含 `{secret}`）按 `binding["location"]`/`["name"]` 渲染成 header、查询参数或顶层 JSON 字段。
- **从 JSON blob 提取一个字段：** `secret_file_injector`、`oauth_injector` → `_token_from_json(blob, binding["secret_field"])` 提取一个令牌（默认字段 `access_token`），随后由 `_place()` 放置它。

`_place()` 对查询与 JSON 绑定覆盖同名的调用方值，使被注入的凭据获胜。绑定校验只接受 `header`、`query` 或 `json`，并拒绝每个位置内重复的目标名。新增一种形态只需一个函数；代理永远不变。

## 加密 + 令牌(Encryption + tokens) (`crypto.py`)

密钥值在静态(rest)时是 **Fernet 加密**的：`encrypt()`/`decrypt()` 使用来自 `TREG_SECRET_KEY` 的密钥，若未设置则回退到一个临时 `_EPHEMERAL` 密钥（于是密钥不会在重启后存活——这是要求设置该密钥的明显信号）。 `new_key()` 铸造一个。调用方令牌：`new_token()`（url-safe 随机）+ `hash_token()`（SHA-256）；数据库只存储哈希。值绝不返回给客户端。

## OAuth 时效(OAuth freshness) (`domain/connections/refresh.py`)

两种模式，由 `is_refreshable(blob)` 检测（拥有 `refresh_token` + `client_id` + `client_secret`）：
- **自动(auto)：** `ensure_fresh(secret, db, client)` —— 若 `is_stale()`（已超过 `expires_at`/`expiry` 减去 `_SKEW=60s`），`OAuthRefreshPort` POST 到 `token_uri`（默认 `_DEFAULT_TOKEN_URI`），随后领域命令重新加密并持久化新 blob。只读事务在令牌端点 I/O 之前提交，条件写入开启一个新的短事务，因此供应商延迟不会占用任何池化连接。一个 **单飞(single-flight)** 的 `asyncio.Lock`（按 secret id，`_locks`）加上锁内的 `db.refresh()` 复检，防止刷新风暴(stampede)。 `_locks` map 现在是 **有界的**：在一次陈旧刷新之前，若它持有超过 512 个条目，则丢弃空闲（未持有）的锁——下次需要时再创建新锁——这样长生命周期的 worker 不会永久地每个 secret 累积一把锁。HTTP 适配器同时更新 `access_token` 与 `token` 键，使任一种绑定的 `secret_field` 都保持新鲜。
- **手动(manual)：** 一个裸上传的令牌（不可刷新）原样注入；用户在过期时重新上传。

`treg.oauth` 为兼容 connect、health、call 与惰性本地运行(local-run)消费者而重新导出刷新族。 `ensure_fresh` 由 `call_tool()` 在注入之前调用，也由健康检查运行器调用。注入器保持「哑」；一个刷新函数同时服务于两者。其写回 **以先前的密文(ciphertext)为条件**（`UPDATE … WHERE value = old`）然后重载该行——因此在多 worker 下，第二次刷新无法破坏第一次已经轮换过的 `refresh_token`（仅靠进程内锁无法跨进程）。适配器总是盖一个回退的 `expires_at`（这样省略了 `expires_in` 的供应商不会在每次调用时都触发刷新），强制转换 null 的 `expires_in`，并在 200 body 不携带 `access_token` 时抛出清晰的错误；`_expires_at` 把朴素的 ISO `expiry` 当作 UTC。

资源发现(resource discovery)与资源选择也在关闭只读会话、开始供应商 I/O 之前调用这同一个 `ensure_fresh` 实现。它们不实现自己的锁、交换或条件写入路径。

`refresh()` POST 该凭据记录的 `client_id_param` 方言（TikTok 读 `client_key` 而非 `client_id`），它在铸造(mint)时刻被快照到 blob 上，因此数月后的刷新仍使用授予时所在的方言。同样的快照覆盖了 `token_endpoint_auth_method`：X 与 Pinterest 要求 secret 放在 HTTP **Basic** 中，而一度只有 `exchange_code` 知道——于是连接成功、两小时后每次刷新都 401（对调用方表现为 `502 oauth refresh failed`；≥6 个 org 线上踩过）。现在该方法随 blob 携带且 `refresh()` 遵守它；一个缺少该字段的遗留 blob 先用 body 鉴权，然后在 4xx 时用 Basic 重试一次，并盖戳记录成功者——既有的损坏连接在下次调用时自愈，无需迁移。

blob 还快照了 `client_secret` 与 `token_uri`，且团队成员可以重写 blob。因此对于 treg 自己的 app，`ensure_fresh` 不信任其中任何一个：当 `Secret` 行的 `provider` 是一个注册表供应商、且 blob 的 `client_id` 是本部署为该供应商配置所对应的 `client_id` 时，`oauth_providers.platform_refresh_blob` 会替换当前的 env secret **与** 该配置自身的 `token_uri`，且两者都不会写回（已存储的 blob 保留自己的值）。任何其他 blob，包括仅仅指名了 treg 的 `client_id` 的，都只用其自身存储的内容刷新。因此轮换一个 treg app secret 是一次 env 变更加上在每个执行刷新的服务上重新部署；一旦该部署上线，旧 secret 即可在供应商处删除。

**Meta App Secret Proof。** treg 的 Meta app 要求 App Secret Proof，因此 Graph 拒绝任何未配对 `appsecret_proof` = HMAC-SHA256(app secret, token) 的用户或 Page 令牌的服务器调用（400，code 100）。使用那个 app 的配置声明 `appsecret_proof=True`（`facebook`、`meta-ads`、Instagram 的 `facebook-page`），且 `oauth_providers.appsecret_proof` 仅在该令牌的 blob 指名本部署为该配置所配置的 `client_id`、且请求发往该配置自己的 API 或发现主机时才计算一个。发送此类令牌的每一个请求都携带它：relay 与健康探测（`connection_appsecret_proof`，使用绑定注入的那个令牌，因此 Page 调用用 Page 令牌做证明）以及账户选择器、`application/connect.py` 中的 Page 令牌查找与资源设置。令牌交换与刷新发送 app secret 本身，不需要证明。一个团队自己的 Meta app 永远不会用 treg 的 secret 计算出一个证明。

**连接流程（铸造第一个令牌）：** `consent_url(pending)` 构建供应商同意(consent) URL（默认 `access_type=offline` + `prompt=consent` 以便取回一个刷新令牌）；`exchange_code(pending, code, client)` 用授权码换取令牌并返回一个可自刷新的 blob。两者都遵守携带在 `PendingOAuth` 上的各供应商怪癖（下面从注册表条目快照而来）：一个供应商的 `auth_params` **整体替换** Google 默认值（LinkedIn/X/TikTok/Meta 拒绝 `access_type`）；PKCE（`pkce_challenge()`——X 要求一个 verifier；TikTok 的 `pkce_loopback_hex` 仅在 `public_url` 为 localhost 时发送一个十六进制 SHA-256 challenge，存入 `auth_params`，因为 TikTok 把 localhost 重定向当作桌面 app）；`token_endpoint_auth_method` = `client_secret_basic`（X 把 secret 放在 HTTP Basic 而非 body）；`client_id_param`/`scope_separator` 方言；以及 `long_lived_exchange`（`_extend_meta_token()` 把 Meta 约 1 小时的换码令牌换成约 60 天的那个，失败非致命）。由 `/oauth/*` 端点驱动（[interface/api.md](../interface/api.md)）。

**过期作为一个独立维度（`expiry_of` / `expiry_state` / `connection_view`）。** 健康检查回答「这个凭据是否工作」；过期回答「它还能工作多久」——对于一个 **不可刷新** 的令牌这是两个不同问题（一个 LinkedIn 非合作伙伴令牌在 ~60 天前一直显示为健康，直到它悄然死亡）。 `secret_is_refreshable(secret)` 在服务端解密（blob 从不离开函数）以区分 auto 与 manual；`expiry_state(expires_at, refreshable)` 返回 `fresh|expiring|expired|unknown`——一个可刷新的凭据 **始终是** `fresh`（treg 按需铸造，因此用户从不被催促），只有不可续期者才会得到警告（`EXPIRING_SOON_DAYS=7`）。 `connection_view()` 是仅含元数据的形态（无令牌材料），由 dashboard/CLI 读取，带一个可操作的 `needs_reconnect` 标志。

## 精选 OAuth 供应商注册表(Curated OAuth provider registry) (`oauth_providers.py`)

Octen 是一个带 `x-api-key` 绑定的 API-key 供应商。其连接探测发送一个空的 Search 查询：有效密钥收到一个不计费的 400 校验响应，无效密钥收到 401。 `TREG_PLATFORM_KEY_OCTEN` 通过类型化设置提供可选的共享绑定；团队自有密钥仍居首位且不被计量。该凭据没有已文档化的账户余额端点。

Parallel 是一个带 `x-api-key` 绑定的 API-key 供应商。其连接探测读取免费的 `GET /v1/monitors/stats`：有效密钥收到 200，无效密钥 401。其余额路由使用一个 Account API OAuth 令牌而非此密钥，因此它不是探测目标。 `TREG_PLATFORM_KEY_PARALLEL` 提供可选的共享绑定；团队自有密钥仍居首位且不被计量。

连接一个供应商会把它的 API `base_url` 与索引过的 `host` 持久化到团队的 tool 上。改变注册表的 base URL 会影响新连接与直接目录调用，但一个已命名的既有 tool 或 URL 透传(passthrough)调用会一直使用其存储的主机，直到重连或一次有作用域的数据迁移。主机迁移必须通过连接绑定识别供应商创建的 tool，把手动注册的 tool 留在调用方选定的 URL 上。

连接一个供应商有两种方式。 **自带(Bring-your-own, BYO)：** `POST /oauth/start` 接收调用方提供的 `client_id`/`client_secret`/URI——适用于任何 OAuth2 供应商。 **精选(Curated)：** 对于 **treg 自身持有已审批 app** 的供应商（Google Search Console/Analytics/Business Profile/Tag Manager/Ads、YouTube、LinkedIn、X、TikTok、Facebook、Instagram、Meta Ads——由 PR #20/#21 添加），用户选择一个供应商并同意，不需提供任何东西。这种不对称正是一个托管注册表的意义：这些平台上的门槛成本是 *审批*(approval)（一个 Google Ads developer token、Meta App Review），而非 OAuth 之舞——treg 已经清过了。treg 自己的 client id/secret 从 `Settings` 加载（由 `client_id_setting`/`client_secret_setting` 命名，因此它们像其他设置一样来自 `.env`）。Meta 这一对携带三个层级——read / post / **manage**（Instagram 上的评论 + DM；engagement、visitor content、metadata/webhooks、Messenger、Page video、leads_retrieval 及其必需的 `pages_manage_ads` 附加项，以及 Facebook Pages 上的 catalog_management）——按 2026-08 App Review 包的规模设定；Instagram manage 同时包含 `instagram_manage_messages` 与其 Page 侧 `pages_messaging` 附加项。 `default_capability` 按设计保留为最宽的层级。 `TREG_OAUTH_REVIEW_PENDING` 是不完整供应商审查的唯一运营来源。通用注册表元数据把每个 key 映射到其回退、条件警告、有效的新连接选项，以及默认方法。两个 Instagram 密钥都待审时，普通 Connect 使用 Page 的 `page-tools`；审查者与 app 角色仍可以显式选择 `page-messages` 或直接 Instagram Login。移除一个密钥会在重启后一起改变 API、CLI、agent 与 dashboard 的体验。Meta 最初返回一个长期 **用户** 令牌，但 Instagram Graph 操作——尤其是 Messaging API——必须通过链接到所选专业账户的 Facebook Page 行动。因此 Instagram 供应商声明一个资源令牌查找。在账户选择时，`select_connection_resource()` 私下解析链接的 Page 令牌，把它作为 `page_access_token` 存储在同一加密 OAuth blob 中（保留 `access_token` 用于发现），且被供应的 tool 的通用 OAuth 绑定注入那个派生字段。供应商元数据把链接的 Page id 映射进加密的 `page_id` 上下文字段，并声明一个通用的资源设置请求。对于 Instagram，该请求把 Page 订阅到 app 的 `messages,messaging_postbacks` 字段。该设置是范围门控(scope-gated)的，因此只读/只发的连接不会尝试它。供应商发现与设置 HTTP 调用在只读数据库会话关闭之后运行；结果写入一个新的短事务。资源列表与连接视图绝不包含 Page 令牌；既有连接必须重新选择一次账户以填充它。令牌与对象 id 是分开关注点：Instagram 的 profile/media 操作仍以 Instagram 账户 id 为目标，而 Facebook-login 收件箱同步是 Page 消息面——列出用 `/{page_id}/conversations?platform=instagram`，回复用 `/{page_id}/messages`。用 Instagram 账户 id 调用 conversations 边会产生 Meta 错误 `(#3)`，即使 Page 令牌有效。Facebook Pages 使用同样的查找但不含设置请求：每个 Page 边都拒绝用户令牌（code 190 / subcode 2069032），因此选择一个 Page 会把它那个 Page 的令牌存为 `page_access_token`，且一个 Facebook 连接作用于一个 Page。在资源被选择之前，`_provider_bindings` 绑定根的 `access_token`，因此探测与选择器在派生令牌存在之前就能工作。一次重连替换整个 blob，因此回调取消选择资源，并在其提交之后从新授权再次派生令牌。当新授权不再到达该资源时，连接停留在根令牌上并报 `setup_required`。Google Search Console 的手写 tool 示例指出了它独特的直接-tool 约定：用恰好编码一次的值（`sc-domain%3Aexample.com`）替换 `{site_url}`，且绝不再对 sites list 返回的属性标识符做二次编码。

Google Tag Manager 共享标准的 Google 客户端凭据，并暴露三个累进的层级：`read` 授予 `tagmanager.readonly`；`write` 增加 `tagmanager.edit.containers`；`manage` 增加 `tagmanager.edit.containerversions` 与 `tagmanager.publish`。账户列表既是健康探测也是资源选择器，被选中的 `accounts/{id}` 路径被盖戳进 tool 示例。treg 刻意 **不** 请求 `tagmanager.delete.containers`、`tagmanager.manage.users` 或 `tagmanager.manage.accounts`：agent 可以审计配置、准备工作区变更、创建版本并发布（包括通过发布较早版本来回滚），但不能删除整个容器或管理访问。

每个条目是一个冻结的 `OAuthProvider` dataclass；`REGISTRY` 是 `{service: provider}` 映射。关键模块符号：
- `get(service)` —— 查找一个供应商。`credentials(provider)` —— treg 自己的 id/secret（若本部署未设置则抛出）。`is_configured(provider)` —— 本部署是否能提供它（一个 `token` 种类供应商不需要 treg 提供任何东西，因此总是可提供的）。
- `listing()` —— 目录载荷（`GET /oauth/providers`）：每个供应商按 `CATEGORY_ORDER` 分组，各自标记为 `configured`，每个能力已通过 `scope_label()`/`SCOPE_LABELS`（以原始 scope 字符串为键的查找；`test_every_requested_scope_has_a_plain_english_label` 守护它）以纯英文呈现。授权方法包含它们的展示标签、连接描述，以及它们自己的配置状态。dashboard 与 CLI 消费这些元数据，而不是自己映射供应商或方法 id。一个多方法供应商的顶层 `configured` 值在任一声明的方法被配置时为真。
- `CatalogTarget` 与 `profile_for_catalog_host()` 让一个供应商选择把目录端点的可选 `host` 绑定到一个确切的供应商审批 HTTPS base URL。一个 target 可以覆盖供应商的令牌放置与格式，就像 Diffbot Web Search 对 Bearer 鉴权所做的那样。目录数据不能添加凭据目标；选择加入(opt-in)的供应商解析会在任何 secret 到达 relay 或预留(reserve)资金之前拒绝一个未审批的主机。没有 target 的供应商保留其先前的主-base 行为。
- `consent_notice` —— dashboard 在同意弹窗打开 **之前** 显示的一行，针对一个其同意屏幕命名了用户在 treg 上未见过的事物的供应商。只有 Meta 家族携带一条：共享的 Meta app 注册名为 **Crewlet**，是同一公司（Superdesign Dev Inc）的兄弟产品，而 Facebook 只渲染那个光秃秃的 app 名、不带父级业务，因此没有该提示的话，treg 用户会被要求授权一个陌生人。它像其他供应商字段一样随 `listing()` 携带，因此 UI 绝不对哪些服务获得提示做硬编码；`test_only_the_meta_family_carries_a_consent_notice` 从 `auth_uri == _META_AUTH` 而非服务列表派生该集合。Meta Developer Policy 1.6 要求在同意点披露该关系，这正是它不是一个 docs 链接的原因。
- **范围是按能力(CAPABILITY)而非按供应商的**（`scopes: dict[capability -> list[scope]]`）。能力是累进的超集（write ⊇ read）；`default_capability` 是 **最宽** 的（一个 agent 产品最终需要 write，因此一次诚实的同意屏幕胜过连接两次）。`scopes_for()` / `satisfied_capabilities()` 决定一个后续能力何时需要重新同意。
- `platform_billed` + `billed_read_usd`/`billed_write_usd`/`billed_write_link_usd` —— 那些 **上游(upstream)** 按使用向 app 所有者计费的供应商，无论谁发的调用。X 是唯一一个条目：它放弃了计划层级，改为预付费按使用付费（每个资源读取 / 每次写入发布，于 2026-08-12 核对），因此一次注册表 X 连接消耗 treg 的额度(credits)，代理把这些调用按组织的余额计量（`api.py` 的 `_billed_marketplace` → tier-4 的 reserve→settle 路径；[money](money.md)）。由部署通过 `TREG_OAUTH_BILLED_PROVIDERS`（`config.oauth_billed_set`——空意味着免费，即 `platform_providers` 使用的开关(kill-switch)形态）选择加入来门控。这里的费率是未编目路由的回退；一个已计价的目录条目获胜——而由于一个 `free` 块带有假值(falsy)的 `usd`，「已计价」必须被理解为 *非免费*，否则一个声称 $0 的目录会悄悄地去计回退费。**因此每个 X 条目都携带一个真实费率**，取自 X 的按资源类型费率卡而非一个读价一个写价（`x.yaml` 精选五个；`catalog_ingest.X_RATES` 转录该卡，`X_ROUTE_RATES` 把其余 168 条路由映射到它），且 `tests/test_marketplace_call.py` 遍历该供应商，断言已发布数字等于已预留数字。此处的 `billed_*` 字段是一条无条目声明的路径的回退；**$0.001 的自有读费率刻意不在其中**，因为 X 只把它授予 app 自己的所有者，而一次注册表连接的成员永远不是。 `listing()` 携带 `metered` + `billed_rates`，使 dashboard 能在同意 **之前** 显示价格——也让目录自身的价格展示可以停止把一个已连接账户称为免费（`catMetered`，[dashboard](../interface/dashboard.md)）。一个 **BYO 连接绝不计量**——回调仅在注册表模式下盖戳 `secret.provider`，而那个归属就是整个检测依据。
- `auth_kind` = `"oauth"`（treg 的 app）、`"token"`（用户粘贴的 Bearer 令牌：Slack 以及 MiniMax、OpenRouter、Replicate 与 reAPI 这些 AI 生成供应商；PiAPI 粘贴一个 `X-API-Key` 且是一个 `"key"` 供应商），或 `"key"`（通过粘贴密钥连接的 **API-key 供应商**：Apollo、PDL、Akta、Hunter、Crunchbase、Lusha、Coresignal、Diffbot、The Companies API、位于新 **Enrichment** 架上的 LeadMagic、Social 下的 TikHub + Bright Data + Just One API、位于 **SEO** 下的 Semrush + DataForSEO、SE Ranking、Moz、Majestic、Serpstat，以及位于 **Advertising** 下的广告情报密钥 SpyFu、Apify、Meta Ad Library、SerpApi——连同 OAuth 广告平台 Google Ads + Meta Ads，以及 **未配置** 的 Microsoft Ads、Snapchat Ads、Pinterest Ads（标准 OAuth，一旦本部署设置其客户端凭据即上线）和 TikTok Ads（一个占位符：其非标准的 app_id/auth_code/Access-Token 流程在运行前需要 oauth.py 的工作））。一个 `token` 与一个 `key` 共享 **同一条** connect/verify/auto-provision 路径，因此 `uses_pasted_secret`（`token | key`）对其做门控，而 `is_token_kind` 对 Slack 仅 bot 的副本保持狭义；key 供应商不需要 treg 提供任何东西，因此 `is_configured` 对它永远为真。粘贴的凭据装在 header（`token_header`/`token_format`，默认 `Authorization: Bearer {secret}`）或 **查询参数**（`token_location="query"` + `token_param`——Semrush 把其密钥拼作 `?key=`）中；连接探测命中 `base_url`+`probe_path`，或当最便宜的密钥检查在另一个主机上时命中绝对 `probe_url`（Semrush 在 `www.semrush.com` 上的余额端点）。有效性从 HTTP 状态、一个真值的 JSON `token_verify_field`（Slack 的 `ok`、Apollo 的 `is_logged_in`——两者即使在 **坏** 密钥下也回答 200）、一个 `token_ok_field`==`token_ok_value` 匹配（Majestic 的 `Code`=="OK"）、一个存在的 `token_reject_field`（Serpstat 的 `error`），或一个 `ERROR` 前缀的文本 body（Semrush）读取。连接探测可以是一个带 `probe_json` body 的 POST（Serpstat 的 JSON-RPC），且 `token_encode="base64"` 把一个粘贴的 `login:password` 转成 `Basic {secret}` 的 Basic blob（DataForSEO、Moz）。绑定也携带 `token_encode`，且注入器的 `ensure_base64` 在调用时重新应用相同的已编码检查，因此由 `treg secret add <provider>`（它从不运行连接探测）存储的原始对渲染出相同的 header。 `can_autoprovision`（拥有 `base_url` 且要么不需要第二个凭据、要么 treg 持有它）驱动在成功连接时自动构建一个可调用 tool；`needs_extra_credential` 覆盖主槽位无法携带的第二个 header：Google Ads 的 `developer-token`（treg 持有，经 `extra_credential_setting`）与 Tomba 的每用户 `X-Tomba-Secret`（设置留空 → 用户通过 `POST /connections/{id}/extra-credential` 提供，它用 **两个** 绑定重建 tool——主半部分来自 `_provider_bindings`，因此它遵循供应商自身的鉴权形态而非假设 OAuth）。Tomba 的探测（`/v1/usage`）刻意只用密钥作答，因此连接时验证在 secret 绑定之前就能工作。`required_headers` 携带固定的供应商协议头，必须在每个请求上随凭据一起发送（Crustdata 固定 `x-api-version: 2025-11-01`）。连接探测也发送它们，且 `_provider_bindings` 把每一个变成一个基于同一 secret 引用的普通常量格式绑定。因此通用注入器覆盖一个陈旧的调用方值，而无需教代理它正在中继的是哪个供应商。`_platform_bindings` 在 tier 4 启用时镜像相同的常量，因此一个平台密钥不会静默丢失一个必需的协议头。仅元数据本身仍不会把一个供应商选择加入 tier 4；定价、一个已配置的平台密钥设置，以及部署允许名单仍是独立的门。密钥证据清洗(scrubbing)忽略一个 format 中没有 `{secret}` 占位符的绑定。这使诸如 `2025-11-01` 这样的协议常量排除在密钥拼写集合之外，而真正的凭据及其渲染出的鉴权值仍被清洗。**拆分主机(split-host)供应商每个主机获得一个额外 Tool**（`extra_tools`）：GA4 在 `analyticsdata` 上跑报告，却在 `analyticsadmin` 上列出那些报告所需的 property id——一个范围覆盖两者，但 `/call/` 解析是按 HOST 的，因此没有第二行，agent 就会被挡住（admin 路径在数据主机上 → Google 404；admin 主机 → treg「无已注册 tool」；观察到 13 次调用/7 个 org 卡在那里）。额外工具（`<connection>-admin`）绑定 **同一个** secret，在连接/重连时幂等(idempotent)地 upsert，且 `_backfill_provider_extra_tools` 在有序发布升级的 schema 阶段之后运行，以自动治愈较旧的连接。schema 阶段对空或已盖戳的数据库直接使用 Alembic，并拒绝一个非空未盖戳的数据库，附带 0.14.x 采用补救措施。默认的 `python -m treg` serve 命令在 Uvicorn 之前运行该阶段；裸 ASGI 部署每次发布运行一次 `python -m treg upgrade`。回填是注册表通用的：它扫描供应商归属的 Secrets，要求相应的主 Tool 绑定到该 Secret，然后调用同一个额外 upsert，因此未来添加一个 `extra_tools` 条目不需要一次性迁移。吊销已经会清扫伴随项（任何唯一绑定就是被删凭据的 tool 会一并消失）。`resource_example` 从另一侧闭合循环：用户一选定其 property（`POST /connections/{id}/resource`），模板就把 `{resource}`/`{resource_name}` 渲染进一个现成调用，盖戳进数据 tool 的示例（标记 `stamped: resource`，因此重新选择是替换而非堆积）。
- 连接后由 dashboard/CLI 驱动的辅助函数：资源 **发现(discovery)**（`supports_discovery`、`discover_*`——此连接作用于哪个 site/property/account）、行 **富化(enrichment)**。`list_connection_resources` 把 YouTube 的 `quotaExceeded` 发现响应转成稳定的 `youtube_quota_exceeded` 错误码，因此频道选择器可以解释这个临时限制，而不展示 Google 的原始错误文本。发现可以遍历第二个列表（`discover_extra_path` + `discover_extra_list_paths`）：Meta 的 Business Manager 代表用户持有资产，因此一个代理成员从 `/me/accounts` 看到的恰好是他们整天管理的 Pages/Instagram 账户的 `[]`——Business 遍历（`/me/businesses?fields=owned_pages{…},client_pages{…}`，门控于现在每个 Facebook/Instagram 能力中都有的 `business_management` 范围）把嵌套的主形态行列表扁平化成同一个选择器，按 id 去重且主列表获胜，且失败的额外列表被吞掉（scope 前的连接得到一个干净的权限错误，必须读作「无额外资产」），（`supports_enrichment`、`enrich_*`——Google Ads 返回裸 id，因此每行一次查找填补人类可读名称），以及 **身份(identity)**（`has_identity`、`identity_*`——没什么可选择的供应商，如 LinkedIn/X/TikTok，捕获是谁同意的）。一个 `probe_path` 给注册表 tool 一个真实的健康检查。
- **一个带版本的路径在日历上过期，而非在部署上。** Google Ads 把它的 API 版本放在 URL 中，因此 `probe_path`、`discover_path`、`enrich_path` 与 `examples` 都硬编码一个版本。Google 在每个大版本约 12 个月后弃用(sunset)：v21 死于 2026-08-05，且每个 Ads 调用——包括连接时的账户列表——都失败，直到 2026-08-17 把 pin 移到 v25。代码库中没有任何东西能捕获这个。没有提交改变，没有测试失败（测试套件中没有一个做实时调用），且两种失败模式读起来不同：一个 **从不曾存在** 的版本返回 HTML 404，一个 **已弃用** 的版本返回 JSON 400 `UNSUPPORTED_VERSION`。 `POST /health/run` 会在它坏掉的那天暴露它——它通过同一个带版本的 `probe_path` 探测每个凭据，但默认没有任何东西调度它。运营者可以把一个健康 worker 加到自己的部署中。在全部四个地方一起抬高版本：`oauth_providers.GOOGLE_ADS`、`catalog/google-ads.yaml`、`catalog/google-ads.extended.yaml`，以及 `scripts/catalog_ingest.py:GADS_VERSION`。

## 凭据健康(Credential health) (`health.py`)

`run_all(db, client, org_id=None)` 遍历 tools（设置 `org_id` 时按它过滤，因此 `/health/run` 绝不泄露另一个 org 的凭据）：对每个 oauth secret 执行 `oauth.ensure_fresh`（刷新失败 → 该 secret 被 `_mark` 为 `invalid`），随后通过 `_probe()` 运行 tool 的可选探测（一个注入到 `health_check.path` 的请求，按 `expect_status` 校验；一个非 dict 的 `health_check` 被忽略）。**每个 tool 都在自己的 try/except 内处理**——一个坏 tool（畸形的 `health_check`、古怪的绑定、解密错误）把它自己的 secret 标记为 `unknown` 且批处理继续，因此单个 tool 绝不可能让整个运行 500（回归：它曾经会）。绑定用 `b.get("secret_id")` 读取，跳过任何没有活动 secret 的。按 secret 的状态被持久化；运行只通知/报告 **本次运行评估过** 的 secret（不是每个已持久化 `invalid` 的 secret，否则一个早已解绑的会被永远重新告警）。一个 secret 从其最后一个 tool 解绑后被重置为 `unknown`（没有冻结的陈旧裁定）。`_notify()` 尽力把无效凭据 POST 到所有者的 `webhook_url`——搜索所有者的 **全部** 成员资格（webhook 通常只设在个人 org 上，否则一个团队-org 凭据永远不会告警），随后若所有者已离开则回退到当前 org-所有者的 webhook——但只发往一个 **`safe_webhook_url`** 目标：`webhook_url` 是用户设定的（甚至经由未认证的 `register_user`），因此非 http(s) / 环回(loopback) / 私有 / 链路本地(link-local) 主机在设置时就被拒绝，并在 POST 前重新检查（盲 SSRF 守卫）。按需触发，或由 cron 命中 `POST /health/run` 触发（超级管理员可传 `?all_orgs=1`，使一个 cron 令牌清扫整个平台）。Webhook 目标遵循与上游调用相同的全局可路由单播规则。拒绝 CGNAT `100.64.0.0/10` 保护覆盖网络服务与元数据端点，如阿里云的 `100.100.100.200`，即使该范围不是普通私有 IPv4 空间。把非全局 IPv4 目标映射走的 NAT64 翻译前缀也是内部的，不是绕过此规则的手段。地址空间理由见 [proxy target guards](proxy-model.md#resolution-and-relay-guards)。

裁定在一个运行内遵循 **最坏状态获胜(worst-status-wins)**（一个无探测 tool 不能把一个真实探测刚标记为 `invalid` 的 secret 降级），传输错误 / `5xx` / `429` 映射为 `unknown`（而非假的 `invalid` + webhook 垃圾告警），注入失败映射为 `invalid`，且只有 **本次运行评估过** 的 secret 被通知/报告。运行还调用 `gc_expired_invites(db, org_id)` + `gc_stale_pending_oauth(db, org_id)`（被遗弃的 OAuth 连接在 `OAUTH_PENDING_TTL_MIN` 后过期，因为它们持有一个加密的 client_secret + 一个可重放的 `state`）。连同探测裁定一起，运行通过 `needs_reconnect()`（构建于 `oauth.expiry_state`）遍历 **每个** oauth secret 的 **过期(expiring)** 列表——不只是 tool 探测碰过的那些——因为一个未绑定、未探测、完全健康的凭据仍可能在数日内悄然死亡（LinkedIn 形态）。`_view()` 现在携带 `provider`/`refreshable`/`expiry_state`/`expires_at`，使调用方看到两个维度。`_probe()` 用 `copy_add_param` 把一个绑定的查询合并到 URL 上，而不是传 `params=`（否则 httpx 会 **替换** 掉探测路径自身的查询串，例如 YouTube 的 `?part=snippet&mine=true`，并让一个健康凭据失败）。

一个在 `TREG_PAUSED_PROVIDERS` 中的供应商被整体跳过：不刷新、不探测、不裁定、不告警过期。一个暂停的上游会让每次检查都失败，而连接必须在暂停解除时完好。没有任何任务在失败检查后删除或禁用一个连接；移除只能由用户断开(disconnect)。

## treg 自己的账户

一个供应商的 tier-4 密钥是 `TREG_PLATFORM_KEY_<PROVIDER>`；一对中的另一半有它自己的设置（`TREG_PLATFORM_KEY_TOMBA_SECRET`）。 `TREG_PLATFORM_ACCOUNTS` 以 JSON 从供应商到带标签的账户设置添加更多账户，且一个畸形值会拒绝启动。这些值只活在环境中：一个绑定指名一个设置，并在有多个账户时指名一个账户标签，绝不指名一个值（[proxy model](proxy-model.md)）。

## 存储 / 安全姿态(Storage / security posture) (MVP)

传输中仅 TLS（粘贴/上传走 https，像 GitHub/Vercel secrets）；静态用 Fernet。按成员资格的令牌门控 API（`require_member`，[interface/api.md](../interface/api.md)）并把每个调用按 org 限定作用域（[multi-tenancy](multi-tenancy.md)）。「无持有使用(use-without-hold)」：一个 tool 绑定可以引用队友在同一 org 中上传的 secret；密钥保持服务端侧。后续：本地密钥端到端加密、更细的权限层级。

## 密钥种类 + 唯一的发布例外

`kind` 还新增了 **`param`**——一个非密钥值（project/org id），像 secret 一样存储并注入，但绝不接受健康检查或被标记为 invalid（配置，而非凭据）。每个种类在静态时仍经 Fernet 加密，且绝不被 `_secret_view` 返回。**唯一** 被批准返回值的路径是一次本地运行的 **grant**（[local-run](local-run.md)）：仅限成员+、每个 tool 所有者选择加入、经审计，且对 oauth 它只释放短期的叶子(leaf)（access token）——`refresh_token`/`client_secret` 绝不离开服务器（一个 oauth `secret_field` 允许列表强制执行此点）。即便如此，该值也不交给成员：在 Linux 上 CLI 以专用的 `treg-run` 用户运行，因此凭据活在该用户下（成员自己的 uid 不可读），而非成员的账户上。一个刻意的、狭窄的例外。

**归属边界(Ownership boundary)（谁可以使用哪个 secret）。** 一个成员只能 **绑定/注入其拥有的 secret**（`domain/tools/bindings.py`——`validate_bindings` / `validate_cli_secrets`，两者都调用 `require_secret_ownership`；`routers/resources.py` 保留同名包装，把领域的 `ToolConfigError`/`SecretOwnershipError` 翻译成 422/403）；管理员/所有者可以接好共享密钥 tool。这阻止了一个成员把一个队友的密钥洗白(laundering)进一个其控制的 tool（随后经由代理的 `base_url` 或 `/grant` 外泄(exfiltrate)它）。编辑一个 tool **祖父化(grandfather)** 已经在其上的 secret——只有新加的绑定/注入才做归属检查——因此重新保存一个管理员接好的共享密钥 tool 不会把其所有者锁在外面。而一个会返回调用方 **不** 拥有的 secret 的 `/grant`（一个他们可以运行但不可读的共享密钥 tool）需要 **runner 证明(runner proof)**（`X-Treg-Run-Proof` == `TREG_RUN_PROOF`，仅由根安装的 `treg-run` runner 持有）——因此一个直接的成员调用无法读取别人的密钥值。一个 tool 的 `base_url` 在注册时针对内部地址黑名单（环回/私有/链路本地/元数据，含数字 IP 编码）做校验，且代理在调用时重新解析主机（`infra.upstream.ssrf.host_is_public`，也由 `health` 重新导出，由 `proxy_ssrf_check` 门控）——无 SSRF，即便经由 DNS 重绑定(rebinding)。`routers.resources._require_public_base_url` 也拒绝一个指回 treg 自身的 `base_url`（`application.hub.points_at_treg`），因此一个团队无法注册一个经由代理调用 treg 自己 API 而非直接用 treg 的 tool id 的 tool。

## Kitt AI 密钥连接

`TRYKITT` 把 Kitt AI 注册在 `trykitt` 下，带位于 `https://api.trykitt.ai` 的 `x-api-key` 头注入。 `/credit` 即使在有效零余额时也返回 200，对伪造密钥返回 401。 `platform_key_trykitt` 加载 `TREG_PLATFORM_KEY_TRYKITT`；常规的 platform-provider 允许名单也是必需的。自有密钥始终优先。

## ContactOut 粘贴 API 令牌

`oauth_providers.CONTACTOUT` 针对 `/v1/stats` 校验，且除了 HTTP 成功外还要求 `status_code: 200`。其绑定注入原始 `token` 头。垃圾拒绝与有效连接创建都已通过线上测试。

## HarvestAPI 集成

`HARVESTAPI` 使用粘贴的 `X-API-Key` 与内部 `/users/my-api-user` 探测。钱包端点不是目录工具。

## Dropleads 密钥连接

`DROPLEADS` 使用标准的粘贴密钥连接路径并注入 `X-API-Key`。免费的 `/api/v2/prime-db/credits/balance` 探测拒绝无效密钥，并接受零余额的有效账户。一个连接供应主 `dropleads` tool 与 `dropleads-contact` 伴随 tool；两者都绑定同一个 secret。 `CatalogTarget` 另行允许目录调用发往伴随主机。 `platform_key_dropleads` 提供可选的共享密钥，且 platform-provider 允许名单仍然必需。一个组织自己的密钥有优先且绝不被 treg 计量。

## Prospeo 密钥连接

`PROSPEO` 使用标准的粘贴密钥连接路径并注入位于 `https://api.prospeo.io` 的原始 `X-KEY` 头。其显式的 `GET /account-information` 探测接受一个有效的 Starter 账户，并以 `INVALID_API_KEY` 拒绝垃圾密钥；账户路由保持内部而非成为目录工具。 `platform_key_prospeo` 提供可选的共享密钥，由 platform-provider 允许名单门控。一个组织自己的密钥保持优先且绝不被 treg 计量。
