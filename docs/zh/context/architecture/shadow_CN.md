---
title: Shadow provider — 候选供应商在事后被问与已服务调用相同的问题，并做比较
status: building
sources:
  - src/treg/domain/catalog/shadow.py
  - src/treg/application/shadow.py
  - src/treg/alembic/versions/0086_shadow_pairs.py
  - tests/test_shadow.py
related:
  - architecture/catalog.md
  - architecture/search-experiment.md
---

# Shadow provider（影子供应商）

一种在任何客户看到之前，用真实流量衡量候选供应商的方式：它多久应答一次、它的答案与 treg 所提供的答案多久一致一次、它多快、以及它会花多少钱。关于该候选的一切都不在公开目录中；它仅由一个私有的 `shadow_provider` 设置描述，而一个空设置会把整件事关掉。

## 它如何运行

- `treg-worker shadow collect`（一个 cron）在其游标（`ShadowCursor`，一行）之后读取新的 `CallRecord` 行。第一次运行只记录最新的调用 id，因此历史永不被读取。
- 当一次调用的端点有一个路由适配器，且其能力在设置中被命名时，才考虑该调用。调用按能力采样（`sample`，默认全部），通过一个带盐的调用 id 哈希。
- 已服务的请求与答案来自归档，经由竞技场（arena）收集器所用的同一个读取器（`application.arena_insights._evidence`）。因此一个选择退出归档的团队永远不会被配对。
- `domain.catalog.shadow.request_identity` 通过已服务适配器的纯 `in` 映射（只能由表达式设置的字段无法读回）把已服务的请求读回到契约的字段中。候选的适配器（来自设置）然后构建它自己的请求；一个它不接受的能力被计为不可映射且永不发送。
- 候选从 worker 用它自己的密钥（`shadow_provider_key`）调用，最多同时 `shadow_concurrency` 个、每秒 `shadow_per_second` 个，每个限制为 `shadow_timeout_s`。没有 hold、没有结算、没有团队余额：客户的调用早已结束。
- 两个答案都经由各自的适配器进入契约的字段；`compare` 按每个共享的标量字段记录是否一致（域名按主机、名称在去除重音与法律后缀后按相似度、其他字段按归一化相等）。可选的 `count` 与 `with_email` 输出键给出列表大小，因此"找到了"与"带着邮箱找到了"被分开报告。

## 存储什么

`ShadowPair`，每对一行：能力、已服务端点、身份的一个带盐哈希、每侧是否找到、列表计数、逐字段的是/否映射、候选的状态、时间与计费单位（来自
`units_header`），以及已服务调用的收费。没有姓名、邮箱、电话号码或答案 body。每次运行删除比 `shadow_retention_days` 更老的行。

## 报告

`GET /admin/shadow?days=N`（超级管理员）与 `treg-worker shadow report`：按能力与已服务端点，给出对数、候选应答的对数（拒绝、超时或 5xx 都不算答案：它计入错误率且留在每个命中率之外）、每侧的命中率、候选带邮箱的命中率、其错误率、p50 与 p95 时间、逐字段一致性、候选每 1,000 对的单位数，以及每 1,000 次调用已服务的成本。

## 设置

```json
{"base_url": "https://candidate.example", "units_header": "x-units",
 "sample": {"people.search": 0.05},
 "capabilities": {"companies.enrich": {"method": "GET", "path": "/company",
   "accepts": [["domain"]], "in": {"domain": "queryParams.domain"},
   "out": {"name": "data.name", "domain": "data.domain", "industry": "data.industry"},
   "miss": "data == null"}}}
```

适配器键就是路由 YAML 的（`accepts`、`in`、`in_expr`、`const`、`out`、`miss`），且
`count_with(rows, 'path')` 统计在某一路径上携带值的行数。
