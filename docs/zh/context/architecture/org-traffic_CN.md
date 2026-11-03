---
title: Process-local organization traffic logs（进程局部组织流量日志）
status: shipped
sources:
  - src/treg/infra/org_traffic.py
  - src/treg/infra/structured_logging.py
  - src/treg/bootstrap.py
  - src/treg/routers/call.py
  - src/treg/routers/table.py
  - src/treg/mcp.py
  - src/treg/application/call/types.py
  - src/treg/application/call/service.py
  - tests/test_org_traffic.py
  - tests/test_org_concurrency.py
related:
  - architecture/org-concurrency.md
  - architecture/composition.md
  - architecture/proxy-model.md
---

# Organization traffic logs（组织流量日志）

`org_traffic.RequestLogMiddleware` 为每个 `/call/`、`/catalog/call/` 与 `/table/` 请求发出一行应用拥有的 `request` JSON。既有的 Uvicorn 传输访问日志没有解析出的 Caller，且被 MCP 的进程内 HTTP 客户端绕过；Render 边缘日志在应用控制之外。这个刻意很小的应用日志覆盖 HTTP 与 MCP 两个根。`structured_logging.get_logger` 仅为具名的 `treg.org_traffic`、`treg.org_flow_control` 与 `treg.capacity_events` 事件 logger 提供一个纯 stderr handler，当它们没有配置 handler 时。它们的级别仍继承自 `treg` 或 root；不更改任何 root 级别、handler 或格式。默认 handler 防止通过 MCP 的 root console 格式化器进行包裹与重复传播。因此 root handler 路由、过滤器与格式化不适用于这些流。在具名 logger 上配置 handler 与过滤器以自定义它们的目的地；既有的具名 handler、级别与传播设置被保留。自定义格式化器应保持每个 JSON 记录在一行物理行上。它包含一个固定的 surface/adapter 标签、worker PID、可信的 `Caller.org_id` 与 `api_key_id`、服务端生成的 `call_ref`、HTTP 方法、解析出的工具/端点、状态、结果与 handler 持续时间。`failure_kind` 通过请求状态复制既有的 `tool_called` / `call_intake_failed` 事件属性，包括 caller 解析之前或之后的 `db_pool` 与 `unexpected_exception`。当没有事件分类可用时（包括成功的调用）它为 null（或针对 MCP 预检省略）。它仅是一个 JSON 字段，没有额外的日志标签或计数器维度。API key ID 来自解析出的 Caller；没有托管 key 的会话与未解析的鉴权记录 `api_key_id: null`。`call_ref` 来自完成时的请求状态，包括由拒绝处理生成的 ID；没有分配 ID 退出的记录 null。它标识这个根调用上下文：一个幂等重放可以在其响应中返回原始调用 ID，而此日志保留新上下文的 ID。`replay_of` 从服务端拥有的重放结果记录那个原始 ID，或缺失时为 null。`CallContext` 在既有解析期间快照 `tool_name` 与 `endpoint_id`；路由用 `describe` 复制这些标量，包括失败时。Catalog/路由调用保留被请求的端点；一个解析出的底层工具提供它的名称，否则使用已知的 catalog 或 hub 名称。一个同名的自有工具保留它自己的身份，没有猜测的 catalog 端点。未知目标、解析之前的退出，以及幂等重放把未解析的目标字段留为 null；用 `replay_of` 找原始调用。没有仅为填充日志而添加的查找。

`method` 是标准 HTTP 方法或 null；一个 MCP 适配器预检没有 HTTP 方法。`provider`、`credential_tier` 与 `refused_by` 是根调用的审计事实，以同样方式复制：catalog 行的 provider、哪个凭据应答了（`platform`、`credential`、`tool`、...）以及 treg 自己的拒绝种类（`capacity`、`balance`、`request`、`policy`、...）。一个在解析或鉴权期间被拒绝的 catalog 调用有一个 provider 与拒绝但没有层级；一个由 overflow 应答的调用记录 `platform-overflow` 且没有拒绝，是调用方得到的答案而非直接尝试。自有工具与未解析目标记录 null。一个路由或 hub 根不命名 provider：它的 children 是带独立审计行的独立调用。它们让仅从这些行就能读出 treg 自己账户上的每供应商成功率。不添加任何路径、查询字符串、头部、IP、用户代理、用户名、邮箱、凭据值、请求/响应 body 或异常文本。调用方提供的身份头部绝不用于归因。新字段不添加计数器维度或改变日志前缀。

`mcp_adapter` 标记 `_call_impl` 与 `_call_media_impl`（包括目录适配器）。它们底层的 HTTP 根拥有单条请求日志与计数器；成功的 MCP 信封也都不添加。适配器预检退出与急切的 MCP HTTP 401 挑战记录一个 null org 且不被聚合：它们尚未带着可信 Caller 进入共享 handler。功能关闭的 HTTP 面可以记录它们解析出的 org 但不增加 handler 到达数。路由、验证、overflow 与 hub children 直接调用 application 且绝不增加这些根计数器。直接的 `/hub/run`、provider-resource、Arena 与后台工作在此范围之外。

## 窗口与生命周期

`run_call_surface` 在 caller 解析之后立即于进入时调用 `identify(..., enter=True)`，在上下文创建与 Org 暂停/速率/并发准入之前。`requests` 计数这些到达，包括守卫拒绝。鉴权/适配器预检时间被排除。在途（in-flight）度量与延迟在根 ASGI 调用返回或抛出时结束，位于 body 传输、上游关闭，以及 awaited 财务清理之后。中间件不添加任何 await、缓冲、响应包裹或清理任务，并重新抛出原始异常/取消。

`completed`、`status_429`、`status_503` 与延迟直方图计数**完成**窗口中的终态退出，即使到达是在更早的窗口。因此 `completed` 是延迟与状态率的分母；它可能超过 `requests`。取消与错误也是终态退出。状态是已开始 HTTP 状态，否则未处理异常为 500，或在任何响应之前取消时为 null。一个已开始的 200 失败流保留状态 200 并记录 `outcome: error` 或 `cancelled`；不发送合成 HTTP 状态。

每个 all/dataplane worker 每 60 秒发出一行 `org_traffic_top`，即使为空，来自一个由它的 app 生命周期拥有的引用计数事件循环计时器。重叠的生命周期共享它；最后一个关闭取消它。没有周期性的 asyncio 任务、Redis/DB 调用、指标后端、端点或设置。可观测性失败是尽力而为，不能替代响应、拒绝或异常。如同任何事件循环计时器，停顿可以延迟名义上的 60 秒窗口；`window_end_unix_s` 与连续的日志时间暴露这一延迟。进程退出丢失部分窗口。

`Counters.snapshot` 按到达数排名（平局：升序 org ID），最多发出十行，重置窗口计数器并移除不活跃的 org。它跨窗口保留实际的活跃请求，并用该活跃计数播种每个被保留 org 的下一个 `in_flight_max`。因此一个被携带的请求可能以零到达与非零峰值/完成计数出现。

存储被限制为 `MAX_ORGS=4096` 个身份与每 org 33 个计数器，绝不为单独的延迟样本。超出上限的新身份在被滚动腾出空间之前不被跟踪；活跃身份绝不驱逐。任何非空的 `overflow_requests`、`overflow_in_flight` 或 `overflow_completed` 明确意味着摘要是部分的，包括未跟踪的工作跨窗口时。这三个溢出总计不保留额外的 org 身份。每请求日志仍包含每个解析出的 org，包括溢出的 org。Top 10 在被跟踪 org 中是精确的；如果发生溢出，使用请求日志。

`p95_ms` 是终态 handler 持续时间的近秩（nearest-rank）第 95 百分位，报告为直方图桶的**上界**：1、2、4、... 2^31 毫秒。它可能高估最多两倍。在最后一个溢出桶中的秩，或没有完成，返回 null。此方法每次请求使用常量工作与存储，并包含取消/失败的请求。

## 读取日志

示意性合成示例（省略普通 logger 前缀）：

```text
request {"worker_pid":123,"surface":"call","adapter":"call","org_id":42,"api_key_id":7,"call_ref":"0123456789abcdef0123456789abcdef","status":503,"outcome":"completed","failure_kind":"db_pool","method":"GET","tool_name":"example","endpoint_id":null,"replay_of":null,"provider":null,"credential_tier":null,"refused_by":null,"handler_ms":800.2}
request {"worker_pid":123,"surface":"call","adapter":null,"org_id":42,"api_key_id":7,"call_ref":"fedcba9876543210fedcba9876543210","status":503,"outcome":"completed","failure_kind":null,"method":"GET","tool_name":"example.read","endpoint_id":"example.read","replay_of":null,"provider":"example","credential_tier":null,"refused_by":"capacity","handler_ms":4.1}
request {"worker_pid":123,"surface":"mcp","adapter":"call","org_id":null,"api_key_id":null,"call_ref":null,"method":null,"tool_name":null,"endpoint_id":null,"replay_of":null,"provider":null,"credential_tier":null,"refused_by":null,"status":null,"outcome":"preflight","handler_ms":null}
org_concurrency rejected org_id=42 limit=8 config_version=3 status=429
org_flow_control_rate_limited {"worker_pid":123,"org_id":42,"call_ref":null,"capability":"pause","capabilities":["pause","rate","concurrency"],"status":429,"config_version":3,"rps":2,"burst":4,"retry_after_s":1,"suppressed_since_last_log":0}
org_traffic_top {"worker_pid":123,"window_s":60,"overflow_requests":0,"overflow_in_flight":0,"overflow_completed":0,"top":[{"org_id":42,"requests":120,"completed":118,"in_flight_max":8,"status_429":3,"status_503":2,"p95_ms":1024}],"window_end_unix_s":1800000060.0}
```

查看跨所有服务实例/worker 的一两个最近的 `org_traffic_top` 间隔，以找出驱动到达、峰值或 503 的 org，然后按 `org_id` 过滤 `request`、`org_concurrency rejected` 或 `org_flow_control_rate_limited`。把日志平台的实例/进程身份与 `worker_pid` 一起使用；单独的 PID 在容器之间不是唯一的。按时间戳对齐窗口（worker 窗口不同步）。对所选窗口中同一 org 的请求、完成与状态计数求和。Top-10 截断意味着这些跨 worker 的求和是下界，且可能漏掉低于每个 worker Top 10 的 org；请求日志提供完整的归因。对每 worker 峰值求和是对同时全局并发的上界，因为峰值无需重合。**不要添加或平均 p95**：一个全局百分位需要底层持续时间（在请求日志中作为 `handler_ms` 可用）或合并的直方图，这是此摘要不导出的。这些是调用 handler 度量，而非 DB 连接占用、供应商扇出或端到端鉴权延迟。

速率限制事件每 worker 每五秒最多聚合一次，跨 Org 与版本；它的抑制计数不是 Org 特定的拒绝计数。请求日志与 `status_429` 总计仍包含每个终态拒绝。见 [已发布准入](org-flow-control.md#evidence-and-recovery-boundaries) 了解读取器与暂停事件抽样。
