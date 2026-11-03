---
title: 工具枢纽(tool hub) — 一个 maker 发布、由其他工具组成的工具
status: built (phases 1–10, 2026-09-09/14; pricing flexibility 9.1–9.5 (`docs/hub-pricing-decisions.md`), listing + public run log 10.1–10.5 (`docs/hub-listing-decisions.md`)); behind `hub_enabled` (TREG_HUB_ENABLED), off in production until the final merge
sources:
  - src/treg/domain/hub/__init__.py
  - src/treg/domain/hub/manifest.py
  - src/treg/domain/hub/refs.py
  - src/treg/domain/hub/graph.py
  - src/treg/application/hub/__init__.py
  - src/treg/application/hub/runner.py
  - src/treg/application/hub/sandbox.py
  - src/treg/application/hub/limits.py
  - src/treg/application/hub/health.py
  - src/treg/hub_sandbox.py
  - src/treg/routers/hub.py
  - src/treg/routers/catalog.py
  - src/treg/routers/web.py
  - src/treg/routers/hub_gate.py
  - src/treg/application/call/service.py
  - src/treg/domain/money/__init__.py
  - src/treg/mcp.py
  - frontend/src/state/hub.js
  - frontend/src/pages/HubPage.vue
  - frontend/src/pages/HubRunPage.vue
  - src/treg/cli.py
  - src/treg/worker.py
  - src/treg/models.py
  - src/treg/web/index.html
  - src/treg/web/skill.md
  - src/treg/web/llms.txt
  - src/treg/alembic/versions/0044_hub_tools.py
  - src/treg/alembic/versions/0045_hub_runs.py
  - src/treg/alembic/versions/0046_hubtool_check_result.py
  - src/treg/alembic/versions/0047_hubrun_output.py
  - src/treg/alembic/versions/0048_hubtool_data.py
  - src/treg/alembic/versions/0049_hubtool_listed_public_log.py
  - src/treg/alembic/versions/0050_hub_listing.py
  - docs/hub-recipes/data-sheets/run.js
  - docs/hub-recipes/data-csv/run.js
  - docs/hub-recipes/engineering-team-size/run.js
  - tests/test_hub.py
  - tests/test_hub_sandbox.py
  - tests/callmatrix/test_hub_run.py
related:
  - architecture/proxy-model.md
  - architecture/money.md
  - architecture/catalog.md
  - architecture/import-boundaries.md
---

# 工具枢纽(The tool hub)

一个 **hub 工具(hub tool)** 是一个 maker 在 treg 上发布的、由其他工具组成的工具：可以是一个 JSON 步骤列表，也可以是一个在沙箱中运行的脚本。每一步都是一次普通的 treg 调用，因此身份、访问规则、密钥注入与金钱在每次调用时都已存在；hub 增加的是图(graph)、沙箱、maker 的道路、卖家的价格与各个表面。决策在 `docs/HUB-DECISIONS.md`（50 个问题，2026-09-09 敲定）；案例研究（一个真实的 Supabase 表作为一个工具、手工走通）记录在本文件末尾。

一切都在 `hub_enabled`（`TREG_HUB_ENABLED`，默认关）之后：标志关时每个 hub 路由回答 404，调用道路从不问 hub，agent 文件不含 hub 文本，且 dashboard 不显示 Hub 条目。标志开时，`TREG_HUB_TEAMS`（逗号分隔的团队 slug 列表，默认空）是「关」与「开放」之间的中间阶段（owner，2026-09-24）：每个有调用方的门（`hub_app.enabled_for(slug)`：hub 路由器、一个 hub id 的 `/call/`）对列表外的团队回答 404，与标志关时完全一样。开放表面遵循 READER（owner，2026-09-26）：目录搜索与 `catalog_search`、目录 get 与其兄弟行、分享页、`/skill.md` 与 `/llms.txt` 的 hub 段落，以及 MCP 工具 `hub_create`、`hub_update`、`hub_mine`（`mcp._HubToolsGate` 在 `tools/list` 上）解析请求携带的 key 或会话（`routers/hub_gate.reader_team`）并询问 `hub_app.visible_to(slug)`；一个没有团队的读者只在没有设置列表时才能看到 hub。`TREG_HUB_USERS`（登录邮件，owner 2026-09-26）是团队列表旁的第二份列表：一个被列出的人在他们所代表的每个团队中都看到 hub，而他们未被列出的队友则看不到（`enabled_for(slug, email)`、`hub_gate.reader`，调用方在 `/call/` 与 hub 路由上的邮件）。`treg skill bootstrap` 发送那个 key，因此一个被列出读者的 agents 获得 hub 段落。一个凭据是谁被记住 60 秒（`hub_gate.remember`，以 key、会话与团队头的哈希为键；MCP 也如此）：在设置了列表时，每个携带 key 的开放请求否则会花费 3 到 5 次数据库读取。只有可见性依赖它。静态插件文件从不携带它们（`build_plugin.py`）。空列表意味着每个团队。

## 词汇表(Vocabulary)

| 词 | 含义 |
|---|---|
| maker | 发布一个 hub 工具的团队 |
| caller | 运行它的团队 |
| version | `HubTool` 的一行：发布的四（五）个文件；`<id>@N` 固定一个 |
| run | 一次执行：一个 `HubRun` 行、父调用，以及每步一个子调用 |
| step | 一次运行内的一个调用（一个 JSON 步骤，或一个 `ctx.call`）；一个针对上限的单位 |
| the check | `check.json` 在发布时真实运行一次，并按计划运行 |

## 四个文件，以及第五个(The four files, and the fifth)

`recipe.json`（清单 manifest）、`run.js`（脚本配方）、`check.json`、`README.md`，以及可选的 `data.csv`。`treg hub init <name> [--script]` 写出一个供应商中立的骨架。`docs/hub-recipes/` 持有三个做好的配方，每个带一个矩阵测试：一个作为工具提供服务的公开 sheet、一个上传的 CSV，以及 `engineering-team-size`，一个跨两个目录工具（用于身份的 company enrichment 与一个可能的 R&D 类回退，外加 CrustData 的 role headcount）的脚本阶梯，带一个 $0.15 的 `ctx.charge` 费用。另外四个，每条道路一个，选自客户调用最多且要求最多的，已实况验证但尚未带矩阵测试：`seo-domain-snapshot`（JSON 步骤、固定价格）、`brand-mentions`（一个跨 Reddit 与路由 X 搜索、丢弃松散匹配的脚本，按 mention 计费）、`email-list-hygiene`（一个跨上传域名列表的脚本、无工具调用）与 `hn-mentions`（一个跨无密钥自有工具的脚本）。一个 JSON 步骤的 `input` 是一个对象，因此 DataForSEO 的数组 body 实时端点需要一个脚本。

**清单(The manifest)**（`domain/hub/manifest.py`）由纯规则验证；每个拒绝都是 `ManifestError(field, rule)`，一个深入文件的带点路径加上它违反的规则，因为 maker 通常是一个修复文件的 agent。字段：`name`（`<team-slug>.<name>` 成为 id）、`summary`（≤200）、`writes`、`inputs`、`uses`、`limits`、`pricing`（或一个扁平 `price_usd`），恰好一个 `steps` | `script: "run.js"`、`output`。从 Crawl4AI 配方继承的规则：一个 input 通过没有 `default` 而变为必需（一个 `required` 键被拒绝）；每个非密钥 input 携带一个 `example` 或一个 `default`；一个 `int` input 命名一个 `max`。`uses` 是安全边界：每个条目是一个目录 id 或 maker 自己的一个工具名；一个 hub id 被拒绝（深度一）；一个只服务其自身数据的脚本可以把留空。每个步骤的 `call` 必须在 `uses` 中（自有工具为 `<tool>/<path>`，可选 `method`、`allow_fail`）。限制：`steps` ≤ 20、`wall_s` ≤ 120，金钱字段 0–100 美元且至多六位小数。**定价(Pricing)**（`docs/hub-pricing-decisions.md` 第 4 轮，2026-09-24）：每种类型一条规则，且只有 maker 的部分（供应商费用、目录步骤是额外向 caller 计费的）。一个 steps 配方每次成功运行有一个固定价格，`"pricing": {"price_usd": N}`（只有顶层 `price_usd` 的文件含义相同；两者一起除非是已存储清单的同一个数字，否则被拒绝）。一个脚本声明 `"pricing": {"max_price_usd": N}` 并在 run.js 中用 `ctx.charge` 自行定价（见下）；一个没有 `pricing` 的脚本是免费的且 ctx.charge 被拒；一个脚本上的 `price_usd` 被拒。存储为 `{"mode": "per_call", "price_usd"}` 或 `{"mode": "charge", "max_price_usd"}`（`stored_pricing`）。验证器返回 runner 的微元视图（`Validated.pricing`：`mode`、`price_micro`、`max_charge_micro`）；`pricing_micro(manifest)` 与 `price_label(manifest)`（「$0.01 a run」、「up to $0.05 a run」、「free」）读取一个已存储的；`range_label` 与 `seller_part_micro` 构建下面的标题范围。引用必须能解析且图在发布时构建，因此一个环或一个未知步骤在任何人付费前就被拒绝。`validate_check` 把 `check.json` 固定到清单；`validate_data` 检查 `data.csv`（≤ 5 MB、一个表头与一行；这些行在每次运行时进入引擎）。

## 引用语言与图(JSON 道路)(The reference language and the graph (JSON road))

`domain/hub/refs.py` 已完成且刻意保持小：`$input.<field>`、`$<step>.<path>`（任意深度，单个项用 `[0]`）、`$<step>[]`（一个重复步骤的每个回答）、`$<step>.length`、`$0.<path>`（位置别名）、`$<as>.<field>`（在一个 repeat 内）。恰好一个引用的字符串解析为该值；一个模板解析为文本。一个缺失字段读作 `None`；一个未知根在发布时被拒。无算术、无条件、无函数：一个需要这些的配方是脚本。`domain/hub/graph.py` 从引用（从不声明）派生边，拒绝环与未知步骤，并保留每个步骤的 `wave`（其深度）用于追溯(trace)。

## 运行器(The runner) (`application/hub/runner.py`)

`POST /call/<team>.<name>`，输入作为 JSON body。运行器一次性强制转换输入（默认值、类型、int 钳制到 `min..max`、未知或缺失必需项 → 422 `hub_input_invalid` 指名字段），从 `X-Treg-Run-Max-Cost` 读取上限(ceiling)，否则从工具自己的 `limits.cost_usd`（其 maker 知道一次运行花费多少），否则 $1.00（价格加步骤，计入在途的），打开价格预留(hold)，然后运行道路：

- **JSON 道路：** 每个就绪步骤启动，一次四个，等待最先完成的那个；`for_each` 把一个步骤扇出成计数的单位；`skip_if_empty`；`allow_fail`。
- **脚本道路：** 沙箱中的 `run.js`；每个 `ctx.call` 是同一个子调用。

卖家价格的预留使用 `reserve_admission`，就像一个计量的目录预留一样。当配置的资金准入等待过期时，它返回 429 `money_admission_timeout`，带有与目录预留相同的抖动(jittered) `Retry-After`，在打开价格预留或启动任何步骤之前。Redis 基础设施错误保留既有的数据库回退；卖家价格的结算与释放不变。

每个单位是在子预留 `{run}:s{n}`（`{run}:s{n}.{i}` 对于一个项）下的一个 `execute_call`：同样的门、同样的密钥注入、同样的预留-结算，如同一次直接调用。**两个团队在一次运行中相遇：** 一个目录步骤作为 caller 运行（他们的钱、他们的规则、他们的密钥若他们持有一个，否则 treg 的）；一个 maker 自有工具上的步骤作为 maker 运行（他们注册的密钥、不计量），这是一个共享配方如何使用 caller 从不持有密钥的方式。来自案例研究的两规则：一个步骤绝不被压缩回答（runner 自己读取字节；每个子调用上 `Accept-Encoding: identity`），且一个脚本可以在 `ctx.call` 上设置头，减去身份与成帧(framing)头（`authorization`、`cookie`、`apikey`、`host`、`content-length`、`x-treg-*`；工具的绑定总是获胜）。

失败：当一个步骤失败时，没有新步骤启动，在途步骤完成，运行回答 424 `hub_run_failed`，带 `{error: hub_step_failed | hub_script_failed | hub_output_invalid | hub_step_cap, step, status, trace, charged_micro, price_micro: 0}`；一个全局拒绝（余额、上限）保留它自己的种类与状态；通过上限是 402 `hub_run_max_cost`。完成步骤上花费的钱保持花费；一个失败步骤自己的预留按端点的正常规则释放；价格被释放。每个团队同时四次运行（`application/hub/limits.py`，进程内，对单进程生产部署是精确的）：第五次是 429 `hub_busy` 带 `retry_after_s`。

回复：`{run_id, recipe: "<id>@<v>", output, usage: {cost_micro, steps_micro, price_micro, steps, ms}, trace, log}` 带 `X-Treg-Run-Id`（= 父调用 id）、`X-Treg-Steps`、`X-Treg-Cost-Micro`（总计）。`Idempotency-Key` 通过父存储覆盖整个运行。`HubRun`（迁移 0042、0044）每次运行保留一行：状态、步骤、成本、价格、时长、脱敏(mask)输入、trace、log、error，以及一次成功运行的输出；随调用团队删除。

## 沙箱(The sandbox) (`application/hub/sandbox.py`, `treg/hub_sandbox.py`)

`run.js` 在每次运行一个独立的短生命周期进程中运行，`python -m treg.hub_sandbox`，以 `runner.py` 的纪律生成：一个被擦除的环境（绝不服务器的）、一个私有的临时 HOME、它自己的进程组、POSIX rlimits（CPU、文件大小、无 core、Linux 上的 RLIMIT_AS）、一个墙钟(wall-clock)kill、每次退出时整个组被 kill。在其中，QuickJS（`quickjs` 包，server extra）没有网络、没有文件系统、没有 `require`、没有 `process`、没有定时器；引擎的堆上限为 64 MB。脚本获得的整个表面：`ctx.inputs`、`ctx.call(target, {method, query, body, headers})` → `{status, headers, json, text, truncated, cost_usd}`（x-treg-* 头被移除；`cost_usd` 是那个调用计的费用，因此脚本可以保持自己的预算并在上限前停止：一个通过它的运行被 treg 停止且不返回任何东西）、`ctx.charge(usd, label)` → 无（脚本的价格，一次一行，见下）、`ctx.csv(text)` → 按表头（RFC 4180）键控的行、`ctx.data` → `data.csv` 的行（≤ 5 MB，在父进程中每次运行解析一次）、`ctx.log(text)`（50 行 × 2 KB）。`ctx.call` 作为一行 JSON 经 stdin/stdout 跨到父进程；父进程强制执行每次调用的 `uses`（列表外的调用被拒且运行停止）、20 次调用上限、上限与输出（一个 ≤ 2 MB 的 JSON 对象携带 `output.fields` 中的每个字段，否则 424 `hub_output_invalid`）。一个内存炸弹结束为 `memory`，一个死循环为 `timeout`（父进程的 kill；引擎无法以自己的时间限制调用 Python），一个抛出为 `script`，每个一行是 maker 在运行日志中读取的。

`target` 有三种形态：一个目录 id；`<tool>/<path>` 对于自有工具；一个完整 URL，仅当它以一个在 `uses` 中命名的自有工具的 base URL 开头时才允许（其查询合并到调用的查询下）且对任何其它主机拒绝。「我的脚本需要我自己的服务器」由那扇门回答：服务器是一个自有工具（`treg tool add my-api --base-url https://api.mine.com`，secret 可选；一个公开 Google Sheet 不需要）；treg 发出请求；沙箱从不打开 socket。`ctx.call` 返回一个 promise 且不阻塞引擎：子进程持续泵送作业队列，并在父进程对该 id 的回复到达时结算每个 promise，因此在一次 `Promise.all` 中的五次调用就是五次在途，由父进程作为任务每次四个（`MAX_PARALLEL`，JSON 道路的宽度）运行，并以它们完成的任意顺序回答。一个一次等待一个调用的脚本行为如旧。`ctx.call` 选项里的 `timeout_s` 是脚本对那一次调用的自己的限制：通过它回答 `{status: 0, timed_out: true}` 而非结束运行，被取消的子进程释放它的预留，且 trace 把该步骤记录为 `timeout`。2026-09-23 为 AI 可见性工具添加：五个回答引擎每个 30-47 秒无法在 120 秒内一个接一个放下，且一个永不回答的引擎绝不能花费其他四个。**沙箱的安全审查计划作为发布前的单独一轮**（owner 的备注）。

## ctx.charge：一个脚本的价格(ctx.charge: a script's price)

一个脚本自行定价：`ctx.charge(usd, note)` 向 caller 计费一行，maker 需要几行就几行。一笔费用（`ctx.charge(0.01, "fee")`）、每个结果（`rows.length * 0.002`）、一个目录调用的加价(`margin`)（``r.cost_usd * 0.2``），以及一个 treg 看不到的 own-key 步骤在供应商处的成本（一个 own-key 步骤花费 caller 什么都没有，规则 1，且 maker 真金白银；一个跨此类供应商的瀑布一次运行花费 $0.001、下一次 $0.50，且只有脚本知道走了哪个分支，因此它在看到答案之后才计费）。清单声明 `pricing.max_price_usd`，所有行在一次运行中可能总计的最大值；caller 在运行前看到它（价格标签读作「up to $X a run」）。运行器在该 cap 上持有 `{run}:price` 预留；父进程拒绝一个会超过它的行（以及第 21 行）且运行停止；每行是 trace 中带 maker 备注的一个 `charged` 条目；`usage.charged_micro` 是它们的和，且价格结算给 maker，预留的其余部分退款。一个失败的运行释放整个预留。2026-09-24 与 Jason 敲定：一个机制而非三种定价模式。

## maker 的道路(The maker's road) (`routers/hub.py`, `application/hub/__init__.py`)

`POST /hub/tools`（member+）把文件作为字段接收（`manifest`、`script`、`check`、`readme`、`data`），针对团队的世界验证它们（目录 id、团队自有工具、既有 hub id；422 `{error: manifest_invalid, field, rule}`），把下一个版本存储为 `checking`，然后 **真实运行 `check.json` 一次**：一个携带 maker 身份头的、到 `POST /call/<id>@<version>` 的进程内请求，因此步骤按正常价格计到 maker 的余额上，绝不会是卖家的价格。通过（每个 `check.fields` 存在且非空，达到 `min_rows`；`health.verdict_from` 是唯一的规则）⇒ `live`，且 201 携带调用行与分享页；失败 ⇒ 该版本作为 `failed` 保留，原因在 `check_result`（迁移 0043）。`PUT /hub/tools/{id}` 发布一个新版本（名字必须匹配 id）。`POST /hub/run` 是 `treg hub run .` 背后的 dry run：文件加 `inputs`，作为 maker 真实运行，不存储任何东西，每个 trace 版本 0。`PATCH /hub/tools/{id}` `{price_usd}` 改变最新 live 版本的价格供后续运行，无版本凸起(bump)。`DELETE /hub/tools/{id}` 退休每个版本（立即从调用道路移除；行保留）。`GET /hub/tools/mine`（每个版本带派生的健康与 30 天数）、`GET /hub/tools/{id}[@N]`、`GET /hub/tools/{id}/health`、`GET /hub/tools/{id}/earnings?days=N[&format=csv]`、`GET /hub/runs/{run_id}`（caller 看到它付了什么、输入、trace、输出；maker 看到密钥脱敏的输入、trace、log 与完整 error；caller 的 trace 与 error 从不携带上游错误 body；任何其它团队 404）。

版本：最新的 `live` 服务于 `/call/<id>`；`<id>@N` 固定一个，且一个固定的旧版本在存在更新的 live 之后仍可调用 30 天（`application/hub.tool_for`）。调用道路的解析顺序对今天存在的一切保持不变，并增加一个第三者、最后一步：自有工具获胜，然后目录 id，然后 hub（`application/call/service.py`）。

经 MCP（`/mcp/`）：`hub_create`、`hub_update`、`hub_mine`；调用仍是 `call`。`hub_create` 的描述携带 owner 的规则：一个团队不持有的凭据绝不硬编码进脚本；先注册它，然后指名该工具。CLI 镜像它：`treg hub init | run | publish | ls | earnings | price | retire`；一个拒绝打印字段、规则与带缺失工具名字的修复命令，每行一条命令。

## 健康与按计划检查(Health and the scheduled check) (`application/hub/health.py`)

健康是派生的，从不存储：一个版本在其最近三次运行（caller 的运行与计划检查都一样）全部失败时是 `failing`，否则 `ok`，任何运行之前 `unknown`。一个 failing 工具仍可调；公开页、`catalog_get` 与 maker 的健康视图说明状态；下一次通过的运行清除它。`treg-worker hub check`（每 6 小时 cron 一次）作为 maker 运行每个 live 工具最新的 `check.json` 一次：身份从数据库重建（发布者的成员资格，否则一个 owner 的），运行经过 runner、按步骤价格计到 maker 而非卖家价格，该行是一个 `HubRun` 带 `caller_email = "hub-check"`，裁定落到带 `scheduled: true` 的版本。一个失败的 check 绝不自己退休一个工具。

## 卖家的钱(The seller's money) (`domain/money/__init__.py`)

一个 maker 的价格与一步使用相同的原语：在运行开始时在 caller 上一个额外的预留 `{run}:price`（在任何步骤之前的 402 `hub_price_unaffordable` 带金额），成功时结算，任何失败或停止时释放。**持有的是什么：** maker 在此次运行能赚到的最多：一个配方的 `price_usd`，或一个脚本的 `max_price_usd`。**结算的是什么：** 配方的价格全额；一个脚本的 ctx.charge 行之和（`actual_micro`），预留的其余部分退款。结算是 treg 中唯一跨团队的资金移动：`settle_to_in_transaction(db, call_id, payee_org_id, actual_micro=)` 从 caller 的预留消费结算金额，把预留的其余部分退款给 caller，并在同一事务中用一个结算金额的 `earned` 块贷记 maker 的团队（付款方上一个命名收款方的 `settle` 条目，收款方上一个命名付款方运行的 `grant` 条目）；`actual_micro=None` 结算整个预留，即 per_call 情形。不变量在每瞬间对两个团队都成立。MVP 中没有加价、没有平台分成。当 caller 是 maker 时不计费（他们自己的运行、那个 check）。`earned` 在免费种类之后、购买的钱之前花费（`_KIND_ORDER`）。提现是待办。收入视图只是销售（maker 自己的运行排除）、计数与金额，从不谁调用；`avg_price_micro`（earned ÷ 成功运行，每天与整体；`avg_price_usd` 在 CSV 中）是 maker 看到一个可变价格落在哪的方式。`treg hub price` 设置一个配方的 `price_usd` 或一个脚本的 `max_price_usd` 供后续运行，无版本凸起；一个脚本的金额只随 run.js 的新版本改变。

## 各个表面(The surfaces)

- **agent 的前门：** `skill.md` 与 `llms.txt` 在 `<!--hub-->…<!--/hub-->` 块内携带一个 hub 段落，在标志关时 `routers/web.py` 剥除它（如同它剥除路由发现块）；`scripts/build_plugin.py` 同样丢弃该块，`--with-hub` 在最终合并时保留它。`GET /catalog/endpoints/<id>`（在 `catalog_get`、`treg catalog get` 之后）针对一个 hub id 回答公开契约（`kind: "hub"`、summary、inputs、output、价格行（`price_range` 领先：近期成功运行花费了什么、步骤与卖家价格一起，以及对于一个脚本卖家在该值之后的上限（「$0.0103/run so far · seller up to $0.02 a run」：近期运行可能都只计了很少），来自 `application/hub.price_ranges` 跨 30 天每个成功运行、只在有其他团队的运行时才用（否则 maker 自己的，标记），带 `price_samples`；在任何运行之前是声明的最坏情况加「+ steps」；然后 `price_label`：模式与最坏情况；`cost.usd` 是最坏情况）、健康、版本、`call_template`、页面 URL、readme）；绝不会是脚本、maker 的工具或密钥。搜索只在一个 hub 工具经 treg 批准其列表时列出一个（一个状态为 `approved` 的 `HubListing` 行，见下）：最新 live 版本由 `catalog_store.score_extra` 用目录自己的 token、别名、平台提升、idf 与准入门评分，然后按分数与无提升合并（`merge_by_score`，并列时目录行在前）。该行是公开契约加上由其他团队运行得到的 30 天 ok 率；未列出、未批准、失败与退休的从不出现。它的 `added` 是批准的 UTC 日（`HubListing.decided_at`），因此最近添加的搜索把它与目录工具并排列出（`search_listed(everything=True)` 无词；catalog.md 的「`added`」）。
- **列表审查(The listing review)**（`docs/hub-listing-decisions.md` 第 2 轮，2026-09-24）：`PATCH /hub/tools/{id} {"listed": true}`（`treg hub list`）是一个请求、一个 `HubListing` 行，每个工具一个而非每个版本一个，因此在每个新版本被审查时列表保留（见下；迁移 0050；旧的每版本 `hubtool.listed` 列保持未读，仅扩展）。`set_flags` 在状态 `requested` 创建它，从 `rejected` 再次询问，对 `requested` 与 `approved` 不动；`listed: false` 删除它。一个超级管理员读取队列（`GET /admin/hub/listings?state=`，`pending_listings`：summary、价格标签、uses、check 裁定）并决定（`POST /admin/hub/listings/{id} {decision: approve|reject, reason}`，`decide_listing`）；一个拒绝需要原因，maker 在 `treg hub list`、`/hub/tools/mine`（`listing: {state, reason}`）与 dashboard 的 Listing 标签中读取。dashboard 的 Admin 页携带队列。maker 视图中的 `listed` 只在批准时为 true；另一个团队对一个工具的视图从不携带该请求。
- **能力(Capability)**（第 3 轮）：一个可选的清单 `capability`，一个目录 capability id（在发布时针对 `cat.capabilities` 检查），只是一个提议。批准设置 `HubListing.capability`（管理员可改变它，或用 `""` 清除；一个拒绝清除它）。一个批准的作业把该工具添加到该作业的每个供应商的 `catalog_get` 的 `siblings`（`capability_siblings`），给该工具自己的 `catalog_get` 那些供应商作为兄弟，并把它的 capability 词加入到它的搜索分数（`W_CAPABILITY`，像一个供应商行）。它的 `observed.ok_rate` 被播种（`seeded_observed`：90% 计为 5 次运行，与过去 30 天其他团队的运行混合，低于 20 次运行为 `estimated`），因为一个新工具没有可比较的。它绝不是路由子项：一个 agent 比较并挑选（不可协商 4）。
- **对列表工具的更新(Updates to a listed tool)**（第 4 轮）：一个在 APPROVED 工具上通过其 check 的版本变成 `review`，而非 `live`（`_hold_for_review`），因此每个读取 `live` 的表面保留批准的版本；一个更新的等待版本使较旧的变成 `superseded`。`tool_for` 只向 maker 团队的调用提供固定的 `review`（或 `checking`）版本；不指名任何 caller 的公开视图（catalog get、分享页）从不显示它。`treg hub price` 在一个批准工具上被检查并存储为 `HubListing.pending_pricing`。队列是 `GET /admin/hub/updates`（`pending_updates`：现在服务的与将替换它的并列）；`POST /admin/hub/updates/{id} {decision, reason}`（`decide_update`）批准（该版本上线、价格生效）或拒绝（该版本变成 `rejected`、价格被丢弃、maker 读取 `listing.update.reason`）。`_hold_for_review` 与 `set_price` 以 `HubListing.reviewed` 为键，由第一次批准设置且从不清除（第 5 轮）：取消列出一个被审查的工具只把它移到状态 `unlisted`（移出搜索；再次列出恢复 `approved` 无新审查），且一个把批准收回的拒绝保持它已审查，因此两者都不是绕过审查的方法。一个从未被批准的请求通过取消列出被删除，且该工具保持自助服务。一个拒绝的原因在 maker 再次询问时留在行上。批准的 capability 跨一个批准的更新保留；管理员通过再次批准列表来改变它。
- **团队名(Team names)**（第 5-6 轮）：`reserved_reason` 按读法判断一个名字（`_reads_as`：NFKC、形近字母与数字映射到 Latin、拆成词）：当它以 `treg` 开头或有一个以 `treg` 开头的词、有一个以 `official` 或 `verified` 开头的词、或读作一个目录供应商（一个等于它的词，或整个名字以一个 5+ 字母的名字开头）时拒绝；一个平台（`signup.reserved_team_names` 中 `=` 标记的、像 `people` 这样的普通词）只作为整个名字。这样的团队不能被创建、重命名到、或发布 hub 工具，除非超级管理员行动：一个 hub id 以团队 slug 开头。一个新用户的邮件派生团队回退到 `team-<user id>`。
- **Rejected 意味着不可调用(Rejected means not callable)**（第 6 轮）：`tool_for` 只向它 maker 的团队提供 `HubListing.state` 为 `rejected` 的工具（`is_rejected`）；另一个团队的调用得到 404、分享页 410、`catalog get` 404。一个从未被审查的工具按 id 仍可调。
- **无中继(No relays)**（第 6 轮）：一个团队工具的 `base_url` 不能是 treg 自身（`points_at_treg`、`treg_hosts`：公开 URL 的 host 与 `PUBLIC_HOST_ALIASES`），在 `/tools` 处拒绝，并在 runner 中对之前添加的工具再次拒绝，因为它会让一个 hub 工具调用其他 hub 工具。
- **审查者读取什么(What the reviewer reads)**（第 6 轮）：列表队列携带脚本（或步骤）与自有工具的 base URL（`own_tool_urls`）；更新队列是代码的统一 diff，从批准到新（`_code_diff`）。check.json 可持有 `{"cases": [...]}`，最多 5 个，每个在发布时运行；第一个失败的 case 使 check 失败（`verdict.case`）。一个 maker 不能审查它自己 hub 工具的运行（`feedback.submit_review`）。公开价格只计被定价版本的运行（`price_ranges` 按清单的 `version` 过滤；maker 的列表给 live 版本定价），且费用行命名什么运行付了钱（「about $0.005 so far, at most $0.1 a run」）。
- **一次运行计费什么(What a run charges)**（第 5 轮）：一个每个声明的输出字段都为空（None、""、[]、{}）的回答不论脚本计了多少费都把卖家价格结算为 0（`runner._empty_answer`）。价格行携带供应商费用上限（`fees_label`：「+ provider fees up to $1 a run」、工具的 `limits.cost_usd` 或 runner 的默认）且 `PAY_NOTE` 替换「you pay only what completes」：一个失败的运行不付卖家价格但付已运行步骤的供应商费用。公开价格（`price_ranges`）只要有其它团队的运行就基于它们，否则基于 maker 自己的运行与检查，标记 `price_from_tests` 与「(from the maker's own tests)」。契约命名一个版本调用的 maker 自有工具的主机（`own_hosts`、`sends_inputs_to`）：caller 的输入到达它们，且它们可以在无新版本时改变。
- **maker 的日志绝不指名 caller**（2026-09-26）：自有工具步骤在一个带邮件 `hub-caller:<org>` 且无密钥的快照上运行（`_maker_snapshot` 丢弃 caller 的密钥 id、名字与前缀）。
- **审查者从一个更新看到什么(What a reviewer sees of an update)**（第 5 轮）：一个 maker 写它自己的 check.json，因此一个 check 几乎证明不了什么。更新队列比较批准版本 check 运行的输出与新版本的（`_fields_lost`）并指名批准版本填充而新版本留空的每个字段（「no longer returns: industry」）。
- **公开分享页(The public share page)** `GET /hub/<id>`（以及 `.md`；`@N`）：给一个人或公开样式表上一个 agent 的契约；价格作为模式与最坏情况（「seller $X per unit, up to $Y per run」；schema.org 的 Offer 携带最坏情况）；当 maker 打开了 `public_log`（10.3）时的 RUN LOG：其他人的最近 20 次运行与跨 30 天每天的运行，每行时间、结果、ms、步骤、`units` 与付的价格，从不 caller、输入或输出；check trace 只作为形态（绝不每个步骤调用了什么）；「made of N tools (names and keys hidden)」；跨 30 天的可靠性；较旧版本仍可调；无需登录即可读；`noindex`，不在 sitemap 中。
- **dashboard**（`frontend/`：`state/hub.js`、`pages/HubPage.vue`、`pages/HubRunPage.vue`）：给 maker 的 Hub 视图（列表；一个带 Overview、Versions、Price、Listing、Earnings、Runs & log、Health 的详情；复制调用行、复制分享 URL、退休）与运行页 `/app/runs/<run_id>`，在两种登录模式下加载时打开。hub 关时（`/meta.hub` false）dashboard 不请求任何 hub 路由；否则 Hub 条目在 `/hub/tools/mine` 为活跃团队回答时出现，并在切换团队时再次探测。超级管理员列表队列以同样方式跟随 `/meta.hub`。文件在 dashboard 中是只读的：新版本来自终端或 agent。冻结的遗留 dashboard 在退役前携带同样的视图。
- **CLI：** `treg hub init` 搭建一个 `pricing` 块（配方为 `price_usd` 0；脚本为 `max_price_usd` 0.05 与一个 `ctx.charge` 行）；`treg hub ls` 显示价格标签；`treg hub earnings` 打印每次成功运行的平均价格；`treg hub list | unlist` 请求搜索中的一个位置或撤回它（`HubListing`，见上）且 `treg hub log --public on|off` 翻转 `HubTool.public_log`（迁移 0049），两者也在 dashboard 的 Listing 标签上。

## 案例研究（2026-09-09）与它的教训(The case study (2026-09-09) and what it taught)

owner 与助手在带标志开的本地服务器上，手工走通 maker 的道路，针对一个真实的 Supabase 表（owner 的 `krew-saas` 项目 `hubdemo` schema 中 2,592 行 SEO 排名跟踪行）：`treg hub init` → 四个文件一起写出 → 一个没有注册工具的运行（拒绝：`uses[0]`、规则、修复命令）→ `treg secret add` + `treg tool add supabase` 带两个绑定（`Authorization: Bearer` 与 `apikey`）→ `treg hub run .` → `treg hub publish .`（check 通过，0 µ$：唯一步骤在 maker 自己的密钥上运行）→ 第二个团队调用 `unclecode-superdesign-dev.keyword-rankings` 并得到了行；Supabase URL 与任何密钥材料都没有出现在回复中。它发现了上面的压缩规则与头规则、供应商中立的 `init` 模板，以及 house-style 的 CLI 输出。发布前还计划两次走通：owner 手工用 CSV 配方，以及一个 Claude Code agent 经 MCP。

## 待办(Backlog) (owner's order)

更多数据提供商的模板含 `treg hub init --from <template>`；提现；列表道路（pull request + 验证）；一个团队私有开关；一个平台费用；dashboard 中的脚本编辑器；运行的实时轮询；计算计费；Crawl4AI 作为内建；一个基准/审计器；作业队列、recipe-calls-recipe、重试、实时进度、团队沙箱。

## 安全轮（8.1，2026-09-10）与它的改变(The security pass (8.1, 2026-09-10) and what it changed)

两位审查者加敌对探测；对发布重要的发现在一个 PR 中修复，其余进入待办。自那以后的不同：价格预留关闭在每条路径上（整个运行周围的守卫：一个拒绝或断开释放它，一个崩溃变成 424 `hub_run_crashed`，绝不带开放预留的 500）；一个步骤的回答被读进内存至多 1 MB 且超过即关闭流（脚本回复上的 `truncated`、JSON 道路上的失败步骤）；子进程的成本来自调用记录，绝不来自上游的 `X-Treg-Cost-Micro`；一个子调用绝不解析到 hub 工具（`CallInput.child_of`）且一个用点命名的自有工具不能在 `uses` 中（无嵌套运行）；caller 的 trace 在 200 body、424 detail 与幂等重放上携带工具种类而无上游错误 body；`GET /hub/tools/{id}` 在另一个团队的工具上只返回公开契约；公开页从不打印 check 的样本输入；自有工具步骤审计为 `hub-caller:<org>`；一个处于 check 下的版本只对它的 maker 可见且一个崩溃的 check 把它留为 `failed`；墙钟在桥接调用期间持续运行且 JSON 道路也有一个；发布与计划检查在运行期间不持有数据库连接；上限头、`price_usd`、运行 body（深度、`NaN`）与头名被验证为 4xx；服务器 traceback 绝不到达 maker 的日志；`..` 在调用路径中被拒；`data.csv` 上限 5 MB。待办：卖家价格的平台加价（margin 为 0）、可写全局中的桥接状态、发布时的输出根验证、并发发布 409、以 `http` 开头的 slug、少付(shortfall)提示、402 上限路径缺失的运行行。
