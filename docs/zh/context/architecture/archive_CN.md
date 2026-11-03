---
title: 归档(archive) — 带版本的(visioned)历史与缓存准入(cache admission)
status: building
sources:
  - src/treg/archive.py
  - src/treg/catalog/hunter.yaml
  - src/treg/domain/catalog/results.py
  - src/treg/alembic/versions/0031_archive_result_admission.py
  - tests/test_cache_result_admission.py
  - tests/test_archive_batch.py
  - tests/test_archive_batch_postgres.py
  - src/treg/archive_bodies.py
  - src/treg/config.py
  - src/treg/infra/object_store.py
  - src/treg/alembic/versions/0032_archive_body_storage.py
  - tests/test_archive_r2.py
  - tests/fake_object_store.py
  - scripts/smoke_archive_r2.py
  - src/treg/alembic/versions/0002_archive_tables.py
  - src/treg/alembic/versions/0003_callrecord_cached.py
  - src/treg/alembic/versions/0004_archivekey_request_shape.py
  - src/treg/alembic/versions/0011_callrecord_archive_link.py
  - src/treg/application/call/service.py
  - src/treg/application/call/settle.py
  - src/treg/alembic/versions/0039_archive_own_key_and_repeat_pricing.py
  - scripts/backfill_call_archive_links.py
  - src/treg/api.py
  - src/treg/bootstrap.py
  - src/treg/routers/admin.py
  - src/treg/application/asynctasks.py
  - src/treg/application/archive_erasure.py
  - src/treg/alembic/versions/0067_org_archive_opt_out.py
  - tests/test_archive_opt_out.py
related:
  - architecture/data-model.md
  - architecture/proxy-model.md
  - architecture/catalog.md
---

# 归档(The archive)

异步结算把终端供应商 JSON 归档在 `treg://asynctasks/<call_id>` 下，使用原始端点与供应商。这个强制证据可能包含过期的(到期)结果 URL；worker 绝不跟随那些 URL 也绝不存储生成的媒体字节。`load_terminal_responses((call_id, endpoint_id), …)` 通过它们被存储于其下的索引键哈希查找它们（容忍一个被修剪的载体），并读取它们回来（每个键的最新快照，跟随 `body_of`）用于 Activity 显示，其通过描述符而非猜测供应商的形态来提取工件。

图片/视频 API 条目携带有效的 `cache: forbidden`，包括扩展目录行。`lookup` 与刷新检查当前策略，因此旧的缓存响应不被重放或刷新。这不删除历史快照也不改变普通查询缓存。终端证据是刻意的例外：只有获胜的调用方/worker 终结器把它存储在原始调用 id 下，独立于重放策略；生成的媒体字节绝不被下载。

两个概念，各一个词——词汇表是刻意的并镜像宪章的纪律：**缓存(cache)** 是一个键最后确认的、有用的答案，在它新鲜且没有被后来的决定性观察使其无效时，用来代替供应商调用服务；**归档(archive)** 是每个答案的每个版本，带着其时间戳保留。缓存是归档的顶层。历史被刻意保留：它是未来的数据产品（每键的时间序列——随时间变化的反向链接画像、价格历史），而非废物。

**构建状态：完整(COMPLETE)（PR 6 of 6 —— 原始的五个之后发出了面板）。** 所有五个切片都存在于 `TREG_ARCHIVE_MODE` 之后：骨架、记录器(recorder)、目录 `cache` 字段 + 报告、服务路径、以及学习器 + 刷新 worker。每个凭据层级都参与（自有密钥答案被记录并服务，见「自有密钥答案」）且一个已计量命中有一个定价差异（见「命中定价」）。不存在的东西：phase-3 聚合器表面（历史端点）——不要把它们记录为已存在。自 2026-09-03 起存在的是下面的每调用读取：一个团队可以看到其 **自己** 调用得到的答案。

## 自有密钥答案(Own-key answers)

一个自有密钥目录调用（tier `tool`/`credential`，从不计量）也是一个缓存参与者。`_execute_call` 在 relay 之前像已计量调用一样查找一个可存储的问题，且 relay 之后当答案适合 `archive_max_body_bytes` 时整体读取 2xx 答案（`settle._read_whole_if_small`：有界，在头发出之前——一个已计量调用已经付出的同等有界缓冲）；一个不适合的答案，或其声明的 `Content-Length` 超出上限，原样流式传输且不被记录——绝不是前缀。relay 向此类调用要求 identity 编码（`force_identity`），且一个无论如何都压缩的供应商不被记录（`_identity_encoded`）。自有密钥路径从不读取的调用方 body（流式、无小的 `Content-Length`）无法键化问题：无查找、无记录。自有工具(own-TOOL)调用（无目录条目）保持原样。**一个回显团队自己凭据的答案绝不被记录**（`_echoes_own_credential`：错误掩码使用的精确渲染，在无法渲染时失败关闭）。同一守卫、同一 `origin_org_id` 来源与同一共享规则适用于一个在 org 凭据上、乘坐 treg 的按使用付费 OAuth app（`billed_oauth`）的已计量调用：令牌是团队的。

**自有密钥命中是免费的**：什么都不预留或结算（不可协商 1），响应携带相同的 `X-Treg-Cache: hit` 头与审计行 `cached: true`，且 `cache_price` 报告 `free`。自有密钥观察训练该计时器与 **其** 密钥的结果状态，如同任何其他。

### 共享：这是谁的问题(Sharing: whose question is it)

存储与共享是两个维度，分别判断。许可(licence)（`cache.mode`）说字节是否可以被 **保留**；`archive.sharing(entry, own_credential=…)` 说答案是 **谁** 的问题——「供应商允许存储」绝不意味着「答案不依赖于谁问」。

| 谁问的 | `scope: any_account` | `scope: own_account` |
|---|---|---|
| treg 的平台密钥 | `public` | （从不：own_account 需要调用方的凭据） |
| org 自己的凭据（API 密钥或 OAuth 令牌，已计量或未计量） | `org`，或仅在端点声明 `cache.sharing: public` 时 `public` | `connection` |

共享由 **密钥** 强制执行，而非读取时的过滤器：`scope_tags` 把 `org:<id>` 或 `conn:<id>:<已排序的绑定 secret id>` 折叠进 `cache_key`，因此私有历史位于一个无人能计算的哈希之下，其计时器只从其自己的答案学习，且一个团队中的两个 Google 账户永看不到彼此的站点（重连是一个新 secret，因此是一个新历史）。一个调用方最具体地先咨询其 scope——仅 connection；然后 org 然后 public（一个平台密钥获取可能为自有密钥调用方免费服务）；仅 public——并在第一个下记录。`ArchiveKey.scope`（`org` | `conn` | NULL = public，包括此列之前的每个密钥）让刷新 worker 跳过私有密钥：treg 的平台密钥无法重新询问它们。此规则之前的历史（平台与 billed-OAuth 行，都 NULL-origin，都在 public 密钥上）因此从不服务于一个 `own_account` 调用方，且只在 `any_account` 端点上服务，那里它本来就是一个 public 问题。`cache_sharing` 与，在命中时，`cache_scope` 在 `tool_called` 上。

`cache.sharing: public` 是一个 **端点声明**（`_validate_cache` 拒绝它在供应商头上、拒绝除 `public` 外的任何值、并拒绝它在 `own_account` 端点上）：它说这个端点的答案无论谁问都相同——treg 自己的服务 OAuth 读取 public 数据是预期情形——且它按端点判断，绝不从供应商的许可继承。已发布的目录中还没有任何东西声明它。

### 选择退出：一个不想存储任何东西的团队(Opting out: a team that wants nothing stored)

一个团队管理员可以把团队移出归档（`PATCH /orgs/{id}/settings {"archive": false}`、`treg org archive off`、Team 页）。该设置是 `Org.archive_opt_out_at`（迁移 0067）：一个时间戳，而非标志，因为团队反对的那一刻就是数据处理请求所要求的处理记录。它被携带到调用运行时的 `OrgSnapshot`，因此该门不耗费查询。

该门是一个完整绕过，在每个层级：`_execute_call` 对一个选择退出的团队不做查找也不做记录，无论计量或自有密钥，因此没有键哈希到达结算，也没有 `ArchiveKeyOrg` 标记被写入。该团队也从不服务于一个 public 答案，即使服务一个不会存储任何属于他们的东西：一次命中触及键的需求并针对该问题标记团队，而最简单的承诺是「我们不记录你问了什么」。成本是团队的：每次调用都是 live 的 live 价格，无免费自有密钥命中，无重复价格。`tool_called` 上的 `cache_outcome` 读取 `org_opt_out`。在退出那一刻在途的调用如其开始般完成，因此来自它的记录仍可能落地；那是开关做它所说的事（从现在起没有 **新** 东西被存储），而擦除(erasure)是移除其余的东西。

**擦除是一个独立的动作，绝不能是开关的副作用。** 两件事运行它：删除团队，以及当一个团队要求删除其存储的答案时 `treg-worker admin erase-archive --org <id>`（`application/archive_erasure.erase_org`）。两者都拒绝一个仍在归档中的团队：在门关闭、其行被移除时没有任何团队的东西被记录，这正是使工作简单的原因。无清扫、无待定状态、无与记录器的协调。什么算「团队的」由治理域决定（`teams.private_archive_key_ids`、`teams.erase_archive_rows`）：每个在该团队自己的 `org:`/`conn:` scope 下的键，带着其快照与键行携带的请求形态，加上团队的每个 `ArchiveKeyOrg` 标记。一个平台密钥答案是一个 public 问题且保留；一旦标记消失，归档中没有东西指名团队。对象在行之前走，以密钥批，在请求池上的短事务中，跨对象 I/O 不持有连接（不可协商 3）：`teams.archive_bodies_only_under` 在一个反连接(anti-join)中判断，哪些内容哈希没有其他键的快照共享（一个 body 是内容寻址的且在键之间去重），那些对象通过 store 唯一的 `delete` 删除并被进程内上传缓存（`archive_bodies.forget`）遗忘，且只有那时行才被删除。另一个进程的缓存无法被告知，因此 store 对任何人都不再是仅追加的：`archive_bodies.prepare` 只在一次 `head` 确认对象仍在（受 `archive_r2_read_timeout_s` 约束；一次 miss 或无应答的 HEAD 再次上传）后才信任一个被记住的上传，因此擦除后记录的一个相同答案绝不提交一个指向已消失字节的指针。一次失败的对象删除在该行之前停止本次传递，因此重试从它们开始；一个被删除的行本会把它对象永久留下。端点运行总计随行移动，取自每个 DELETE 返回的内容而非之前读取的计数，因此同一行上的两个擦除器只减一次。一个竞争被接受并在模块中记录：在判断一个 body 为孤儿与删除它之间，另一个团队可以记录相同的字节；其快照随后读作「字节不在文件上」，每个读取者容忍为一次 miss。

删除一个团队：所有者路由设置退出选择并提交它，在其请求会话已释放其连接之后、且在级联之前调用 `erase_org`（一个失败保持团队、选择退出，以待重试），然后级联。`cascade_delete_org` 自身删除行（归档键在团队处无外键，因此级联的 FK-walking 守卫测试从不会看到它们），这使每个其他删除路径（admin 强制删除、沙箱收割器、演示重置）不会留下行，代价是这些路径不清空的对象。刻意超出范围：异步任务的终端证据（`treg://asynctasks/<call_id>`，在一个 public 密钥下无团队来源的结算证据）、`callrecord` 审计轨迹与幂等重放存储，后者是调用方自己的请求且有自己的窗口。

## 命中定价(Pricing a hit)

一个已计量命中经过与 live 调用相同的预留 → 结算（hold 在查找之前预留，且无论什么回答都结算一次）。唯一的差异是金额，且它是按 **团队** 与按 **问题** 的：一个团队对一个问题第一次已计费调用支付全价，无论供应商还是归档回答了它——归档为 treg 省了一次供应商调用，而非为该团队省下它的第一次价格——且从该团队的第二次调用起，一个命中以 `archive_hit_repeat_price_percent`（默认 10）结算 live 调用会花费的成本。另一个团队对同一问题的第一次命中是全价。一次强制 live 调用（`Cache-Control: no-cache`）是一个像其他任何一样的已计费调用且计数。

证据是 `ArchiveKeyOrg`——每（org，键哈希）一行，由 `archive.note_org_use_in_transaction` **在结算事务内部** 写入（`_platform_settle`，allowlisted 写入 `archive_org_use_in_settle`），因此标记随收费一起落地或根本不落。`note_org_uses_in_transaction` 把重复键折叠为计数并按 `(org_id, key_hash)` 顺序写入有界批；`close_deferred` 一起传递其所有标记，且单标记条目使用同一写入器。PostgreSQL 与 SQLite 对该对的唯一约束使用原子 upsert：一个冲突递增 `calls` 并更新 `last_call_at`，保留 `first_call_at`。每个批使用一个时间戳。PostgreSQL 通过语句内查找重用既有的标记不可变 ID，仅当该语句的快照无行时才分配序列值；并发首次插入仍可能留下序列间隙。唯一约束而非查找来仲裁并发计数。返回的行刷新会话中已加载的任何标记。所有块留在调用方的事务中；一个真正的写入错误传播，因此收费与标记都回滚。这减少了数据库往返，而金钱行锁仍被持有。只标记一个 **可存储** 的问题：`record()` 为每个已计量 2xx 交回一个哈希（phase-0 统计也计数动作与禁止的供应商），且对一个永不能是命中的答案的标记是对金钱路径上的一个浪费写入。`lookup` 在命中时读取它（`repeat_for_org`），调用服务把 `cached_hit`/`cached_repeat` 交给结算，其在账本应用 margin 之前缩放 RAW 金额（地板除法）。结算条目的 meta 携带 `cached: true` 与 `cache_price_percent`；`tool_called` 携带 `cache_price`（`full` | `repeat` | `free`）。把百分比设为 100 恢复「一次命中像 live 调用一样计费」；0 使重复免费。自有密钥命中在此之外：从不计量，从不标记。

## body 存储与 R2 双写(Body storage and R2 double writing)

`archive_bodies` 拥有 body 准备、对象读取、独立的上传队列与完成的存储观察。`archive.py` 保留请求键、快照、事务、TTL 学习与修剪。`infra.object_store.ObjectStore` 只暴露 put/get/head（同一个桶也通过自己的 `build_r2` 客户端以命名 `find-vectors/...` 对象持有 find 的 card 向量，`NamedObjectStore`，见 [find](find.md)，以及 `treg host` body 作为 `hosted-media/v1/...` 对象，`StreamedObjectStore`，见 [media](media.md)，为其 30 MB 文件调整大小）；`open_r2` 惰性导入 obstore 且 bootstrap 拥有其生命周期。测试通过 `bootstrap.configure_archive_object_store` 或 `create_app(archive_object_store=...)` 注入 `MemoryObjectStore`。

每个对象名是原始 body 的 SHA-256，无前缀。调用方提供其已计算的内容哈希给 PUT，它验证哈希形状的命名并使用 `checksum_algorithm=SHA256` 以便 R2 验证上传校验和。一次成功的单 PUT 返回其哈希与字节大小，无后续 HEAD。HEAD 为大小做一个请求。不存储或检查自定义 sha256 属性；GET 强制执行大小限制并验证下载的哈希。相同 body 的并发上传在进程内共享一个 PUT；最近成功的哈希跳过 PUT。R2 存储原始字节，独立于任何特定调用的媒体类型。DB 压缩保持不变。GET 在返回数据前验证完整哈希。

迁移 `0032` 添加可空 `ArchiveSnapshot.body_storage`：`db`、`both` 或 `r2`；NULL 被解释为遗留 DB 路径且不承诺字节被保留。既有的 `content_hash` 命名 R2 对象。仅 R2 快照无 `body_of`；DB 与双写快照保留既有的载体去重。没有历史行、body 列或对象被此变更迁移或删除。

所有开关都是设置，带环境前缀 `TREG_`：

| 设置 | 值 | 默认 |
|---|---|---|
| `ARCHIVE_BODY_WRITE` | `db`、`both`、`r2` | `db` |
| `ARCHIVE_BODY_READ_LOOKUP` | `db`、`r2-first` | `db` |
| `ARCHIVE_BODY_READ_RESULT` | `db`、`r2-first` | `db` |
| `ARCHIVE_BODY_READ_TERMINAL` | `db`、`r2-first` | `db` |

`both` 先上传，然后进入既有的每键锁 / DB 信号量与事务以存储 DB body 并发布 R2 位置。在行锁下或带着已检出的 DB 连接时不会发生 PUT。上传失败时，两种 R2 写模式都保留一个合格的 DB 副本，位置为 `db`；写设置选择正常目的地，而 DB 仍是罕见的失败路径。一次成功的上传之后跟着一个失败的 DB 事务可能留下一个无引用的内容寻址对象；没有指针指名一个失败的上传。既有的策略与大小门在上传之前适用。哈希仅历史在字节不合格时留在 DB。

R2 有独立的 `ARCHIVE_R2_UPLOAD_CONCURRENCY`（8）、`ARCHIVE_R2_MAX_PENDING`（256）与 `ARCHIVE_R2_MAX_PENDING_BYTES`（128 MiB）预算。一个 leader 为其有界尝试序列持有一个上传槽，包括重试抖动；重复等待者不持有上传槽。DB 阶段保持其原始两个槽与 30 秒截止。上传准入失败在两种 R2 写模式下回退到独立有界的 DB 队列。被策略或大小拒绝的 body 保持哈希仅；一个后来的 DB 队列拒绝仍是一个可观察的被丢弃记录。

`ARCHIVE_R2_TIMEOUT_S`（10 秒）在上传槽准入之后界定完整 PUT/重试序列，包括重试抖动。上传槽等待在该超时之外并作为 `queue_wait_ms` 单独测量。不引入额外的超时层。`ARCHIVE_R2_READ_TIMEOUT_S`（2 秒，可配置）分别界定每次 lookup/result/terminal GET 包括物化字节。共享 SDK 传输使用较大的超时，因此它不会过早切断任一操作；应用截止强制执行独立的预算。终端证据绕过尽力而为的队列准入并同步重试上传至多 `ARCHIVE_R2_TERMINAL_ATTEMPTS`（3）次，带界定的退避，在 DB 写入之前。429/5xx 对终端证据也上限为两次尝试；其他终端失败保留配置的重试上限，现在在共享传输预算内。终端证据有 8 秒的总上传预算（包括队列等待与重试），DB 至多 20 秒，且 28 秒总截止。上传耗尽即使在仅 R2 模式下也回退到 DB。一个被取消的等待者在传播取消之前排空那个有界证据操作；失败与截止显式记录日志。其结算已经提交且不能被存储失败撤销。终端失败也记录一个有界错误，因为一个 worker 完成没有待定的调用方事件可注释。

读取者使用 `archive_bodies.pointer` 在一个会话内收集 R2 元数据（`r2-first` 的 `defer(ArchiveSnapshot.body)`），然后在 `archive_bodies.read` 之前关闭它。当需要 DB 字节时，包括 R2 失败之后，一个新的短 DB 会话用于回退字节。终端与 Arena 批使用至多 8 个同时读取。这适用于 lookup、调用结果、终端、admin 与 Arena 读取，包括外部请求会话。`r2-first` 独立于 `body_storage` 尝试所选快照的内容哈希：历史回填不重写原始存储标记，且一个被修剪的 DB 副本仍可能存在于 R2。缺失对象、超时、错误与校验和不匹配回退到精确的 DB 快照/载体。一个哈希仅行不承诺一个 R2 对象；一次不成功的读取返回不可用，绝不是一个不同版本。授权、密钥 scope 与结果选择在 body 解析之前。Lookup 在既有的结果状态与已观察版本守卫下选择 `result_snapshot_id`，然后在关闭会话之后分类已解析的 body。未知结果保留决定性快照；空结果使服务无效而不删除历史。修剪保护决定性快照与存活版本的 DB 载体。合格的 `both` 行丢失 DB 字节并变成 `r2`；它们的对象保持原样。`db` 不联系 R2，包括仅 R2 行。Admin 与 Arena 跟随结果读取开关；比较与惰性初始化跟随 lookup。Admin 回退使用 admin 池；观察/初始化使用后台池；Arena 使用其 worker 会话工厂。读开关应在任何未来仅 R2 写推出之前启用。没有服务 allowlist、cohort 或生产设置在此被改变。

在读诊断到位之前启用任何 `r2-first` 开关。Lookup 把 `cache_body_source`（`db`、`r2`，或当无字节可用时 `none`）、`cache_body_fallback_reason`（无回退时 `none`）与 `cache_r2_read_ms` 加到既有的 `cache_diagnostics` / `tool_called`。不添加额外的调用事件或每调用 DB 写入。所有路径记录有界原因而不含异常文本、键、body 或凭据：`not_found` 与 `timeout` 是 WARNING；`permission_denied`（包括签名失败）与 `hash_mismatch` 是 ERROR。超大对象也是 ERROR（`too_large`）；其他传输错误与一个不可用的客户端是 WARNING（`store_error`、`store_unavailable`）。HTTP 429 是 `rate_limited`，HTTP 5xx 是 `upstream_error`，读取回退上都是 WARNING。这些相同的原因名出现在失败的上传上。日志包含异常类，绝不异常文本。一个带 NULL 遗留存储标记的缺失对象在 INFO 记录：这也包括刻意的哈希仅历史，因此缺失不是丢失的证明。既有的每路径进程计数器保留；额外的有界每路径/原因计数器区分失败类。

每个公共读取器调用在一个 `finally` 中发出一个尽力而为的 `archive_body_read` 完成事件，包括取消与 DB 回退错误。它报告 `path`、原始 `storage`（NULL 为 `legacy`）、`read_mode`、最终 `source`、`outcome`（`r2`、`db`、`db_fallback`、`unavailable`、`db_error`、`cancelled`）、`fallback_reason`、`r2_attempts`、`r2_retry_reason`、`r2_retry_recovered`、`r2_read_ms`、`db_read_ms`、`total_ms` 与返回的 `bytes`。计时覆盖公共读取器，而非前面的元数据查询；在 DB 模式下指针可能已经持有字节。该事件不含 body、哈希、URL、调用或团队身份，并接收正常的 build/config 指纹。对于最终的 `unavailable` 或 `db_error` 结果，当 `BodyPointer` 携带一个时它也包含 `snapshot_id`。这识别所选快照，而非其 `body_of` 载体，用于后续诊断查找。成功的读取、成功的 DB 回退、取消与无 ID 的指针省略该字段。报告重用既有的指针而不额外数据库 I/O；快照 ID 绝不成进程计数器标签。`read_<path>_<outcome>` 进程计数器包含成功读取作为分母；仅回退日志单独不证明 DB 拯救了一次读取。分析保持尽力而为，而非完整覆盖的证据。

DB 回退需要一个仍含 DB 字节或 DB 载体的快照，通常在 `db`、`both` 或一次失败的仅 R2 上传期间写入。成功的 `r2` 写入无 DB 副本：一个 R2 读取失败变成一次缓存 miss 并向上游查找；历史返回 `stored=false` 且无响应 body，且终端视图无归档终端 body。一个旧的 `both` 快照或一次 R2 上传的 DB 回退在全局写开关改变后仍可服务。一次失败的读取不意味着对象从未被归档或已被删除。读取超时与回退可观察性必须在 `r2-first` 之前，因此整个双写窗口有可见的回退率。观察这些率是关闭双写窗口并切换新写入到 `r2` 的先决条件。

`tool_called` 在调用完成时发出并包含 `archive_body_write`；归档队列延迟不能延迟它。独立的 `archive_body_stored` 完成事件携带 `call_ref`、`storage`、`upload_status`、`upload_ms`、`queue_wait_ms`、`dropped` 与 `drop_reason`。通过 `call_ref` 连接。一次失败的 R2 上传之后跟着一个已提交的 DB 副本不被丢弃。仅 R2 上传失败跟随那个同样的 DB 回退用于合格字节。这些保持尽力而为的后台写入：一个被杀的进程可能丢失完成事件，但不能扣留调用事件。同一完成事件测量归档阶段，包括在超时或取消时经过的工作：

| 字段（毫秒） | 作用域 |
| --- | --- |
| `compare_sem_wait_ms`、`compare_ms` | 预比较槽等待，然后指针查询/读取与任何 JSON 归一化。两者都在 DB 写入截止之前。 |
| `record_key_wait_ms`、`record_sem_wait_ms` | 同键锁等待，然后写入槽等待，在 DB 写入截止之内。 |
| `record_db_ms` | 持有写入槽时的墙钟时间：池检出、body 打包、SQL/提交，与完整性重试/退避。这不是纯 SQL 时间。 |
| `observe_sem_wait_ms`、`observe_ms` | 可选的提交后变更报告槽等待与工作，在 DB 写入截止之外。 |

未进入的阶段是 `null`。`failure_phase` 命名被逃逸异常（包括取消）打断的被测量阶段；当没有被打断时为 `null`，包括记录开始之前的队列拒绝。内部处理的比较失败仍回退到原始哈希并使用既有计数器。一次提交后的观察取消不意味着快照丢失：`storage`/`dropped` 继续描述已提交的写入。计时不添加 DB 写入或每调用事件且不改变截止、两个归档槽或池大小。

统计计数在 DB 或 R2 中有可恢复 body 的快照，包括去重版本；`kept_bytes` 是逻辑保留响应字节，而非 PostgreSQL 物理表大小。

当归档模式启用时，任何 R2 开关需要 `ARCHIVE_OBJECT_STORE_ENDPOINT`、`ARCHIVE_OBJECT_STORE_BUCKET`、`ARCHIVE_OBJECT_STORE_ACCESS_KEY_ID` 与 `ARCHIVE_OBJECT_STORE_SECRET_ACCESS_KEY`；bootstrap 在打开 DB 连接之前拒绝不完整的配置。见 SECURITY.md。`scripts/smoke_archive_r2.py` 只在 `treg-archive-dev` 上执行真实的 PUT/HEAD/GET，在 CI 之外；它留下一个微小的测试对象。它只读取环境变量并在配置/凭据缺失时打印带缺失变量名的 SKIP。`.env.example` 包含空白占位符。无真实 smoke 作为单元测试的一部分运行。生产值在 treg-internal 中单独管理。

## 调用→归档链接(The call→archive link)（2026-09-03）

`record()` 返回 `(key_hash, content_hash)` —— 同步计算并交给 `_store` 以便哈希只取一次 —— 且 `lookup()` 把 `key_hash`、`content_hash` 与 `version` 加到其 dict。调用服务（`application/call/service.py`）把它们保留在 `archive_key_hash` / `archive_content_hash` 中且 `_audit` 闭包把它们写到 `CallRecord` 上（迁移 0011：两个可空列，无索引——读取从按 id 的 org 限定行开始且两个目标都已被索引）。`archive.resolve_result(key_hash, content_hash)` 走 行 → 键 → 带有该内容哈希的最新快照 → `body_of` 载体，并返回请求形态（`req_*`，注入前）加上答案；一个哈希仅版本报告 `stored: false`。`GET /calls/{id}/result`（api.py；`id` 是行 id 或 `X-Treg-Call-Id`）把它暴露给该行的 org 的成员，在每个「无文件」分支上有 `note`；`/calls` 行携带 `has_result`。一个路由父没有其自己的链接（它包装一个子的答案）；其读取列出 `children`、子行（`<ref>:r<n>`，check、upgrade）带着其状态与 `has_result`，每个都通过同一端点可读。子在父之前被审计，因此查找读取父行前一小时的：一个 `(org_id, created_at)` 索引读取，宽到足以应对任何上游超时瀑布。归档保持平台限定作用域——使读取安全的是该行属于团队且指名该团队已经收到的精确字节。失败证据（`error_*`）保持原样且仍仅 admin 可见。

早于迁移的行无链接且不能得到精确的一个（密钥需要审计行从未保留的查询与 body）；`scripts/backfill_call_archive_links.py` 尽力链接它们——同一端点、同一字节大小、±10 s 内获取、双向无歧义——默认 dry run 且需要 `--apply` 来写。部署特定的执行属于 operator runbook。

## 结果准入(Result admission)

`domain.catalog.results.classify` 检查已缓冲的供应商字节而不重写任何响应。`has_result_rules` 仅对带有已验证适配器与非空命中/未命中表达式的端点启用结果感知行为。那些端点复用 `Adapter.is_miss`。一个适配器只针对契约验证，因此一个绝不应被路由的能力仍可通过 `routed: false` 契约选择加入（catalog.md，Routing）；influencers.club enrich tiers 是第一个。`results.verdict`，在它旁边，为审计行读取契约的 verdict 词（catalog.md，Hit rate）；它不参与准入，且下面的严格验证器不改变它。

严格结果验证器覆盖 `hunter.companies.emails`、`leadmagic.x.employee-finder`、`seranking.google.keywords.volume`、`leadsforge.people.email.find`、`hunter.people.email.find` 与 `findymail.search.name`。最后两个需要 `data` 或 `contact` 内一个成形的 email 字符串；一个显式的 null email 是空，且 Findymail 也接受显式 null contact 作为空。缺失字段、空字符串与畸形地址是未知。Leadsforge 另外需要其下面描述的成功的 status。结果是 `found`、`empty`、`error` 或 `unknown`，带有有界原因码。Hunter 需要真实的 email 值；LeadMagic 需要人员身份字段，而非 email 地址；SE Ranking 需要布尔 `is_data_found` 与找到行的一个有效非负 volume。零 volume 是有用的数据。一个混合的 SE Ranking 批是有用的，如果至少一行有数据且每行有有效的形态。显式的空数组/无数据标志是空。一个失败该端点自己 `expect` 成功规则的 2xx body（`results.fails_expect`；一个在 20000 envelope 下的 DataForSEO 任务状态非 20000）是一个原因 `expect_failed` 的错误，在任何适配器读取它之前。规则 `misses` 中列出的一个值（一个供应商的 200 `not_found` 状态词）不是失败：适配器判断那个 body。HTTP 错误与显式的供应商错误 envelope 是错误；无效 JSON、谓词失败与不支持的形态是未知。通用适配器规则保留其既有语义，包括它们对缺失字段的限制；针对 fixture 的验证不意味着完整的响应 schema 验证。

没有启用命中/未命中规则的端点保留其原始的 latest-snapshot 服务、TTL 学习与刷新行为，每个端点有一个例外：一个失败 `expect` 规则的 body 从不被记录，且一个已存储的从不被服务（lookup 报告 `result_error`）。它们的未知业务结果指标不拒绝缓存。模式、服务 allowlist、cohort 与保留门对每个端点保持权威。此策略不为额外端点启用缓存服务。

`ArchiveKey.result_state` 与 `result_snapshot_id` 跟踪最后一个决定性的 found/empty 观察，独立于最新的历史快照。`result_observed_version` 标识此代码评估的最新版本。迁移 `0031` 添加可空列而不重写历史或重置 TTL/计数器。遗留键从其最新 body 惰性分类；一个由更旧的二进制在推出期间追加的版本同样使保存的决定无效。Lookup 针对当前规则重新检查候选的 body 且从不在显式空之后搜索。指针由归档写入器拥有且键所有权在读取时检查；快照从不被删除，因此不引入循环外键。

对于启用了命中/未命中规则的端点，只有 found-to-found 观察可以计为稳定。默认比较带排序对象键与紧凑空白的 JSON；数组、类型与值保持显著。声明的 `cache.ignore_paths` 额外排除特定字段。非 JSON 或不可用/歧义 body 回退到精确原始字节哈希。Found-to-empty 计一次改变并使服务无效；重复的空结果既不增长也不收缩 TTL。Empty-to-found 计一次改变并恢复资格。错误与未知在既有捕获策略下添加历史但不替换决定性证据或更新学习。一个保留的阳性结果仍在其自己的时间戳过期，而非稍后错误的时间戳。缓存命中保持读取，绝不新鲜的学习证据。既有的稳定/改变汇总只接收这些合格的增量；历史计数器保持混合策略的终生总计。

字节保留与精确字节去重独立于有用性。空的 2xx 答案仍链接到调用方的历史。非 2xx 捕获作用域不变。异步终端证据保持强制历史且从不是学习证据。记录与无效化仍使用既有的有界、尽力而为后台写入器，因此它们在该事务提交之后生效；这不是一个同步无效化保证。

## 学习器(The learner)（PR 5）

在记录器内部运行于已知键的决定性重新获取上，受上面的结果准入约束。对 `ttl_s` 的 AIMD：稳定 ⇒ ×1.5，由 min(30 d，判断的 `cache.max_age_s`) 封顶；改变 ⇒ ×0.5，下限 60 s。一个键其第一次 `_NEVER_AFTER`（4）重新获取所有改变标记自己 `ttl_s = TTL_NEVER (-1)` —— 在稳定重新获取重置它之前从不服务。lookup 偏好学习到的计时器（`ttl_s > 0`）而非固定的 phase-1 猜测。

**比较(Comparison)。** 结果准入选择决定性基线并控制哪些转换训练 TTL。相同的原始哈希计为稳定；不同的哈希在默认的 JSON 归一化（可选地排除 `cache.ignore_paths`）使比较相等时仍可计为稳定。遗留的字段噪声启发式保持移除；观察报告从不决定 TTL。

## 刷新 worker(The refresh worker)（PR 5）

`archive.refresh_worker` 从 lifespan 在进程内运行（adsconv 的纪律），由 `worker_enabled()` = serve 模式 AND `archive_refresh_daily_cap > 0` 门控；间隔 `archive_refresh_interval_s`（300 s）。对于启用了命中/未命中规则的端点，只有带有确认的 `found` 决定的键可以赢得刷新；未分类/空/未知键等待调用方观察。其他端点保留原始的刷新资格。一个键 **赢得** 刷新：窗口 ≥ 80% 已消耗 AND `last_requested_at > fetched_at`（自上次获取以来有调用方问过——刷新本身绝不计为需求）。刹车：每供应商每日调用上限（从 `origin="refresh"` 快照计数——无记账表可漂移）与每次通过 10 个。该调用重放存储的请求形态——方法、面向供应商的 URL、body，与键化(KEYING)头（`req_headers`；没有它们记录落到一个不同的键下，在测试中以困难方式发现）——用由一个 **权威构建器**（`oauth_providers.platform_bindings` —— 移出 api.py 因此该 worker 绝不导入 api；routers→api 导入边界禁止那个链）构建的注入与来自设置的键值。刷新花费是 treg 自己的，不附加到任何 org 且不在账本中——上限就是刹车。每次刷新通过同一 `_store` 记录（`origin="refresh"`），因此刷新 **就是** 教导计时器的采样。

## 服务(Serving)（PR 4）

`archive.lookup()` 在 `call_tool` 中在 **relay 的位置** 运行——在每个 access/deny/cap 门 **之后** 且金钱预留之后，只替换网络行程。**命中上的金钱与 live 调用形状相同**：预留、结算、成本头与账本行——只是当团队之前已为该问题付费时结算以重复价格关闭 hold（见「命中定价」；自有密钥命中免费）。响应携带 `X-Treg-Cache: hit`、`X-Treg-Fetched-At`、`X-Treg-Age`，且审计行（+ `/calls`）携带 `cached: true`。一个命中 **不是** 一个新的观察：无快照、无改变统计——只有 `last_requested_at`（fire-and-forget `_touch`），PR 5 读取的需求信号。

新鲜度(phase 1)是 `archive.ttl_for(entry)`：按能力前缀的固定猜测（`crypto.price` 5 分钟、`web.search` 1 h、`people.`/`company.` 7 d、默认 1 h），总是由判断的 `cache.max_age_s` 封顶（CoinGecko 的 24 h 职责）。学习器(PR 5) 为每个键替换这些。`declared_max_age_s()` 把供应商上限提供给默认值、学习与 lookup。服务即使对一个已学习到的阳性 TTL 也用那个声明封顶，然后用调用方 `X-Treg-Max-Age` 封顶。没有声明的上限，学习到的 TTL 可超过能力默认；lookup 绝不使用静态默认来封顶一个阳性的学习 TTL。

唯一的例外是一个 **易变能力(volatile capability)**（`volatile_max_age_s`）：命名移动数据的能力段 —— `live`、`realtime`、`quote`（60 s）、`price` 与任何 `hot*`/`trend*` 段（300 s）—— 是对默认值、服务与刷新的 **硬上限**，即使超过一个学习到的计时器。学习器无法区分「周末持平」与「稳定」；一个在重新获取间相同的 live quote 或 trending 列表仍不能在数小时后服务。一个供应商 `max_age_s` 与一个 operator 上限与它叠加（最小值获胜）。

调用方控制，总是被遵守：`Cache-Control: no-cache`/`no-store` 强制一次 live 调用（读后写(read-after-write)的逃逸——归档从不猜测跨端点效果）；`X-Treg-Max-Age` 收紧（绝不放宽）窗口；畸形值被忽略。在每个不确定分支上都不 —— 服务关闭、veto、未判断策略、无/陈旧/哈希仅快照 —— 且一个 lookup 故障降级为一次 live 调用（一个 api 侧 belt 甚至捕获 lookup 自己管道中的故障；通过使其爆炸来测试）。

`CallRecord.cached`（迁移 0003）在模型中声明为 LAST 以匹配 ALTER TABLE 的追加位置，使 `create_all` 测试 schema 与迁移的生产形态对齐。

## 目录 `cache` 字段(The catalog `cache` field)（PR 3）

每个 **供应商** 一个许可判断，写在 YAML 文件头一次并继承其下每个端点；一个端点自己的 `cache:` 覆盖。 `catalog_store` 把头形态带入 `provider_meta["cache"]`（dict，非字符串化）并把有效值盖戳到每个归一化端点（`entry["cache"]`，缺失 ⇒ None ⇒ forbidden）。来源形态是 `{mode, license_quote, source_url, checked}` 加可选的 `ignore_paths` 与 `max_age_s` —— 一个学习器(PR 5) 必须当作硬上限对待的供应商强加之刷新上限。一个仅用于比较的映射包含 `ignore_paths` 不需要声明许可模式；它保留配置的默认保留策略。`tests/test_archive.py` 验证已发布目录中每个声明的字段：一个已判断的条目必须携带其 quote、source 与 date。

第一次判断集合（checked 2026-08-27）：**coingecko** `transient` 带 `max_age_s: 86400` —— 其 API 条款允许缓存且强制 24 小时刷新且 §6.2 禁止任何更长寿命的东西；**finnhub** `forbidden` —— 其条款禁止与任何第三方共享数据或派生结果，且把一个团队的缓存获取服务于另一个是恰恰那个。DataForSEO 与 SerpApi 的条款同日读取，对存储 **沉默** —— 留空（= forbidden）而非猜测。其他 36 个平台供应商保持未判断：空、forbidden、安全。

## phase-0 报告(The phase-0 report)（PR 3）

`GET /admin/archive`（superadmin）：总计（模式、键、快照、保留的 body、保留字节）与每端点行 —— 键、重新获取（稳定+改变）、`change_ratio` = 改变/重新获取（它移动多快的原始信号）、最新获取。这是缓存判断的证据表面，后来也是计时器的；它补充 `/admin/reconcile/repeats`，其给重复花费定价。

## 记录器(The recorder)（PR 2）

挂在 `call_tool` 中紧接 `_buffer_response` 之后 —— 那一行是「已计量平台调用，body 已在内存中」成为事实的地方，那正是资格门 3。仅已计量 2xx，且绝不是一个容量签名表读作我们自己的账户耗尽的 2xx（Icypeas 的 200「insufficient credits」），也不是一个提交（`_unfinished_submission`）：在一个创建拥有的资源（`resource_ownership.produces`）或是异步的行上，任何非完成的答案。那是一个作业或任务 id，而非一个可重放的答案：一个重放会向询问团队出售另一个团队的 id 而非其自己的资源。同样的原因，服务路径从不对这样的行做 lookup（`_only_submits`），除非它是 `terminal_on_submission`，其只存储与服务完成的答案。服务路径已经发出 `X-Treg-Cache: hit`。调用上下文也携带来自 `served_hit` 的 `cached`，因此 review 邀请可以独立于响应头排除归档命中。`archive.record()` 是 fire-and-forget，带审计的纪律：有界待定集（512）、失败被吞下但在 **ERROR** 记录日志（一个丢失的记录必须清除 `FaultCaptureHandler` 的阈值才可被报告；像 lookup 回退到 live 调用这样不花费任何东西的降级保持在 WARNING）、`drain()` 在关闭时（bootstrap，**在** `analytics.drain()` **之前** 因此期间的丢失仍被报告）与在测试中。一个记录器崩溃不能使一次调用失败（已测试）。`drain()` 移除它自己收集的任务而非等待其 done 回调——审计的精确 drain 纪律；两者都避免的忙自旋（2026-08 串行 Postgres CI 挂起）在 `tests/test_audit.py` 中为两个模块解释并钉住。

**哪个池(Which pool)。** 这里的每次写入 —— `_store_locked`、`_touch_write`、`prune_once`、`refresh_once` —— 使用 `background_session_maker`。`lookup` 是唯一的例外并刻意使用 API 池：它在调用方的 `/call/` **内部** 运行，因此它绝不能排在这个模块自己的写入之后。`tests/test_db_pool_isolation.py` 按函数钉住那个分割；也见下面的 Record throttle，其在池内限定并发。

**计数 vs 保留(Counted vs kept)。** 统计与原始 body 的 `content_hash` 为每个被观察的答案记录（一个哈希是一个身份，而非内容）；body **字节** 只在条目的缓存策略是 `transient`/`archive` **且** body 适合 `archive_max_body_bytes`（默认 2 MB —— 整体跳过，从不截断）时才保留。连续的相同答案通过 `body_of` 去重；一个在字节从未保留时到达的相同答案现在存储它们，因此策略升级向前修复而无回填。键 URL 重建为供应商看到的样子（解析的上游 + 转发的调用方参数，解析消耗的命名排除）—— 凭据注入稍后发生，在 relay 中，因此凭据不能从请求侧进入键或存储。PR 3 每供应商判断考虑的一个边缘：一个在 2xx body 中 **回显** 请求凭据的供应商会把它存储 —— 带着那个考虑判断每供应商的 `cache`。

## 模式开关(The mode switch)

`TREG_ARCHIVE_MODE`（配置 `archive_mode`，默认 `off`）→ `archive.mode()`：`off` | `shadow`（记录 + 学习，不服务任何东西 —— phase 0）| `serve`（shadow + 回答合格的 fresh 命中 —— phase 1+）。任何无法识别的值降级到 `off`：一个拼写错误必须禁用，绝不启用。回滚是通过部署的正常配置过程的一个环境设置改变。

在 serve 模式下两个推出门默认开启：`TREG_ARCHIVE_SERVE_ENDPOINTS` 是 `*`（策略允许的每个端点）且 `TREG_ARCHIVE_SERVE_PERCENT` 是 `100`（sha256 团队/端点 cohort 在低于 100 时仍适用）。allowlist 是逗号分隔的且混合三种条目形式：一个精确的端点 id、`capability:<prefix>`（整个家族 —— `capability:people.` 匹配能力以其开头的每个端点；`endpoint_served` 检查条目的能力），与 `*`。空服务于无 —— 回滚杠杆。一个 operator 通过把列表收窄到 id 或家族来分阶段推出；托管服务的 staging 计划在其私有 runbook 中。刷新 worker 在查询之后在 Python 中应用一个家族或 `*` allowlist（`serve_ids_only` 决定）。`TREG_ARCHIVE_SERVE_MAX_AGE_S` 保留每端点 operator 上限且 `TREG_ARCHIVE_HIT_REPEAT_PRICE_PERCENT`（10）是重复价格。

## 保守比较与受控服务(Conservative comparison and controlled serving)（2026-09-08）

比较设置与辅助被移除。旧的 `TREG_ARCHIVE_COMPARISON_MODE` 环境值被忽略，包括 `legacy_noise`。事件与 admin props 现在报告 `json`：对象顺序与空白默认被忽略。端点声明可以使用 `cache.ignore_paths` 进一步放宽比较；`archive_change_observed.masked_by_ignore` 报告被任一归一化或声明的字段排除拯救的字节改变。一个带此标志的空改变路径列表指示仅表示的改变。

TTL 学习与 lookup 保留原始行为：稳定的观察把计时器增长 1.5，改变观察减半它，且 TTL_NEVER 保持被尊重。固定的能力计时器只是初始/回退值。切换比较模式不重置既有的计时器、易变路径或累积计数器；新观察继续更新既有状态。没有独立的固定 TTL 模式或学习版本迁移。旧的稳定/改变计数器保持终生混合策略统计，而非严格比较的干净测量。`/admin/archive` 暴露那个警告加上比较模式、自适应 TTL 策略、端点 allowlist 与推出百分比。

服务现在需要三者全部：`TREG_ARCHIVE_MODE=serve`、逗号分隔的 `TREG_ARCHIVE_SERVE_ENDPOINTS`（默认空）中的一个精确端点 ID，以及 `TREG_ARCHIVE_SERVE_PERCENT`（默认 0）的准入。 `rollout_reason` 把团队 ID 加端点哈希到稳定的 0-99 桶；增加百分比保留既有的处理团队。超范围百分比禁用服务。空的调用方 cohort 也失败关闭。这些门在打开 lookup DB 会话之前运行。记录是独立的，因此未选择的团队与端点继续 live 调用与观察。一个 cohort 是一个实验分配，而非授权边界或缓存键修复。

只审查其请求头、账户上下文与重用权利适合既有遗留键的端点，然后再 allowlist；键 v2 仍是未来工作。

`TREG_ARCHIVE_REFRESH_DAILY_CAP` 现在默认 0，因此实验不会意外触发平台花费。显式启用的刷新需要一个非空的 serve allowlist 与有效的正向推出百分比；其候选查询被限制到 allowlisted 端点并使用同一有效 TTL 策略。在初始测量期间关闭它。

既有的 `tool_called` PostHog 事件携带 `cache_outcome`、`cache_mode`、`cache_comparison_mode`、`cache_ttl_policy`、`cache_rollout_percent`，以及当尝试时 `cache_lookup_ms`。快照查找额外暴露 `cache_age_s` 与 `cache_window_s`。结果区分 hit、key_missing、stale、snapshot_unavailable、body_missing、ttl_disabled、policy_excluded、caller_bypass、endpoint_disabled、rollout_disabled、missing_cohort、control、lookup_error、result_empty、result_error、result_unknown 与 not_attempted（或直接禁用查找的 mode_disabled）。缓冲的调用遥测也包括 `result_state`、`result_reason`、`cache_result_policy`（`hit_miss` 或 `legacy`）与 `cache_admission`（`eligible`、`empty`、`error`、`unknown` 或遗留的 `not_applicable`）。准入描述结果门，而非持久化成功或服务权限。业务 `hit` 是 true/false/null 使用同一分类器；没有启用规则的端点保持 null。`cached` 与 `cache_outcome=hit` 描述缓存重用，一个不同的事实。一个被拒绝的存储 body 出现在 `cache_outcome`；最终的 live 答案出现在 `result_state`。没有请求键、body、被忽略的字段路径或头被加到分析。既有的有界、有损分析 sink 被复用；不添加新的每命中 DB 行或额外的网络请求。`cache_lookup_ms` 包含门/DB/解压缩时间，而非仅 SQL；父事件上的 `duration_ms` 保持端到端调用计时。捕获漏斗之前的早期拒绝可能缺少缓存字段；缺失字段不是 miss。Shadow 仍只记录/学习：它不产生假设的命中计数或新鲜答案比较。

一个 hub 工具调用（`<team-slug>.<name>`，在自有工具与目录 id 都未命中之后在 `_execute_call` 中第三解析）在到达任何这些之前返回；它通过 `hub_runner.run_hub_tool` 而非 marketplace/relay 路径运行，因此下面没有任何东西适用于它。那个路径见 [hub](hub.md)。

## 资格 —— 三个门，按顺序(Eligibility — three gates, in order)

1. **种类(Kind)。** 只有一个 `data` 读取（目录的默认种类）被存储。`action` 改变世界；`utility` 是一个任务状态轮询或一个模型列表，其中存储的「running」会打破每个轮询器；`account` 回答关于调用方自己账户（余额、配额、自己 profile）的问题，在它被花费的那一刻就陈旧。 `archive.cacheable_kind`（更早只有 action 被排除）。
2. **许可(License)。** 每目录条目：`cache: forbidden | transient | archive` —— 要么一个裸字符串，要么一个来源 dict `{mode, license_quote, source_url, checked}`，完全像 `cost` 来源。 **缺失 ⇒ `archive_default_policy`**，自创始人的保留全部决定（2026-08-29）起是 `transient`：未判断供应商的 body 被保留为短寿命缓存，且 env 把它翻转回 `forbidden` 而无须部署。一个被判断的 forbidden（一个被读取且说 no 的许可 —— Finnhub）总是被尊重，且一个缺失条目从不存储。
3. **body 在手(Body in hand)。** 一个已计量平台答案已经为结算完全缓冲（`_buffer_response` 需要供应商报告的成本），因此记录不添加延迟。一个自有密钥目录答案只有当它适合归档的大小上限时才整体读取（见「自有密钥答案」）；更大的流式传输原样。自有工具调用（无目录条目）从不被触动。一个自有凭据答案可以服务于谁由其被记录于其下的 **键** 决定（「共享」）。

门 1+2 是 `archive.policy(entry)`；门 3 是钩子站点自己的上下文。

符合 `MarketplaceCall.streamable_free_result` 的成功免费最终获取绕过 lookup 与记录，即使其零额金钱生命周期仍被计量。它们没有缓冲的 body，因此不记录空的或部分 body/哈希。其他超过结算缓冲 8 MiB 限制的调用在记录之前失败且不能填充缓存或幂等成功。一个 spooled 答案（`spooled_response`，内联媒体）从磁盘上的证据结算且从不被记录：其 body 不在内存中，且多 MB 的生成媒体不是一个可重用的答案。

## 缓存键(The cache key)

`archive.cache_key(method, endpoint_id, upstream_url, body, headers, scope="")` → 在规范请求上的 sha256：大写方法、目录端点 id（一个供应商 URL 重排开始一个新鲜历史）、排序查询对、规范 JSON body 哈希（非 JSON 的原始哈希），加上仅来自调用方头的 `Accept` 与 `Accept-Language`，加上当答案非 public 时的共享 scope（`org:<id>` / `conn:<id>:<secret ids>`，见「共享」；一个 public 键像它总是那样哈希）。Auth/cookie/tracing/encoding 从不进入键 —— 且凭据无论如何也不能：注入在键被取之后发生。

## 表(Tables)（迁移 0002）

`ArchiveKey` —— 一个逻辑问题：`key_hash`（唯一）、`endpoint_id`、`provider`、有效 `policy`、AIMD 计时器状态（`ttl_s`，稳定重新获取时增长 ×1.5 封顶 / 改变时缩减 ×0.5 下限 —— 学习器在 PR 5 落地）、改变统计（`change_seen`/`stable_seen`/`last_changed_at`）、遗留 `volatile_paths`（为 schema 兼容性保留，不再读取或更新），与需求（`heat`、`last_requested_at`）。平台限定作用域，无 `org_id`：一个团队的获取可能温暖另一个团队的命中；一个自有凭据答案的覆盖是其 **键** 的 scope（`ArchiveKey.scope`，迁移 0039，以及折叠进哈希的 scope —— 见「共享」），快照的 `origin_org_id`（同一迁移）是来源，且 `ArchiveKeyOrg`（同一迁移）是每（org，键）的「已为该问题付费」标记，为重复命中定价 —— 见「命中定价」。

`ArchiveSnapshot` —— 一个版本：唯一 `(key_id, version)`、`逐字` body 字节、`content_hash`（原始 sha256）用于去重 —— 一个相同的连续答案存储一个 `body=NULL`、`body_of=<载体行>` 的版本行而非再次存储字节。Body 住在 Postgres 中（the `IdempotentCall` precedent）；超大的 body 被记录器跳过，从不截断。`origin` 说谁获取了：`caller` | `refresh` | `sample`。

## 归档绝不触碰什么(What the archive must never touch)

金钱。一个缓存命中只会 **标记** 既有记录「cached」—— 缓存命中的计费是一个显式推迟的创始人决定，且没有归档代码导入账本/计费。Relay 忠实性也随时间延伸：服务的字节恰是供应商发送的。

## 测试(Tests)

`tests/test_archive.py` —— 模式降级、默认拒绝策略、键规范化，与表往返；列在 CI 的串行 Postgres 作业中（绝不 xdist —— 共享数据库）。

## 面板(The panel)（PR 6）

`GET /admin/archive/panel` 服务 `src/treg/web/archive-panel.html` —— 一个无数据的页面 SHELL，刻意不认证：每个数字通过一个 fetch() 带着页面要求 operator 粘贴的 admin 令牌到达（保存在 localStorage；一个被拒的令牌重新打开门）。它每 5 s 轮询 `/admin/archive`，且一个被点击的端点行加载 `/admin/archive/keys?endpoint_id=`（键最新需求优先，每个带计时器状态与其最后 12 个版本，加上端点的近期调用事件带着其 `cached` 标志 —— 面板的 HIT/LIVE feed）。点击一个版本方块打开 `/admin/archive/body?key_hash=&version=` —— 存储的字节美化打印；一个去重引用跟随 `body_of` 到其载体并说哪个版本携带它；一个哈希仅版本诚实地回答什么也没保留。每个指标、chip、条、标签与版本方块携带一个 `data-tip` 弹出解释其自身 —— 面板预期被忘记了数字含义的人阅读，因此解释是产品的一部分，而非装饰。报告为面板获得了附加字段：每端点 `hits` 与 `kept_bytes`，与总计 `hits_today`、`refreshes_today`、`worker_on`、`refresh_daily_cap`。

## 运行总计(The running totals)（2026-09-03）

面板的报告读取 `ArchiveEndpointStat` —— 每端点一行（键、稳定、改变、快照、bodies_kept、kept_bytes、newest_fetch），只由记录器用原子列算术维护（credit-block 漂移是为何在计数器附近禁止读-改-写）。旧的每加载聚合在 prod 上 434k 键花费 9.9s + 8.0s + 14.8s；汇总读取在任何规模下都是毫秒。迁移 0013 从 live 归档一次性回填表并添加一个跨刷新来源快照的部分索引用于「今天的刷新」计数；一个 30s 进程内报告缓存保留作为针对轮询叠加的 belt（每个测试 beside  drains 清除）。

该行被每个团队共享，因此一个每记录 UPDATE 在它上面排队忙端点并留下每个调用一个死元组。因此一个记录在其自己的提交之后把其计数加到进程内 delta（`_count_stats`，因此一个丢弃或重试的记录不计任何东西），且 `flush_stats` 几秒后作为一个语句每端点落地 delta，按端点顺序因此两个进程不能死锁。刷新获取归档的写入信号量，因此它保持在归档的后台池预算内。`drain()` 等待一个被打断的刷新把其 delta 放回去，然后刷新它们；一个失败的刷新保留其 delta 给下一次。一个在刷新之间死掉的进程丢失那个窗口的计数：总计是一个员工报告，没有东西从它服务或计费。修剪器与团队删除仍直接减。只有当行存在时列算术才交换，因此一个端点的第一次记录在其自己的事务内创建该行，清零（`_ensure_stat_row`）；一个进程只在其一个记录以该行提交之后跳过该检查，绝不在一个未提交或已回滚的记录上。在第一次刷新之前的擦除然后从该行列减而非匹配无。

## body 压缩(Body compression)（2026-09-03）

存储的 body 在它缩小它们时用 zlib 6 级压缩（`enc` 列：NULL = 原始、「zlib」）；低于 256 字节的 body 保持原始。在 40 个真实 prod body 上测量：5.2x、68 MB/s 进、~1 GB/s 出 —— 记录器写入低于 1 MB/s，因此成本不可见且 ~6.5 GB/天变成 ~1.25 GB/天。每个 DB body 读取器解包（服务 lookup、去重载体跟随、调用结果读取器、面板的 body 查看器），因此调用方总是接收精确原始字节；`size_bytes` 与 `content_hash` 总是描述 RAW 字节，保持去重与统计语义不动。迁移 0014 之前的行保持原始且永远可读。创始人的键-对-值想法被检查并拒绝：压缩无论如何移除重复的 JSON 键，且从存储值重建 JSON 冒风险破坏哈希依赖的逐字节承诺。

## 修剪器(The pruner)（2026-09-03）

利润形状的货架清理：一个服务的命中是无供应商成本的收入，因此一个 body 对磁盘的权利是其盈利能力。 `prune_once` 只剥离 **字节** —— 每个版本行保留其哈希、大小与时间戳，每个键的最新版本保持完整（服务与改变检测需要它），决定性快照与其载体在后来的错误之后仍受保护，且剥离集在载体保护之前决定，因此一个存活的去重引用从不丢失其载体。移除排名：从不服务的键（TTL_NEVER）精确保留一个 body，年龄不是防御；然后旧的（在 14 天无需求的键上 `archive_prune_min_age_days` 7）版本超过最新的 `archive_prune_keep_versions`（2）。Archive-policy 端点被豁免 —— 它们的历史是未来的数据产品。从 lifespan 在刷新 worker 旁边运行，只要归档记录，`archive_prune_batch`（500）每 `archive_prune_interval_s`（3600）body 每通过；批 0 禁用。汇总计数器（bodies_kept、kept_bytes）只在剥离最后一个保留副本时原子地减少。被剥离的 `both` 行变成 `r2`，因此其逻辑保留计数不变。存活版本的 DB 载体保持受保护。不存在 R2 删除或修剪操作。

## 记录器节流(Recorder throttle)（2026-09-03，内存有界 2026-09-07）

至多 `_MAX_CONCURRENT_WRITES`（2）个记录同时接触数据库 —— 审计的精确循环界信号量模式（直到 2026-09-07 为四个；每个槽由每个 uvicorn worker 支付且再由每个滚动部署实例支付，且一个记录是对已在内存中的 body 的一次 INSERT）。在那之前，一个突发可以把至多 512 个并发短会话放在 API 的 15 槽池之前（SToneX 的池压力报告）；那些写入现在落在 **后台** 池上（`ops/deploy.md` § Database pools），因此信号量是内部界而非唯一界。排队的记录在它们的 fire-and-forget 任务内等待，因此调用方不受影响；30s 界覆盖等待+写入，因此一个卡住的队列仍脱落而非楔住。节流，而非脱落：突发测试证明所有 12 个并发记录都落地而峰值 DB 并发保持 ≤2。

**内存界(Memory bound)。** 每个待定任务在其闭包中持有其 `body` 字节，因此仅任务计数不足够的内存界。`_MAX_PENDING_BYTES`（256 MiB）在 DB 中限定待定工作的 body 字节：`record()` 当 **任务计数** 或 **字节** 阈值之一超出时脱落。done 回调在一个任务完成时释放字节，保持预算准确。独立的 R2 队列默认添加 128 MiB，在 SDK、压缩与终端证据开销之前总共 384 MiB body 预算。生产事件证据与部署大小在私有 operator runbook 中维护。

信号量是进程本地的；记录器也支持多进程部署。在信号量之前获取一个精确进程内键锁，因此重复记录排队而不消耗两个数据库写入槽且不相关的键继续移动；弱引用丢弃不活动的锁。一旦准入，写入器在读取最新快照与分配版本 N+1 之前锁定并刷新匹配的 `ArchiveKey` 行。刷新很重要，因为更早未锁的 lookup 已经填充了 SQLAlchemy 的身份映射。每键 Postgres 行锁序列化跨进程写入器；SQLite 在进程内由键锁保护。快照插入被显式刷新，且版本冲突传播到界定的外部重试以覆盖首键与多进程 SQLite 竞争。

## 键-端点权重修复(Keys-endpoint weight fix)（2026-09-03，池压力重复）

`/admin/archive/keys` 对每个键运行一个整行查询，只为了报告一个是否存在就把每个存储的 **body** 拖出数据库 —— 且面板为每个端点行（limit=100）触发它一次以填充 TTL 单元格：每页打开约 50 个接近同时的重调用。现在：版本来自 **一个** 仅列查询（`body IS NOT NULL` 读取头，绝不字节），且面板只从检查器自己的加载为 operator 点击的端点填充 TTL 单元格。TTL 列中的破折号意味着「点击以学习」。

启动使用归一化归档模式（未知值禁用它）。仅 R2 写入需要三个读取都是 `r2-first`；默认、EU 与 FedRAMP R2 端点被接受。dev smoke 脚本无桶参数且只接受 `treg-archive-dev`。

ObjectStore 拥有唯一的下载哈希验证；内存 fake 遵循同一契约。`put` 接受内部计算的内容哈希以避免重新哈希不可变字节。读取与写入错误使用同一分类。`R2ObjectStore._failure` 保留类型化的 auth/not-found/timeout 原因。obstore 0.11.1 把 HTTP 429/5xx 作为 `GenericError` 暴露且无 status 属性；只有那个 SDK 类型为其锚定的传输状态前缀被检查。裸数字与响应 body 内的 status 文本不符合。不记录或发出 SDK 文本；`ObjectStoreError` 只携带一个有界原因与底层异常类。真实轮(reel)循环回送测试 `test_real_obstore_http_status_classification` 覆盖 PUT/GET/HEAD 并证明零 SDK 重试。

修剪仍在双写期间剥离合格的 DB 字节。一个被剥离的 `both` 行变成 `r2`；其内容哈希与对象保持完整，且逻辑保留 body 统计不减少。既有的去重 DB 载体与结果基线保留其保护。admin body 查看器使用公共读取器并保留去重载体版本元数据。退役的 `volatile_paths` 保留在 schema 中但不再显示。

对于 R2-first 记录，`_ignored_matches` 也在结果状态需要惰性初始化时预分类最新快照。原始相同的字节复用当前响应；否则这共享预比较读取与截止，路径为 `initialization`。`_store_locked` 只接受该分类用于键锁下的实际最新快照。如果一个竞争或预比较截止留下无分类，写入器为那个精确最新快照/载体保留原始的仅 DB 惰性初始化。这保留一个既有的决定性结果当 R2 慢时；无可用 body 仍意味着未知基线。`change_outcomes` 计数器 `initialization_db_recovered` 与 `initialization_db_unavailable` 在该公共读取器之外报告这个最后的回退。写入器选择 body 存在而非加载 blob 用于去重，且绝不在其事务下执行对象 I/O。

`WritePlan` 是传入 DB 写入器的单一 body 保留决定。DB 保留从其存储位置推断；失败的合格仅 R2 上传变成 `db` 计划。每个开始的记录从一个 `finally` 块发出其完成报告，而队列回调释放预算并报告从未启动的任务的取消。`tool_called` 保持独立。对象存储 lifespan 选择一次真实或注入的上下文并总是重置接缝。

## 相同哈希上传去重(Same-hash upload deduplication)

`archive_bodies.prepare` 保留一个进程本地 20,000 个成功上传内容哈希的 LRU。一个 LRU 命中返回一个成功的 `WritePlan` 带 `upload_status=skipped_duplicate`、零新传输时间与无 PUT/HEAD。只有一个完成的带匹配 `ObjectInfo` 的 PUT 进入 LRU。失败与取消绝不会。当存储改变时 `configure` 重置缓存；重启或 LRU 逐出允许稍后的幂等重新上传。一个发现对象缺失或损坏的 GET 使其最近成功条目无效，因此既有的 live-refetch 路径可以修复它。

对于一个新哈希，`prepare` 在等待上传信号量之前注册一个在途 future。跟随者用 `asyncio.shield` 等待其结果，不持有信号量槽或 DB 连接，并在成功时报告 `upload_status=coalesced`。一个被取消的跟随者不能取消其 leader。一个被取消的 leader 释放跟随者到正常的 DB 回退并移除在途条目。所有跟随者共享失败原因；没有人为失败飞行发布 R2 指针。在途条目在每个出口被移除并保持在既有的已准入记录工作内。

`submit` 在 R2 计数/字节准入门之前检查最近的、排队的与在途的哈希。一个排队的哈希被同步注册，因此即使在后台任务启动之前的突发也只消耗一个 R2 待定条目与一个 body 大小的字节分配。重复记录反而使用归档既有的有界 DB 队列；`prepare` 在任何 DB 会话之前仍加入/跳过 PUT。每个已准入的调用保留其自己的历史/统计写入如初。重复从不变成无界工作：DB 队列的 512-记录/256 MiB 限制仍适用。不同 body 的突发仍可耗尽 R2 未改变的 256-记录/128 MiB 预算；增加那些设置不在此修复内。`duplicate_queue_bypass`、`skipped_duplicate` 与 `coalesced` 进程计数器补充既有的每记录 `archive_body_stored.upload_status` 值。

`timeout`、`rate_limited`、`upstream_error` 与有界 `store_error` 失败在非终端上传上得到一次重试。每次尝试上限为四秒与配置传输预算的 40%，因此两次尝试与抖动共享既有截止而非重启它。限流/上游重试保留 1.0-1.5 秒的抖动；超时/存储重试使用 0.05-0.15 秒。Leader 在该延迟期间释放上传信号量并在同一截止内重新获取它，而同 body 跟随者继续共享 leader 的结果。Permission、missing、hash、size 与不可用存储失败不被重试。耗尽在 `both` 模式下保持 `storage=db` 带 `upload_status=failed` 与分类的 `drop_reason`；DB 副本不被报告为丢弃。仅 R2 模式对合格字节使用同一 DB 回退。`archive_body_stored` 报告 `upload_attempts`、`upload_retry_reason` 与 `upload_retry_recovered`；有界进程计数器记录重试原因与恢复。不启用 SDK 重试，不添加额外的 DB 事务或新的列/表，且不改变生产设置。

R2-first 读取应用同一可重试原因策略。它们最多做两次 GET 尝试，每次上限为一秒与配置读取超时的一半，带至多 0.1 秒抖动。缺失对象、哈希不匹配、权限失败、超大对象与一个不可用的存储立即回退。一个可重试失败仅当第二次尝试也失败时记录为回退。Lookup 诊断添加 `cache_r2_attempts`、`cache_r2_retry_reason` 与 `cache_r2_retry_recovered`；有界进程计数器覆盖结果、终端与观察读取。DB 会话仍只在所有对象 I/O 完成之后打开。

### 计时与队列解释(Timing and queue interpretation)

在此修复之前，`upload_ms` 已经在获取上传信号量之后开始并在 `ObjectStore.put` 返回/抛出之后结束。非终端记录做一次尝试。信号量等待已经隔离在 `queue_wait_ms`；因此一个四秒失败的非终端 `upload_ms` 是 SDK/传输操作中的四秒，而非等待本地槽的四秒。锁定的 obstore 0.11.1 带 `max_retries=0` 在回送(loopback)回归中对一个 429 恰好发出一个 HTTP 请求；其配置的 SDK 重试计数保持零。两个事实都不识别生产网络/服务器操作的哪部分导致延迟。

在此修复之后，leader `upload_ms` 包含其传输预算下的所有尝试与抖动；`queue_wait_ms` 包含每次尝试的信号量获取。跟随者在 `queue_wait_ms` 中记录其共享飞行等待且零传输时间。LRU 命中有零传输/等待时间。不要把这些修复后每记录值解释为一次 SDK 请求的延迟，或把重复的重复状态与零传输失败等待者平均进物理 PUT 延迟。R2 待定记账也跨越记录的 DB 完成；它不只是活跃 PUT 的数量。在增加队列预算之前比较推出后的既有失败/丢弃原因、leader 计时与重复状态。

## 改变观察(Change observation)

在 `_store_locked` 提交之后，`_observe_change` 报告一个字节哈希改变，来自实际上驱动 TTL 学习的基线，仅对 `caller` 与 `refresh` 来源。缓存命中与异步终端证据从不发出 `archive_change_observed`。后台任务在既有的 30 秒 DB 阶段之后有一个独立的 3 秒观察预算。失败不能撤销或阻止记录。`_read_change_body` 在一个短后台会话中收集一个 `archive_bodies.pointer`，关闭它，然后调用 `archive_bodies.read`。观察跟随 `TREG_ARCHIVE_BODY_READ_LOOKUP`：默认 `db` 不做 R2 请求；`r2-first` 使用已验证 GET 且仅回退到后台池。它不能独立于既有的启动检查或回滚开关启用 R2。

`TREG_ARCHIVE_CHANGE_OBSERVATION_ENABLED=false` 禁用改变报告与其读取/CPU 工作（默认 true）。声明的 ignore-path TTL 比较仍是一个独立的决定机制。Ignore 比较与改变报告共享记录器/触摸信号量预算二，包括回退会话与 CPU 工作。在对象 I/O 期间不持有 DB 连接。不被策略/大小/存储保留的新 body 跳过观察。DB 模式读取也跳过已知的哈希仅先前快照；R2-first 可以在 DB 修剪之后恢复先前 body 的迁移对象。进程本地 `change_outcomes` 计数 `observed`、`body_unavailable`、`observation_failed`、`ignore_body_unavailable` 与 `ignore_comparison_failed`。`/admin/archive` 暴露这个映射与 `body_outcomes`（archive_bodies.outcomes），包括缓存报告响应；计数器在重启时重置且每进程，而非持久或 fleet 范围总计。

`_change_summary` 跑离事件循环。结构比较每个子树只访问一次而无重复的 JSON 序列化，保留类型敏感比较。取消保持信号量槽被占用直到有界大小的 CPU 工作完成；asyncio 超时不会停止一个 Python 线程。JSON 差异使用点路径，把数组索引折叠为 `[*]`，停在六层并保留前 20 个排序的不同路径。`path_count` 在截断之前计数所有不同路径；`truncated` 标记多于 20。添加/移除字段、数组长度与类型改变计数；在深度边界的改变容器在其边界路径计数。根改变使用 `$`。`leaf_count` 计数同深度边界的新 body 叶子（空容器计为一个）。仅字节的空白/键顺序改变可以有零改变路径。非 JSON 对使用 `changed_paths: [non_json]`、`path_count: 1`、`leaf_count: 0`。`sole_path` 是当计数为一时唯一路径，否则 null。

分析发出 `archive_change_observed` 带不同 ID `archive` 且只有 `endpoint_id`、`provider`、`changed_paths`、`path_count`、`truncated`、`leaf_count`、`sole_path` 与 `masked_by_ignore`（仅当一个声明的 ignore 比较实际拯救一个稳定的 TTL 决定时为 true）。路径报告使用那同一个 TTL 基线，包括跨干预的未知/错误观察的结果感知端点的一个更旧的决定性快照。无值、body 片段、调用引用或键身份被发送。路径是来自 JSON 的结构属性名；这些报告不是一个 schema 也不是一个字段可安全忽略的证据。观察是只读的且不改变准入、学习、存储字节、去重或服务。

### 七天 HogQL 审查(Seven-day HogQL review)

粘贴进 PostHog SQL 编辑器。每端点/路径一行；所有比率使用该端点观察到的字节改变作为分母。`sole_change_ratio` 计数仅那个路径改变的事件；`endpoint_sole_ratio` 计数任何 sole-path 改变。空路径列表保留在总计中。截断使每路径比率成为下界，因此在选择一个列表之前检查 `truncated_ratio`。缺失 body 与丢弃的分析不在这些分母中。`non_json` 是一个标记，而非一个 ignore 候选。SQL 使用 PostHog 支持的 [JSON/array 函数](https://posthog.com/docs/sql/clickhouse-functions)。

```sql
WITH observed AS (
    SELECT properties.endpoint_id AS endpoint_id,
           properties.sole_path AS sole_path,
           toInt(properties.path_count) AS path_count,
           properties.truncated = true AS truncated,
           JSONExtract(ifNull(toString(properties.changed_paths), '[]'), 'Array(String)') AS paths
    FROM events
    WHERE event = 'archive_change_observed'
      AND timestamp >= now() - INTERVAL 7 DAY
), totals AS (
    SELECT endpoint_id, count() AS changes,
           countIf(path_count = 1) / count() AS endpoint_sole_ratio,
           countIf(truncated) / count() AS truncated_ratio
    FROM observed GROUP BY endpoint_id
), per_path AS (
    SELECT endpoint_id, path, count() AS path_changes,
           countIf(sole_path = path) AS sole_changes
    FROM (SELECT endpoint_id, sole_path, arrayJoin(paths) AS path FROM observed)
    GROUP BY endpoint_id, path
)
SELECT totals.endpoint_id, totals.changes, per_path.path,
       per_path.path_changes / totals.changes AS path_ratio,
       per_path.sole_changes / totals.changes AS sole_change_ratio,
       totals.endpoint_sole_ratio, totals.truncated_ratio
FROM totals LEFT JOIN per_path ON totals.endpoint_id = per_path.endpoint_id
ORDER BY totals.changes DESC, path_ratio DESC, per_path.path
```

## JSON 比较与声明的忽略路径(JSON comparison and declared ignore paths)

每个保留的调用方/刷新响应使用 `_ignored_matches`，即使无 `cache.ignore_paths`。`_normalized_hash` 解析一个私有 JSON 副本，只删除声明的路径，然后以排序对象键与紧凑分隔符哈希 JSON。数组顺序、长度、类型与未忽略的值保持显著。重复对象键、解析会丢失精度的数字、无效 JSON 与不可用 body 回退到原始字节哈希。原始字节、内容哈希、去重、历史与服务的响应从不改变。

`cache.ignore_paths` 是可选的且默认空；只有显式声明排除字段。people 与 company enrichment 端点声明其供应商在每次请求改变而不改变答案的字段：作业与请求 id、credit 计数器、验证与处理时间戳、分页游标（Hunter 的 `data.verification.date` 是原始例子）。没有声明，这样一个字段使每次重新获取计为改变并缩小一个没有移动的答案的计时器。邮箱值、分数、验证状态与 found/empty 转换保持显著。`test_catalog_preserves_ignore_paths_and_defaults` 钉住已发布的声明，因此添加一个意味着扩展那个列表。其他试点端点声明无忽略字段，包括 Findymail 的 `contact.id`。一个仅用于比较的映射不覆盖保留策略也不断言供应商许可许可。没有自动字段选择；`ArchiveKey.volatile_paths` 保持未使用。

路径段可以以数字开头，且 `[*]` 选择数组元素。缺失路径是无操作。删除 `items[*].request_id` 保留所有元素；删除 `items[*]` 删除数组内容。比较没有六级报告限制且从不用报告/截断的路径作为策略。

`_ignored_matches` 在 DB 写入之前最多预加载最新与决定性快照 body。它先检查键与原始哈希，除非一个有可读 body 指针的不同候选，跳过新的响应 JSON 归一化。新的键与原始相同基线因此不需要归一化；相同的原始哈希也跳过 body 读取。指针会话在 JSON 归一化或对象 I/O 之前关闭。预读取使用共享归档信号量与三秒预算，独立于写入截止。

只匹配的快照 ID 被传给 `_store_locked`；一个并发改变基线回退到原始哈希而不跨 I/O 持有行锁或添加协调写入。`ignore_body_unavailable` 与 `ignore_comparison_failed` 对默认 JSON 比较与显式字段排除保留其诊断名。报告可以独立禁用；TTL 比较保持活跃。

`changed_paths` 与 `masked_by_ignore` 描述实际用于学习的基线。后者现在覆盖默认归一化以及声明的路径。结果感知端点使用它们最后的跨未知/错误响应的决定性 found/empty 快照；遗留端点使用最新的。重复的空结果不学习或发出改变事件。Ignore 规则从不放宽准入、掩码 found/empty 转换或改变缓存计费。既有的 TTL/计数器不被部署回填；生产 operator 上限独立于历史学习 TTL 限定服务的年龄。

## Leadsforge email 缓存试点(Leadsforge email cache pilot)

`leadsforge.people.email.find` 使用严格结果准入：一个 `succeeded` 响应需要一个带基本邮箱/域形态的非空 email 字符串；无 email 的 `not_found` 是空。其他状态/字段组合是未知且不能服务。这是结果验证，而非邮箱可投递性验证。历史字节保持不变并在 lookup 时被重新分类。

`TREG_ARCHIVE_SERVE_MAX_AGE_S` 是一个精确端点 ID 到正整数秒的 JSON 映射（默认空）。它是一个 operator 新鲜度上限，独立于供应商声明。Lookup 取学习 TTL、供应商上限、operator 上限与调用方 max-age 的最小值；`TTL_NEVER` 保持权威。刷新 worker 也尊重 operator 上限用于其 80% 到期阈值。它不重置或重写历史学习计数器。`/admin/archive` 报告 `serve_max_age_s` 以便 operator 可以验证运行配置。全局团队 cohort 百分比不变。生产试点值与回滚在 treg-internal 中。

遗留归档链接回填接受一个显式的数据库连接（`--dsn` 或 `TREG_DATABASE_URL`）。它不提供网络访问或读取云凭据。
