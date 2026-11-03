---
title: The table layer — 一次调用，以行列形式作答（`/table/`）
status: built, behind `table_enabled` (TREG_TABLE_ENABLED), off by default
sources:
  - src/treg/domain/table/__init__.py
  - src/treg/application/table.py
  - src/treg/routers/table.py
  - src/treg/routers/call.py
  - src/treg/call_surface.py
  - src/treg/config.py
  - src/treg/domain/identity/mcp_oauth.py
  - src/treg/application/auth.py
  - src/treg/routers/auth.py
  - tests/test_table.py
  - tests/test_table_oauth.py
related:
  - architecture/proxy-model.md
  - architecture/hub.md
  - architecture/catalog.md
  - interface/api.md
---

# The table layer（表格层）

`* /table/{rest:path}` 接受与 `/call/<tool id>` 完全相同的请求（method、query、body、key、`Idempotency-Key`），并以 `{shape, columns, rows, ...}` 回答同一次调用，面向想要一个网格的客户端：首先是 Google Sheets 插件。它是 `/call/` 的**兄弟**，而非它的一个选项：`/call/` 把每个查询参数透传给供应商（一个 `?format=` 会到达它），且它必须原样返回供应商的答案（AGENTS.md，不可协商之 4）。

## 一条调用路，两种结尾

`routers.call.run_call_surface(rest, request, caller, prefix=, finish=, headers=)` 是每个调用面（call surface）的整条调用路：为拒绝回退而藏起的调用方身份、从 `raw_path` 在 `prefix` 之后重建的原始路径、`CallInput`、`create_call_context`、`execute_call`，以及每次退出时相同的簿记（审计行、幂等声明释放、`X-Treg-Call-Id`）。`call_tool` 传入 `_relay_answer`（原样流式传输答案、附上异步描述符与评审邀请）；`table_tool` 传入 `_table_answer`。`finish` 在同一个 `try` 内运行，因此转换期间的故障像任何其他故障一样被审计与释放。

`table_tool` 传入 `headers=application.table.plain_headers(...)`：调用方的头部带 `Accept-Encoding: identity`，因为表格必须解析 body（hub runner 以同样方式问它的步骤）。一个供应商无论如何都用 gzip 或 deflate 回答时会被解码（`_decoded`）；任何其他编码被读作一个 `raw` 表。

`/table/` 位于 `call_surface._CALL_SURFACES`（surface 标签 `table`），因此它的拒绝得到 `X-Treg-Error: 1` 与审计回退，且位于 `bootstrap._DATAPLANE_ROUTE_KEYS`。demo 锁定（`domain.identity.access`）只允许 `/call/` 用于非读方法，因此 `/table/` 留在 demo 或组织之外。

## 金钱

这里没有任何东西预留、计费或退款。`execute_call` 返回时调用已被结算（它的成本作为 `X-Treg-Cost-Micro` 在答案上），因此一次失败的转换只能让视图变成 `raw`：它绝不会计费两次或留下一个打开的 hold。表格答案携带调用自己的 `X-Treg-*` 头部（调用 id、成本、served-by、`X-Treg-Idempotent-Replay`），且同一个 `Idempotency-Key` 免费返回同一个表。`application.table.read_answer` 最多读取 `MAX_TABLE_BYTES`（8 MiB）；更大的答案变成 `raw`、`truncated: true`、切到 64 KB。

一个上游非 2xx 保留它的状态并回答 `{error: "upstream_error", upstream_status, body_excerpt}`（前 2 KB）。一个 treg 拒绝（`CallFailure`）被精确地与在 `/call/` 上一样抛出。

## 标志

`application.table.enabled_for(slug, email)`：`table_enabled`，然后 `table_teams` / `table_users`（任一列表都让一个调用方进入；两者皆空意味着每个团队），与 hub 相同的模式。范围外的调用方回答一个**返回的**纯 404、**而非抛出**：在一个调用面上抛出的 404 会被盖章并作为拒绝被审计，且在该标志关闭时路由必须不留下任何行。`llms.txt` 与 `skill.md` 在该标志关闭时不提及 `/table/`。

## "用 treg 登录"（插件的 OAuth 客户端）

该插件是一个带 PKCE 的公开客户端：`client_id` `mcp_oauth.SHEETS_CLIENT_ID`（`treg-sheets`）、scope `treg:table`、resource `mcp_oauth.sheets_resource_url()`（`<public_url>/table`）。它不是一个表行：`application.auth._sheets_client` 从 `sheets_redirect_uris`（精确匹配，每个 Apps Script 项目一个）构建它，且它只在 `table_enabled` 开启且设置了一个 URI 时存在。`_client_resource` 给它那个 resource 且没有其他，且拒绝那个 resource 给每个其他客户端，因此一个 MCP 令牌在这里永不工作，且该令牌在 MCP 上永不工作。

两个 owner 决策（2026-09-26）塑造了它：

- **令牌只在表格路由上工作。** `routers.table.table_caller` 在 `/table/*`、`/table-columns/*` 与 `/table-account` 上接受 `Authorization: Bearer`，检查受众（audience），并把该人作为一个两分钟身份呈现给 `require_member`，如同 MCP 交换它自己的令牌（`mcp._internal_auth`）。每个其他路由忽略一个 Bearer 头部，因此该令牌在那里得到 401。目录搜索与端点页面不需要 key。在调用之前 `Authorization` 头部被移除（`plain_headers(drop_authorization=True)`）：它是 treg 的令牌，不是供应商的。
- **授权是这个人而非一个团队的。** 同意页（`routers.auth._sheets_consent_page`）没有团队选择器；该令牌携带该人的第一个团队作为默认，且每次请求用 `X-Treg-Org` 选一个团队，由 `require_member`（成员关系、角色、暂停）每次检查。一个其默认团队被该人离开的刷新把默认移到他们的另一个团队；只有离开每个团队才结束该授权。`GET /table-account` 列出 `{email, active_team, teams: [{org_id, slug, name, role, balance_micro}]}`：OAuth 登录可能使用的每个团队（遵守 SSO 范围与必需 SSO），或带团队 key 的 key 的那一个团队。

生命周期是 MCP 的：访问 `ACCESS_TTL_SECONDS`（1 小时）、刷新 `REFRESH_TTL_S`（30 天，每次刷新续期、轮换，重放撤销该族）。登出是 `POST /oauth/revoke`。

## 免费列预览（`GET /table-columns/<tool id>`）

一个客户端在任何人付费之前显示一个工具的列（插件的工具卡片与填充模式）。与 `/table/` 相同的 key、相同的标志与团队列表，但没有供应商调用、没有金钱、也没有审计行，因此它**不是**一个调用面。一条独立的路径，而非 `/table/...?preview=1`：`/table/` 把每个查询参数传给供应商。`application.table.preview` 回答 `{shape, columns, column_source, tables?}` 且无行（`domain.table.columns_only`）：

- 一个路由化的工作：它的契约。一个列表工作转换一个样本项，取自 `routed_children` 中第一个有已保存示例的（`domain.table.sample_items`），因此预览先显示被映射的列，然后是该供应商自己的字段。其他供应商可能添加其他字段；一个路由化的工作也回答 `coverage`（`_coverage`）：对于每个输出字段（一个列表工作：仅列表字段），`{filled_by, providers}`，其中 `providers` 计数带适配器的 children 且 `filled_by` 是那些其适配器的 `out` 映射该字段的。最便宜的供应商先回答，因此一个只有某些供应商给的字段可能返回空；插件只勾选每个供应商都填充的字段；
- 一个 hub 工具：它清单的输出字段；
- 任何其他目录端点：它已保存的示例答案（`_example_body`，来自已加载目录行的文件名，绝不来自请求）通过同一转换器；
- 这些都不是：404 `{error: "no_preview"}`。

## 转换器（`domain.table`）

纯函数且仅标准库（import-linter 契约 "Table domain is a pure stdlib leaf"）。`to_table(body, contract_output=, list_field=, hub_fields=)` 永不抛出：任何它无法成形的东西都是 `raw`。`application.table.table_answer` 选择列的来源（`column_source`）：

- **contract**：一个路由化的工作（`catalog.by_id[id].kind == "routed"`，契约来自 `catalog.contracts[capability]`）。一个扁平契约：它的 `output` 字段按契约顺序，然后 `served_by`（来自 `_treg.served_by`）；一行，当 `_treg.outcome == "miss"` 时无。一个带必需 `list` 字段（`people`、`companies`、`results`...）的契约：成形为 `list`，每项一行。项是供应商自己的对象，因此 `LIST_MAPS`（数据，按列表字段键控；今天是 `people`）先把常见名称映射到固定列：`first_name`、`last_name`、`title`、`company`、`linkedin_url`、`location`，第一个持有文本的匹配路径胜出（`organization.name` 是一个路径；一个对象绝不被取，因此一个对象 `company` 落到 `company.name`）；每个其他字段跟随在供应商自己的名字下，减去被映射列用的路径。
- **hub**：一个不在目录中但 `hub.tool_for` 为该调用方解析的 id（一次短读，在答案被读取之后：不可协商之 3）。列是清单的 `output.fields`，或它的 `output` 键，按清单顺序；一行。
- **generated**：其他任何东西。`_find_tables` 收集每个对象列表，在一个其键在 `ENVELOPE_KEYS`（`summary[0]`、`tasks[0].result[0]`）中的单对象列表内搜索，且绝不在表自己的项内。无：形状 `flat`，一行 `flatten`（点键，`MAX_DEPTH` 3）。一：形状 `list`（带它的 `path`）。两个或更多：形状 `nested`，带 `tables`（名称、路径、row_count、列、行）与 `summary`（`field`、`value` 行，来自表的共同父级；一个对象列表是每项第一个值的一个单元格）。`columns`/`rows` 是摘要，因此一个只读那些的客户端仍得到一个网格。

单元格（`cell`）：标量原样；标量列表用 `", "` 连接；一个对象或持有对象的列表作为紧凑 JSON。一个名称以 `_` 开头的字段（`_treg`、一个供应商的 `_note`）绝不是一个列；一个路由化答案的 `_treg` 进入回复的 `_treg`，带 `call_id` 与 `cost_micro`。

**陷阱：** 已保存的示例答案（`src/treg/catalog/examples/`）以字符串 `"… N more item(s) truncated"` 结束每个长列表（由 `scripts/catalog_verify.py` 写入）。一个带该标记的列表不是"所有对象"，因此转换器跳过它（`_TRUNCATION_MARK`）；真实答案从不携带它。
