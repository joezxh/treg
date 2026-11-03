---
title: 已发布组织的暂停、速率与并发准入
status: shipped
sources:
  - src/treg/infra/org_flow_control.py
  - src/treg/infra/structured_logging.py
  - src/treg/infra/kv.py
  - src/treg/config.py
  - src/treg/routers/call.py
  - tests/test_org_flow_control.py
  - tests/test_org_flow_control_reader.py
  - tests/test_org_flow_control_redis.py
  - tests/test_org_rate_limit_redis.py
  - tests/fixtures/org-flow-control/generate.ts
related:
  - architecture/org-concurrency.md
  - architecture/money.md
  - architecture/proxy-model.md
  - ops/deploy.md
---

# Published organization pause, rate and concurrency admission（已发布组织的暂停、速率与并发准入）

精确的一次性 org/端点调用配额使用独立的 [quota store](org-endpoint-quota.md)。这些临时配额允许在未知 Redis 状态下调用，包括此前被限制的目标；它们不修复缺失的计数器。下面这些仅根、会过期且缓存的准入策略不适用于它们。

`org_flow_control.check` 在 `routers.call.run_call_surface` 读取运营者发布的 Redis 快照，位于可信 Caller/上下文解析之后、可选的 Org 速率/并发门、金钱准入、body 消费或上游工作之前。它适用于与 [Org 并发](org-concurrency.md) 相同的根面：`/call/`、`/catalog/call/`、`/table/` 以及使用它们的 MCP 适配器。直接的 hub 运行、provider-resource 请求与应用/后台调用仍在此门之外。鉴权查询发生在它之前。

一次读取器检查返回针对**暂停、速率与并发**的有效快照。一个活跃的暂停立即拒绝。否则 `org_concurrency.acquire` 应用一个非空 `rate_limit` 和/或 `concurrency_limit.max_in_flight`。当配置了速率时，一个 Redis Lua 操作在消费任一之前检查令牌桶与可选的共享槽位限制。每个空字段只禁用那一个限制，没有静态回退。一个快照观察不是对每个 worker 都已应用它的确认。

## 配置与发布契约

默认关闭；启用需要一个显式有效的 Redis `TREG_KV_URL`，指向与发布者相同的数据库。没有本地存储替代，此路径上也没有 PostgreSQL 读。

```sh
TREG_ORG_FLOW_CONTROL_ENABLED=false
TREG_ORG_FLOW_CONTROL_REFRESH_S=2
# 在启用之前 privately 设置 TREG_KV_URL。
```

刷新间隔是 0.2–10 秒。读是惰性的，按活跃 Org/worker；一个安静的 worker 不轮询也不确认一个版本。间隔后的一次请求执行一次有界刷新；没有后台监视器或发布者。

键是 `treg:traffic-control:org:<org_id>`，包含完整的 JSON 信封：

```json
{
  "org_id": 42,
  "version": 1,
  "config": {
    "schema_version": 1,
    "pause_until": null,
    "rate_limit": null,
    "concurrency_limit": null
  }
}
```

所有字段都是必需的。未知字段、重复键、错误的 Org ID、不支持的版本、被胁迫/布尔数字、无效限制以及非 UTC 暂停时间戳都被拒绝。读取器不写、不过期、也不删除已发布的键。一个发布者必须使用更高的版本来更改或恢复内容；清除一个暂停意味着在一个新的完整版本中发布 `pause_until: null`。清除速率或并发意味着 `rate_limit: null` 或 `concurrency_limit: null`；暂停在它的绝对 UTC 时间独立过期，与那些字段无关。仅一次配置保存不会发布或激活那个版本。在部署会强制执行它们的 worker 之前，审查既有的非空速率与并发值。见 [并发迁移](org-concurrency.md#configuration-migration-and-rollback) 了解被移除的环境设置与授权的发布序列。

`tests/fixtures/org-flow-control/` 中的合成 fixture 捕获参考发布者的实际 `publish` 序列化，覆盖关闭的控制、亚秒级 UTC 时间戳、已填充的限制与一次恢复。消费者的严格验证不变。

## 原子速率与并发准入

一个非空 `rate_limit` 包含 `rps`（正数、有限的每秒请求数，允许分数）与 `burst`（一个正整数令牌容量），例如 `{"rps":2,"burst":4}`。每个被接受的根请求消耗一个令牌；令牌持续补充直到 `burst`。该桶跨该 Org 的 API key 与 worker 在 `treg:org-rate:v1:<org_id>` 共享，独立于配置版本。一个缺失的桶从满开始。一个版本变更、暂停或并发更新不授予一个新的 burst。

Redis 操作使用微秒分辨率的 `TIME`。它用存储的先前速率补充一个既有桶，然后把令牌夹到传入的 burst 并记录传入的速率。那些元数据与补充更新也发生在拒绝时，不消耗令牌也不添加槽位。脚本只在两个配置限制都通过时才准入，然后消耗一个令牌，并在配置时插入唯一拥有的槽位。一个并发拒绝绝不消耗速率令牌；一个速率拒绝绝不创建槽位。没有等待队列。

桶过期不早于它会变满的时间，包括任何来自 Redis 时钟回滚的延迟。如果一个非常小的速率无法表示一个安全的 TTL，桶保持持久而非提前过期。`rate_limit: null` 绕过桶；它不重置它。Worker 在既有刷新窗口期间仍可以应用一个更旧的有效缓存配置；桶不添加第二个版本权威或全员 worker 激活屏障。

速率令牌计入通过了这些检查的准入尝试。它们在应用失败、取消或模糊的 Redis 回复之后不被退还；因此一个丢失的回复可能消耗一个令牌而不运行该调用。这避免了让取消或重试成为配额绕过。任何可能已获取的并发所有者仍通过既有的所有者安全路径被清理。

## 拒绝与失败

一个未来的 `pause_until` 返回 HTTP 429、`Retry-After` 从剩余秒数向上取整，以及带 `config_version` 的 `detail.error=org_traffic_paused`。UTC 过期在每次请求上检查，独立于刷新时序。保留普通的 call-ID、错误头部与拒绝审计处理；MCP call/media 响应保留重试指导。

只有有效的、未过期的暂停、耗尽的速率桶，或在有效发布的并发限制下的争用会拒绝新的根。速率耗尽返回 HTTP 429 `org_rate_limit` 与 `Retry-After` 等于令牌缺口除以 `rps` 的上限（加上任何保留的时钟回滚延迟），至少一秒且上限为 2147483647 秒。并发争用返回 HTTP 429 `org_concurrency_limit`、`Retry-After: 1`。两者都包含 `retry_after_s` 与 `config_version`；重试指导不预留未来容量。刷新失败遵循这些策略：

| 刷新结果 | 准入行为 |
| --- | --- |
| Redis 连接性、初始化或超时失败 | 允许，绕过缓存的暂停、速率与并发，直到后续刷新。保留快照用于恢复与版本比较。 |
| 健康的缺失键 | 清除本地快照并把该 Org 当作未配置的第零版。 |
| 无效 JSON、错误类型、超大或不可解码数据 | 保留之前有效的快照，包括它的速率/并发限制与原始暂停过期；若无则允许。 |
| 更低版本或同版本下变更的内容 | 保留之前有效的快照，包括它的速率/并发限制与原始暂停过期。 |

`kv.FlowControlReadFailure` 区分无效数据与传输不可用；`None` 意味着缺失，字符串是有界载荷。一个被取消的读传播取消而不改变共享快照、可用性或刷新截止。下一个调用方或等待的请求可以立即刷新；取消绝不变成 HTTP 503。

快照刷新与组合的速率/槽位 Redis I/O 有 200 ms 截止。每 Org 单飞与一个 32 读的 semaphore 限制刷新工作；失败被缓存直到下一个间隔。worker 最多有 4096 个 LRU 条目，保护活跃的暂停、配置的速率/并发限制，以及有活跃调用方/等待方的条目。如果没有条目可被驱逐，未缓存的 Org 被允许，不添加条目也不读 Redis，带一个有界容量警告。读 Redis 期间不持有任何 DB 连接。速率/槽位初始化、获取与超时失败也允许新工作，无需已确认的令牌或并发槽位；只有显式配置的限制拒绝。没有 Redis 失败被这些守卫转换成 HTTP 503。

已接受的工作永不再被检查：流、结算、释放与取消清理通过它们既有的路径完成。关闭该标志使用正常的部署流程，且不取消已接受的工作或擦除 Redis 数据。

## 证据与恢复边界

单行 `org_flow_control_version_observed`、`org_flow_control_paused` 与 `org_flow_control_config_unavailable` 记录携带 worker PID、可信 Org、调用引用、版本、兼容字段 `capability=pause`，以及 `capabilities=["pause","rate","concurrency"]`。版本观察包含 `max_in_flight` 与一个 `rate_limit` 对象，各自在禁用时为 null。这些能力描述读取器支持的准入检查，而非成功的槽位获取或全员 worker 的确认。记录省略原始配置、凭据与异常文本。它们使用 [Org 流量日志](org-traffic.md) 中描述的 scoped plain handler，继承既有的 logger 级别，并保留显式配置的具名 handler。根日志不被改变；根 handler 路由与过滤器不适用于默认事件汇。暂停事件与刷新警告各自每 Org 每五秒限制为一个；下一个事件报告该事件类别的 `suppressed_since_last_log`，可能跨版本或失败原因。一个条目被驱逐或 worker 退出时剩余的计数会丢失。容量警告每 worker 每五秒限制为一个。普通请求日志仍描述每个请求的结果；抽样的暂停事件不是一个完整的拒绝计数。观察是按 worker 且按需的，而非心跳或完整的 worker 确认集。速率拒绝发出 `org_flow_control_rate_limited`，带可信 Org、配置版本、`rps`、`burst`、重试指导与一个空调用引用。这些结构化的单行事件每 worker 每五秒限制为一个，带 `suppressed_since_last_log`。这一聚合跨 Org 与版本；使用请求日志与它们的 429 结果获取完整的拒绝计数。

版本保护只与驻留缓存一样持久。重启、驱逐与一个健康的缺失键会遗忘历史。一个冷缺失键无法区分一个未配置的 Org 与丢失的 Redis 数据。在启用/重新启用 worker 之前恢复已发布的键；读取器在丢失它自己的水位（watermark）后无法检测一个更旧的有效的 Redis 备份。Redis 桶丢失、驱逐、重启或故障转移同样可以恢复一个完整的 burst；这是一个面向可用性的守卫，而非持久的计费配额。
