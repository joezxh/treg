---
title: 数据模型(data model) — 注册表表、异步 DB、审计写入器
status: shipped
sources:
  - src/treg/alembic/versions/0042_pinned_read_scope.py
  - alembic.ini
  - src/treg/alembic/env.py
  - src/treg/alembic/versions/0001_baseline_current_schema.py
  - src/treg/alembic/versions/0002_archive_tables.py
  - src/treg/alembic/versions/0003_callrecord_cached.py
  - src/treg/alembic/versions/0004_archivekey_request_shape.py
  - src/treg/alembic/versions/0005_capacity_policy_snapshot.py
  - src/treg/alembic/versions/0006_overflow_route.py
  - src/treg/alembic/versions/0007_overflow_spend.py
  - src/treg/alembic/versions/0008_org_platform_overflow_disabled.py
  - src/treg/alembic/versions/0009_callrecord_hit.py
  - src/treg/alembic/versions/0017_async_task_record.py
  - src/treg/alembic/versions/0018_async_resource_ownership.py
  - src/treg/alembic/versions/0019_async_poll_failures.py
  - src/treg/alembic/versions/0020_callrecord_created_at_indexes.py
  - src/treg/alembic/versions/0021_ledgerentry_org_created_at_index.py
  - src/treg/alembic/versions/0022_org_spent_today_counter.py
  - src/treg/alembic/versions/0023_callrecord_org_user_created_at_index.py
  - src/treg/alembic/versions/0024_membership_calls_today_counter.py
  - src/treg/alembic/versions/0027_enrich_arena.py
  - src/treg/alembic/versions/0028_arena_insights.py
  - src/treg/alembic/versions/0029_arena_verification_snapshot.py
  - src/treg/alembic/versions/0011_callrecord_archive_link.py
  - src/treg/alembic/versions/0015_idempotentcall_membership_cascade.py
  - src/treg/alembic/versions/0053_idempotentcall_membership_expires_index.py
  - src/treg/alembic/versions/0054_callrecord_org_id_id.py
  - src/treg/alembic/versions/0061_remove_redundant_unique_indexes.py
  - src/treg/alembic/versions/0091_remove_prefix_covered_indexes.py
  - src/treg/alembic/versions/0034_managed_api_keys.py
  - src/treg/alembic/versions/0035_default_key_generation.py
  - src/treg/alembic/versions/0036_activity_key_indexes.py
  - src/treg/alembic/versions/0038_endpoint_day_stats.py
  - src/treg/alembic/versions/0074_endpoint_stat_dirty.py
  - src/treg/infra/catalog_stat_dirty.py
  - src/treg/maintenance.py
  - src/treg/web/sitetrack.js
  - src/treg/models.py
  - src/treg/alembic/versions/0052_async_task_hit.py
  - src/treg/alembic/versions/0031_archive_result_admission.py
  - src/treg/alembic/versions/0032_archive_body_storage.py
  - src/treg/alembic/versions/0039_archive_own_key_and_repeat_pricing.py
  - src/treg/alembic/versions/0043_provider_resources.py
  - src/treg/domain/provider_resources.py
  - src/treg/routers/provider_resources.py
  - src/treg/alembic/versions/0033_signup_promo_eligibility.py
  - src/treg/alembic/versions/0071_signup_promo_claim.py
  - src/treg/alembic/versions/0041_searchlog.py
  - src/treg/alembic/versions/0055_find_v2_log.py
  - src/treg/alembic/versions/0056_searchlog_verdict.py
  - src/treg/alembic/versions/0065_call_verdict.py
  - src/treg/alembic/versions/0066_endpointdaystat_verdicts.py
  - src/treg/alembic/versions/0070_api_key_spend_rollup.py
  - src/treg/alembic/versions/0072_callrecord_call_ref_index.py
  - src/treg/alembic/versions/0073_org_flow_control_version.py
  - tests/test_org_flow_control_schema.py
  - src/treg/alembic/versions/0075_ad_click_stash.py
  - src/treg/alembic/versions/0079_enterprise_sso.py
  - src/treg/alembic/versions/0082_oauth_sso_provenance.py
  - src/treg/alembic/versions/0083_enterprise_sso_safety.py
  - src/treg/alembic/versions/0084_enterprise_workos_cleanup.py
  - src/treg/alembic/versions/0085_enterprise_sso_blocks.py
  - src/treg/alembic/versions/0087_rankings_snapshot.py
  - src/treg/alembic/versions/0088_call_usage_rollup.py
  - src/treg/alembic/versions/0089_ledgerentry_settle_spend_index.py
  - src/treg/alembic/versions/0090_ledgerentry_topup_index.py
  - src/treg/application/call_usage_rollup.py
  - src/treg/application/call_usage.py
  - tests/test_call_usage_rollup.py
  - src/treg/timeutil.py
  - src/treg/infra/db.py
  - src/treg/infra/money_timing.py
  - src/treg/infra/money_admission.py
  - src/treg/infra/kv.py
  - src/treg/infra/money_admission_reporting.py
  - src/treg/infra/money_trace.py
  - src/treg/infra/money_trace_runner.py
  - src/treg/domain/referrals.py
  - src/treg/audit.py
  - src/treg/application/evidence_retention.py
  - src/treg/analytics.py
  - src/treg/bootstrap_handlers.py
  - src/treg/ratestore.py
  - src/treg/application/auth.py
  - tests/test_postgres_reset.py
  - tests/test_alembic_expand_safety.py
  - tests/test_redundant_index_migration.py
  - tests/test_api_keys.py
  - tests/test_money_timing.py
  - tests/test_money_admission_reporting.py
  - tests/test_kv_lease_diagnostics.py
  - tests/test_money_trace.py
  - tests/test_money_trace_postgres.py
  - tests/test_money_trace_runner.py
related:
  - architecture/archive.md
  - architecture/proxy-model.md
  - architecture/auth-secrets.md
  - architecture/ads-conversions.md
---

# 数据模型(data model)

修订 `0077` 添加了空的 `TeamDatabase` 与 `TableDoc` 控制平面表，用于 [Workbench 表存储](workbench-storage.md#management-metadata)。它不配置远程数据库或业务行。既有表与数据不被该迁移改变。

迁移 `0079` 添加 `EnterpriseSSO`（团队的套餐、订阅状态、WorkOS organization、连接与目录）；`EnterpriseSSOIdentity`（稳定的团队专属 SSO profile 链接）；`EnterpriseDirectoryUser`（目录名册，包含从未登录过的用户）；`EnterpriseSSOEvent`（WorkOS webhook 去重）。团队删除在其 `Org` 之前移除团队限定行，且活跃订阅在取消前阻止团队删除。迁移 `0083` 记录 SSO 是否创建了一个成员资格、在其团队内使一个 IdP subject 唯一、为每个团队保留一个待定的企业 Checkout、并标记在 SSO 强制下签发的密钥。既有密钥没有 SSO 签发证明，无法进入一个被强制的团队。迁移 `0084` 记录 WorkOS 清理何时完成。那个标记使取消重试幂等，并在仍有可计费的 WorkOS 资源时阻止一次新的 checkout。迁移 `0085` 回填并以最小的 `EnterpriseSSOBlock` 行把手动移除决定与身份行分开存储。那些行在连接清理后保留，但随团队或被擦除的用户一起离开；它们不含邮件或 WorkOS 标识符。

迁移 `0043` 添加 `ProviderResource`，即既有异步所有权行的持久、组织所有的对应物。它存储供应商、资源种类、上游 id、显示名、创建者、来源调用、生命周期状态与时间戳。`(provider, resource_kind, upstream_id)` 全局唯一，因此一个共享账户对象无法被分配给两个组织。删除把行 tombstone 化，保留重试授权与可审计性。`GET /orgs/{org_id}/provider-resources` 只暴露活跃成员的组织，并按供应商/种类过滤。BYOK 对象从不写到这里。

修订 `0027` 为 [Enrich Arena](../interface/enrich-arena.md) 添加 `ArenaRun` 与 `ArenaEvaluation`。运行冻结加密的输入、适配器请求、结果收据；评估记录一个不可变的偏好，带有暴露的候选集与反馈上下文（自版本 2 起归因）。两者都是创建者/团队限定作用域，并在 30 天后过期。运行通过条件更新认领；一个唯一的 run-id 评估约束与 run-row 锁把并发反馈串行化；查看结果不提交一次投票。这些表没有写余额的职责。

`AsyncTaskRecord` 是一个由原始 `call_id` 键控的延迟已计量提交：`org`、供应商、端点、提取的任务 id、可选的 fetch/result id、可选的已验证动态轮询 URL、预留的微元-USD、冻结的描述符/basis/请求证据、调度尝试、状态与完成/错误字段。迁移 `0017` 添加该记录，`0018` 仅扩展式地添加可空、已索引的结果 id 并添加 `AsyncResourceRecord`：一个 org/供应商/资源-种类/id 所有权元组，用于其计费不使用延迟 hold 的遗留异步对。它们随行为一起发布，因为旧代码忽略这些新增项，而新代码在没有它们的情况下无法安全地保留一个异步 hold 或授权一个共享供应商结果。

修订 `0069` 向 `AsyncTaskRecord`、`AsyncResourceRecord` 与 `ProviderResource` 添加可空的 `key_slot`：该对象所位于的 treg 自有账户的标签，因此其轮询、获取与编辑使用那个账户（[代理模型](proxy-model.md)「多个 treg 拥有的账户」）。NULL 是每一个更早的行，且意味着主账户。

修订 `0052` 添加可空的 `hit`：原始提交的最终联系判定。最终终结器随结算提交它。审计写入器在插入一个提交 `CallRecord` 之前锁住任务行，因此一个率先完成的轮询仍给那一行其最终判定；当审计行赢得竞争时，终结器排队一个后台修正。两者都使用原始 `call_ref`，包括路由子项。一个确认的终端失败为带有已验证结果规则的端点存储 `false`，因为那次尝试未产生命中。一个待定或超时的提交保持未决定。修订 `0065` 在其旁添加可空的 `verdict` 词，由同一个终结器写入并经由同一个插入与修正复制；只有一个成功的终端答案携带一个。

迁移 `0019` 添加 `consecutive_failures`，保留服务器默认零，以允许推出期间的旧写入器。有效的轮询重置它；失败把重试延迟增长到 15 分钟。`attempts` 也充当一个认领版本：旧 worker 无法覆盖一个更新的认领。调用方轮询可以独立终结原始任务；终端状态守卫防止重复计费。

迁移 `0031` 添加可空的 `ArchiveKey.result_state`、`result_snapshot_id` 与 `result_observed_version`。归档拥有它们：最后一个决定性结果与最新历史响应无关。不发生回填或 TTL 重置；遗留观察被惰性分类。见 [归档结果准入](archive.md#result-admission)。迁移 `0032` 添加可空的 `ArchiveSnapshot.body_storage`（`db`、`both`、`r2`；NULL 使用遗留 DB 路径）。归档仍是唯一的写入器。一个 R2 位置只在一次已验证的上传在任意 DB 会话之外完成后才发布；`content_hash` 是对象名。不发生新索引、回填、body 列移除或破坏性迁移。双写行保留其 DB body/载体；R2-only 行不需要载体指针。见 [归档](archive.md#body-storage-and-r2-double-writing)。迁移 `0039` 添加可空的 `ArchiveSnapshot.origin_org_id`（其自有凭据获取了该答案的团队；NULL = treg 的平台密钥，其前的每一行——来源）、可空的 `ArchiveKey.scope`（`org` 或 `conn` 用于一个私有到某 org 或某连接的键；NULL = public，其前的每一个键——共享 scope 也被折叠进键哈希）以及 `ArchiveKeyOrg` 表，在 `(org_id, key_hash)` 上唯一：哪些团队已为哪些已归档问题付费，由归档在已计量的 settle 事务内写入，并由 lookup 读取以给一次重复命中定价。见 [归档](archive.md#own-key-answers)、[共享](archive.md#sharing-whose-question-is-it) 与 [命中定价](archive.md#pricing-a-hit)。

修订 `0033` 添加可空的 `User.email_verified_at` 与非空的 `signup_promo_available`，对既有行保留数据库默认 false 以及旧写入器。新的应用用户显式插入 true。余额或历史金钱条目不变。成功的邮件证明设置验证；只有原子的身份声明消耗可用性，与注册赠送一起提交。见 [注册资格](money.md#signup-credit-eligibility)。

修订 `0071` 添加 `SignupPromoClaim`（`inbox` 主键，`user_id` 无 FK，`created_at`）：每个收到注册礼物的邮箱一行，与用户级声明一起暂存。它从已验证但不再合格的用户回填。

## Org 流控制配置存储(Org flow-control configuration storage)

修订 `0073` 添加 `OrgFlowControlVersion`（`orgflowcontrolversion`），由 `(org_id, version)` 键控。每一行存储一个必需的完整 `config` 快照（PostgreSQL 上是 JSONB，SQLite 上是 JSON）、创建者、原因与 UTC 创建时间。发布元数据记录 `unpublished`、`pending`、`published` 或 `failed`，带有可选的发布者与发布时间；`published` 要求两者都有。主键支持每 Org 历史，且 `ix_orgflowcontrolversion_publish_status` 支持有界的发布状态扫描。

这只是存储：还没有配置 API、发布器或调用路径读取器。schema 强制执行唯一正版本与有效的发布元数据。递增版本分配、JSON schema 验证与不可变快照是管理写入器的职责；该迁移不授予那个写入器访问权，也不禁止任意 SQL 更新。不回填行且既有请求准入不变。`org_id` 没有外键，使该迁移独立于对余额表的锁。`cascade_delete_org` 显式地在其 Org 旁边移除该历史。管理写入器必须在其清理开始之前验证 Org 存在并与 Org 删除协调保存；直接 SQL 写入或删除没有数据库强制的引用完整性。一个应用回滚把表留在原地；一个 schema 降级删除其保存的历史。

## 注册表表(Registry tables)

- **`Feedback`** - 持久的团队限定问题报告与建议。包含提交的类别/消息/引用、已认证的 org 与用户归因，以及针对该团队调用记录或账本验证过的引用。修订 `0025`；`domain.feedback` 拥有插入；`application.feedback` 提交。团队删除移除这些行。见 [feedback](feedback.md)。
- **`Media`** - 一个成员为供应商获取而托管的引用文件（`treg host`）：不透明的令牌、org、媒体类型、大小、字节（`body`）或持有它们的对象存储键（`object_key`）、创建与过期。修订 `0037`、`0092`；`application.media` 是唯一的写入器，并在每次上传时清扫一批过期行（它们的对象经一个后台删除器与桶生命周期规则）。团队删除移除这些行；它们的对象随后不命名任何东西，并随桶的生命周期规则离开。见 [media](media.md)。
- **`FeedbackHandling` / `FeedbackHandlingEvent`** - 内部当前处理状态与带版本的（修订 0030）历史，由该 schema 拥有，且只由私有管理服务端服务写入。两者都从原始报告级联。见 [feedback](feedback.md)。

`src/treg/models.py` 对列、索引与默认值是权威的。本节记录字段声明本身无法解释的归属与行为。[多租户](multi-tenancy.md) 定义 org 限定作用域与角色门。

修订 `0010` 向 `PendingOAuth` 与 `Secret` 添加 `authorization_method`，把既有 Instagram 授权回填为 `facebook-page`，并区分新的 `instagram-login` 授权。选择使用这个元数据，绝不使用加密令牌的形态。

- **`Org`** - 拥有资源的租户：`id, name, slug`（唯一）、`previous_slug`（上次重命名前的 slug，仍作为别名解析）、`suspended`（管理员锁）、`demo`（由 [onboarding](../interface/onboarding.md) 播下种子的一个沙箱团队 —— 带标签 + 可移除）、`public_demo`（其成员令牌被发布(PUBLISHED)的团队，例如在落地页上 —— 非管理员成员被锁定到 `/call` + 读取，且绝不能作为用户行动；在 `domain.identity.access.require_member` / `require_identity` 中门控）、`created_at`。**`ad_gclid`/`ad_click_id_type`/`ad_click_at`/`ad_landing`**（迁移 A37，全部可空）— 在注册时一次性设置，来自第一方 `treg_ad` cookie；绝不覆盖。历史上命名的 `ad_gclid` 持有点击值；`ad_click_id_type` 表示 `gclid`/`gbraid`/`wbraid`，NULL 表示遗留 GCLID。**`utm_source`/`utm_medium`/`utm_campaign`/`utm_term`/`utm_content`/`utm_referrer`**（迁移 A40，全部可空）— 来自第一方 `treg_utm` cookie（`web/sitetrack.js`，在访客的 **第一个** 页面上设置，首次接触(first touch)获胜，90 天）的第一接触流量来源，在两个门都在注册时持久化一次。这是回答「活动 X 带来了多少个团队」的列集 —— `ad_*` 列只知道 Google 点击。`utm_referrer` 是引用主机名，即使没有 `utm_*` 标签存在也保留。**`first_call_at`**（与 `ad_*` 同一迁移）— 由 `/call/` 处理器中的一个受守卫 UPDATE 一次性设置，刻意 **不** 从 `CallRecord` 派生（后者在负载下 `audit.py` 会丢弃，恰在流量最高时少计）。两者都供给 [ads-conversions](ads-conversions.md)。
- **`User`** - 一个 **全局身份** 而已：`email`（唯一）、`is_superadmin` + `suspended`（平台标志，见 [super-admin](super-admin.md)）、`token_version`（撞(bump)以吊销该用户持有的每个会话 cookie + 身份令牌 —— 签名令牌携带其被铸造时的 `tv`；见 `make_session` / `make_identity` / `auth_revoke_tokens`）、`onboarded`（完成/跳过了首跑）、`demo`（一个假的引导队友 —— 无法登录，从统计中排除）、`created_at`。（令牌 + 角色移到了 `Membership`；一个在 N 个 org 中的用户有 N 个成员资格。）
- **`Membership`** - 把用户链接到一个 org：`user_id`、`org_id`、`role`（owner|admin|member）、`token_hash`（第一个 bearer 凭据的兼容哈希）、`webhook_url`（健康告警 POST 到这里）、`daily_call_cap`（每用户、每日用量上限；**-1 = 无限**，默认 —— 见 `governance/usage.enforce_daily_cap`）带有 `calls_today` / `calls_today_day`，上限被对照检查的计数器（每个受限事件一次条件 UPDATE，修订 0024；只有受限成员被计数，名册读取日志）；唯一 `(user_id, org_id)`。**一个令牌 = 一个 `(user, org)` 对。** `ROLE_RANK` 排序角色。
- **`ApiKey`** — 一个凭据控制行。它保留 `org_id`、可空 `membership_id`、保留的身份标签、kind、name、安全前缀、可选唯一 SHA-256 哈希、state、`default_generation`、生命周期时间、创建者、替换 id，以及可选的 SSO 签发团队。一个人类成员资格对签名的身份密钥有一个 `default_human` 行，并可以有许多 `additional_human` 行。一个作用域受限的 agent 有一个当前 `agent` 行。`legacy_human` 行在兼容发布期间保持旧存储的成员令牌可用；新人类成员资格把旧的令牌哈希字段留空且不创建遗留行。被吊销的行保留用于审计。附加/agent 轮换把前驱标记为从正常清单中隐藏，同时保留其替换链接、事件与 Activity 快照。成员资格移除清除它们的成员资格链接。默认轮换改为自增同一行的 generation 并只使该团队先前的签名令牌失效。`last_used_at` 是节流的、尽力而为(best-effort)的展示元数据；它不被写在认证事务中。
- **`ApiKeyEvent`** — 密钥管理审计轨迹：团队、密钥、操作者、保留的身份、动作与时间。它从不存储完整的密钥。
- **Activity 密钥快照** — `CallRecord` 与 `RunRecord` 保留可空的 `api_key_id`、name 与安全前缀。旧记录保持未分配。新记录在其轮换、吊销、隐藏或成员资格移除之后保留其安全密钥身份。
- **`Invite`** — 一次性加入码：`org_id, email, role, code_hash (idx), status`（pending|accepted|revoked）、`invited_by`。携带第二个拆分机密，`email_token_hash (idx, nullable)` — 仅嵌入在邀请邮件链接中的收件箱专用登录令牌（管理员可见的码只用于加入，绝不是认证因子）；首次使用时置空（每链接一次登录），在拆分前的邀请上为 NULL（它们回退到预填登录流）。见 `api.auth_invite_signin`。
- **`Secret`** - 一个存储的凭据：`org_id`（FK，idx）、`name`、`owner`（创建者邮件）、`kind`（`env` | `secret_file` | `oauth` | `cli_auth` | `param`）、`value`（**静态 Fernet 加密**，从不返回）、`bundle_id`（FK），以及健康字段 `health_status`（`unknown`|`ok`|`invalid`）/`health_detail`/`health_checked_at`。`param` 是一个非机密值（项目/org id）像 secret 一样注入但从不健康检查。**连接元数据**（为注册表铸造的 OAuth 连接设置 —— 见 OAuth marketplace / `oauth_providers.py`；为空表示上传的或自带 app 的凭据）：`provider`（**已索引** — 哪个精选注册表供应商铸造了它）、`granted_scopes`（空格连接的，用户 **实际** 同意了什么）、`resource_ref` + `resource_name`（该连接所作用的选定 site/property/account，加上其人类标签，因为上游 id 是不透明的）。**过期是一个独立于 `health_status` 的轴** — `health` 说「它工作吗」，过期说「它还能工作多久」（一个不可刷新的令牌在它悄然死亡前一直保持健康）：`expires_at`、`last_refresh_at`、`last_error`。
- **`Tool`** - 一个可调用能力：`org_id`（FK，idx）、`name`（**按 `(org_id, name)` 唯一**）、`owner`、`base_url`、`host`（base_url 的 netloc，**已索引** 用于 URL-透传解析）、`bindings`（一个 **JSON 列表** — 见下）、`health_check`（可选 JSON）、`examples`（可选 JSON 列表 `[{method,path,note}]` 在 dashboard 中暴露）、`cli`（可选的 JSON 本地运行配置，用于 `treg run --local` — 见 [local-run](local-run.md)）、`bundle_id`（FK）。
- **`Bundle`** - 一个技能(纯打包)：`org_id`（FK）、`name`、`owner`、`recipe`（SKILL.md 文本）、**`files`**（JSON `{relpath: content}` — 文件夹的其余部分：参考文档、脚本、嵌套子目录，减去机密 + 二进制，因此整个技能文件夹经 `skill install` 旅行），把它的 secret + tool(s) 分组。**两个** `treg run` 层级的运行配置现在都位于 **`Tool.cli`** 上（工具侧统一，PR #3）；旧的 bundle 侧 `runtime`/`package`/`entrypoint`/`runnable` 列被一次启动迁移折叠进 `Tool.cli` 且不再声明（它们可能在旧 DB 中物理上存在，未被读取）。
- **`PendingOAuth`** - 一个在途连接流：`org_id`（FK）、`state`（唯一，CSRF/查找键）、`client_id`、`client_secret`（加密）、`auth_uri`、`token_uri`、`scopes`、`redirect_uri`、`status`（`pending`|`done`|`error`）、`secret_id`（成功时创建的 secret）、`detail`。**Marketplace/怪癖字段**，全部默认，通过重定向携带，因此回调以构建同意 URL 完全相同的换码：`provider`（这个连接针对哪个精选注册表供应商 —— 自带 app 连接为 `""`）、`code_verifier`（PKCE；`""` = 未使用）、`auth_params`（额外同意 URL 查询参数的 JSON）、`token_endpoint_auth_method`（`client_secret_post` 默认）、`client_id_param` + `scope_separator`（TikTok 把 client id 拼作 `client_key` 并用逗号连接 scopes）、`long_lived_exchange`（仅 Meta — 在存储前把短期令牌换成约 60 天的那个）、以及 `replaces_secret_id`（这个同意 **替换** 哪个既有连接 — null = 添加一个新连接，因此回调不再需要按供应商 blanket-替换）。
- **`CallRecord`** 记录 org、调用方、tool、方法、路径、状态、计时与调用方归因。它的 `kind` 是 `call`、`local_run`，或者针对一次已授权的免费平台状态读取的 `async_poll`。轮询行仍按调用引用可用并在管理员诊断中可用，但 `/calls` 在分页之前排除它们。不需要迁移或历史重分类。

  **它的索引是平台的吞吐量。** 它是最大的表，且每个时间窗口问题都需要一个兼容的 `created_at` 索引。没有它，索引携带意味着规划器为另一列选择一个索引并在内存中过滤日期，读取一个端点或 org 的整个历史来回答一个有界的问题。修订 0020 添加 `(endpoint_id, created_at)` 用于目录观察刷新，以及 `(org_id, created_at)` 用于每成员每日计数；0016 已经为最新-N feed 配对 `(endpoint_id, id)`，0012 为 `cached` 添加一个部分索引。把这个搞错的代价不是一个慢页面：所有三个连接池共享一个 Postgres，因此这里的一次扫描把每个其他查询排队，API 池清空进 `503 treg_saturated` — 见 [deploy](../ops/deploy.md) § Database pools。该表还没有保留清扫，因此它只增长。

  **目录可靠性读取计划折叠。** 它的缓存刷新不再聚合原始审计行。目录统计与 Arena 滚动洞察 worker 按主键增量遍历审计行。修订 0038 添加目录的每日读取模型：`EndpointDayStat`（每个端点每个 UTC 天一行：计数、最新成功、命中统计与一个有界的延迟样本，加上 `verdicts`，每个判定词的调用数，由 `0066` 添加可空；主键 `(endpoint_id, day)`，由 `day` 索引用于窗口修剪）以及单行的 `EndpointStatCursor`（`cursor_id`、the `created_at` 水位与 `caught_up_at`）。读取器需要一个最近的已完成折叠且从不回退到实时聚合。`application/catalog_stats.py` 是两者的唯一写入器。修订 `0074` 添加 `terminal_reconciled`（遗留桶为 false）与 `EndpointStatDirty`：主键 `(endpoint_id, day)`、单调自增的 `revision`、未覆盖修正的年龄界 `queued_at`，以及索引的重试调度 `(retry_at, endpoint_id, day)`。`infra/catalog_stat_dirty.py` 拥有所有标记写入，不提交：审计在其终端更新同事务中标记原始天；worker 经其折叠光标替换整个桶并只确认一个未改变的 revision。通知保留 `queued_at`；一次成功的完整替换在同一事务中把一个保留的更新 revision 的年龄界前移到源扫描起点，不把更新时间戳向后移，也不改变重试退避。失败的替换保留旧的年龄。既有的异步/结果-适配器桶从汇总表排队，且在被修正之前保持不可用。这些表是可选的 analytics，绝不确定一次金钱事务。见 [catalog](catalog.md) § 在供应商之间选择。

  **`LedgerEntry` 是另一个，且它更大。** 它是仅追加且从不修剪（2026-09-06 生产上 4.38M 行 / 2.3 GB，约每天 400k 行），且 `ledger.spent_today` — 失败关闭(fail-closed)的每日上限 — 在 **每个** 已计量调用内部、在 reserve 事务内部、在 api-pool 连接上读取它。只有单列索引时，规划器通过 `ix_ledgerentry_created_at` 遍历整个平台的当天，并在内存中过滤 org：每次调用丢弃 322k 行并触碰 381k 缓冲区，一旦当天的页从 512 MB 缓存中被逐出，耗时 56-106 s，且堆读取了 65 亿块 — 是 `callrecord` 的四倍。修订 0021 添加 `(org_id, created_at)`，它也为 `entries_of`（the `/billing` 页，此前是对整个 `created_at` 索引的向后遍历）服务。那修复了轻量 org 与 `/billing`，但不是写半个当天的两个 org — 它们的行在当天的每一页上，规划器继续遍历它（0021 之后每次调用 395k 缓冲区触碰）；因此上限不再读取该表：`Org.spent_today_micro` / `spent_today_day` 由修订 0022 添加，由 `domain/money` 在余额 UPDATE 内部保持，用一个主键查找读取；日志聚合作为 `spent_today_from_ledger` 保留用于对账。在 `callrecord` 上同样的形态 — 每用户每日调用上限，`count_today`，它通过 `ix_callrecord_user_email` 把成员整个历史 BitmapAnd 化（287k 行成员的 3.0 s 中的 2.6 s）— 在修订 0023 得到 `(org_id, user_email, created_at)`，然后是和账本相同的答案：索引仅扫描仍获取今天尚未 vacuum 的页的堆（110k 堆获取，2.8 s），因此修订 0024 把门移到 `Membership.calls_today` 且日志计数留给名册与 `/usage/me`。一个团队的最新行：`/calls` 按 id 在 `(org_id, id)` 上分页，本地运行（一个团队行的一小片）读取部分 `(org_id, created_at, id) WHERE kind = 'local_run'`（修订 0054）；没有它们，第一个遍历主键测试 `org_id`，第二个读取团队整个历史。Activity feed 的 calls 页按时间在 `(org_id, created_at)` 上。一个团队在窗口内的花费（`money.spend_since`、Usage 页与 `/usage/by-tag` 总计）读取账本上的部分 `(org_id, created_at) INCLUDE (amount_micro) WHERE kind = 'settle'`（修订 0089）：仅 `(org_id, created_at)` 上窗口内的每一行都花费一次堆获取，在冷缓存上每行一次随机读取。查询把 `'settle'` 作为一个常量陈述，因为 Postgres 只针对一个常量匹配部分索引。一个大到在修订的语句超时内无法建索引的账本先被 `CONCURRENTLY` 在带外(out-of-band)建同一个索引；修订随后跳过有效的那个。一个团队的充值（自动充值上限的月份、下一个默认金额、支付页的 auto 标志、发票恢复边界）读取部分 `(org_id, created_at) WHERE kind = 'topup'`（修订 0090），`'topup'` 同样作为常量；在它之前 Postgres 交叉 `org_id` 与 `kind` 位图并读取团队的每一行来寻找少数几个。

  **每个 API 密钥的花费属于账本，以同样方式折叠。** 修订 0070 添加 `ApiKeySpendDay`（团队 + API 密钥 + tool + UTC 天 -> `spent_micro`、`charges`；主键 `(org_id, day, api_key_id, endpoint_id)`，`api_key_id = 0` 用于未归因行）以及单行的 `ApiKeySpendCursor`（一个 `(created_at, id)` 水位、`history_from`、`caught_up_at`）。`application/key_spend_rollup.py`（作为 `treg-worker spend rollup` 运行）是两者的唯一写入器，且 Team 与 Usage 页只读取它们；见 [money](money.md) § 每个 API 密钥的花费。团队删除清除一个团队的行。

  **每个成员的调用计数也被折叠。** Usage 页的计数与观察到的 agent 名册每页打开对一个团队整个 30 天窗口的 `callrecord` 分组；`(org_id, created_at)` 索引找到窗口，但每一行都是一个宽审计行的堆获取，且一个繁忙团队的报表比报表会话的语句超时活得更久。一个覆盖索引被拒绝：它将复制每个审计行的四个字符串列并拖慢每个审计插入。修订 0088 添加 `CallUsageDay`（团队 + UTC 天 + 成员 + kind + tool + client -> `calls`、`last_at`）以及单行的 `CallUsageCursor`（`cursor_id`、最后一个折叠的 `CallRecord.id`；`history_from`；`caught_up_at`）。`application/call_usage_rollup.py`（作为 `treg-worker usage rollup` 运行）是两者的唯一写入器：它按主键遍历 `callrecord`，带与 `catalog_stats` 相同的提交滞后，从 31 天历史的第一行开始，并在一个事务中移动计数与光标。光标锁是一个 no-op UPDATE，在 SQLite 上也锁（那里 SELECT FOR UPDATE 被忽略）。一个新光标在创建它的事务中删除旧的天行，因此一次重建从不加到先前历史。没有重数：审计按设计是有损的，且唯一剩下的竞争是少计一行队列本可丢弃的行。一个报表（`application/call_usage.py`）在一个语句中读取折叠的行与光标之后的团队行，因此两半共享一个快照且没有被计数两次或遗漏的行；尾部在 `(org_id, id)` 上找到，是在 cron 运行时几分钟的调用。`cursor_id` 行（worker 从未运行，例如一个小型自托管注册表）报表仍实时聚合 `callrecord`；有一个未追上进度的光标时它们说 usage 正在准备，且一个比 `history_from` 更老窗口从那里开始并说明这一点。成员与 agents 列表的 `used_today` 一旦 rollup 追上就以同样方式读取今天的行，之前实时读取 `callrecord`；它从不等待。`RunRecord` 仍实时读取：它不再增长。团队删除清除一个团队的行。

  **`ix_callrecord_call_ref`，以及一个数据库为何可能缺少它。** 模型与修订 0001 声明它，因此每个 Alembic 创建的数据库都有它。一个早于 Alembic 的数据库从旧的 `init_db` `ALTER TABLE ... ADD COLUMN` 获得 `call_ref`，它不添加索引，然后只在基线处被盖戳，因此它从未运行 0001 的 `create_index`。那里每个 `call_ref` 查找都读取整个审计表：花费 rollup 的键查找（`call_ref IN (...)`）、`GET /calls/{call_ref}` 与 `audit.py` 中的异步命中 UPDATE。修订 0072 在它缺失处构建它：在 Postgres 上并发地，不带迁移语句超时（一个大表耗时超过 120 s），丢弃并重建一个被中断的构建留下的 INVALID 索引，并留一个有效的 alone。它的降级是一个 no-op，因为 0001 拥有该索引。一般教训：一个被盖戳的数据库有基线的表，不一定有其索引；在依赖一个之前检查 `pg_indexes`。

  该 rollup 的账本遍历状态把水位作为一个索引界，`created_at >= watermark AND (created_at > watermark OR id > watermark_id)`，绝不作为单一 OR：整个条件在 OR 内部时，Postgres 只从上方限定 `created_at` 索引扫描并在每个批上从最老的行遍历它。

  `refused_by` 区分一个 treg 拒绝（`auth`、`policy`、`balance`、`cap`、`resolution`、`request`，以及其他机制特定值）与上游答案，那里它为 null。在处理器内的审计标记它们自己的结果；共享异常处理器使用请求状态身份记录更早的拒绝，对无效认证匿名。`endpoint_stats` 排除被拒绝的行。

  `error_request` / `error_response` 持有经掩码的、截断的失败证据，横跨平台、自有密钥与自有工具调用。成功时把它们留空。被捕获的供应商头使用覆盖重试/auth/限流与请求/跟踪标识符的允许列表。`/calls` 既不获取也不暴露这些宽字段；`GET /admin/errors` 拥有读取访问（只读）且 `treg-worker admin purge-evidence` cron（`application/evidence_retention.py`）是 14 天保留清洗，把过期证据替换为 `<expired>`。

  在 `application.call.evidence` 中的掩码是安全敏感的：

  1. 渲染每个被注入的凭据，包括 OAuth/secret-file JSON、敏感的叶字符串、绑定选择的字段与 Bearer 形态。保留非机密诊断字段。
  2. 掩码精确值与编码形态：任一大小写的百分号转义、表单编码、JSON 转义，以及解码的 Basic-auth 凭据加上其用户名/密码两半。
  3. 应用模式掩码，然后重新扫描一个百分号解码、JSON 去转义、小写的副本。一个渲染失败或残留的机密替换整个片段。
  4. 只在掩码之后截断，因此部分凭据无法逃过精确匹配。

  未计量的上传只为证据而缓冲，且声明的 `Content-Length <= 64 KiB`。失败的流式响应最多保留前 8 KiB，把所有字节重放给调用方。清洗绝不在请求上运行：一个读取错误的管理员页曾每次加载都清空平台范围的证据。

  `archive_key_hash` / `archive_content_hash` 把合格的已计量平台响应链接到 `ArchiveKey` / `ArchiveSnapshot` 用于 `GET /calls/{id}/result`。它们是可空的、未索引的字段，由 `0011` 添加。归档存储、资格与保留属于 [归档](archive.md)；调用方标签与金钱连接见下。

  `upstream_ms`（Alembic `0063`）是 `duration_ms` 中供应商的份额：从发送请求直到其答案被读取（或，当答案流式传输时，直到其头到达）。它排除令牌刷新、归档 lookup、一次 `retry-after` 睡眠与 treg 自己的工作。当没有请求到达供应商时，以及在该列存在之前写入的行上为 NULL。

  `verdict`（Alembic `0065`）是契约对答案的 verdict 词，由同一个适配器在 `hit` 旁设置：`valid` / `invalid` / `catch_all` / `risky` / `unknown` 用于 email verify，`verified` / `unverified` 用于 email find（供应商自己的声明）。契约封闭列表中的一个词，绝不是内容。当契约记录无 verdict、答案未携带任何、或供应商使用其适配器不映射的词时为 NULL。见 [catalog](catalog.md) 的声明。
- **`IdempotentCall`** - 一个调用方限定、24 小时的重放缓存，用于已计量成功，由 `(membership_id, key)` 键控，并携带 `org_id` 用于团队清理。它不是审计记录：一旦成员资格被吊销，就不存在可以重放它的有效调用方。`delete_membership` 显式移除它，且 `membership_id` 外键使用 `ON DELETE CASCADE` 作为 schema 后盾（Alembic `0015`），因此一个缓存的已付费响应绝不会把令牌吊销变成 500。一个 `pending` 行是一个由一个调用拥有的租约：它从声明携带那个调用的 `call_ref`，所有者在它运行时每 `IDEMPOTENCY_LEASE_RENEW_S` 续新 `created_at`，且每个存储、释放与续新都以 `call_ref` 为栅栏(fence)。一个比 `IDEMPOTENCY_STALE_PENDING_S` 更老、在 `call_ref` 下没有开放 hold 或待定异步任务（及其 `call_ref:` 子项）的租约通过比较并交换(compare-and-swap)（所有者和 `created_at`）关闭，带一个存储的终端 410：`idempotency_response_lost` 当所有者的账本显示一个时带 charge，否则 `idempotency_outcome_unknown`。该键永不再次运行：一个失效的租约不证明其所有者已停止。没有 `call_ref` 的行（此前写入）保持回答 409 直到它们过期。一个超过 `archive_max_body_bytes`（2 MB，归档自己的上限）的被保留答案不被存储：`_store_idempotent` 保留一个终端 410 `idempotency_response_too_large`（`call_id`、charge、`size_bytes`）替代。调用方已经收到了完整答案；一个重试永不再次运行。每调用过期标签清扫读取 `(membership_id, expires_at)`（Alembic `0053`），因此其代价是过期行，而非调用方持有的每个标签。它最多删除它能锁住的 `IDEMPOTENCY_SWEEP_BATCH` 行（`FOR UPDATE SKIP LOCKED`），因此一个成员的并发批从不彼此排队在对方的过期行上；一个被跳过的行随后来的一次调用走。被重用的标签由重放 lookup 自己的删除释放，而非由清扫。
- **`ToolRequest`** - 一个「目录没有 X」报告（`POST /tool-requests`，开放 + 每 IP 限流）：`capability`（标题，≤200 字符）、`query`（返回为空的搜索 —— 由 agents 自动填充，去重/优先级信号）、`note`、`contact`、`source`（`web` | `cli` | `mcp` | `claude-connector` | `api`）、`status`（`open` | `done` | `dismissed`，手动翻转），以及 **可空** `org_id`/`user_email` — 当调用方恰好有一个时，身份是归因，绝不是要求，因为通常的提交者是一个零结果且无令牌的 agent。通过查询该表审查；一个 Slack 通知器稍后可能挂在插入上，但行是记录。
- **`SearchMiss`** - 一个返回 **无物** 的目录搜索：`query`（截到 300 字符）、`source`（`api` 用于服务 web + CLI + 原始 API 的 HTTP 路由；`mcp` 用于团队 MCP；或 `claude-connector` 用于 V2；`web-find` 用于 `/catalog/find`）、`created_at`，以及在 find 上的 `reason`（0055：`gap` | `not_task` | `judge_off` | `scope`，见 [find](find.md)）与 `engine`（被服务的 find 引擎；一个 shadow 答案不归档任何）。在 `ToolRequest` 前一步的需求信号：大多数错过的 agents 从不提交，因此查询文本是它们留下的全部。通过 `audit.record_search_miss` fire-and-forget 从两个搜索路径写入 —— `GET /catalog/search` 与进程内 MCP `catalog_search` 工具。刻意无身份；由私有 usage 报表暴露，它针对目录读取 miss 以把覆盖缺口与命名/发现失败分开。
- **`SearchLog`**（0041）- 在 **发现实验**（见 [search-experiment](search-experiment.md)）下的一个 MCP 目录搜索：`query`、`source`、调用方的 `org_id`/`user_email`（结果是该调用方后来的 `call`，因此该行不是无身份）、`mode`、`arm`、作为 `[id, probability]` 行的 `baseline_ids` 页、作为 `[id, owner]` 行的 `judged` 页、`shown` 页、`baseline_total`（0 = 词法门未承认任何东西）、`differs`，以及 judge 的 `judge_ms` / tokens / `judge_error`。通过 `audit.record_search` fire-and-forget 写入；由 `scripts/search_experiment_report.sql` 连接到 `CallRecord` 读取。当 `search_experiment` 为 `off` 时不写入任何东西。`/catalog/find` 以 `mode=find`、`source=web-find` 与无身份写入同一行；0055 添加 `engine`（v1 | v2）与 v2 的读数：`platform_choice`、`platform_conf`、`name_p`、`recall_ms`、`embed_ms`、`embed_error`，以及作为 `[kind, id, p]` 行的 `units`（[find](find.md)）；0056 添加 `verdict`，一个 v2 答案结束于的 verdict 及其原因（冒号后）：`none:gap`。
- **`RunRecord`** - **服务端运行** 审计行（一个 `treg run --server` CLI 执行 —— usage rollups 中的 "kind" `server_run`）：`org_id`、`user_email`、`bundle_name`（自工具侧运行统一以来持有 **tool** 名；列名是历史的）、`argv`（JSON —— 绝不携带机密值；机密经 env 注入，而非命令行）、`exit_code`、`duration_ms`、`created_at`。脱离请求路径写入，像 `CallRecord` 一样。**用量计量**（`GET /orgs/{id}/usage`，每用户每日上限）把 `CallRecord` + `RunRecord` 一起计数 —— 见 [API 片段](../interface/api.md)。
- **`AdConversion`** - Google Ads 转换发件箱(outbox)：`org_id`、`action`（`signup`|`first_call`|`paid`）、`dedupe_key`、`value_usd_micro`、`created_at`、`uploaded_at`（NULL = 尚未上传）、`next_attempt_at`（退避）、`failed_at`（终端/死信状态）、`attempts`、`error`。后两个时间戳列是迁移 A38。一个待定行三个状态时间戳都为 NULL；uploaded 与 failed 是显式的、互斥的终端状态。在 `(org_id, action)` 上唯一 —— 唯一的幂等机制，而非 check-then-insert。按设计持久（在触发代码的同一事务中同步写入，不同于 `audit.py`/`analytics.py`，它们可丢弃）；一个后台 worker 稍后上传它。完整链路与一个非原子触发点：[ads-conversions](ads-conversions.md)。
- **`Ephemeral`** - 必须 **在重启后存活且跨实例保持正确** 的短寿命键值状态：邮件 OTP 码 + 其暴力破解计数器，以及认证限流滑动窗口。由 `(ns, k)` 键控 —— 一个命名空间（`otp` | `otp_start` | `sandbox_hit`）加上其中的键 —— 带一个不透明的 JSON `v` 与一个 `expires_at`（行被惰性清扫）。这是曾经是认证 HTTP 层每进程字典（backlog #3）的 DB 归属：计数器不能再被一次重新部署重置，且一个每 IP / 每邮件上限不能被运行多于一个实例所削弱。访问辅助函数在 `ratestore.py`（`kv_put`/`kv_get`/`kv_pop`、`rate_check` 滑动窗口、`sweep`）。CLI 配对也使用这个表：`application.auth` 拥有 `cli_login`（待定码/尝试或完成结果）与 `cli_oauth`（社交登录返回映射）。它们的键哈希登录 ID 或 OAuth state；码、凭据与返回登录 ID 都是 Fernet 加密的。批准在配对行通过转换及其 Default-密钥创建的期间锁住它；结果与 OAuth-state 消费使用 `DELETE RETURNING`。待定、完成与 OAuth 条目各自在 `HANDSHAKE_TTL` 之后过期；读取强制执行过期。
  `_prune_handshakes` 在 CLI 启动时在一个单独的事务中运行，从 `cli_login` 与 `cli_oauth` 最多删除 100 个过期行。PostgreSQL 物化候选批并跳过锁住的行；不相关的命名空间与活跃行不被触及。进一步批在后来的启动上运行，因此过期是立即的但物理移除可能滞后空闲期或一个积压。不需要 schema 迁移。
- **`DenyRule`** - 关于什么可以被 **调用** 的 org 策略：`org_id`、可空 `user_id`（NULL = 整个 org，设置 = 一个成员/agent）、可空 `project_id`（NULL = 任何 tool，设置 = 只有 **通过** 该项目的 tool 的调用 —— 迁移 A22；`delete_project` 清扫命名它的规则，与 `_drop_member_deny_rules` 同样的悬空 FK 推理）、`host` / `path_prefix` / `method`（一个空字段意味着 **任何**，因此只携带 `method="DELETE"` 的规则阻止每次删除）、`verdict`、`note`、`created_by`。该表本身是新的，因此 `create_all` 创建它。`verdict` 今天是 `deny` 且存在以便批准要求的动作稍后无需迁移即可落地这里，镜像 `localrun.py` 已经使用的 `verdict` 词汇。强制执行：[proxy-model](proxy-model.md)。
- **运行时归因** - `CallRecord.client` + `RunRecord.client`（迁移 A23，`''` 默认）：哪个 coding agent 做了调用（`X-Treg-Client`，由 CLI 经 env 指纹自报；归因，绝非认证）。供给 `GET /orgs/{id}/agents/observed` —— 每（成员、运行时）一行，agents 故事中自动捕获的那一半。`Membership.created_by`（同一步）命名铸造了一个 agent 的管理员；对门/邀请加入为 `''`。
- **`CapacityPolicy` / `CapacitySnapshot`** - 每个 treg 拥有的供应商账户（tier 4）计量什么以及如何资助，以及对它剩余什么的有界观察的仅追加记录。`capacity_type` 包含 `rolling_quota` 用于跨移动窗口而非日历重置衡量的配额。只由 worker 的 `treg-worker capacity sweep` 写入，绝不由调用路径写入；该 sweep 还把每个供应商的最新状态发布到一个 `Ephemeral` 下的 `capacity:state:<provider>`，数据平面在其自己的断路器锁（`capacity:lock:<key>`，只由调用路径写入）旁经 TTL 读取。只有数字 —— 绝不是一个凭据。见 `ops/capacity.md`。Alembic 修订 `0005` 创建这两个表。
- **`OverflowRoute`** - 一个 `(endpoint_id, aggregator)` 对：经一个 treg 拥有的聚合器账户服务的同一供应商端点，带有聚合器的价格、价格比率、验证戳与一个派生的 `enabled`。只由 `treg-worker overflow sync` 填充（Alembic `0006`）；对调用路径只读。见 `ops/capacity.md`。
- `Org.platform_overflow_disabled` - 团队的 overflow 退出（Alembic `0008`）。见 `ops/capacity.md`。
- **`OverflowSpend`** - 每个聚合器每个 UTC 天：调用数、聚合器的收费、对 treg 直接价格的增量。写在 overflow 子项的 settle 事务内部（以及由 shadow 探针）；每天 $20 的预算读取它。Alembic `0007`。不是一个余额。

`CallReview`（修订 0026）为每个唯一调用引用存储一个私有有用性评级。它有端点/时间与租户索引，并经由 `ORG_SCOPED_MODELS` 与其团队一起删除。见 [feedback](feedback.md) 的归因、提交、采样与仅收集作用域。

## 绑定（多凭据形态）(Bindings (the multi-credential shape))

`Tool.bindings` 是一个 JSON 列表；每个条目是 `{secret_id, injector, location, name, format, secret_field, token_encode}` —— 一个凭据注入。一个请求应用一个 tool 的 **全部** 绑定（例如 google-ads = 一个 oauth bearer + 一个 `developer-token` 头）。API 经 `_flat_binding()` 从扁平字段构建一个单绑定 tool；注入在 [auth-secrets](auth-secrets.md) 中。

## 异步 DB（`src/treg/infra/db.py`）

三个异步 SQLAlchemy 引擎针对一个数据库，由 `POOL_SPECS` 声明并暴露为 `session_maker`（api）、`admin_session_maker`（`/admin/*`）与 `background_session_maker`（审计、归档写入、ads worker）—— 一个舱壁(bulkhead)，因此没有任何一类工作能耗尽另一类的槽；大小、语句超时与推理在 [deploy](../ops/deploy.md) § Database pools 中。`/call/` 的 relay 后簿记步骤使用 `session_maker`；请求会话在 relay 之前提交，因此它们没有任何一个等待它，见 [proxy-model](proxy-model.md) § 连接纪律。公共的 `dispose_engine()` 在一个显式维护事件循环退出之前关闭池化连接，因此一个后来的服务循环无法继承绑定到已关闭循环的的接。连接。`verify_db()` 是只读的生命周期与 worker 守卫：它保留缺失-Fernet-key 拒绝，要求在 head 处一个盖戳，拒绝一个已知的更旧修订，并在未知-更新修订上警告但服务以用于增量时代回滚。`reset_db()` 仅用于测试：它处置每个循环绑定的池，删除每个应用行（并回退 Postgres 序列），然后写入 Alembic head 盖戳。它只在它的列与索引指纹不同于它上次构建的指纹时才重建 schema：一个新鲜数据库，或一个更改了共享 schema 的测试。避免每个测试的 Alembic 运行与 DDL 使套件快速而不削弱 autogenerate 漂移守卫。`get_session()` 与 `get_admin_session()` 是 FastAPI 依赖。本地 SQLite（`aiosqlite`），Render 上 Postgres，相同代码。**时间戳是 naive UTC：** `_now()`（the `created_at` 默认）丢弃 tzinfo，因为列是 `TIMESTAMP WITHOUT TIME ZONE` 且 asyncpg 在 Postgres 上拒绝 tz-aware 值；应用全程比较 naive UTC。共享的请求时间转换位于 `timeutil.utcnow_naive` 与 `timeutil.as_naive`，在分阶段路由迁移期间临时重新导出为 `api._utcnow_naive` 与 `api._as_naive`。与带时间戳列比较的查询参数遵循与插入或更新值相同的约束。

`TREG_READ_DATABASE_URL` 可选添加一个独立的 SQLite / PostgreSQL 引擎与 `read_session_maker`。PostgreSQL 默认其事务为只读；SQLite 在专用读取连接上启用 `PRAGMA query_only` 而不影响主库。这些守卫意外写入，而非禁用这些设置的蓄意 SQL。该引擎被包含在处置中，但从不 schema 写入；PostgreSQL 也在遥测中暴露其 `read` 池。一个空 URL 把现有的主会话制造器别名为未改变的写入行为；配置的数据源失败在没有主回退的情况下传播。`/admin/errors` 经 `get_admin_read_session` 选择加入，当未配置读取 URL 时它改而使用 admin 主池。它的授权仍位于主库，并在读取证据与 org 名之前释放其连接。在选入之前必须处理供应/复制、副本滞后与每个调用方的写入边界；一个 URL 本身不同步数据库或添加其他方言支持。见 [deploy](../ops/deploy.md) § 可选读取副本用于配置与连接预算。

## Alembic 执行与采用地板(Adoption floor)

Alembic 经 `maintenance._upgrade_schema` 拥有所有生产 schema 执行。一个空或被盖戳的数据库运行 `alembic upgrade head`。一个非空未盖戳的数据库被拒绝，无检查或无写入，且必须经过采用发布 0.14.x。显式升级也拒绝一个未知-更新的修订，因为它无法安全地跨越一个回滚地板迁移。

迁移脚本位于 `src/treg/alembic/`，在已发布的 wheel 内部。仓库根的 `alembic.ini` 为开发者 CLI 使用指向那里，而 `maintenance._alembic_config` 解析已安装的包资源并提供配置的数据库 URL。Alembic 命令经 `asyncio.to_thread` 运行，因为环境拥有自己的 `asyncio.run`。在 Postgres 上，`env.py` 在迁移之前设置 `lock_timeout = 5s`，因此锁争用干净地使一次尝试失败，并按其自身提交每个修订，因此 `maintenance` 的有界重试在超时的修订处恢复（见 [deploy](../ops/deploy.md)）。

权威漂移守卫升级到 head，针对 `SQLModel.metadata` 运行 Alembic autogenerate，并要求空 diff。测试经 `reset_db()` 保持快速的 `create_all` fixtures，它在同一事务中盖戳 head。漂移守卫在完整套件中的 SQLite 上与 `test-postgres` CI 中的 Postgres 上运行。

`test_alembic_expand_safety.py` 只解析每个修订的 `upgrade()` 主体，并允许一个封闭集合的增量 Alembic 操作。任何 ALTER、DROP、原始执行或未知操作必须设置模块级 `contract = True` 并在模块 docstring 中命名其回滚地板。修订 0003、0004 与 0008 声明了它们的：每个添加一个 NOT NULL 列并丢弃其服务器默认，因此更旧的代码不能再插入行。

修订 `0061` 移除 `ArchiveKey.key_hash`、`OAuthRefresh.token_hash`、`OAuthClient.client_id`、`OAuthCode.code` 与 `ArenaEvaluation.run_id` 上冗余的普通索引。它们的命名单列唯一约束保留索引查找与唯一性；模型元数据只声明那些约束。复合前缀索引不变。该迁移在丢弃任何东西之前检查每个替换，并拒绝意外的定义或一个不可用的唯一索引。PostgreSQL 在一个 autocommit 块中并发地丢弃每个索引，之后恢复有界的超时。一个部分尝试可以被重试。降级并发地重建普通索引，修复无效的构建碎片，且需要那些索引的空间。没有行或外键改变。

修订 `0091` 把同样的纪律应用于只重复同一表上存活的复合索引或唯一约束的前导列的单列索引：`LedgerEntry.org_id`（由 `(org_id, created_at)` 服务）、`CallRecord.org_id`（`(org_id, created_at)`、`(org_id, id)`）、`TagSpend.org_id`（`(org_id, dim, val, created_at)`）、`ArchiveSnapshot.key_id`（`uq_archive_snapshot_version`）与 `ArchiveKeyOrg.org_id`（`uq_archive_key_org`）。模型元数据不再声明它们；外键保留。其预检要求每个存活者是一个有效的、无条件的 btree，其第一键列是被丢弃的那列。每个丢弃都是 `IF EXISTS`，因此一个索引在其部署前经 `DROP INDEX CONCURRENTLY IF EXISTS` 被带外丢弃的数据库只记录该修订。

## 审计写入器（`audit.py`）

`record_call` 与 `record_run` 经 `background_session_maker` 调度尽力而为的写入。它们从不延迟或使一个被代理的响应失败。`_pending` 保留任务；一个循环绑定的信号量限制活跃写入，且 `_MAX_PENDING` 通过丢弃多余行来界定队列。API 流量在 Postgres 上有独立的池；SQLite 把池别名化。

写入失败与丢弃的行在 ERROR 级别记录日志，以便故障捕获能暴露丢失的证据。`drain` 循环直到队列为空，包括关闭期间添加的任务。`_known_fields` 针对模型字段过滤遥测并警告未知键，防止一个新字段丢弃整行。Schema 与遥测更改仍必须一起落地。

审计是有损的 analytics 与诊断。金钱操作必须使用同步账本。

## 产品 analytics 写入器（`analytics.py`）

与 `audit.py` 同样的损纪律，但 sink 是 PostHog 的 `/batch/` 端点，而非 DB。`capture(distinct_id, event, properties, groups=)` 是同步的且 **绝不抛出**（调用点位于 Stripe webhook 内部，那里一个异常会 500 并触发一次已贷记支付的重试）；它排队至多 `_MAX_PENDING` 个事件（越过界后丢弃最新），且一个 flusher 任务微批处理它们（每个 POST 至多 `_BATCH_MAX`，最多每 `_FLUSH_INTERVAL_S`）经每个 flush 的 httpx 客户端 —— 没有信号量，因为到 PostHog 的 HTTP 从不触及 DB 池。**空的 `posthog_key` = 模块关闭**（自托管者与测试套件什么都不发送）。`$groups: {team: org_slug}` 镜像浏览器的 `posthog.group('team', slug)`。每个事件也携带 `build`（`TREG_BUILD`，否则主机导出的提交变量，否则已安装包版本；`build_id`）与 `archive_config`（改变一个调用行为的归档设置的一个 12-hex 摘要：模式、服务允许列表与百分比、重复价格、年龄上限、body 写与全部三个读模式、改变观察；`archive_config_id`），且生命周期每个进程发出一个 `service_started`，带有角色与那些归档设置。它们存在以便一个分析可以被限定到一个代码版本或一个缓存配置，而非一个被记住的部署时间：一个更旧的构建从不发出该属性的事件在其中读作 null，且没有该边界那个 null 看起来像一个状态。归因产品事件使用调用方的邮件与团队组，因此它们连接到 SPA 识别的同一个 PostHog 人/组。一个预身份 `call_intake_failed` 事件反而使用固定的 `treg-server` 身份且无团队，因为认证无法获得一个 DB 连接。发射器：`call_tool` 的 `_audit` 漏斗（`tool_called`，带有作为供应商的目录 `provider` 或自有工具的 upstream host；字段列表在 [proxy-model](proxy-model.md)）、`bootstrap_handlers._pool_saturated`（`call_intake_failed`）、`billing_topup`（`topup_started`），以及 `billing._credit`（`topup_completed`，由 `fresh` 门控）。在生命周期 `finally` 中 **最后** 排出 —— 在 `audit.drain()` 与 `archive.drain()` 之后，因为它是这两个报告其损失的 sink，且先排出它会把那些事件困在一个被取消的 flusher 后面。引擎为非零 SQLite URL 添加 Postgres 池卫生（`pool_pre_ping`/`pool_recycle`/sizing），且 `verify_db` 拒绝在一个真实 DB 上无 `TREG_SECRET_KEY` 启动（一个临时密钥会在重启时丢失每个存储的机密）。

`capture_quota_fail_open` 使用同样的 flusher 与关闭排出用于一个有界的每进程 60 秒摘要，而非每个调用排队一个事件。它的计数与上限目标示例描述未确认的准入，而非一个持久的限额审计；见 [org-endpoint 配额](org-endpoint-quota.md#store-contract) 的事件契约。

`infra.money_timing.observe_money` 用本地单调计时器测量普通调用的 `reserve`、`close` 与 `deferred` 应用范围。这些覆盖可选的金钱准入、池获取与会话清理，包括失败时的回滚；reserve 也包括其提交后余额重载。它们不是纯行锁持续时间或全部金钱写入者的普查：Hub、billing、直接账本调用方与异步任务 worker 在这个观察边界之外。固定的 `preflight`、`ledger`、`commit` 与 `post_commit` 阶段分隔准入检查、账本工作、提交与额外读取；账本阶段本身可能包括惰性收割器的独立提交。没有计时器发出 SQL、await、改变一个事务边界或抑制一个业务异常/取消。

既有的 `bootstrap.pool_gauge` 计时器每个进程最多排出三个 `money_operation_gauge` 事件，在 analytics 关闭之前带一个最终的局部窗口。它们携带已完成的阶段计数、失败（包括普通拒绝）、取消、SQLSTATE `40P01` 失败、经过总计与最大值、不相交的持续时间桶、批项计数、每阶段总计/最大值与活跃阶段峰值。一个操作的整个持续时间属于其完成窗口；一个跨越边界的活跃阶段保留在下一个窗口的 in-flight 计数中。那些计数不是已检出的 DB 连接。一个 `process_instance` 令牌把每个摘要连接到同一进程的 `db_pool_gauge`。事件与保留的聚合都没有每团队基数。每个操作/窗口至多最慢的已完成阶段在可用时、验证过的不透明调用 ID、批大小、结果与该阶段持续时间下产生一个 WARNING 日志；不记录金额、body 或异常消息。这些观察通过既有的有界 analytics 队列保持尽力而为。

`infra.money_admission.snapshot` 按操作（`close`、`deferred`、`async`、`hub`、`reserve`、`release`）与模式（`disabled`、`redis`、`fallback`）添加有界的 `money_admission_gauge` 摘要。合格的调用在准入禁用时记录同样的计时边界。一个 `close`、`deferred`、`async` 或 `hub` 上的空 org 列表仍跳过该观察。`reserve` 与 `release` 带有空或无效 org 在会话之前抛出 `AdmissionRefused` 且不记录一个 fallback 行。模式 `fallback` 中的 `fallback_*` 计数是降级：body 仍在数据库路径上运行。一个 reserve 获取超时反而记录模式 `redis` 中的 `rejected=1`，带有 `failed=0`、零执行时间与无活跃阶段或 fallback 计数。其清理期间的取消仍是一个取消，而非拒绝或 fallback。当它们的更宽预算（租约的两倍，至多 hold grace 的一半）过期时，`reserve_admission` 也只在其之上带 `fallback_wait_timeout` 发出一个尽力而为的 `money_admission_rejected` WARNING，带数字 `org_id`、操作、原因与抖动的 `retry_after_s`；org ID 保持在聚合维度之外。释放与结算在模式 `fallback` 下记录 `fallback_wait_timeout`，仅当它们的更宽预算过期时；一个等待超过 reserve 预算然后拿到租约的结算记录模式 `redis`，其整个等待在 `wait_*` 中。一个 Redis 租约串行化已准入的同 org 余额工作；reserve 超时拒绝把这些过期的等待者挡在资金事务之外。

`money_admission_reporting.emit_snapshot` 写入一个本地 JSON 记录，并经由既有的 web 分钟计时器与最终局部窗口为每个有数据的操作/模式排队一个 PostHog 事件。worker 在命令退出时发出其累积窗口并尝试一个有界的 analytics 排出；本地退出摘要是在交付失败时的回退证据。这些聚合中没有每调用网络事件或 org/调用 ID。

`kv_lease_error` 是一个本地诊断日志，而非 PostHog 事件。租约异常按 `phase`（`acquire`、`renew`、`release`）与七个 `error_type` 值之一累积在 `infra.kv` 中：`deadline_exceeded`（Python 超时）、`redis_timeout`、`authentication`、`permission`、`connection`、`response`，或 `other`。至多 21 个桶保留计数、UTC 首次/最后失败时间戳与 `elapsed_max_ms`，加上 socket 超时默认（1,000 ms）与外层命令尝试截止（1,500 ms）。续新/释放尝试也共享一个 2,500 ms 每键预算；剩余的已确认租约有效性可以进一步缩短续新。URL 查询覆盖可以在不改变这些报告默认值的情况下改变有效的驱动 socket 超时。

经过时间是客户端观察到的，包括连接建立与事件循环调度，而非 Redis 服务器执行时间。一个类型缩小失败的边界；它自身不建立网络或服务器根因。正常的争用与任务取消不是租约错误。计数描述失败的命令尝试，包括一个重试恢复的首次续新或释放尝试；它们不是失败金钱事务或失败租约范围的计数。准入的续新/释放 `kv_errors` 只在终端不可用或一个意外的存储异常时递增。一个被恢复的失败尝试仍出现在诊断中，但不在那个计数器中。已确认的租约有效性耗尽作为 `deadline_expired` 每个准入范围计数一次，与 `lease_lost` 并列。这包括续新前注意到的过期、一个 `deadline_expired` 存储结果、一个晚到的续新回复，以及门自身的有效性超时。一个在有效性过期之前引发的存储超时仍是一个 KV 错误。实际的命令失败仍留在尝试诊断中，即使在失败清理期间有效性过期。这些范围计数到达既有的 `money_admission_gauge` 日志与 analytics；有效性过期之前的命令不发送虚构的尝试。

`MoneyTraceRunner._emit` 在其既有的分钟节奏与关闭时在本地 sink 关闭之前排出这些桶。既有的有界后台日志 sink 添加 build/进程/角色并写入它们；租约操作不执行诊断 I/O。不保留异常消息、栈、URL、键或所有者令牌。队列/速率/sink/关闭损失仍可能发生，并由 runner 既有的损失/错误计数器暴露；缺失一个细节日志不是无失败的证明。既有的 `money_admission_gauge` KV/fallback 计数器仍是独立的聚合信号。

`kv_lease_gauge` 重用同样的分钟/worker-退出 runner 用于本地日志与 PostHog。每个实际租约命令尝试按阶段与固定结果递增一个内存桶；每进程至多存在 14 个桶。每个摘要持有 `count`、`retry_count`、`elapsed_total_ms`、`elapsed_max_ms` 与不相交的持续时间桶（至多 10、50、100、200 ms，或 200 ms 以上），带有 build/进程/角色、窗口持续时间与关闭元数据。`retry_count` 计数第二次续新/释放尝试，包括失败或被取消的。一个失败的尝试用 `unavailable` 表示；本地 `kv_lease_error` 提供其错误类。`deadline_expired` 表示一个被其已确认有效性超时停止的续新尝试，没有 KV 错误。一个外层门超时反而可以取消该命令（`cancelled`），而其准入摘要记录 `deadline_expired`。`not_owned` 意味着一个释放重试没有找到匹配的令牌：更早的删除可能在没有回复的情况下成功，或者租约过期/改变了所有者。它既不是已 Renew 所有权的证明，也不是一个新的 `lease_lost` 观察。先前检测到的续新丢失仍被记录。正常的 `busy` 尝试与取消有不同结果。不保留 org、键、令牌、URL 或异常文本。没有新的采样器、探针连接或每命令 analytics 调用。一个短的 worker 的本地退出摘要在其 analytics 尾部未送达时是覆盖的权威来源。日志共享既有的速率/队列限制；analytics 保持尽力而为。均值使用经过总计除以尝试计数；桶界定分位数，而非精确的 p95。客户端经过时间包括连接建立、网络与调度；这些测量本身不隔离服务器执行或解释一个准入队列的长尾。

`wait_total_ms` / `wait_max_ms` 覆盖会话之前的准入，包括失败获取的清理。`execution_total_ms` / `execution_max_ms` 覆盖已准入的应用会话范围，包括池检出与回滚/关闭；它们不是被测量的连接持有时间。`total_total_ms` / `total_max_ms` 包括两者加上租约清理。`completed` 计数已完成的范围，包括 `failed` 与 `cancelled` 子集。使用经过总计之和除以已完成范围之和获得加权均值。等待桶是不相交的上界区间；既不是桶也不是分钟最大值都是每调用 p95。`waiting`、`active` 与它们的峰值描述该进程的这些范围，而非全局同时并发或数据库连接。整个持续时间与 fallback 计数器属于完成窗口；一个未完成的操作可以跨越多个窗口。

`fallback_*`、`lease_lost` 与 `kv_errors` 暴露降级的隔离，独立于业务失败。比较一个推出时把 `process_instance`、`build` 与 `role` 连接到池与金钱操作摘要。禁用与启用的 org 队列可以有不同工作负载；一个延迟差异本身不是一个因果比较。既有的 `money_operation_gauge` 可以比较早于准入遥测的构建，但覆盖一个不同的人群与边界，而非准入 gauge。PostHog 仍是一个有损诊断 sink，绝不是账本或单个收费已提交的的证据。

`infra.money_trace` 分别跟踪公开金钱条目背后的实际数据库事务，包括赠送、充值、Hub 转移、批关闭与陈旧 hold 释放。应用调用范围也标记账本更新前后的 preflight 与工作。`mark_money` 只附加本地元数据；SQLAlchemy 钩子在连接被获取后附加一个进程唯一的 `app_txn_id` 并读取 asyncpg 已知的 backend PID 而不执行 SQL。一个在金钱条目之前开始的事务保留其原始观察到的开始。每个根事务在提交、回滚、失效清理或会话关闭处结束；savepoints 与 flushes 不创建虚构的根事务。陈旧 hold 恢复中的独立提交产生独立的 ID。一个 backend PID 可重用，因此调查必须匹配其时间间隔与 `app_txn_id`，而非把所有带该 PID 的记录连接为一个事务。

`money_stage` 标记声明、块锁定、余额更新、tag 花费、归档-使用簿记与其他金钱步骤；钩子也区分 flush 与 commit。阶段退出恢复父阶段或 `between_stages`。SQL 回调只保留计时与 SQLSTATE，绝不与 SQL 文本、参数、金额或异常字符串。这些是衡量一个仍待完成语句与应用时间之间的客户端观察跨度：它们既不测量服务器锁持续时间，也不包括事务开始之前的连接池等待。

`money_trace_runner` 每秒采样一次活跃金钱事务。一个超过一秒的事务在仍打开时可以发出 `money_txn_slow`，至多每五秒一次，加上完成时的一个 `money_txn_end` 记录。两者都包含有界的 org/调用身份、阶段历史、事务时间戳与进程/build 归因。活跃样本只检查 `src/treg` 内拥有任务自己的协程位置，绝不检查帧局部或源文本。有界的 `await_chain` 可能跨 SQLAlchemy greenlet 部分；其捕获时间戳使一个被保留的样本区别于结束事务的当前栈。一个慢语句本身不是死锁或哪个其他事务持有其锁的证明。关联 PostgreSQL 的阻塞者 PID 与这些应用记录来定位持有者的工作。

收集不执行数据库/网络 I/O，不给金钱操作添加 await，并保留它们的事务边界与异常。本地跟踪独立于可选的 PostHog 键。活跃注册、事件队列、阶段历史、身份与日志输出都有显式限制；累积丢弃与诊断错误由 `money_trace_gauge` 暴露。一个守护线程经一个有界队列写入 JSON 日志；一个被阻塞的日志 sink 不能阻塞事件循环或无限期延迟 worker 关闭。分钟 gauge 报告采样器新鲜度、事件循环唤醒延迟与输出健康，没有 org/调用基数。一个延迟的唤醒暗示调度器饥饿但不识别其原因。如果循环停滞，采样也停滞；缺失样本或丢弃记录是证据限制，绝不是无阻塞者的证明。runner 在关闭期间发出一个最终的局部本地窗口。worker PostHog 交付保持尽力而为；短生命周期 worker 从本地日志而非一个假设的 final 网络 flush 验证。PostgreSQL CI 作业也运行跟踪验收测试：它们重现一个真实的锁持有者与等待者，并要求一个可归因的持有者快照在任一事务完成之前，连同取消、清理与无额外 SQL 检查。

Arena 在其声明/最终保存之后添加 `arena_run_started` / `arena_run_completed`；普通的 `tool_called.client=enrich-arena` 仍归因每个 lookup、Try 与验证。浏览器 `TregTracking.identify` 把那些邮件身份连接到匿名的 Arena 页面浏览与活跃团队组。邮件 OTP 与社交认证只在提交一个新建用户后发出 `signup_completed`。`treg_entry_surface` 是一个首观察到的、90 天的产品表面 cookie；服务端 `funnel_surface` 只接受固定的表面名，绝不为 URL 或搜索数据。手动充值事件包括这个获取表面与一个单独的 `checkout_source`，也经由 Stripe 元数据复制到持久的充值账本元数据。见 [Arena 转换跟踪](../interface/enrich-arena.md#conversion-tracking) 用于事件定义、转换分母与 person-to-team 支付连接。

基础设施故障使用经 `capture_fault` 的同样 DB 独立队列：PostHog `$exception` 事件有固定的 `treg-server` 身份并只携带异常类、至多 500 字符的其字符串、一个未处理的机制，以及组件/日志器标签。异常值中的 URL 查询字符串在截断 **之前** 被替换为 `?[redacted]`，因此查询注入的凭据无法泄漏；帧、局部、请求 body 与用户身份从不包含。`FaultCaptureHandler` 在 analytics 启用时镜像 ERROR+ 记录；它忽略 `treg.analytics` 日志树，标记记录以防止重复的 root/Uvicorn 交付，并使用一个线程局部重入守卫加一个永不抛出的 `emit`。生命周期在 root 上并直接在 `uvicorn.error` 上安装该处理器（Uvicorn 的默认父级不传播到 root），然后在关闭排出后移除它。`bootstrap_handlers._pool_saturated` 直接调用 `capture_fault`，因为其类型的 503 在 Uvicorn 会记录它之前被处理。

**Repeats 滚动汇总；它们不限流。** `_note_fault` 为每个 `(fault type, logger/site)` 打开一个 `_FAULT_WINDOW_S` 的 `_FaultWindow`：第一次出现立即报告，其余被计数，且 `_emit_fault_summaries` 在 flusher 的计时器上 **以及再次在 `drain()` 中** 释放计数 —— 绝不在下一次出现的背后，这正是一个已停止（或事件中途重启）的风暴曾如何带走其计数的方式。每个事件携带 `fault_occurrences`，它代表的数字，因此 `sum(fault_occurrences)` 是真实总计；PostHog 的问题列表计事件数且是一个下界。一个窗口的负载在构建时 **固定**：PostHog 基于异常类型 + 值指纹，因此携带一个后来出现的消息的摘要会落入与其摘要不同的 issue 并拆分总和 —— 对按 issue 过滤的任何人低估，这是读取 Error Tracking 的正常方式。代价是该窗口报告其第一条消息，而非最新的，且该键的其他消息在它之下被计数。代价由键 **基数**（`_FAULT_MAX_KEYS`，LRU 逐出）界定，而非体积，这就是为什么不存在全局预算：这个被替换的进程范围桶让一个响亮的键沉默每个其他键，包括从未重现以携带自己计数的首次出现。故障只在共享队列真正积压时（`_FAULT_QUEUE_SHARE` 的 `_MAX_PENDING`）才被丢弃 —— 节流从来意图防止的拥塞，而非针对一个空队列触发的时钟速率。

**丢失数据是 ERROR，而非 WARNING。** `audit._write_batch`、`audit._enqueue` 的反压丢弃，以及 `archive` 的 `_store`/`_touch_write` 丢弃都在 ERROR 记录日志，因为 `FaultCaptureHandler` 从 ERROR 开始：在它之下损失到达容器 stdout 且别无他物，因此它既无法被告警也无法被找到，除非已经怀疑它。不花费任何东西的降级（一个归档 lookup 回退到一次 live 调用、一次重试过的传递）保持在 WARNING —— 界线是数据是否真的丢失。

## 租户作用域(Tenant scope)

每个租户资源携带 `org_id`；一个成员资格令牌在一个 org 内识别一个用户。`owner` 记录创建者并参与角色检查。见 [多租户](multi-tenancy.md) 的隔离与清理。

## `CapabilityPin` ——「对于这份工作，我们团队使用这个供应商」

每个 `(org, capability)` 一行。刻意 **不是** 一个 `DenyRule`：一个 deny 是消极且封闭的，因此阻止九个供应商中的八个会留下第十个在目录加入第十一个的那天被允许。一个 pin 是积极的且随着目录增长保持正确。

它是一个门，而非提示 —— 一个对某个被 pin 能力的不同供应商的目录调用在 `_resolve_marketplace_call` 中被拒绝，在预留任何东西之前，且 403 携带 `use_endpoint`，因此调用方被告知该用什么替代，而非只是「不」。两半都在 pin 设置时针对目录验证，因为一个拼写错误否则会阻止一个团队真正使用的工作并在 agent 的日志中在凌晨 3 点浮现。见 [catalog](catalog.md) 与 `docs/CAPABILITY-CHOICE-PLAN.md`。

## OAuth（MCP 授权服务器）

四个表，都随 MCP 前门添加。推理见 `architecture/mcp-oauth.md`。

| 表 | 持有 | 注 |
|---|---|---|
| `OAuthClient` | 一个可能请求令牌的客户端 | DCR 与 CIMD 共用一个行形态，因此 authorize/consent/token 从不询问它如何到达 |
| `OAuthCode` | 一次性授权码 | 在赎回时删除，而非标记 —— 一个仍存在的已用码是一个竞争 |
| `OAuthGrant` | 一个刷新族的可变权威 | `current_org_id` 是未来令牌花费的地方；`granted_at` 是稳定的同意时间 |
| `OAuthRefresh` | 一个刷新令牌，**已哈希** | `family_id` 把一次授予的每个后代分组，因此一次重放可以吊销它们全部 |

`OAuthCode` 与 `OAuthRefresh` 是 org 限定作用域的，因此列在 `ORG_SCOPED_MODELS`（`domain/governance/teams.py`）中；`OAuthGrant` 由 `cascade_delete_org`（在 `domain/governance/teams.py` 中）显式清除，因为其 FK 刻意命名为 `current_org_id`。该级联吊销经当前权威或任何历史 `OAuthRefresh.org_id` 命名被删团队的家族的并集，因为只删一个退休的来源行会擦除重放证据而保留其活跃后代可用。`OAuthClient` 不是 org 限定作用域 —— 一个客户端是全局的，且它没有任何东西属于一个团队。每个 `OAuthRefresh.org_id` 是不可变的签发来源；移动一个家族只更新 `OAuthGrant.current_org_id`。

## 调用方标签（`X-Treg-Meta`）

两个新表与少量列携带一个转售构建者的归因。设计原理在 [money](money.md) 中；这是形态。

| 表 | 行含义 | 由谁写入 |
|---|---|---|
| `TagSpend` | 一次调用花费了什么，归因到它的标签之一 | 只有 `domain/money`，在金钱事务中 |
| `TagBudget` | 一个构建者对一个 `(dim, val)` 设置的限制，以及限定基数的注册表条目 | `api.py`（首次发现时自动创建） |

`CallRecord` 获得 `call_ref`（回显给调用方的 `X-Treg-Call-Id`，并用作已计量调用上账本的 `call_id` —— 一个值连接审计行、金钱行与构建者自己的记录）、`budget_dim`/`budget_val`（主键对的索引副本）与 `tags`（整个包）。

`Org` 获得 `budget_dims`（哪些键可以携带预算，≤3）、`primary_dim`（限定幂等的作用域）与 `daily_cap_micro`（团队自己的花费上限，0 = 跟随部署默认）。`Membership` 获得 `pinned_tags`。修订 `0042` 向 `RunRecord`、`AsyncTaskRecord` 与 `AsyncResourceRecord` 添加可空 `tags` 快照。不推断历史所有权：NULL 快照对固定读者不可见。reserve 的 `LedgerEntry.meta.tags` 冻结有效的归因而无需一个新账本列，允许在审计损失或释放之后进行作用域限定的账本只读读取。

这些列是 Alembic 基线 schema 的一部分（曾经添加它们的遗留启动迁移已被删除）；`TagSpend` 与 `TagBudget` 是普通的基线表。

## `Referral` —— 一个邀请，以及它所欠的

由 `domain/referrals.py` 写入；它产生的金钱经 `ledger.grant` 赠送。策略与门见 [money](money.md)。关于 **形态** 有两件事属于这里：

**两个 UNIQUE 列做仲裁，而非应用代码。** `referred_org_id`（一个 org 可以被推荐恰好一次，永远）与 `qualifying_payment_intent`（一个支付资助一个资格）。`ledger.grant(once=True)` 不够：它的检查是一个没有支持唯一索引的 SELECT，它存活一次重试但不存活两次并发赎回 —— 而这是欠第三方的钱，而非一个注册促销。`NULL` 免于唯一索引，因此任意数量的 `pending` 行共存。

**`status` 是一个阶梯且每个终端状态都被保留**，从不删除：`pending`（已注册，不欠任何东西）→ `qualified`（朋友付费，在 hold 之后欠两个奖金）→ `paid`；或 `capped`（推荐者超出自助服务额度）/ `rejected`（一个门说不行，或资助支付在 hold 内被反转 —— `reject_reason` 说明哪个）。一个被删除的行无法回答「为什么我没拿到钱」，这是该功能生成的第一个问题。

`User.referral_code` 在 **用户** 上，而非 Org：一个人推荐一个朋友，且任何人可以创建无限 org，因此一个每 org 码会把同一个人类无限码交给其耕种。它在首次访问 Referrals 页时惰性铸造 —— NULL 是正常状态。

`Referral.card_fingerprint` 持有 Stripe 每卡稳定的 id。它 **不是卡片数据**（在我们自己的 Stripe 账户之外是不透明的）且只在这里单独存在，绝不在 `Org` 上，这保持 `Org.stripe_default_pm` 的无卡数据姿态完好。

## Arena 统计

修订 `0028` 添加 `ArenaObservation`（匿名分类审计事实，30 天窗口）与 `ArenaInsightState`（收集光标与聚合 JSON）。只有 `application.arena_insights` 写入它们。它们没有审计外键，因为审计保留是独立的；两者都不存储原始请求、响应或凭据。公共表读取这些数据库聚合，而非打包的生产指标。见 [Enrich Arena](../interface/enrich-arena.md) 用于分类与刷新语义。

修订 `0029` 添加 `ArenaVerificationSnapshot`，只由 `application.arena_verification_insights.publish_snapshot` 写入。其不可变的 run ID、内容摘要、发布时间与聚合 JSON 使验证试点独立于滚动观察。它不持有联系人 nor 原始证据。公共洞察 API 经发布时间索引选择最新发布；见 [Enrich Arena](../interface/enrich-arena.md) 用于估计语义与仅聚合导入工作流。

## 归档保留

归档保留统计计数带有可恢复 body 的逻辑快照，包括 R2 与去重版本。修剪 DB 字节把 `both` 变成 `r2` 而不减少那些计数；修剪最后一个 DB 副本清除 `body_storage` 并递减它们。失败的 R2-only 上传仍追加一个 null 位置的仅哈希快照。退役的 `volatile_paths` 列保留用于兼容性且不再出现在 admin 响应中。

## 托管密钥迁移顺序与 Activity 索引

未发布的托管密钥修订遵循当前 schema：`0034` 添加密钥控制、事件、可空 Activity 快照，以及仅哈希回填；`0035` 添加 Default-密钥生成。`0034` 是安全回滚地板：旧服务端代码无法强制禁用或已吊销的密钥。两个修订都不在持有列 DDL 锁时在大 Activity 表上建索引。

`0036_activity_key_indexes.upgrade` 在 `callrecord` 与 `runrecord` 上构建部分 `(org_id, api_key_id, id)` 索引，其中 `api_key_id IS NOT NULL`。它们支持 `list_calls` 与 `list_runs` 中的团队/密钥过滤器与最新优先分页。历史未分配行保留在索引之外。PostgreSQL 在这个单独的修订中在列事务提交之后使用 `CREATE INDEX CONCURRENTLY`。它保留有效索引，重建一个被中断构建的无效碎片，并恢复正常的迁移超时。SQLite 正常创建相同的部分索引。PostgreSQL 构建仍扫描每个表并使用 I/O；不声称任何生产构建持续时间。

## 邮件到点击归因暂存(Email-to-click attribution stash)

`AdClickStash`（增量修订 `0075`）由 `application.signup.stash_ad_click` 拥有。其邮件主键提供唯一性与索引查找；`raw_cookie` 存储编码的、长度上限的点击字段，且 `created_at`/`updated_at` 使用 naive UTC。认证路由提交已证明邮件的观察；无 cookie 的注册使用最近 90 天的观察。注册一旦其团队持有该点击就删除该行，且 `treg-worker admin purge-ad-clicks` 删除超过 90 天的行。不涉及 analytics 或审计发射。见 [ads conversions](ads-conversions.md)。

## 排名(Rankings)

增量修订 `0087`：`rankingssnapshot`，一行（`id = "current"`）持有每个 /rankings 板作为 JSON、它覆盖的最新完整 UTC 天（`through`）以及它何时构建。只由 `application.rankings.refresh`（the `treg-worker rankings refresh` cron）写入，它替换整行；页读取它。它按 tool 与端点持有计数、比率与持续时间，绝不是一个团队、密钥或金钱，因此团队删除没有要移除的东西。见 [catalog](catalog.md)。

## Showcase 排行榜与图片(Showcase leaderboard and pictures)

增量修订 `0076`：`showcaseapp`（一个条目：状态、live 字段、同意标志、usage 来源、作为 JSON 的待定提案）、`showcaseappevent`（仅追加历史，每条目与版本唯一）、`showcaseappkey`（其调用是一个条目的活动的 API 密钥；每密钥一个条目）、`showcaseweek`（每来源一行 —— 一个团队、`api_key_id` 0，或一个密钥 —— 每 UTC 周）、`showcasecursor`（被计入一个来源周的最后调用 id）与 `showcasevote`（每条目与人唯一），都只由 `application.showcase` 写入；该条目的子项与它级联，两个活动表由团队与密钥键控，且团队删除移除它们全部。`org.avatar_key` 与 `user.avatar_key` 命名公共媒体桶中的一张图片，且只由 `application.images` 写入。见 [showcase](showcase.md)。
