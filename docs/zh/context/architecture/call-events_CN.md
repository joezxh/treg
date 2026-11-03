---
title: Call events — 每次调用一个伪匿名事件，写入 Postgres 之外的 Iceberg 表
status: building
sources:
  - src/treg/call_events.py
  - src/treg/application/call_events.py
  - src/treg/catalog/contracts.yaml
  - tests/test_call_events.py
---

# Call events（调用事件）

catalog 端点的基准（一个 finder 多久找到一次、它找到的东西之后多久被验证、两个供应商在同一问题上如何比较）是对数月调用的批量读取。它们不属于生产数据库：`callrecord` 很大、一个路由父级没有结果列、`params_hash` 按端点、且把一个 find 的答案连接到一个后来的 verify 意味着重新解析已归档请求并从对象存储读取 body。调用事件按每次调用携带这些读取恰好需要的东西，写入一个 Apache Iceberg 表（一个 Cloudflare Pipelines 流，带一个 R2 Data Catalog 汇）。不碰 Postgres：调用路径上没有表、列或查询。

## 保证

- **除非配置否则关闭。** `TREG_CALL_EVENTS_URL` 与 `TREG_CALL_EVENTS_HMAC_SECRET` 必须都设置；否则什么都不构建或排队。`TREG_CALL_EVENTS_TOKEN` 在流需要鉴权时作为 bearer 发送。
- **绝不挡调用路。** `emit` 是同步的，不取锁、不开会话、绝不抛出。它排队一个已在手中的列的小字典加一个构建器；构建器（解析请求与答案 body 并对标识符哈希）在一个每进程唯一的 flusher 任务中运行。与 `audit.py` 和 `analytics.py` 相同形态：有界队列（`_MAX_PENDING`）、对等待的构建器保持存活的东西的限制（`_MAX_RETAINED_BYTES`：body、查询字符串，以及一个路由父级的 caller body 与按已知大小的组装答案；超出后该事件不带输入/答案列出去）、批 POST、在溢出、失败或一个抛出的构建器上丢弃并计数（`call_events.counters`，在第一次丢弃与每千次记录到 ERROR）。丢失一个事件代价是一个样本，绝不是金钱、响应或 hold。
- **重试，然后丢弃。** 一个瞬时的 POST 失败（超时、传输错误、429、5xx）以退避重试两次；一个拒绝（其他 4xx）不重试。一旦一个批次耗尽它的重试，后续批次各得一次尝试直到一个落地，因此一个流中断绝不因退避而让 flusher 停滞。关闭以每批次一次尝试排空。
- **可能重复；在 `event_id` 上去重。** 一个超时的尝试仍可能已被流接受，因此它的重试可能让同一批次落地两次。每个事件携带一个唯一的 `event_id`；读取方计数不同的 id。
- **损失可度量。** 每个进程每五分钟记录它的累计计数器（`call events stats: pid=… pending=… queued=… sent=… retried=… dropped_failed=…`），并在关闭时记录一次。每进程的损失率是它最新一行中的 `dropped_* / queued`。
- **伪匿名。** 不发出原始邮箱、姓名、域名、电话或 URL。标识符在服务端密钥下做 HMAC-SHA256（32 个十六进制字符），因此没有密钥就无法测试一个猜测的地址。一个选择退出归档的团队（`Org.archive_opt_out_at`）没有答案列；它的输入键保留，因为需要它们来按问题计数它的调用且不携带任何可读内容。
- **每个异步任务恰好一个终态事件**（一个 `event_id`；一个重试的 POST 可能存它两次）。见下。

`archive_key_hash` 与 `archive_content_hash` 是归档自己的身份（纯 SHA-256，非密钥），被携带以便一个样本可以追溯它的存储 body。

## 事件在哪里发出

| 站点 | 种类 | 备注 |
|---|---|---|
| `service._audit`（每个解析出的 catalog 调用：直接、路由 child、check、poll） | `call` / `async_submit` | 输入来自通过适配器读回的供应商请求；答案来自缓冲的 body |
| `service` marketplace 拒绝（未解析的 catalog 调用） | `call` | 仅通用列 |
| `service._routed_event`（每个路由父级一次，在 `run_routed` 返回或抛出之后） | `call` | 输入来自 caller 的字段；答案来自路由器的核心输出；`served_by`、`tried_count`、`check_verdict` 来自 `CallContext.route_summary` |
| `asynctasks._finish_terminal`，以及 worker 超时 / 退役账户释放 | `async_terminal` | 答案来自终态 poll body |

自有工具与 hub 运行不发出它们自己的（一个 hub 步骤是一个普通的 catalog 调用且作为一个发出）。overflow children 尚未发出。一个答案通过无缓冲流式传输的自有 key 调用没有答案列，因为它在 `callrecord` 中没有 `hit`。

## 链接

`call_ref` 是调用的 `X-Treg-Call-Id`。一个 child 的 ref 是它父级的加一个步骤（`:rN` 瀑布尝试 N、`:v` check、`:pN` 路由 poll、`:sN` hub 步骤）；事件携带从它解析出的 `parent_ref`、`step` 与 `waterfall_position`。一个异步任务的提交（`async_submit`）与它的结果（`async_terminal`）共享提交的 `call_ref`；终态事件携带 `hit`、`verdict`、`cost_charged_micro`（任务结算于的价格；提交的为 null）、`async_outcome`（`success`、`failure`、`billed_failure`、`timed_out`、`account_retired`、`closed_hold`）与答案列。它的输入位于提交事件。`_finish` 在任务行锁下把任务移出 `pending` 一次，以 caller 的 poll（`observe_owned_poll`）与 worker 谁先看到答案为准，且只有那个转换发出，因此一个延迟的重读不发出任何东西。

## 列

每个能力一张表。通用列：`schema_version`、`event_id`、`event_time`、`event_kind`、`org_id`、`client`、`capability`、`endpoint_id`、`provider`、`credential_tier`、`call_ref`、`parent_ref`、`step`、`waterfall_position`、`is_eval`（列在 `TREG_CALL_EVENTS_EVAL_ORGS` 中的团队）、`status_code`、`refused_by`、`hit`、`verdict`、`cached`、`cost_estimated_micro`、`cost_charged_micro`、`upstream_ms`、`duration_ms`、`served_by`、`tried_count`、`check_verdict`、`async_outcome`、`archive_key_hash`、`archive_content_hash`、`adapter_fingerprint`（适配器定义的 12 位十六进制，因此映射的变更显示在数据中）。一个没有值的列从事件中省略而非作为 null 发送，因此它读作 SQL NULL（一个 `json` 列中的 JSON null 会作为字符串 `'null'` 存储）。

能力特定的数据在字符串键的映射中携带，因此一个新能力不需要表变更。该流没有映射类型；它们作为 JSON 对象（`json` 列）传输：

- `input_type` 命名问题以之表达的契约身份变体，`input_id` 是那个变体的归一化值的 HMAC。它在派生之后（`canonical_identity`）从契约身份计算，绝不从供应商请求的形状。一个直接调用通过它的适配器的 `in` 映射加任何恰好命名为身份字段的请求参数读回（一个发送 `full_name` 的 finder 可能用 `first_name` + `last_name` 调用）。Caller 的 `first_name`+`last_name` 派生 `full_name`，因此 `{full_name, domain}` 与 `{first_name, last_name, domain}` 对一个直接 finder、一个路由 child 或路由父级的询问给出一个 `input_id`。
- `input_keys` — 派生后存在的每个身份字段的 `{field: hmac}`。
- `input_meta` — 非敏感段：`domain_class`（`company`、`webmail`、`edu`、`gov`）与输入域（或邮箱的）的 `tld`，加任何声明了 `analytics: value` 的过滤器。
- `answer_keys` — 声明了 `analytics: key` 的输出字段的 `{field: hmac}`。
- `answer_values` — 声明了 `analytics: value` 的输出字段的 `{field: value}`，作为字符串（最多 256 字符），恰好如适配器产生的那样。
- `answer_flags` — 从 email 形键派生：`is_role`、`free_mail`，以及当输入命名了一个域时的 `domain_match`（对于 `email` 以外的字段前缀 `<field>_`）。同一 `domain_match` 比较作为 `_treg.domain_match` / `X-Treg-Domain-Match` 披露给调用方在一个路由的 email-find hit 上（见 [catalog.md](catalog.md)）；此事件标志保持分析形态。

一个输出字段去哪由契约（`contracts.yaml`）声明，默认 `skip`：

```yaml
output:
  email: {type: str, required: true, analytics: key}
  verified: {type: bool, analytics: value}
```

解析器拒绝任何其他的词，且一个过滤器绝不能是一个 `key`。公开 catalog 契约不显示该注解。

段字段（2026-10）：公司 `industry`、`employees`、`founded` 与 HQ `location`；公司的域或网站作为键，因此一个 `companies.enrich` 答案在同一个域上连接一个 find；一个人的 `location` 与公司域；电话国家与线路类型；搜索 `country` 过滤器。值作为供应商写的那样存储且在此不解析：国家、地区与大小桶在分析时派生（数据湖 ETL），因此一个更好的解析器可以重读旧事件。

**隐私。** 标识符（邮箱、姓名、域、电话、URL、LinkedIn 句柄）只作为 HMAC 键离开。`answer_values` 不是无标识符的：一个人的 `location` 可以命名一个城市，且紧挨那个人密钥的它是个人数据。它是有意保留用于分析的。绝不注解为值：姓名、公司名、描述、`about` 文本、关注者计数、列表。Iceberg 对 `analytics.call_events` 的保留必须在此增长之前设置并记录。

哈希前的归一化：邮箱小写化；域无 scheme、路径或 `www.`；LinkedIn URL 与句柄缩减为小写句柄；其他文本大小写折叠并折叠空格。因此一个 find 的 `answer_keys['email']` 等于一个后来 verify 的 `input_keys['email']`。

## 未构建

每能力基准表之后从这一张表批量派生。这里不读回该表。
