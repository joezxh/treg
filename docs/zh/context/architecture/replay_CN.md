---
title: Replay — 录制的交换经由一个 checkout 的计费、结果与路由代码重跑
status: building
sources:
  - src/treg/application/replay/__init__.py
  - src/treg/application/replay/__main__.py
  - src/treg/application/replay/records.py
  - src/treg/application/replay/engine.py
  - src/treg/application/replay/fixtures.py
  - src/treg/application/replay/differ.py
  - tests/test_replay.py
related:
  - architecture/money.md
  - architecture/proxy-model.md
  - architecture/catalog.md
---

# Replay（重放）

一次重放回答关于一个变更的一个问题：给定相同的录制交换，这个 checkout（代码加 catalog）是否像另一个那样预留、结算、判定与路由它们？它是针对必须不移动金钱或结果的 catalog 与计费变更的proof gate，也是看清一个本应移动它们的变更到底移动了哪些端点的方式。

一次重放是一个记录与一个 checkout（代码加 catalog）的纯函数。它绝不打开网络连接、数据库会话或账本事务，也绝不调用供应商：重新询问上游会花钱并返回与已计费那个不同的答案。`tests/test_replay.py` 在拒绝 socket 与会话制造器的前提下重放整个 fixture 语料库。

## 接缝（seams）

引擎调用生产代码，绝不调用它的副本。每个接缝是从仍调用它的路径中提升出的一个纯函数：

| 接缝 | 从哪提升，且仍被谁调用 | 决定 |
|---|---|---|
| `call.resolve.price_call` | `_resolve_marketplace_call` | 估算、每行与每信用单位、冻结的结算基础、请求证据 |
| `call.settle.decide_settle` | `_platform_settle`，账本之前的一切 | 可计费、原因、观测到的、原始实际（在重复价格与路由 child 免费规则之后）、在利润之后的计费 |
| `call.route.child_outcome` | `_run_routed` 中的路由 child 循环 | `declared_miss`、`not_found`、`rejected`、`error`、`adapter_error`、`miss`（带原因）或 `hit`（带行） |
| `call.service.submission_state` | 调用用例，在结算之前 | 一个 `when: terminal` 2xx 是否是一个待处理任务，以及一个为何不是被接受的提交 |
| `asynctasks.terminal_judgement` | `_finish_terminal` | 一个终态结果记录的 hit 与 verdict 词 |

引擎自身只镜像调用点的参数（那个 `provider_failed_<status>` 原因、对一个被拒绝提交的观测覆盖）并组合下面的既有纯函数。

## 一次重放运行什么

| 输出组 | 生产函数 | 字段 |
|---|---|---|
| `reserve` | `price_call`、`money.with_margin` | `estimate_micro`、`hold_micro`、`unit_micro`、`reported_charge_unit_micro`、基础的 `when`、kind、预留与回退，以及整个基础的一个摘要 |
| `settle` | `submission_state`、`decide_settle` | `deferred`、`billable`、`reason`、`observed_micro`、`actual_micro`、`charged_micro` |
| `outcome` | `results.classify`、`results.verdict` | `state`、`reason`、`hit`、`verdict` |
| `adapter` | `Adapter.from_upstream`、`Adapter.is_miss` | body 是否为 JSON、适配器 miss、映射核心的摘要、空的必需字段 |
| `routing` | `child_outcome`（仅验证的、可路由适配器） | `kind`、`why`、`rows` |
| `stats` | `stats.Tally.fold` | 该行是否计数，以及它移动哪些计数器 |
| `async` | `asynctasks.classify_terminal`、`settlement.settle`、`terminal_judgement` | 终态 `outcome`、`settled_micro`、`charged_micro`、`hit`、`verdict` |

每次调用作为对 treg 自己 key 的调用重放（`tier: platform`），使用运行它的进程的设置。一个不能应用的步骤是 `null`；一个抛出的步骤只报告异常的类型与类型化种类，绝不它的消息，那可能引用 body。一个被接受的异步提交是 `settle.deferred`，没有 outcome、adapter 或 routing：它在它的终态答案上结算、被判定并被路由，那由一个 `async_terminal` 记录携带。那个记录在它携带它们时结算在它自己的冻结基础与描述符上，否则结算在 checkout 派生的那些上。

## 语料库记录

每行一个 JSON 对象，body 为 base64，每个部分带一个保真度标志：

```
{ "rid": "<opaque>", "endpoint_id": "...", "class": "hit|miss|non2xx|async_terminal",
  "captured_at": "...", "source": "archive|error_evidence|async_terminal|fixture",
  "request":  { "method": "...", "vendor_url": "...", "query_items": [[k, v]], "path_params": {},
                "body_b64": "...", "accept": {}, "fidelity": "exact|reconstructed|snippet" },
  "response": { "status": 200, "media_type": "...", "headers": null, "body_b64": "...",
                "fidelity": "exact|snippet_redacted_truncated" },
  "recorded": { "estimate_micro": 0, "observed_micro": null, "charged_micro": 0, "hit": null,
                "verdict": null, "credential_tier": "platform", "routed_child": false },
  "async":    { "descriptor": {}, "settlement_basis": {}, "status": "...", "settled_micro": 0 } }
```

`query_items` 是 caller 的查询，如定价读取它，包含路径参数；`path_params` 命名其中哪些被路径消费。`recorded.routed_child` 把结算重放为一个路由 child。引擎不从 `recorded` 读其他任何东西：生产自己的金额是为抽取语料库的人携带的，而非比较。一个记录不持有团队、成员、key、调用引用或 IP。

## fixture 语料库

`fixtures` 从 checkout 自己的 catalog 写一份语料库，针对每个已定价端点（正价格、请求表或用量计；路由父级除外）：提交的示例答案、一个适配器判定为 miss 的答案（沿适配器自己的 miss 路径把示例清空）、声明的 miss 状态、一个 2xx 错误信封、一个 400 与一个 500，以及针对异步端点的终态成功、失败与计费失败文档。请求来自 `test_request`，因此一个记录的请求保真度是 `reconstructed` 且它的响应不带头部。其中没有任何客户数据，且它是生成的，绝不提交。

## 运行它

```bash
uv run python -m treg.application.replay fixtures corpus.jsonl
uv run python -m treg.application.replay run corpus.jsonl baseline.jsonl --fingerprints baseline.json
# ... 在另一个 checkout 上，用同一个语料库文件：
uv run python -m treg.application.replay run corpus.jsonl candidate.jsonl --fingerprints candidate.json
uv run python -m treg.application.replay diff baseline.jsonl candidate.jsonl \
  --base-fingerprints baseline.json --candidate-fingerprints candidate.json --declared declared.yaml
```

`diff` 在任何变更字段未声明或任一侧缺失记录时退出 1。

## 差异报告

differ 按 `rid` 连接两个输出并每行打印一个端点与类：记录数、变更的记录数、每个变更字段带 `old -> new`，以及覆盖它的声明（没有时 `NO`）。一个值只在它是数字、布尔、null 或短码时才被打印；任何其他字符串缩减为它的字段名。一个仅在原因码或摘要中的变更被列在它自己的表中，与金钱或结果的变更分开。

跟随两个更多小节：

- **没有被记录执行的声明**，因此一个什么都没测的声明可见。
- **被触及的端点**：每个端点，其生效 catalog 条目（加载的行、它的成本视图、它的适配器与契约）在两个指纹文件之间不同，带它每类的记录；一个没有的是 `untested`。

### 声明一个差异

一个声明是一个 YAML 映射；一个文件持有它们的一个列表：

```yaml
- provider: serpstat               # 或 endpoint: <id 或 glob>，两者中恰好一个
  field: settle.actual_micro       # 一个字段或一个 glob（`settle.*`）；默认每个字段
  from: 4000                       # 可选：仅此旧值
  to: 0                            # 可选：仅此新值
  where: {outcome.state: error}    # 可选：候选的其他字段必须持有这些
  reason: serpstat envelope        # 必需；显示在报告中
```

一个变更字段在某一声明匹配它的端点或供应商、它的字段、它的旧与新值以及它的 `where` 时被声明。一个列表值逐元素匹配一个列表字段。报告命名第一个匹配的声明，但每个匹配某个变更的声明都计为已执行。

## 在 CI 中

`.github/workflows/replay.yml` 在每个拉取请求上运行：它从 base（合并提交的第一个父级）生成语料库，在 base 与合并结果上重放它，并在未声明的差异上失败。声明是拉取请求正文的围栏 `replay-declared` 块，因此它们属于需要它们的变更且绝不累积在仓库中；编辑正文会重跑作业。报告进入作业摘要。

没有引擎的 base 跳过比较。普通测试套件也重放整个 fixture 语料库，因此一个开始抛出的接缝会让每个拉取请求失败，而不仅仅是那些不同的。
