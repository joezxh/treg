---
title: 代理(proxy) — 忠实注入凭据的中继(relay) + 工具解析
status: shipped
sources:
  - src/treg/infra/upstream/relay.py
  - src/treg/jsontext.py
  - src/treg/infra/upstream/ssrf.py
  - src/treg/api.py
  - src/treg/application/call/authorize.py
  - src/treg/application/call/idempotency.py
  - src/treg/application/call/intake.py
  - src/treg/application/call/resolve.py
  - src/treg/application/call/reserve.py
  - src/treg/application/call/settle.py
  - src/treg/application/call/evidence.py
  - src/treg/application/call/service.py
  - src/treg/application/call/types.py
  - src/treg/application/asynctasks.py
  - src/treg/application/call/keyslots.py
  - src/treg/alembic/versions/0069_platform_key_slot.py
  - tests/test_platform_accounts.py
  - src/treg/client_identity.py
  - src/treg/call_surface.py
  - src/treg/sandbox_identity.py
  - src/treg/domain/governance/access.py
  - src/treg/domain/governance/publicdemo.py
  - src/treg/domain/governance/usage.py
  - src/treg/routers/call.py
  - src/treg/application/hub/limits.py
  - tests/test_ssrf_public_addresses.py
  - tests/test_call_application_contract.py
  - tests/test_call_cancellation.py
  - tests/test_call_response_limits.py
  - tests/test_error_capture.py
  - tests/test_marketplace_call.py
  - tests/test_oauth_billed.py
  - tests/test_passthrough.py
  - tests/test_tag_billing.py
  - tests/test_tag_billing_adversarial.py
  - tests/test_call_architecture.py
  - tests/test_asynctasks.py
  - tests/test_relay_content_length.py
related:
  - architecture/data-model.md
  - architecture/auth-secrets.md
  - architecture/ads-conversions.md
  - architecture/hub.md
  - foundation/charter.md
---

# 代理与调用执行(Proxy and call execution)

`application.call.service` 编排解析、授权、预留、中继与终结(finalization)。`application.call.resolve` 选择目标与凭据；`infra.upstream.relay.relay` 只注入凭据并转发字节。

共享 HTTP 入口可以在 `execute_call` 之前应用默认关闭的 [已发布 Org 准入](org-flow-control.md)。配置了的 Orgs 跨密钥与 worker 共享限流 token 与 Redis 槽；当配置了限流时，一次 Redis 操作在消费任一限制前检查两者。流处理在响应清理期间保留根槽(root slot)。路由子项不获取额外的根槽或限流 token。已发布的 null 禁用其限制；遗留环境映射没有效果。

独立的 [精确 org/端点配额](org-endpoint-quota.md) 在共享调用应用内、规范解析与本地/金钱准入之后、在返回缓存命中或发送直接/overflow 请求之前立即运行。它跨凭据层级计数逻辑准入，并在拒绝时释放未用的 hold。一个耗尽的子项可以被跳过以尝试另一个路由候选。Redis 不确定性允许调用（包括先前受限制的 target），而无需修复计数器；运营者可以在丢失后再次设置限制。可选的验证在已知的拒绝上保留 find 结果。

带授权元数据的具名目录调用在选择供应商与授权方法之前比较主机。这把共享 `graph.facebook.com` 的 Facebook 与 Instagram 工具分开；得到的工具进入同一个 relay，没有供应商特定的 relay 逻辑。

一个实况验证免费的 `GET` 目录行可以声明 `platform_auth: anonymous`。普通的团队工具与团队凭据仍获胜。若两者都不存在，`_anonymous_offer` 要求部署的供应商允许名单并创建一个无绑定、不计量的虚拟工具。`relay()` 因此不注入任何供应商凭据地转发请求。该字段是通用的目录元数据；解析器与 relay 不含供应商特定的匿名路径规则。

缓存实验元数据由调用服务捕获漏斗附加到既有的 `tool_called` 事件：结果/原因、比较与 TTL 策略、发布百分比、查找时长，以及候选年龄/窗口，加上命中时的 `cache_price`（`full` | `repeat` | `free`），以及像每个服务器事件一样来自 `analytics.py` 的 `build` 与 `archive_config` 指纹。它不含响应/请求内容或缓存键。稳定的团队/端点发布在归档 DB 查找之前运行（默认对每个端点与团队开放）；未选中的调用保留正常的 relay 与金钱路径。自有密钥目录调用也参与：一个可存储的自有密钥 2xx 在适合归档上限且被要求身份编码时整体读取，否则原样流式传输；自有工具调用从不接触归档。控件与指标分母见 [archive](archive.md#own-key-answers)。这不会移除授权/预留/结算 DB 工作。

## 忠实中继契约(The faithful-relay contract)

`relay()` 只改变 **三件事**；其余逐字(verbatim)（方法、路径、所有查询参数含重复项、头、cookie、body 字节）：
1. **逐跳传输头(hop-by-hop transport headers)** —— `_HOP_BY_HOP`（`host`、`content-length`、`connection`、`keep-alive`、`te`、`trailers`、`transfer-encoding`、`upgrade`、`proxy-*`）；每跳重新派生，否则流会损坏。一个值被携带而非重新派生：当调用方为一个 body 声明了 `Content-Length` 时，relay 在上游请求上设置相同的值。字节是调用方的、未改动，因此长度精确，且没有它 httpx 会把流式 body 框成 `Transfer-Encoding: chunked`，而 Meta 的 Graph API 边缘不读它（每个 POST body 消失；一个广告创意因「Ad incomplete」失败，直到 spec 被移进查询字符串）。一个流式 chunked 的调用方保持 chunked。
2. **treg 的控制/基础设施 + 边缘转发头** —— `_CONTROL`（`x-treg-token`、`x-treg-org`、`ngrok-skip-browser-warning`、`x-forwarded-*`、`x-real-ip`、`forwarded`、`via`、Cloudflare 的 `cf-connecting-ip` 家族、`true-client-ip`、`cdn-loop`），通过 `_DROP_REQUEST = _HOP_BY_HOP | _CONTROL` 丢弃，外加 `TREG_CLIENT_IP_HEADER` 命名的任何东西，因此没有东西泄漏到上游。MCP 层在其进程内调用上以那个头重新发送调用方的地址；一个 Cloudflare 前置的供应商用 403 error 1000 回答任何仍携带它的请求。`_scrub_treg_cookies` 也从 Cookie 头剥离 treg 自己的 cookie（`treg_session`、`treg_oauth_state`）——否则 dashboard 的 `credentials:'include'` Try-it 会泄漏我们的会话令牌——同时保留其他 cookie。
3. **被注入的凭据** —— 每个绑定只覆盖其目标头、查询参数或顶层 JSON 字段。一个 JSON 绑定是一个显式的供应商契约，且是唯一缓冲并重新序列化调用方 body 的情形；所有其他 body 保留流式字节路径。这是语义 JSON 中继，而非字节忠实(byte-faithful)中继：格式会改变，非 ASCII 文本作为 UTF-8 发出，重复键失败关闭(fail closed)。绝不要在对原始 body 字节做签名或哈希的上游使用 JSON 绑定。
   在连接到 treg 自己的 Meta app 时，凭据包含一个 `appsecret_proof` 查询参数（被注入令牌用 app secret 的 HMAC）替换任何调用方值；何时欠一个见 auth-secrets.md。

   **每个 JSON 重新编码都经过 `treg/jsontext.py`。** `json.loads` 接受一个转义的孤立 UTF-16 代理(`"\ud835"`，一个 JavaScript 爬虫在 LinkedIn 帖子配对中途切断)，而一个普通的 `ensure_ascii=False` dump 在上游回答后抛出。`dumps`/`dumps_bytes` 保留非 ASCII 可读，且只对此类值回退到 ASCII 转义，因此路由 body、hub 的子 body 与 `treg --json call` 中继上游自己的转义。MCP 是唯一有损(lossy)表面：SDK 的 pydantic 序列化器无法写入该转义，因此 `mcp._body` 把每个未配对代理替换为 U+FFFD（配对的文本不变）而非丢失已付费的答案。

一个目录 `ceiling_param` 由调用应用在 `relay()` 之前追加到 `UpstreamRequest.query_items`，且只在调用携带调用方未以此名发送的调用方上限时。 `relay()` 逐字转发那个列表。该对不在入站查询中，因此它不进入 `params_hash` 或归档键。

> **treg 从一次调用保留什么。** 成功不保留内容：relay 转发字节，审计行记录状态、大小与时长。一次 **失败的中继调用** —— 平台、自有密钥或普通自有工具 —— 是例外：`CallRecord.error_request` / `error_response` 保留调用方发送了什么、供应商（或 treg 侧 502）回答了什么的脱敏、截断副本。没有它，一次失败是一个光秃秃的状态码：`path` 持有目录 URL 而非调用方的参数，且 `params_hash` 是单向的。`application.call.settle` 用 `_buffer_response` 缓冲已计量响应，而一次失败的未计量响应被整体读取（`_read_whole_if_small`，至多 8 MiB）以便下方面向调用方的掩码看到每个字节；一个过大者在已计费调用上被替换、且只在未注入任何东西时才原样流式传输（`_peek_stream_head`，8 KiB 证据）。

> **错误 body 中回显的凭据。** 供应商在失败时把请求引号回来（TikHub 的 402 返回每个请求头，含 `Authorization`）。在 4xx/5xx body 到达调用方、幂等重放或证据行之前，`evidence.redact_error_response` 解码它（gzip/deflate，有界；自有密钥调用镜像调用方的 `Accept-Encoding`）并把每个被注入凭据（`_secret_renderings`）的每种拼写替换为 `***`。掩码只精确：admin-log 模式的 nets 会重写普通字段如 `"key": "uniqueId"`。一个仍找到凭据的归一化重检、无法渲染的凭据，或无法解码的 body 会把整个 body 替换为一个 `response_redacted` JSON 错误。一个未改变的 body 保留其字节与编码；一个被掩码的以 fresh `Content-Length` 重新发送为 identity 编码。2xx body 不动。未计量路径上的调用方 body 只在声明了 `Content-Length` 且至多 64 KiB 时才被缓存；大的/chunked 上传保持流式且只保留其查询参数那一半。重做顺序、仅 admin 访问与保留见 [data-model](data-model.md)。

`relay()` 内的忠实机制：
- 请求头从 `UpstreamRequest.raw_headers` 重建进一个 `httpx.Headers` 多字典（保留重复的 header / cookie）；注入（`headers[name] = v`）只覆盖指名的那个。
- 仅平台层级，`service` 先让原始头通过 `relay.scope_shared_idempotency_key`，它把调用方的 `Idempotency-Key` 替换为（org、label）的摘要。每个 org 在 treg 的密钥上共享一个供应商账户，且一个尊重该头的供应商（LeadsForge 如此）否则会用同一个 label 把 org A 的作业返回给 org B——而 `resource_ownership.produces` 随后会把 A 的作业 id 记录为 B 的。treg 自己的幂等表已经为同一 label 重放调用方的答案，因此调用方什么也不损失。一个团队自己的密钥逐字中继该头：那个账户是他们的。
- 仅平台层级，`relay.identify_as_treg` 随后把调用方的 `User-Agent` 替换为 `config.TREG_USER_AGENT`。供应商在那里看到 treg 的账户，且库默认值被读作 bot 流量：LimaData 的 Cloudflare 对每个 `Python-urllib` 调用回答 403（error 1010），Wiza 对其电话 reveal 也如此一天。一个团队自己的密钥逐字中继调用方的头。共享客户端（`app.state.http`）、异步任务轮询器与容量收集器默认发送同一头，因此 treg 自己的请求绝不以 `python-httpx` 发出。
- 查询作为路由器捕获的有序对，在 `UpstreamRequest.query_items` 中（保留像 `?tag=a&tag=b` 的重复键），用 `copy_add_param` 合并到上游 URL 而非作为 `params=` 传入：httpx 在给定 `params` 时（即使空）会替换 URL 既有的查询，这曾在 2026-09-19 之前静默剥掉一个目录路径自己的查询（`/rest/images?action=initializeUpload`）。`tests/test_relay_path_query.py` 钉住了它。
- 路径从 `request.scope["raw_path"]` 重建（在 `call_tool` 中），而非 Starlette 的 URL 解码路径参数——百分号编码存活到上游（npm 的作用域发布 `PUT /@scope%2fname` 若 `%2f` 被解码为字面斜杠会 404）。
- body 经 `content=request.stream()` 流式传输（流式，绝不缓冲）。调用方声明的 `Content-Length` 随行携带，因此流不会被重新框成 chunked（见上面的契约）。例外：调用方可以用 `X-Treg-Body-Encoding` 把 body 做 base64/gzip 编码以让 SQL/HTML 溜过托管边缘的 WAF；`_BodyDecodeMiddleware`（在 api.py 中）随后在 `relay()` 运行 **之前** 缓冲 + 解码它，因此 relay 仍逐字向上游转发真实明文字节。见 [api](../interface/api.md)。
- 上游调用使用 **共享** 客户端（在 `lifespan` 创建的长期 `httpx.AsyncClient`，位于 `app.state.http`——keepalive 是最大的延迟胜利）。
- 基础设施 relay 返回框架中立的 `UpstreamResponse(status, raw_headers, body_stream, close)`。路由器把它包进 `StreamingResponse` 并复制每个上游响应头（含多个 `Set-Cookie`）减去 `_DROP_RESPONSE`。它的 body 包装器与后台任务共享同一个幂等关闭操作，因此完整读取、部分断开、流错误与取消都精确关闭上游响应一次。

一个请求可携带多个凭据：`relay()` 遍历 `tool.bindings` 并对每个绑定调用 `injectors.inject(headers, params, binding, crypto.decrypt(secret.value), json_body=...)`。绑定也可以盖戳供应商协议常量：没有 `{secret}` 的 format 字面渲染（Crustdata 要求的 API-version 头是第一个注册表用例）。它仍携带同一 secret 引用用于绑定验证与生命周期，且赋值覆盖一个调用方提供的值。这是通用绑定行为，而非 relay 中的上游特定分支。一个匿名目录回退使用同一 relay 与空绑定列表。它不剥离调用方头也不重写请求；它只省略一个 treg 否则会注入的凭据。只有当调用方不提供供应商凭据头时目录价格才是免费的。

**平台绑定 —— 注入 treg 自己的凭据。** 一个带 `platform_setting` 键（而非 `secret_id`）的绑定注入一个从 `get_settings()` 读取的 treg 自己的凭据——Google Ads developer token 是存在的情形。该值从不活在 org 的 secret 存储中，因此一个租户无法读取它或通过本地运行提取它；缺失的设置是一个干净的 `502`（`this server has no <setting> configured`）。被 OAuth-marketplace 自动供应器用于一个需要 treg 集中持有的第二个凭据的供应商，也被 tier-4 目录调用使用。Tier 4 也复制供应商的常量 `required_headers` 绑定，因此 Crustdata 的 `x-api-version: 2025-11-01` 固定在 BYOK 与平台密钥调用上相同（见 [api](../interface/api.md)）。

一个看起来相似但 **不是** 平台绑定的独立情形：Google Ads **转化(conversion)** 上传器（`adsconv.py`）也花费 treg 自己的平台连接，但它根本不是一个调用方发出的 `/call/` 请求，因此它从不到达 `relay()` 或 `infra/upstream/injectors.py`——它直接读取平台 org 存储的 OAuth secret 并构建自己的头。见 [ads-conversions](ads-conversions.md)。

**当调用方未发送时，`Accept-Encoding` 归一化为 `identity`。** `relay()` 原样流式传输上游 body（`aiter_raw`），因此若调用方不要求压缩，httpx 否则会加上自己的 `Accept-Encoding: gzip` 并交给一个普通 HTTP 客户端 / agent 它从未请求的压缩字节。要求 `identity` 使调用方收到的与它请求的匹配。

## 连接纪律：在途调用不持有 DB 连接(Connection discipline: a call in flight holds no DB connection)

解析、授权与预留拥有短会话。`service._execute_call` 在打开预留之前提交请求加载 secret 的会话，在 relay 或实时演示的网络调用之前再次提交。不变量是 **上游 I/O 期间零借出的请求连接**，包括限流平滑等待。

结算、首次调用记录与幂等存储使用它们自己的会话。提交不会使已加载对象失效，因为会话创建器使用 `expire_on_commit=False`。OAuth 刷新同样把 DB 读/写与令牌端点网络 I/O 分开。

让请求事务在 relay 期间保持打开会死锁一个饱和的池：每个请求持有一个槽，而它的结算等待另一个。`tests/test_call_pool_discipline.py` 在网络边界检查池占用并覆盖并发调用。池大小、超时与独立的 API/admin/后台池在 [deploy](../ops/deploy.md) 中规定。

## 工具解析(`application.call.resolve`)

`* /call/{rest:path}` → `routers.call.call_tool()` → `routers.call.run_call_surface()`（与 `/catalog/call/` 和 `/table/` 共享，差异只在把答案变成响应的 `finish`：见 [table](table.md)）→ `application.call.service.execute_call()` → `resolve_call_target(...)` 返回一个框架中立的 `ResolvedTarget(tool, upstream)`。每个解析用例拥有并关闭其读取会话。

一个不是 org 工具的具名未命中(miss)按序落空(fall through)：一个目录端点，然后——仅对顶层调用（`request.context.input.child_of is None`）——一个 hub 工具（`<team-slug>.<name>`、`hub_app.tool_for`）。一个自有工具或目录 id 总是获胜；hub 工具绝不遮蔽任一个。hub 运行是什么见 [hub](hub.md)；`service._execute_call` 在每团队 `hub_limits.slot()` 下运行它，以 `429 hub_busy`（指名活跃计数与 `retry_after_s`）拒绝新运行，而非在 `hub_limits.MAX_RUNS_PER_TEAM` 之后排队。**两种形态都按调用方的 org 限定作用域**（`Tool.org_id == org_id`），因此两个 org 独立解析且可复用工具名或上游主机；该用例随后只加载同 org 的 secret。解析后 `application.call.authorize` 按序运行工具/项目 ACL、deny、成员上限与公开演示门，无金钱 hold 或上游访问。它的短会话在预留阶段之前关闭；`-1`/默认成员上限不增加查询。两种解析形态：

`* /catalog/call/{rest:path}` 是仅目录 MCP 表面使用的更窄入口。`routers.call.call_catalog_endpoint` 设置 `request.state.catalog_only`（门控于 `claude_connector_enabled`）然后进入同一个 `call_tool` 处理器；该标志随 `CallInput` 进入 `execute_call`。解析只接受一个精确的目录端点 id，从不调用 `resolve_call_target`，因此一个私有团队工具或任意透传路径无法遮蔽目录条目。目录解析之后的一切保持共享：凭据、ACL、deny 规则、上限、取消清理、计量、审计、幂等，与忠实中继。

- **URL 透传(agent-native)：** `rest` 是真实上游 URL（`/call/https://api.intercom.io/me`）。`_normalize_scheme()` 恢复一个路径参数折叠成 `https:/` 的 `https://`。工具由 **主机** 解析（`_host_of()` = `urlsplit(...).netloc`，与索引的 `Tool.host` 匹配）然后 **最长 `base_url` 前缀**；平局 → `409`，无匹配 → `404`（或当调用方的 ACL 是唯一移除匹配的，见下，`403`）。
- **具名：** `rest = "<tool>/<path>"`（`rest.partition("/")`），按 `Tool.name` 查找；上游 URL = `base_url + path`。**无路径 → base URL 本身，不带尾部斜杠** —— 一个钉到完整资源（`.../v1/charges`）的工具必须原样中继，因为 Stripe 对 `/v1/charges/` 返回 `404`。

一个具名未命中，其 `<tool>` 是一个带其后的路径的精确目录 id（`reapi.tasks.get/tasks/1`），是应用于目录那一半的 own-tool 形态：它在下方任何提示运行之前回答 `400` 指名端点的参数槽与 `--query` 形式。具名未命中也在错误路径上检查 org 的调用方可用的自有工具。当一个点号操作名与其中一个共享其供应商/第一段（例如 `google-analytics.report` 在已连接的 `google-analytics` 工具旁）时，404 携带 `hint` 外加 `did_you_mean` 并指向 `/call/google-analytics/<path>`。若那个点号名是一个真实目录端点，提示跟随目录落空且只在 marketplace 凭据阶梯也死路时附加。目录近似(near-id)匹配保持供应商局部，并对真正的拼写错误优先。

若两种形态都以 404 未命中，一个点号 target 在端点目录中得到最后一次查找。一个 live 行进入 `_resolve_marketplace_call` 与其凭据阶梯。`_marketplace_upstream` 通过百分号编码原始值来填充目录路径占位符，但保留一个含有效 `%HH` 转义的值。这防止一个已编码的 Search Console 属性 id 如 `sc-domain%3Aexample.com` 被双重编码成 `%253A`。原始 `@` 保持字面因为它是一个合法的路径段字符。这也支持 email-path API，如 Tomba 的验证器，它在解码前拒绝 `%40`。斜杠、查询/片段分隔符与无效百分号保持转义；URL 透传字节不变。在构建那个 URL 之前，一个选择在 `catalog_targets` 上的供应商的可选目录 `host` 必须通过 `OAuthProvider.profile_for_catalog_host` 解析到一个精确批准的 HTTPS base URL。没有该选择加入的供应商继续针对其主 base URL 解析目录路径。批准的 root 在 `_marketplace_upstream` 追加端点路径时保留其路径前缀，且所选供应商配置提供正确的凭据绑定。一个未批准或格式错误的 target 在预留与 relay 之前作为 treg 拥有的 502 失败；目录数据无法把注入的凭据重定向到它选择的 host。一个 `retired`/`broken` 墓碑(tombstone) 反而以 410、其 `status_note` 及其可选 `superseded_by` 被拒，在凭据被选择或 relay 可运行之前；该拒绝被审计为 `refused_by=retired`。这个排序是刻意的：一个恰好命名为旧目录 id 的 org 自有工具已经在上面解析且不被遮蔽，而 URL 透传没有目录 id 形态可意外捕获。

**能力替代(Capability alternatives)。** 一个无 `superseded_by` 的 410 墓碑，或一个凭据阶梯 404，包含 `_capability_alternatives(ep)`：精选的同能力端点，最便宜优先，标记为可在 treg 的密钥上调用或需要一个自有凭据。被标记的目录行被排除。该辅助是同步的且不执行任何 DB 读取；测量的可靠性属于目录检查。它建议替代而不替换一个。没有能力的端点无法参与。

**ACL 过滤的候选(ACL-filtered candidates)。** `_resolve_call` 取 **调用方** 并在最长前缀平局打破 **之前** 按 `_tool_usable`（项目作用域与每工具列表）过滤透传候选。一个调用方无法使用的同主机工具绝不能导致一个 `409`——或为某人赢得平局——而那个人在 `list_tools` 中甚至看不到它。这只 **缩小** 候选集，因此它绝不会授予访问：无论解析出什么都仍通过 `_require_tool_use`。具名形态不需要过滤（它解析一个工具，然后门运行）。

**仅 ACL 未命中返回 403。** 解析保留未过滤的主机匹配以区分一个缺失工具（404）与仅被 ACL 移除的候选（403）。后者只命名调用方提供的主机，绝不一个不可访问的工具。

**策略 deny（`_enforce_deny`、`_deny_match`）。** 解析与工具 ACL 之后，解析出的上游与 org 的 `DenyRule` 行（org 级 + 针对此调用方的）匹配 → `403` 指名规则。评估 **解析出的** 上游是让两种调用形态同样被门控的原因——一个调用方无法通过切换到 URL 透传来躲避规则——且 relay 不跟随重定向，因此一个被阻塞的主机无法通过 3xx 弹跳到达。当一个供应商移动其 `base_url` 时，旧的留在 `legacy_base_urls`：该调用也如同发往那里一样被检查，因此一条针对旧主机写的规则保持阻塞，且目录 tier 1 仍找到在其上注册的团队工具。路径匹配锚定在段边界（`/v1/charges` 必须不匹配 `/v1/chargesX`），`_resolve_call` 守卫的同一个陷阱。它适用于 **包括 owner 在内的每个角色**（一个护栏，而非权限层级）以及两个运行层级，其中工具的自己 `base_url` 主机代替请求路径。`_deny_match` 是纯函数，因此无需 DB 即可单元测试——镜像 `localrun.check_deny`，它是低一层的同一想法（argv 而非 URL）。零规则 = 一个索引查询且无行为改变。一个规则也可携带一个 `project_id`：它随后只在通过该项目的工具的调用上触发（那时每个强制点都有一个解析出的 Tool，因此 `_enforce_deny` 取 `tool.project_id`）；一个 org 级工具调用绝不被项目规则捕获。三个作用域轴——主机/路径/方法、成员、项目——以 AND 组合，且每个都是 NULL-意味着-任意。

## 响应与诊断证据(Responses and diagnostic evidence)

两个调用表面的 treg 拒绝都携带 `X-Treg-Error: 1`。机制键控的应用失败映射到 `caller | treg | upstream | org_connection` 归责；HTTP 适配器保留状态与细节。供应商失败仍是响应数据。头契约在 [API 片段](../interface/api.md) 中记录。

凭据刷新与 relay 之后，`_audit` 记录尝试并经由 `_tool_called_props` / `analytics.capture` 镜像它。供应商身份是目录供应商或自有工具的上游主机。分析含结果、状态、时长、成本、调用引用、容量/缓存/平滑信号与 user-agent 归属（外加通过一个 MCP 表面发出的调用的 MCP 主机），以及来自 CLI 的其发布（`client_version`）、哈希会话（`session`）与 agent 标签（`agent`），每个来自其 `X-Treg-*` 头，截断，缺失时为 null。绝不参数或 body。

`domain.catalog.results.classify` 在业务命中遥测与缓存准入之间共享已验证的命中/未命中规则。找到意味着 `hit=true`，显式空意味着 false，错误/未知结果意味着 null。Hunter company emails、LeadMagic employee finder 与 SE Ranking keyword volume 有额外的字段检查；其他已验证适配器保留其未命中表达式。只有启用了命中/未命中规则的端点采用结果感知的缓存行为；未配置或未验证的端点保留原始缓存学习与服务。分类只检查已缓冲的 body 且不改变 relay 字节或结算。既有的 `tool_called` 事件暴露 `result_state`、`result_reason`、`cache_admission` 与 `cache_result_policy`。见 [archive result admission](archive.md#result-admission)。

Overflow 在同一调用引用下保留两个尝试行，但为最终答案发出一个产品事件。`defer_analytics` 持有父事件直到子成功或父的答案成立。失败请求的脱敏与保留属于 [data-model](data-model.md#audit-writer-auditpy)。

异常退出只记录一次，由审计标记守卫：

| 退出 | 事件 |
|---|---|
| 调用方身份之前的池超时 | `call_intake_failed`，仅表面，无团队/target |
| 身份之后的池超时 | `tool_called`，`outcome=gateway_failed`，`failure_kind=db_pool` |
| 等待 `execute_call` 时的意外异常 | `tool_called`，`failure_kind=unexpected_exception`；Starlette 仍返回光秃秃的 500 |

在 target 解析之前，target/供应商身份保持 null。在 `execute_call` 之外、以及处理器返回后的 body 流失败的异常，在这个补偿契约之外。绝不要在响应头已发送后把一个流失败重新标为新的 500。

## 解析与中继守卫(Resolution and relay guards)

**解析 + 错误硬化：** URL 透传前缀匹配尊重一个 **路径段边界**（`norm == base` 或 `base + "/"`），因此 `.../v1` 不再匹配 `.../v10/...` 并注入错误的凭据；最长前缀平局打破比较 rstripped 长度（一个尾部斜杠重复是一个真实的 `409`，而非静默赢家）。当两个同主机工具仍按前缀长度平局时，`_resolve_call` **偏好注册表供应商支撑的工具**（一个其绑定指向带 `provider` 的 `Secret` 的）而非常持有陈旧凭据的手注册工具——那里的 `409` 会恰好打断那些从不输入工具名的 agent 面向 URL 透传调用方；只有真正的歧义（两者或都不供应商拥有）仍 `409`。那个 409 指名每个调用方可用的冲突工具，并引导调用方到无歧义的 `/call/<name>/<path>` 形态。绑定有效性在 **注册** 时检查（`_validate_bindings` 拒绝未知的 `injector` 与跨 org/悬空 `secret_id`；`register_skill` 运行同一门），且 `call_tool` 把调用时注入器的 `ValueError` 与上游 `httpx.RequestError` 翻译成 `502` 而非未处理的 500（并审计失败的尝试，而非只有成功）。一个绑定 `format` 被验证为只用 `{secret}` 与 `name`/`secret_field` 渲染为非空字符串；重复的目标名对 `location:"header"`、`"query"` 与 `"json"` 分别拒绝（它们会静默互相覆盖）。`health._probe` 跳过悬空绑定而非让整个运行 `KeyError`。

**中继安全 + 忠实性（bug 搜猎）：** 响应侧剥离 treg 自己 cookie 名的 `Set-Cookie`（上游绝不能覆盖 `treg_session`/`treg_oauth_state`——固定(fixation)）并添加 `X-Content-Type-Options: nosniff` + `Content-Security-Policy: sandbox`（一个浏览器导航到 `/call/…` 绝不能执行 treg 已认证 origin 下的上游 HTML/JS）。它在无 body 回复（HEAD/204/304）上保留 `Content-Length`，只在调用方发送了 body 时才携带请求 body（GET 上无伪造的 chunked 帧），并尊重一个对等方通过其 `Connection` 头标记的逐跳（RFC 7230）。`injectors._token_from_json` 拒绝非字符串字段值而非注入垃圾。

**调用时 SSRF 守卫（DNS 重绑定防御）。** 就在上游 `send` 之前，`relay()` 重新解析上游主机（`infra.upstream.ssrf.host_is_public`，由 `proxy_ssrf_check` 设置门控）并若任何解析出的地址是内部（环回/私有/链路本地/保留/多播）则以 `502` 拒绝。这捕获 `base_url` 在 **注册** 时公开但其 DNS 现在指向内部 target 如 `169.254.169.254` 或 localhost 的情形——仅注册时检查无法阻止一个后来解析不同的名字。注册本身（`infra.upstream.ssrf.safe_webhook_url`，由 `health` 重新导出并为 `base_url` 复用）也拒绝数字 IP 编码——十进制/十六进制/八进制/短形式如 `2130706433` / `0x7f000001` / `127.1` 经 `inet_aton` 归一化并重新检查，因此它们无法溜过字面 IP 块。Targets 必须是全局可路由单播地址。CGNAT `100.64.0.0/10` 是内部服务空间：Tailscale、WireGuard overlay 部署、Fly.io、一些 Kubernetes pod CIDR，以及阿里云的元数据端点 `100.100.100.200` 使用此范围内的地址。这些正是一个调用方控制的上游绝不能到达的服务。映射非全局 IPv4 地址的 NAT64 翻译前缀不会使那些 target 公开；`64:ff9b::/96` 仍被阻。

（一个狭窄的解析-对-连接竞争仍然存在；固定解析出的 IP 需要一个自定义传输。）

> 为何用 relay 而非对上游建模： [foundation/charter.md](../foundation/charter.md)。

## 路由端点 —— 解析阶段短路(Routed endpoints - the resolve stage short-circuit)

一个带 `kind: routed` 的目录行（`treg.<capability>`，生成的——`architecture/catalog.md` § Routing）从不自身到达凭据阶梯。`service._execute_call` 把它交给 `application/call/route.py`，它构建计划并作为子 `CallContext`（`call_ref` `{parent}:r{n}`）通过 **这同一个用例** 运行每个子端点，因此下方每个规则——阶梯、预留、relay 忠实性、容量、overflow、审计、取消——逐子不变地适用。**结算不** 直接适用：每个子的 `MarketplaceCall.deferred` 指向父的 `CallContext.deferred_settles` 列表，因此 `_platform_settle` 追加一个 `DeferredSettle`（调用 id、可计费、它会收取的_amount、其归档使用标记）并让 hold 保持开放而非关闭它。只有会收取某物的子才推迟：一个不可计费或按供应商报告的零结算的子立即释放，因此其 hold 从不阻塞下一个子的预留。父——而非每个子——决定调用方是否付费，并以 `settle.close_deferred(charge=…)` 精确关闭每个子的 hold 一次：`charge=True` 把每个可计费子作为它自己的结算会做的那样结算，`charge=False` 释放它们全部，因为一个失败的路由调用对调用方零收费。在 `close_deferred` 运行之前的崩溃把 hold 留给收割器(reaper)，它有利于调用方释放。每个子的答案由 `route.child_outcome`（声明的未命中、未找到、被拒、错误、适配器错误、miss 或 hit）读取，重放引擎也调用它（architecture/replay.md）。父只组装 `{output, raw, _treg}` 并拥有幂等标签。

一个其结果仍待定（`202` 带 `X-Treg-Route-Outcome: pending`）的路由调用保留 `request.state.call_cost_micro` 为 `None` 并跳过 `X-Treg-Cost-Micro` 响应头，而非报告一个尚未发生的收费。

## 一个供应商背后的多个 treg 拥有账户(Several treg-owned accounts behind one provider)

`TREG_PLATFORM_ACCOUNTS` 在供应商背后添加账户，作为从供应商到带标签账户的 JSON：`{"contactout": {"b": {"platform_key_contactout": "..."}}}`。部署自己的 `platform_key_<provider>` 是标记为 `primary` 的账户，且调用路径之外的每个读取器（余额收集器、归档刷新、overflow 验证）继续使用仅它。一个账户命名每个每账户不同的凭据。`keyslots.check_accounts` 拒绝在该调用路径无法使用的账户上启动 API 或 `treg-worker asynctasks settle` / `hub check`：一个其主键未设的供应商背后的账户（主密钥是服务开关）、一个没有粘贴平台密钥的供应商，或一个省略其供应商配对设置（Tomba 的 secret、Adyntel 的账户 email）的账户。一个标签，绝不一个凭据，是行、桶与遥测（`tool_called.key_slot`）命名的东西，因此重排账户或重新生成一个的密钥什么都不改变。

`application/call/keyslots.py` 选择账户：

1. 一个作用于任务、结果或托管资源的调用使用创建它的账户。`AsyncTaskRecord`、`AsyncResourceRecord` 与 `ProviderResource` 携带 `key_slot`；NULL 是账户存在之前的行，意味着 `primary`。一个其账户不再配置的调用在预留之前以 410 `platform_account_retired` 被拒；异步 worker 立即释放这样一个任务的 hold（平台吸收任何上游收费，标记为待核对）。退休意味着该供应商的账户在此进程中已配置且该标签不在其中；一个不为该供应商持有进一步账户（或其主）的进程回答 503 `platform_account_unavailable`，worker 在其上退避(back off)，因此一个丢失了环境的 worker 从不释放一个它一旦恢复就能轮询的任务。一个其对象活在不同账户上的调用以 409 `platform_account_split` 被拒。
2. 一个携带 `Idempotency-Key` 的调用使用 org 作用域密钥哈希到的账户，因此再次到达供应商的重试落在供应商能识别它的地方。添加或移除一个账户可以移动一个密钥。幂等声明不是记住账户的地方：一个失败的调用删除其声明，而那正是到达供应商的重试。
3. 否则一个容量未耗尽、其平滑桶等待最少的账户；平局按供应商轮转。规则 1 与 2 在解析期间运行（`pinned`）；这一个在 relay 之前立即运行（`assign`），且所选桶的 token 在之间没有 await 的情况下获取，因此一起解析的突发仍分摊到账户而非都读同一个空闲的。

任何非主账户上的调用在其平台绑定上携带 `account: <provider>/<label>`，且 relay 注入那个账户的值，或在账户未配置时失败 `injection_failed`；它绝不替换另一个账户的凭据。主的凭据是部署自己的字段，因此在其上的调用不携带 `account` 且在供应商自己的桶中平滑：一个只有一个账户的供应商行为完全如初。错误 body 掩码覆盖该设置的每个账户的值。

容量是按账户的。一个余额或配额签名打击并只锁定回答了的那个账户（`marks.lock_key(..., slot)`：主保留供应商自己的密钥，进一步的账户 `<key>#<label>`），一个 2xx 只清除它自己账户的打击，且通过锁的探测去到被锁的账户。一个调用只在预留之前被拒，当它的固定账户，或一个开放调用的每个账户，都耗尽时；`assign` 跳过那些。该清扫仍只读主，因此一个进一步账户的锁在其过期时或通过它自己的探测解除，且突发 429 重发留在同一账户。

## 平台容量：预留前拒绝(Platform capacity: refuse before reserve)（计划步骤 D）

目录 `platform_request` 检查与供应商特定的请求守卫只在选择了一个平台 offer 之后、预留之前运行。精确选择器需要证据如 Tavily Search 的调用方提供的 `include_usage: true`。Openmart 需要其显式的有限记录计数；Tavily Map 与 Crawl 需要 1 到 20 的整数 `limit`。缺失、布尔与超范围的值是调用方错误。一个其结果或收费稍后到达调用方 webhook、在响应结算读取之外的请求选项被彻底拒绝：Ocean.io 的 contact reveal，以及 Apollo person enrichment 的 phone reveal、waterfalls、`webhook_url` 与 `poll_only`。BYOK 不变，因为供应商而非 treg 承担那个账户的暴露。

Tier 4 花费 treg 自己的供应商账户，且那个账户可能为空。`_resolve_marketplace_call` 在 `_platform_offer` 说 yes 之后问：这个调用在进程内容量视图（`domain.capacity.view`，由 `resolve_marketplace_target` 在其会话打开之前从 ratestore 以 60 s TTL 加载）中是否 **耗尽**？两个来源如此说：清扫的 `capacity:state:<provider>`（读到零的余额 API）与调用路径自己的锁 `capacity:lock:<key>`（见下）。若是，它抛出 `CallFailure("provider_capacity", 503, blame="treg")`——**在任何 hold 存在之前**——其 body 在已知时携带 `resets_at` 与来自 `_capability_alternatives` 的同能力替代。treg 仍不为调用方选择（charter）：它指名选项。审计行是 `refused_by="capacity"`、`X-Treg-Error: 1`、成本 0。一个陈旧、空或「ok」的视图从不拒绝；只有确认的信号才拒绝。一个其目录成本为 `free`（`marks.spends_balance`）的路由不花费余额，因此对它只有其端点自己的锁（一个配额）算数：清扫的读取与供应商的余额锁既不拒绝它，也不把它作为探测承认，也不把它的 2xx 当作恢复（`metered=False` 经过 `view`、`keyslots`、路由器与 `_note_capacity_recovery`）。一个在零 credits 上回答免费路由的供应商否则会抹掉每个付费路由的打击并解除每个零读取。

调用路径的断路器（`domain.capacity.marks`）开得慢、关得快。在 tier-4 回答 ≥ 400 之后，`settle._note_capacity_signal` 对供应商的状态/头/body 运行 `domain.capacity.signatures.classify`。一个 `balance` 或 `quota` 签名是一个 **打击(strike)**；10 分钟内第二次打击，且至少在第一之后 15 秒（一个同时击中同一空瞬间的并发调用突发是一次打击），之间无 2xx，**锁**——供应商对余额签名，仅端点对配额签名（allowance 按操作）。锁期间，`resolve` 每进程每分钟承认一次真实调用作为 **探测**（`MarketplaceCall.probe_lock_id`、`tool_called` 事件上的 `probe`）；其 2xx 精确清除那个锁（`settle._note_capacity_recovery`，以锁 id 为条件），任何其他答案保留它。清扫的 `exhausted` 读取从读取后一分钟起承认同一探测，且其 2xx 在下次清扫之前解除那个读取（`marks.clear_sweep_state`，以读取的 `observed_at` 为条件），因此一次充值在一分钟内被注意到而非下次清扫。一个猜测的 hold 持续 1 h，供应商声明的 reset 至多 6 h 无论 `retry-after` 说什么，且清扫从不写这个命名空间。这些写入在结算关闭 hold **之后** 于它们自己的短会话上运行，绝不在在途时，且是这个特性添加的数据面写入（`capacity_exhausted_mark` 在 `tests/test_call_architecture.py` 中）。一个突发 429（`retry-after ≤ 60 s`）或未知的一个只记录日志；步骤 D′ 平滑那些。一个 `edge_block`（供应商的 CDN 回答，而非供应商：`cf-mitigated`、其 HTML 阻塞页，或其 1xxx 问题-JSON）不打击任何东西：一个调用方的请求形态绝不能把供应商从每个其他团队那里夺走。该种类随 `tool_called` 事件作为 `capacity_signal`。Tiers 1/2 更早解析且从不咨询视图：一个 org 自己的密钥耗尽是该 org 自己的答案，逐字中继。该供应商在此调用上的 402 也逐字中继——保护是为下一个调用方。一个 `unrecorded` 信号——一个 4xx 没有匹配行但其 body 仍指名 credits/quota/balance——既不是打击也不是标记：它发出一个 `capacity` `unrecorded` 事件带短语（`ops/capacity.md`）并随 `tool_called` 作为 `capacity_signal=unrecorded` 出现，是一个其 out-of-credit 答案尚未在表中的供应商的绊线（Apollo 的 422 如何在 2026-09-01 不被看见）。

## treg 自己密钥上的突发平滑(Burst smoothing on treg's own keys)（计划步骤 D′）

许多调用方共享一个平台密钥，因此 tier 4 制造自己的突发：leadsforge 429 了 27% 的调用，crustdata 34%，带着下游无人能据以行动的 `retry-after` 头。两个有界机制在 `service._execute_call` 中，都 **在 DB 阶段结束后、relay 之前**（池纪律规则在等待期间保持；由测试证明），都仅平台层级，都绝不拒绝：

1. **间隔器(Spacer)** —— `infra/upstream/limiter.py`：每 `window_s / limit` 每供应商一次调用（容量一的 token 桶——t=0 时 `limit` 的突发对经典桶是合法的，且正是滑动窗口供应商 429 的）。一个会超出速率的调用等待 ≤ 2 s（`DEFAULT_MAX_WAIT_MS`），然后无论如何继续；hold 已经放置，因此 org 付延迟，绝不钱。限制来自容量视图（`view.rate_limit`：由清扫从 `CapacityPolicy.rate_limit` 发布，带已验证默认值——leadsforge 120/分钟、leadmagic 300/分钟、crustdata 30/分钟、tikhub 30/s——在第一次清扫之前）。其上游 allowance 不同于其供应商的端点是它自己的桶（`policy._ENDPOINT_RATE_LIMITS`，经 `view.rate_bucket` 读取）；它替换该路由的供应商限制且不从供应商桶抽取。除主外的每个账户有自己的 allowance，因此自己的桶（`<key>#<label>`）。进程内是故意的：第二个副本使有效速率翻倍。同一桶上的共享窗口可以 beside 它在 observe 模式运行（`TREG_PROVIDER_RATE_MODE=observe`，[capacity](../ops/capacity.md)），它记录它会拒绝什么且不拒绝任何东西。
2. **一次有界 `retry-after` 重发** —— 在 tier-4 **429** 分类为 `burst` 且 `retry-after ≤ 5 s`（`SMOOTHING_RETRY_MAX_S`）时，仅 **无 body 的 GET/HEAD**：关闭第一个响应，sleep，在同一 hold 上再次发送相同的 `UpstreamRequest`，在第二个答案上结算。一个配额 429（lusha「Daily」、hunter「per billing period」、任何 `retry-after` > 60 s）、一个未知 429、一个 POST 或第二个 429 逐字中继。对 401/402/5xx 的「无重试」规则成立。

两者都可见：响应上的 `X-Treg-Smoothed: wait=<ms>` 和/或 `retry=1`（仅计量退出）。尚无审计列——`smoothed_ms` 会是对热 `callrecord` 表的 ALTER，一个保留在此行为 PR 之外的迁移级变更。

## Overflow —— 子循环(Overflow - the child cycle)（计划步骤 E；默认关闭）

**Overflow = 同一供应商端点，我们的另一个账户。** 当一个 tier-4 调用因 treg 侧原因在 treg 自己的密钥上失败——一个余额/配额签名、一个突发 429 平滑无法吸收——且 worker 有一个为该端点启用的 `OverflowRoute` 时，`application.call.overflow.maybe_overflow` 在父的结算释放其 hold 之后运行一个 **子循环(child cycle)**：

1. 从进程内路由视图（`domain.capacity.routes_view`，先 Orthogonal）路由，跳过一个标记为不健康的聚合器（容量视图中的 `overflow:<name>`）或无密钥的；对 `OverflowSpend`（`overflow_daily_budget_usd` 每聚合器每天）做预算检查，于一个短会话上。一个部署的 live 值属于其私有运营配置。
2. **子 hold**，自己的 id `{call_ref}:overflow`，经过普通 `_platform_reserve`（标签预算、每日上限、试用 allowance 适用；空余额是普通的 402）。绝不父的 id：按 id 释放是一个条件声明且 `_finish_cancelled_call` 精确释放两个 id 一次。
3. 一个聚合器运行于 **无 DB 打开**：`infra.upstream.aggregators.<name>.build` 包装调用方的原始查询 + 缓冲 body；密钥来自 `Settings.overflow_key_<name>` 且从不记录。Monid 的异步运行被轮询（有界）。
4. `parse` → 供应商状态 + body + 真实的带内成本。`_platform_settle(child, observed_override=cost, overflow_spend=(aggregator, cost − treg 的直接价格))` 收取 **恰好聚合器的价格，0% 加价**，并把当天的花费增量折叠进同一事务——唯一的 allowlisted overflow 写入（`overflow_spend_in_settle`）。
5. 供应商的 body 作为答案返回，`X-Treg-Served-Via: overflow:<name>`、`X-Treg-Cost-Micro` 是子的收费、`X-Treg-Call-Id` 是父的。两个审计行共享 `call_ref`：父的尝试带其真实状态，子带 `credential_tier="platform-overflow"`。MCP `call` 结果携带与 `served_via` 相同的披露外加一个提示（MCP 客户端从不看到头），且 `/catalog/endpoints/{id}` / `catalog_get` 把路由的价格 upfront 显示为 `overflow_price_usd`——见 `architecture/money.md` § Overflow money。

当解析器已经知道账户耗尽（耗尽的视图）**且** 一个路由开启时，阶梯完全跳过直接尝试（`MarketplaceCall.skip_direct`）：无父 hold、无供应商 402，直接到子——计划的 tier 4b。那个父不获得 `payer_org_id`。取消需要在退款之前有已认证调用方的 org，并随之释放子 hold。

Influencers Club 发现/搜索与 similar-creators 路由，以及 Icypeas people search，对每行的直接价格有已验证的平 Orthogonal 价格。它们被一个绝对费用上限（`routes.request_priced`、`$0.03`）而非价格比率承认，且 `route_for` 不应用每请求检查，因此即使一行请求也能 overflow。原始分页/过滤 body 逐字中继，子按聚合器报告的价格结算一次，即使页为空。验证见 `ops/capacity.md`。

**一个聚合器失败是数据。** 它自己的 401/402/403 或一个畸形信封释放子 hold 并把 `overflow:<name>` 标记为对所有人不健康；一个被中继的供应商答案，签名表读作该供应商自己的 out-of-credit 或配额方言（`VENDOR_DRY`：一个 402、Apollo 经 Orthogonal 的 dry Apollo 账户的 422、一个周期 429）释放子 hold 且只标记 `overflow:<name>:<provider>`——一个供应商的 cap 绝不把其他离线。任一标记持续 15 分钟，且调用方得到分类的 `provider_capacity` 503 带替代；同一调用绝不尝试第二个聚合器。聚合器自己的每请求拒绝（`contract`：其更严格的 schema，或 Orthogonal 的无供应商数据的裸 400/422/404）是请求作用域的——它释放子、不收费且不标记；供应商自己的答案成立，且在 skip-direct 阶梯上，那里没有，调用方得到分类的 503 指名拒绝而非装扮成供应商答案的聚合器信封。`malformed` 保留给根本不是信封的东西（非 JSON、一个 5xx、一个传输错误）；一个验证 400 读作 `malformed` 曾让 Orthogonal 为所有 org 离线 15 分钟。

**影子模式(Shadow mode)**（`TREG_OVERFLOW_MODE=shadow`）：聚合器被调用，状态 / 形态 / 成本被记录且探测的成本记入 `OverflowSpend`（treg 付费，预算有界）——调用方仍得到供应商自己的错误且零收费。这是路由服务之前计划要求的那一周。

绝不在 tiers 1/2、调用方导致的 4xx、一个 401、一个超时、PUT/PATCH/DELETE、worker 未启用的路由，或一个选择退出的团队（`Org.platform_overflow_disabled`、`treg org overflow off`）——在联系任何聚合器之前检查，在两个入口点上。

## 控制头隔离(Control-header isolation)

`proxy._is_dropped_request_header` 剥离每个以 `x-treg-` 开头的请求头，包括未来的控制头。`_CONTROL` 列出非前缀的基础设施头。这防止调用方元数据、运行时身份与路由控制到达供应商；测试包含一个发明的前缀匹配头，因此该保证不能退化为一个枚举。

## 调用路径上的异步提交(Asynchronous submissions on the call path)

一个带 `async` 描述符的目录端点像任何其他端点一样解析（`resolve.py` 冻结一个 `settlement_basis`，`when: terminal` 对一个 table、`usage` 或 `per_call` 价格，以及 `MarketplaceCall` 上的描述符）。在 `service._execute_call` 中，这样一个端点的已计量 2xx 被 **推迟(deferred)**（`application.asynctasks.defer_submission` 写待定行并保持 hold 开放）除非 `_submission_rejected` 说 body 不是被接受的提交（非 JSON、`expect` 规则失败、无任务 id），此时它按供应商报告的收费立即结算，否则零，或描述符的 `terminal_on_submission` 在提交本身找到成功词，此时它像同步调用一样在响应上结算；持久化失败释放 hold 并告警。调用方收到的 body 无论哪种方式都是供应商的。在这样的行上一个「仍在工作」的提交是一个任务 id，而非答案，因此归档不为它记录任何东西。`routers/call._attach_async_descriptor` 把 `X-Treg-Async`（有效描述符）加到响应，也在幂等重放上，因此一个重试的 `--await` 轮询已在运行的任务。结算本身是金钱片段的主题。

Tier-4 调用在预留与 relay 之前添加两个刻意不适用于 BYOK 的检查。第一，一个被用作 table 定价判别符且声明为单例目录枚举的 body 字段（例如 OpenRouter 的 `model`）必须等于那个固定值；严格的 JSON 解析拒绝可能使验证与上游解释不一致的重复键。第二，被引用为异步描述符的轮询或获取工具的端点只接受存在于调用方 org 与供应商的 `AsyncTaskRecord` 中的任务/结果 id，带有同样的冻结端点/参数规则。遗留异步对使用目录 `resource_ownership` 元数据与 `AsyncResourceRecord` 做同一检查而不改变其既有结算行为。正式提交把它们轮询/获取 id 镜像进那个表，因此移除一个 live 描述符引用不会使其工具以开放失败；迁移前的待定行仍通过其冻结描述符授权。其生产者来源未被建模的扩展任务消费者通过 `platform_blocked` 被编目为仅 BYOK，而非在共享账户上接受不可验证的任务 id。未知与跨 org id 在不联系供应商的情况下收到同样的 403。获取模式结果 id 从一次授权的成功轮询或 worker 的终端响应学习。BYOK 保留其忠实中继语义，因为那些 id 属于调用方自己的供应商账户。

持久共享账户对象使用独立的目录 `managed_resource` 契约与 `ProviderResource` 表。Create 在持有 DB 连接的情况下中继，然后在返回供应商 id 之前提交所有权；持久化失败触发尽力而为的供应商删除并返回 treg 502 而不暴露 id。Update 仅在上游成功之后改变本地显示状态。Delete 授权活跃或墓碑化的所有权，把拥有的上游 404 当作已删除，然后本地墓碑化，使重试安全。这些规则只在平台密钥层级运行；自有密钥保留普通忠实中继。一个托管的 `use` 声明可能允许供应商公开 id 经一个有界 GET 谓词。本地所有权检查先运行；跨 org 与墓碑化 id 在无上游 I/O 的情况下被拒，而完全未分配的 id 只在 DB 阶段关闭之后、预留金钱之前验证。托管响应仍受同一 8 MiB 完整 body 限制。

一个带显式免费价格与零估计的拥有的平台状态轮询采用 `MarketplaceCall.free_owned_poll` 分支。它绕过一个新的轮询预留与结算，同时缓冲响应供 `observe_owned_poll`，它学习获取所有权并在终端 2xx 证据上终结原始任务。缺失必需的 usage 让 hold 待定；结算错误保留供应商响应供 cron 恢复。轮询读取 live 供应商，不使用或填充可重放缓存，并释放任何调用方提供的幂等标签以便下一次轮询可观察改变的状态。成功与失败轮询保留带 `kind=async_poll` 与零收费成本的诊断审计行；`/calls` 在分页之前排除它们。原始提交在 Activity 中显示共享终结器的结算状态与结果。终端证据归档在该提交的调用 id 下，而非轮询的 id。

## 完整下载与有界响应证据(Complete downloads and bounded response evidence)

`MarketplaceCall.streamable_free_result` 识别带显式免费价格、零估计、一个必需的获取所有权规则、且无异步提交、拥有的轮询或产生的资源证据的平台获取工具。只有成功的 GET 响应绕过 `_buffer_response`；普通的 ownership 检查仍在 relay 之前运行。它们既有的零额预留/结算门保持就位，而完整上游流与头（含 Range 元数据）传递至路由器的 close-once 生命周期。原始生成任务不被下载观察或终结。审计字节大小未知，而非捏造的零。没有 body 被归档或保留用于幂等重放：这些免费读取释放声明，因此重试再次获取供应商。

其他需要结算或所有权证据的响应有一个硬的 8 MiB 完整 body 预算。`_buffer_response` 在第一个溢出块上、在任何成功头之前抛出 `GatewayFailed(response_buffer_limit)`，并在 EOF、异常或取消时在 `finally` 中关闭上游。应用释放 hold/声明并返回 502 零成本；无部分响应到达结算、归档或重放。这是一个显式的大小限制，而非对任意大的已计量 JSON 的支持。故障归因为 treg 的缓冲限制，而非供应商。自有密钥流在此限制之外。`tests/test_call_response_limits.py` 演练两个真实 HTTP 跳、CLI 输出、边界、Range、断开、结算证据、归档与重放行为。

### 内联媒体的假脱机证据(Spooled evidence for inline media)

一些供应商在其 JSON 答案中返回生成的媒体：Gemini 的 `generateContent` 把 base64 图像与一个多 MB 的 `thoughtSignature` 放在 body 中，2K 时约 9 MB、4K 时约 23 MB，其 token 表（`usageMetadata`）在它们之后。流式传输那个答案意味着在响应发送后结算（无精确的 `X-Treg-Cost-Micro`、断开、路由子项与 overflow 重建的第二个 close-once 路径）；提高缓冲会把每次调用数十 MB 放进一个 web 进程。端点反而声明 `spooled_response: true` 且 `_read_evidence` 把其已计量 2xx 交给 `_spool_response`：

- body 流入 `tempfile.TemporaryFile`（从创建起就 unlinked，因此崩溃的 worker 在磁盘上不留任何东西）于 `spool_max_bytes`（64 MiB）与一个每进程 `spool_budget_bytes`（512 MiB，被并发 spool 共享）之下。一个声明的 `Content-Length` 在第一次读取之前整体认领，因此并发答案被整体承认或拒绝，而非都半读卡住；没有则认领逐块增长。越过任一限制在头之前抛出同样的 `response_buffer_limit`（预算拒绝说它是临时的）；上游在 `finally` 中如 `_buffer_response` 关闭，含临时文件创建。
- 文件用 stdlib `json` 解析一次（在 23 MB Gemini 答案上测量：约 30 ms、约 45 MB 峰值；最坏约 body 的三倍）于一个 worker 线程，每进程至多 `spool_parse_concurrency`（2）。只有该行结算读取的路径存活（`_spool_evidence_paths`：每个 usage 项的顶层对象与 `expect` 叶子，保留在其原始位置，例如 `{"candidates": [{"finishReason": "STOP"}]}`），重新序列化为每个后续消费者看到的 `body`：usage 结算、结果分类与容量签名。非 JSON 对象的 body 产生空证据；一个 `usage` 基础随后按其预留结算。
- 结算随后完全如缓冲 body 一样运行，在响应开始之前，且路由器以 256 KiB 读取中继文件，带供应商的头与重新计算的 `content-length`。重放的关闭归还预算；`weakref.finalize` 对未关闭就丢弃的响应也如此。
- 一个 spooled body 不被归档也不为幂等重放存储；其审计行记录完整大小。非 2xx 答案、自有密钥调用与路由子项（其父读取子的 body）保留其既有路径。`tests/test_call_spool.py` 覆盖生命周期（超大、预算、重置、取消、垃圾回收、解析门）且 `test_call_response_limits.py` 覆盖两个真实 HTTP 跳上的 20 MB Gemini 形答案。

## HarvestAPI 集成(HarvestAPI integration)

目录条目可以选择加入 `strict_query`：`_enforce_catalog_query` 在凭据选择之前拒绝 body、未声明/重复的查询参数、缺失的必需输入与不支持的枚举值。一个声明的路径占位符被允许通过这个检查并在 relay 之前消费；未声明的查询字段仍被拒。它们可以分别选择加入 `body_allowlist`：`_enforce_catalog_body` 拒绝未声明的顶层 JSON 字段、缺失的必需字段、无效的声明标量值，以及超出其声明基数或项枚举的数组。一个对象数组可能要求每个命名的项字段或至少一个命名的项字段而不重写该项。一个省略的可选数组被允许；其基数只在调用方提供它时适用。两个检查适用于每个层级的目录调用，保持未标记的条目不变且不约束任意原始自有工具中继。遗留 `resource_ownership.requires` 接受声明的 body 参数以及路径/查询参数，允许一个 POST 状态工具授权一个不透明的共享账户任务 id。

## 固定的共享供应商读取(Pinned shared-provider reads)

`_enforce_platform_async_ownership` 把 `pinned_tag_predicates` 加到其 org 作用域的任务与资源查询。所有 pin 必须匹配提交快照；一个固定的未知/外部 id 在 relay 之前返回 404。BYOK 与原始自有工具访问保留其既有的凭据 ACL。共享供应商 `Idempotency-Key` 重写额外包含完整的强制 pin，因此不同客户无法通过供应商去重接收一个上游作业。未固定的摘要不变。`intake.prepare_call_intake` 在 Treg 的成员重放命名空间中包含同一完整 pin。历史与账本作用域见 [multi-tenancy](multi-tenancy.md#caller-tags-and-pinned-read-scopes)。

## 可选的已发布根准入(Optional published root admission)

共享 `run_call_surface` 在身份与上下文创建之后、财务准入之前检查 [已发布 Org 流控制](org-flow-control.md)。一个有效快照提供暂停、速率与并发检查。它可以用 429 拒绝新的根调用，针对一个活跃有效的暂停、一个耗尽的速率桶或一个满的已发布并发限制。速率与并发拒绝既不消耗 token 也不消耗槽；准入时已花费的 token 在后续失败或取消后不退款。Redis 失败允许调用；缺失键清除缓存规则，且畸形或冲突的发布保留先前有效的快照与原始暂停过期。既有的已接受工作与其财务清理继续。这个可选的默认关闭检查不覆盖共享表面之外的直接 hub、供应商资源或后台执行。

## 多个 treg 拥有的账户（补充）

（见上文「一个供应商背后的多个 treg 拥有账户」一节；本节内容已并入该处。）
