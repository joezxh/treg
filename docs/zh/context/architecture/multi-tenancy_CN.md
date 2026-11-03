---
title: 多租户(multi-tenancy) — 组织(orgs)、成员资格、邀请、按组织作用域限定
status: shipped
sources:
  - src/treg/domain/governance/access.py
  - src/treg/alembic/versions/0042_pinned_read_scope.py
  - tests/test_pinned_read_scope.py
  - src/treg/models.py
  - src/treg/api.py
  - src/treg/caller_metadata.py
  - src/treg/application/auth.py
  - src/treg/application/asynctasks.py
  - src/treg/application/call/resolve.py
  - src/treg/application/provider_resources.py
  - src/treg/domain/provider_resources.py
  - src/treg/routers/provider_resources.py
  - src/treg/alembic/versions/0043_provider_resources.py
  - src/treg/application/signup.py
  - src/treg/domain/governance/access.py
  - src/treg/domain/governance/budgets.py
  - src/treg/domain/governance/publicdemo.py
  - src/treg/domain/governance/teams.py
  - src/treg/domain/governance/usage.py
  - src/treg/domain/identity/access.py
  - src/treg/domain/identity/api_keys.py
  - src/treg/domain/identity/session.py
  - src/treg/application/enterprise_sso.py
  - src/treg/alembic/versions/0079_enterprise_sso.py
  - src/treg/alembic/versions/0080_enterprise_sso_audit.py
  - src/treg/alembic/versions/0081_sso_manual_block.py
  - src/treg/alembic/versions/0082_oauth_sso_provenance.py
  - src/treg/alembic/versions/0083_enterprise_sso_safety.py
  - src/treg/alembic/versions/0084_enterprise_workos_cleanup.py
  - src/treg/alembic/versions/0085_enterprise_sso_blocks.py
  - src/treg/worker.py
  - src/treg/routers/enterprise_sso.py
  - src/treg/infra/workos.py
  - tests/test_enterprise_sso.py
  - src/treg/domain/identity/promotions.py
  - tests/test_team_limit.py
  - tests/test_auth.py
  - tests/test_token_revocation.py
  - src/treg/routers/auth.py
  - src/treg/infra/turnstile.py
  - src/treg/client_ip.py
  - tests/test_client_ip.py
  - src/treg/web/captcha.js
  - tests/test_turnstile.py
  - frontend/tests/captcha.test.ts
  - src/treg/routers/orgs.py
  - src/treg/routers/resources.py
  - src/treg/domain/tools/bundles.py
  - src/treg/infra/db.py
  - src/treg/alembic/versions/0017_async_task_record.py
  - src/treg/alembic/versions/0018_async_resource_ownership.py
  - tests/test_asynctasks.py
related:
  - architecture/data-model.md
  - architecture/proxy-model.md
  - interface/api.md
---

# 多租户（组织 orgs）

## 企业级 SSO(Enterprise SSO)

团队所有者可以购买企业级 SSO 订阅，随后从团队 dashboard 打开一个短生命周期的 WorkOS Admin Portal 链接。WorkOS 处理客户的 SAML 或 OIDC 连接；treg 保留它自己的 `User`、`Membership`、角色、会话与 API 密钥。一次成功的 WorkOS 换码(code exchange)只有在返回的 organization 与本团队存储的 WorkOS organization 匹配、且其连接与先前使用的是同一个时才被接受。一个新人类以 `member` 加入既有团队；所有者通过常规的 Members 控件改变角色。仅邮件域名绝不会授予访问权。邮件发现(mail discovery)检查 WorkOS 已验证的组织域名，并路由到匹配的付费团队链接；若多个团队匹配，由员工选择一个。它在 Stripe 重试期间接受一个 `past_due` 团队。精确的团队链接绕过发现。两条路径在经 state 校验的 WorkOS 回调核实了人与其组织之前，都不授予成员资格。

所有者可以在一次成功的测试登录后要求 SSO。此后 `require_member` 对非所有者要求携带本团队 ID 的签名浏览器会话。一个 SSO 浏览器会话或派生的 CLI 身份令牌只能访问那个团队，即使用户属于多个团队。常规邮件或社交登录仍识别全局用户，但不打开那个团队。所有者保留一条常规登录恢复路径。API 密钥是独立的凭据，且常规浏览器会话无法为一个被强制(enforsed)的团队铸造新的 Default 密钥。一个 WorkOS 档案通过稳定的 profile 与 IdP ID 关联，后续登录时检查账户邮件；邮件变更需要显式审查，而非静默重新分配账户。新账户要求邮件匹配一个已验证的 WorkOS 组织域名，且该组织的外部 ID 必须匹配 treg 团队。组织外的档案被拒绝。一个既有的全局账户在首次关联前需要同一已验证用户的并发正常 treg 会话。CLI 配对与 OAuth 同意在签发时检查 SSO 作用域与强制状态。OAuth 码、刷新族(refresh families)与访问令牌保留 SSO 团队；交换、刷新与使用都重新检查策略。强制前做出的 OAuth 授权无法延续进被强制的团队。更早的非所有者 bearer 密钥，包括 agent 密钥，在强制后停止授权本团队。通过已授权团队会话签发的新的个人或 agent 密钥携带签发来源(provenance)，并在其成员资格或密钥被吊销前一直工作。员工也可在公司登录后签发一个 SSO 作用域的 CLI 密钥；所有者保留恢复访问权。

在 Directory Sync 方案下，签名的 WorkOS 事件维护一个活跃目录用户名册(roster)，包括尚未登录过的人。一旦目录被连接，SSO 登录要求该名册中有一个匹配的活跃 IdP 用户。非活跃/已删除用户失去其团队成员资格与密钥；删除目录会移除所有关联的非所有者成员资格。所有者恢复始终可用。WorkOS 事件 ID 使重复投递(redelivery)无害。仅 SSO 方案不承诺自动离岗(offboarding)。供应(provisioning)从不把外部组映射进 treg 角色。一个 worker 可以调和完整的 WorkOS 名册以修复错过的 webhook 投递。手动团队移除在所有者恢复访问之前优先于活跃目录记录。持久的、最小的 `EnterpriseSSOAudit` 行记录 SSO 登录与失败、设置动作、角色变更、强制切换、目录移除、手动团队移除与所有者恢复。访问变更与其审计行一起提交；设置动作在 WorkOS 响应之后记录。一个保留(retention) worker 按部署所选策略删除过期行。完整名册修复识别处于 `linked` 状态的 WorkOS 目录，并在其激活 webhook 被错过时能发现一个。它忽略其他目录状态，因此一个已断开的目录无法授权员工。修复还会移除名册中不存在的同步前 SSO 身份。只有 `active` 目录用户算作已供应。在 Stripe 重试 `past_due` 订阅期间，SSO 与 Directory Sync 保持活跃。订阅结束时，强制被解除，使既有成员可以使用正常登录。取消只移除 SSO 创建成员资格；既有的成员保留。清理 worker 随后删除被取消团队的 WorkOS 目录与连接、清除过时的 SSO 身份链接，并在新的结账开始之前记录完成。`EnterpriseSSOBlock` 仅保留团队与 treg 用户 ID 加上一个显式管理员移除的时间戳。`finish_signin` 跨替换的 WorkOS 连接检查它；恢复、团队删除与全局用户擦除会移除它。

注册表是 **租户隔离(tenant-isolated)** 的：一个 **Org** 拥有资源，一个 **User** 是全局身份，一个 **Membership** 用角色把它们链接起来，并且 **是调用方令牌所在之处**。一个令牌 = 一个 `(user, org)` 对，因此每个列表/创建/变更以及代理都按调用方的 org 限定作用域。设计来源：`docs/MULTI-TENANCY-PLAN.md`（独立方案）。

## 拥有团队上限(Owned-team limit)

一个账户最多可拥有 10 个团队（`MAX_OWNED_TEAMS`）。所有所有者成员资格都计入，包括演示(demo)与被挂起(suspended)的团队；以 member、admin 或 viewer 加入不计入。`require_owned_team_slot` 在所有权写入与提交期间锁定用户，然后检查当前所有者成员资格。身份 `lock_user` 使用无操作(no-op)更新在 Postgres 与 SQLite 上做跨进程串行化。常规创建、新手引导演示创建与显式所有者提升(promotion)共享该守卫。超限请求返回 HTTP 403 并带一条可操作信息。删除团队或放弃所有权会释放一个槽位。既有的超额团队仍可访问，且管理员删除唯一所有者时的恢复被保留；不需要迁移或余额变更。这是一个当前所有权上限，而非每日创建上限。

## 模型(`models.py`)

[Enrich Arena](../interface/enrich-arena.md) 的运行与评估要求创建用户与活跃团队都匹配。仅常规团队成员资格不会暴露另一个成员的结果。团队删除通过 `ORG_SCOPED_MODELS` 在其运行之前移除评估。`OrgFlowControlVersion` 配置历史也在该列表中，并随其 Org 被显式删除。其 `org_id` 刻意没有外键；管理写入必须在清理开始前验证 Org 存在并与其删除协调。参见 [配置存储](data-model.md#org-flow-control-configuration-storage)。

- **`Org`** — `id, name, slug (unique), previous_slug, suspended, demo, public_demo, created_at`。拥有 secret/tool/bundle 的租户。**`public_demo`** 标记一个其成员令牌被发布(PUBLISHED)的团队（例如在落地页上）：非管理员成员被锁定到 `/call` + 读取，且绝不能作为用户行动——在 `require_member` / `require_identity` 中强制。
- **`User`** - 仅身份：`id, email (unique), created_at`，外加 `email_verified_at` 与 `signup_promo_available`。无令牌、无角色。已验证账户可跨所有团队领取一次、且每邮箱(inbox)一次（别名共享；旧账户不能再次领取。参见 [money](money.md#signup-credit-eligibility)。
- **`Membership`** — `user_id, org_id, role (owner|admin|member|viewer), token_hash (idx), webhook_url, daily_call_cap`（每用户每日用量上限；`-1` = 无限，管理员设置——见 API 片段的用量计量段落）、**`tool_access`**（JSON；**NULL = 全部工具**——默认值，因此升级时无人被限制——否则为允许的 tool 名称列表）与 **`local_run_enabled`**（bool，默认 true）；唯一 `(user_id, org_id)`。一个人在 N 个 org 中有 N 个成员资格（N 个令牌）。`ROLE_RANK` 排序为 owner > admin > member。
- **`ApiKey`** 把一个凭据解析到一个成员资格。该成员资格仍是角色、工具访问、项目访问、本地运行权限、每日上限与计费身份的唯一来源。更多密钥不会创造更多配额(quota)。一个已知的禁用或吊销密钥无法回退到 `Membership.token_hash`。新人类成员资格只使用其签名的默认密钥，并把那个遗留兼容字段留空；既有的基于哈希的凭据通过迁移继续。成员资格移除后，签名令牌解析检查被分离、已吊销的 Default 控制行，使旧令牌保持未授权；一个钉在被删团队上的令牌是无效的(invalid)，而非一个含糊的缺失团队请求。一个签名 Default 令牌还携带该行的团队局部生成(generation)；轮换在同一行上自增它，使旧令牌失效而不影响另一个团队。
- **`Invite`** — `org_id, email, role, code_hash (idx), status (pending|accepted|revoked), invited_by, expires_at, email_token_hash (idx, nullable)`，外加 **`tool_access` + `local_run_enabled`**（接受时播种到成员资格上的访问——在邀请时设定访问，之后编辑）。附在一个 **邮件** 上：兑换一次性码，**或** 证明那个邮件（任何身份门）并无码接受它——码是捷径而非要求。`email_token_hash` 是邮件链接中仅收件箱可见的 **第二个 secret**——它可以让被邀请者登录（`GET/POST /auth/invite-signin?t=`，一次性），而管理员可见的码永远不能。
- **`Project`** — 一个 org 内 **可选的** 子作用域（`org_id`, `name`, `slug`, 唯一 `(org_id, slug)`）。org 仍是硬隔离边界；project 是之上的更软分组。刻意是一个 **标签 + ACL 作用域，而非命名空间(namespace)**：`Tool.name` 保持按 `(org_id, name)` 唯一，因此不需要重建唯一约束（扁平到 orgs 的迁移已经做过一次，且 SQLite 无法可移植地修改约束）。`Tool.project_id` 为 NULL = **全 org**，即每个早于 projects 的 tool——因此这是纯增量(additive)发布的。secret 刻意保持在 org 级：一个共享凭据正当地支撑多个 project 中的 tool。
- **机器身份(Machine identities)** — 一个位于 **不可路由(unroutable)域名** 上的 `User`，这正是它成为机器而非人的原因。存在两个：已发布的演示令牌（`PUBLIC_DEMO_DOMAIN`）与一个 **agent**（`AGENT_DOMAIN` = `agents.treg.local`）。两者都由管理员铸造，且 **只** 通过其令牌行动：`_is_machine_email` 把它们挡在每一个登录门之外、挡在 `require_identity`（见下）之外。一个 agent 需要 **无新表、无迁移**——它是一个 `Membership`，因此它免费继承了 `daily_call_cap`、`tool_access`、`local_run_enabled` 与每身份审计，而这正是使这些控制 *按 agent* 的原因。注意：「agent」在这里是一个身份；`agents.py` 是不相关的 skill 目录表（「每个 coding agent 把它的 skills 放在哪」）。
- 资源表（`Secret`/`Tool`/`Bundle`/`CallRecord`/`PendingOAuth`）携带 `org_id`；`owner`（创建者邮件）为审计 + 成员角色门而保留。`Tool.name` 按 **`(org_id, name)`** 唯一（`UniqueConstraint("org_id", "name")`），因此两个 org 可以复用名字。

## 强制(Enforcement) (`domain.identity.access` 与 `domain.governance.access`)

- **`require_member`** 解析一个签名默认密钥或一个基于哈希的托管密钥 → 一个活跃 `Membership` → 一个 `Caller`（`membership, user, org, api_key`，带 `org_id`/`email`/`role` 属性）。它在遗留成员资格哈希回退之前检查托管状态。它对缺失、禁用或吊销的密钥返回 401。最后使用的展示元数据是这个依赖提交之后的一个节流后台写入；它绝不延长认证事务或改变授权。
- 新铸造的签名人类凭据在签名的 `scp` 声明中声明其用途。`scp=team` 是一个 Default 密钥：其 `org` 具有权威性，因此冲突的 `X-Treg-Org` 被拒绝，而非对另一个团队计费。该响应告诉较旧的 CLI 用户先运行 `treg update` 再 `treg login`，因为这些客户端可以在获得团队密钥之前保存一个团队。`scp=bootstrap` 是短生命周期、无 org 的登录凭据：它可以识别账户以进行新手引导（列出团队、创建一个、检查/接受邀请），但即使调用方提供 `X-Treg-Org`，`require_member` 也拒绝它。较旧版本铸造的无类型令牌在兼容窗口期内保留先前「header 优先」的行为。
- **`_role_at_least` + `_can_manage`**：admin/owner 可以管理 org 中的任何资源；一个 member 只能管理它创建的（`resource.owner == caller.email`）。当资源在另一个 org 中时更新/删除返回 404，当角色门失败时返回 403。**`_require_can_register`** 门控创建（secret/tool/skill/oauth）：一个 **viewer**（等级低于 member）只能 `call` + 列出，且任何注册都得到 403。`ROLE_RANK` 排序为 owner > admin > member > viewer。
- **每成员工具 ACL（本次发布特性）。** `_require_tool_access(caller, tool.name)` 门控代理 `call_tool` 与本地 `grant_local_run`：若成员的 `tool_access` 为 NULL（全部）或指名了该 tool 则允许；**所有者豁免**（`_tool_allowed`），admin + member 可以被限制。`_require_local_run(caller)` 额外在 `local_run_enabled` 上按本地层门控。包括所有者在内的每个调用方的服务端 CLI 执行都被禁用；`run_tool_server` 始终返回 503。访问通过 `set_member_access`（`PATCH /orgs/{id}/members/{user}/access`，admin+；所有者不能被限制）设定：`_normalize_tool_access` 针对 org 的工具验证名称（未知时 422）并 **把一个全工具选择折叠回 NULL**，使一个全选的成员持续自动获得新工具。它是一个 **显式允许列表**：一个 *定制* 的成员不会自动获得一个新注册的 tool（dashboard 弹出一个提醒）。`Invite` 携带 `tool_access`/`local_run_enabled`（在 `create_invite` 时验证）→ 在两个接受门都复制到成员资格上。`list_members` 返回这两个字段。ACL 拒绝细节源自 `AccessPolicyError`；call、run 与资源 HTTP 表面把它们翻译成同一个 403 响应。
- **Agents（`create_agent` / `list_agents` / `revoke_agent`，`/orgs/{id}/agents`，admin+）。** 为一个机器调用方铸造一个成员身份，复用 `create_public_token` 配方（重新 POST 同一个名字会 **轮换**——旧令牌在那里死亡；吊销删除成员资格）。三个不变量，每个都封堵一个真实的漏洞：
  1. **一个 agent 令牌绝不能作为一个用户(USER)行动。** `create_org` 依赖 `require_identity`，因此没有 `_is_machine_email` 在那里的拒绝，一个 agent 可以创建一个 **它是所有者** 的新 org——而所有者在 `_require_tool_access` / `_require_local_run` 上是豁免的，从而逃脱施加于它的一切限制。
  2. **一个 agent 永远不能是所有者**——在 `create_agent` 与 `set_member_role` 中都被阻断，出于同样的豁免理由。
  3. **地址是按 org 限定作用域的**（`agent-{org.slug}-{name}@…`，镜像 `_public_demo_email`）：两个 org 必须各自拥有一个叫 `deploy` 的 agent 而不共享一个 `User` 行，否则一个超级管理员挂起一个租户的 agent 会杀死另一个的。Agent 总是按 *(org + domain)* 查找，绝不重新计算地址，因此 org 重命名不会使它们成为孤儿；`_agent_name` 剥去当前或之前的 slug 前缀，使重命名前的 agent 保留其名字。每个身份门都在共享瓶颈点 `_find_or_create_user` 处被阻断，外加 `register_user`（早于它并直接创建 `User`）与 `auth_email_start`（提前拒绝，不铸造码）。`list_members` 携带 `is_agent`，使一个名册能区分人与机器。
- **邮件域名黑名单(Email-domain blocklist)。** 同样的瓶颈点，针对一次性邮件与用于批量注册的域名。新验证账户每收件箱可收到一个促销余额，因此即使重复的团队创建与 `+tag` / Gmail-dot 别名不再赚取信用，耕种许多真实或 catch-all 收件箱仍是一条滥用路径。**完全是配置**：分类器（`domain/identity/access.py` 中的 `_is_blocked_email`，纯函数——它只回答；它遍历 `_norm_email` 域名，其尾部点被丢弃，因此 `a@listed.example.` 无法通过）只读取 `TREG_BLOCKED_EMAIL_DOMAINS`，在 `config.py` 中按每个不同值解析一次（trim、丢弃前导 `@`/`.`、小写、丢弃任何无点条目，因此一个打出的 `com` 无法拒绝全世界）。未设置——即默认——不阻止任何东西，且下一个域名是一个 **dashboard 编辑，无需重新部署**。代码中没有任何列表：黑名单是一个减速带，因为一个新域名让对方花费数分钟，因此它唯一真正的价值是在同样的几分钟内可编辑，而一次部署不是。对域名的子串规则曾被尝试并移除——对照一个公开一次性域名语料库，它们只匹配其中的 0.17%，相比精确条目毫无增益，且拒绝了一个域名恰好包含其中一个字符串的真实公司。保留下来的规则，每个都是因为显而易见的实现是错的：匹配 **仅域名**，而非整个地址（匹配地址会误标用户名恰好包含某列表字符串的真实用户）；**遍历父域名**，从前端整标签剥离、绝不只留最后一个裸标签，因为否则注册 `<random>.<listed-domain>` 就是一行绕过；**登录与注册都**（一个早于列表的账户不会获得新会话；既有账户被带外(out-of-band)挂起）。决策(decision)位于应用层 `signup.blocked_email(email, door)`：它拒绝，为每个封锁写一行结构化日志（`event=signup_blocked_domain door=<door> domain=<domain>`——拒绝不泄露任何东西，因此日志是突发唯一检测手段），且 **fail open**，若分类器曾抛错则记录 `event=blocklist_error` 并放行登录，因为配置错误绝不能破坏一次真实登录。门：`start_email_login`（在限流窗口之前，因此无码、无邮件）、`find_or_create_user`（因此 OTP 验证、GitHub 与 Google 回调以及邮件邀请链接 `POST /auth/invite-signin` 在行查找之前拒绝，抛出 `signup.BlockedEmailError`，每个门都把它翻译成 `blocked_domain` 种类）、`register_user`（`POST /users` 一次调用铸造一个未验证用户 + 团队；该团队在该用户首次验证时获得资金）、`create_org`（`POST /orgs`，促销门，用列表前铸造的令牌可达）以及基于码的 `POST /invites/accept`（它直接构造一个 `User`，因此它自我保护）。每个拒绝都是 `machine_identity` 兄弟的精确 403 `this address cannot be used to sign in`（浏览器门上的一个品牌页，像 `suspended`）：调用方既不知道存在列表、也不知道列表内容。刻意只是一个黑名单而非更多：无允许列表、无表、无管理员 UI。未覆盖：域名被列出时已经存活的会话或身份令牌在挂起或过期前继续工作（带外挂起）；促销授予与推荐奖励未单独门控，因为门关闭后不会有一个基于被封锁域名的促销资助团队诞生；接管一份完整的公开一次性域名列表是后续工作（基础 wheel 中的数 MB 包数据，它也发布轻量 CLI，且尚未对照真实用户检查）。**轮换替换的是令牌，而非限制。** 因为轮换与创建是同一个端点，一个缺失的可选字段曾经会回退到其宽松默认——而 dashboard 的 Rotate 按钮只发送 `{name, role, daily_call_cap}`，因此一个受作用域限制的 agent 仅凭拿到一个新令牌就悄然变成无限制（`tool_access=None` = 每个工具）：第 4 轮拦截器 #2。`create_agent` 现在 **只在调用方确实发送了该字段时** 才写入一个字段（`body.model_fields_set`，即 `set_member_access` 已用于 `project_access` 的形态）；一个全新的、没什么可保留的 agent 仍取文档化的默认值。`AgentIn` 现在 **确实** 接受 `project_access`（slugs 或 ids，经 `_normalize_project_access`），因此一个 agent 可以在铸造时按 project 限定作用域——在同样的「已发送」守卫下，因此省略它的轮换仍保留它。`Membership.created_by`（迁移 A23）盖戳铸造它的管理员，给每个 agent 一个名册中的所有者。
- **客户端地址(Client address)。** 每个按 IP 的限制（邮件码请求、tool 请求、公开演示、查找、arena、新手引导沙箱、judge）都以 `client_ip.of(request)` 为键，绝不以客户端写的某个 header 为键。`X-Forwarded-For` 是每个代理追加到的列表，因此其第一项就是客户端自己的声明：信任它会让脚本每个请求发送一个新地址并跳过每个按 IP 的限制。该地址在设置且为有效 IP 时是 `TREG_CLIENT_IP_HEADER`（在 Cloudflare `cf-connecting-ip` 之后，Cloudflare 拒绝来自客户端的它；没有它的请求每个进程最多每分钟记录一次 `event=client_ip_header_missing` 并回退；没有 `X-Forwarded-For` 的请求从未跨过代理，例如健康检查或进程内 relay，保持静默），否则是从右数第 `TREG_TRUSTED_PROXY_HOPS` 个 `X-Forwarded-For` 条目（默认 1，即最近代理追加的那个；直接客户端为 0），否则是 socket 对端。MCP 工具在进程内调用 API：`mcp._bearer` 每个工具先调用，把调用方解析出的地址记录在一个任务作用域变量中，`mcp._api` 在每个内部请求上转发它（`client_ip.forwarding_headers`），因此 MCP 调用方保留它们自己的按 IP 桶，而非共享传输的环回对端。每个进程记录一次 `event=client_ip_sources`，记录哪些地址 header 到达、有多少 `X-Forwarded-For` 条目，绝不包含值。
- **邮件登录上的机器人检查(Bot check)。** Cloudflare Turnstile 守卫 `start_email_login`，这是唯一一个从裸 HTTP 调用铸造收件箱证明的门（GitHub 与 Google 已经身处它们自己的检查之后）。除非同时设置了 `TREG_TURNSTILE_SITE_KEY` 与 `TREG_TURNSTILE_SECRET`，否则关闭，因此自托管者不加载任何 widget 也不调用 Cloudflare。每个带邮件登录表单的页面（CLI 的 `/login` 页包含在内）加载 `/captcha.js`（`routers/web.py` 填入公开 site key）并发送来自 `tregCaptcha.token('email_start')` 的 `captcha_token`；一个页面若 POST 到 `/auth/email/start` 却没这样做，测试会失败。脚本：每个请求一个新鲜的一次性令牌（双击启动第二次检查而非重发一个）；当一个标了 `data-captcha="email_start"` 的字段获得焦点时启动一次检查，因此点击很少等待（邀请与分享邮件字段永不召唤 widget）；`interaction-only`，因此 widget 不可见，除非 Cloudflare 想要一次点击，然后浮在正在填写的表单之下（在一个打开的模态 `<dialog>` 内、在 dialog 自身中，因为顶层在任意 z-index 之上、页面其余部分 inert），在它变得可见以及视口移动时重新放置；一次只运行一个检查，因此重新聚焦字段绝不会浮出第二个 widget；一次提交最多等待 30s 一个未应答的检查（10s 给一个尚未加载的脚本，然后 `!blocked`，但一个等待点击的检查永不拆除，因此下次点击找到其令牌；一个陈旧检查在新检查开始前被移除。当它无法获得令牌时，它发送一个原因而非令牌，`!blocked`（脚本被阻）、`!pending`（仍在等点击）或 `!error`，服务器绝不把它转发给 Cloudflare，只用于消息与日志。`infra/turnstile.py` 只做分类：`pass`（siteverify 成功，action `email_start`，hostname 在 `TREG_TURNSTILE_HOSTNAMES` 中，否则为公开主机及其已知别名）、`missing`、`invalid`（失败、重用、过期、超过 2048 字符，或为另一个 action 或 host 解出）与 `unavailable`（超时、传输错误、Cloudflare 的 `internal-error`，或我们自己的 secret 被拒，后者也记录 `event=turnstile_secret_rejected`：错误的 secret 绝不能读作每个调用方都是机器人）。它绝不抛出。用例先运行每邮件与每 IP 限流窗口并计数被拒请求，因此垃圾令牌无法驱动无界的 siteverify 调用，并在检查之前提交，因此没有连接等待 Cloudflare。然后 `auth._check_browser` 按 `TREG_TURNSTILE_MODE` 决定：`observe`（默认）记录 `event=turnstile_email_start outcome=<outcome> reason=<reason>` 且不改变任何东西；`enforce` 以 400 拒绝 `missing` 与 `invalid`（`captcha_blocked`、`captcha_pending` 或 `captcha_failed`，按原因；无码、无邮件）并放行 `unavailable`。结果(result)随 OTP 的 `Ephemeral` 条目进入验证：在 enforce 模式下一个非 `pass` 以 `signup_promo_available=false` 创建新 `User`（既有用户永不被触碰），因此一次 siteverify 中断让一个新账户失去其信用，而非让每个人失去登录。Cloudflare 脚本本身的中断不被吸收：那时每个浏览器发送 `!blocked`，enforce 会拒绝（消息指向保持开放的 Google 与 GitHub）。一个 `TREG_FIXED_LOGIN_CODES` 账户跳过检查（不邮寄任何东西；审查者可以脚本化它）。`treg login --email` 无法通过浏览器检查：每个 captcha 拒绝都携带 `X-Treg-Captcha: required`，CLI 据此说明并继续浏览器握手；来自 CLI 邮件门的请求得到一条命名 `treg login` 的细节，供只打印它的已发布 CLI 使用。观察模式在强制前度量误拒：`event=turnstile_email_start`（outcome、reason、`client=cli|browser`）与兑现码时记录的 `event=turnstile_email_verify`（outcome、`new_user`、client）配对，因此按结果看，被兑现的份额就是 enforce 会拒绝的真实人的份额；`signup_completed` 也把结果作为 `captcha` 携带。我们自己的规则拒绝的一个真实解出记录 `event=turnstile_mismatch`，带 Cloudflare 的 action 与 hostname，且启动时为半设置密钥对或缺主机名中的公开主机的记录 `event=turnstile_misconfigured`，即 enforce 可能拒绝所有人的两种方式。一个付费解出服务仍通过；该检查提高裸脚本的成本，而非一个坚定农场的成本。
- **被观察的 agent（`GET /orgs/{id}/agents/observed`，admin+）。** agent 故事的另一半：已经在以成员自身令牌调用的运行时。CLI 对其宿主运行时做指纹识别（`CLAUDECODE` → `claude-code`、`CODEX_*`、`CURSOR_*`、…；`TREG_CLIENT` 覆盖）并发送 `X-Treg-Client`；`_client_of` 规范化它（slug ≤32、剥去版本、保留未知但格式良好的以便新运行时无需发布）到 `CallRecord.client` / `RunRecord.client`，在三个审计点上。该端点把 30 天（来自每日用量汇总的调用，[data-model](data-model.md)）聚合成每（成员、运行时）一行，排除 `''`/`cli`（一个把每个真人列两遍的名册毫无教益）与机器身份（已归属到它们自身）。**归属(attribution)，而非认证**——任何持有令牌的都可以声称任何名字，因此没有任何东西门控于它；为一个检测到的 agent 真正限定作用域 = 为它铸造一个令牌（dashboard 的「Scope this agent」提升）。
- **两个 ACL 轴，以 AND 组合**（`_tool_usable` = `_tool_allowed` AND `_project_allowed`）。project 作用域是粗调，`tool_access` 是微调；两者都是 NULL-意味着-一切，且所有者对两者都豁免。`project_access` 持有 project **ID** 而非 slug，因此热路径检查是一个纯集合测试（每次调用无 id→slug 查询）且重命名不会使一个访问列表脱钩(strand)。`project_access=[X]` 且 `tool_access=NULL` 意味着「project X 中的每个工具，**包括之后添加的**」——使粗调单独有用的那种组合。`_normalize_project_access` 接受 slugs 或 ids，未知时 422，并把一个全-project 选择折叠回 NULL（镜像 `_normalize_tool_access`）。端点：`create_project` / `list_projects`（一个受作用域限制的成员只看到自己的）/ `delete_project`（admin+）——删除把它的工具 **释放** 回全 org，而非隐藏它们，并从每个成员的 scope 中丢弃该 id，**把一个已清空的列表存储为 `[]`，绝不存 NULL**。NULL 意味着 *每个 project*，因此把 `[]` 折叠会把手头只被限定到被删 project 的成员交给每个其他 project 的工具运行权限——一次由不相关删除触发的权限提升（第 4 轮拦截器 #1，`test_security_round4.py`）。`[]` 已经带有预期含义（仅全 org 工具），且无人被锁在外面，因为 **被释放的工具** 正是他们保留的：成员在删除前能触及的，删除后仍可触及。那，而非一个被拓宽的 scope，是「绝不把任何人锁在外面」所依赖的。邀请在两个接受门都携带 `project_access` 到成员资格上，正如 `tool_access` 那样。
- 每个列表都按 `caller.org_id` 过滤；每个创建都盖戳 `org_id = caller.org_id` + `owner = caller.email`；`_resolve_call` 把 **命名查找与主机/最长前缀透传** 都按 org 限定作用域；`call_tool` 只加载同 org 的 secret。参见 [proxy-model](proxy-model.md)。

`domain.identity.access` 是共享的身份/访问边界：`Caller`、令牌/会话/org 解析、依赖、角色比较与机器分类。会话签名与验证位于 `domain.identity.session`。两个令牌族共享一个 HMAC 密钥，但新铸造的凭据携带一个签名的受众(audience)：`make_session` 创建 `aud=session`，带必需的 7 天 `exp`，而 `make_identity` 创建 `aud=identity`；复制的团队密钥省略 `exp`，而无 org 的 `scp=bootstrap` 身份在七天后过期。`read_session_claims` 与 `read_identity_claims` 双向拒绝另一个受众；`token_version` 仍是任一族的吊销机制。

遗留令牌早于 `aud`，因此兼容边界遵循签名形态能实际证明的东西。一个 `org` 声明标识一个团队固定的复制密钥，它在先前的 30 天 `exp` 之后仍可用；一个无类型的无 `exp` 密钥也是仅身份的。一个无类型无 org、带 `exp` 的令牌与浏览器会话无法区分：它只在那个时间戳之前在任一条路径上工作，且 bearer 路径一旦过期就拒绝它，而非复活一个过期的 cookie。
- **注册在各门之间共享：** `application.signup.find_or_create_user(db, email)` 查找一个用户或创建他们——**仅用户，无自动个人 org**。每个身份门都调用它（GitHub / Google 回调、邮件 OTP），因此「首次证明 = 注册」是相同的。因此一个全新用户以 **零团队** 落地，且必须命名 + 创建其第一个团队（dashboard 的强制欢迎页，或 `treg org create`）。他们七天的 bootstrap 令牌在 org 存在之前就能工作，但不能调用或读取团队资源。**`create_org` 使用 `require_identity`，而非 `require_member`**——否则一个零 org 用户永远无法创建其第一个团队——并返回新成员资格的团队限定 Default 密钥。参见 [api](../interface/api.md)。
- **无码邀请(Code-free invites)：** `my_invites`（`GET /invites/mine`，`require_identity`）列出调用方已证明邮件的待定邀请，创建时间最新优先、以降序 ID 打破时间戳平局；`accept_my_invite`（`POST /invites/{id}/accept`，`require_identity`）无码加入（若 `invite.email != user.email` 则 403，若已是成员则 409）。码路径保留。
- **Org 管理端点：** `register_user`（`POST /users`，遗留开放注册，由测试 fixture 使用）仍通过 `_make_org_membership`（铸造令牌）创建用户 + 一个 org + 所有者成员资格——dashboard/CLI 登录门不可达，它们不再自动建 org。这个门与 `create_org` 都读取第一方广告点击 cookie（`application.signup._ad_attribution_from`），或当请求无 cookie 时读取邮件的 `AdClickStash` 行，并在启用且存在时把 `Org.ad_gclid`/`ad_click_id_type`/`ad_landing`/`ad_click_at` 盖戳到新 org 上——保留点击是 GCLID、GBRAID 还是 WBRAID——参见 [ads-conversions](ads-conversions.md)。`create_org`（`POST /orgs`，`require_identity`）、`list_orgs`（`GET /orgs`）、`create_invite`（`POST /orgs/{id}/invites`，admin+）、`accept_invite`（`POST /invites/accept`，开放 + 码保护 → 若为新则注册用户，把他们加入被邀请团队，铸造其令牌；一个全新的被邀请者 **只** 加入被邀请团队——无独立个人 org）、`list_members` / `remove_member`（`GET`/`DELETE /orgs/{id}/members[/{user}]`，admin+；所有者不可被移除）。`_require_admin_of(org_id, caller)` 门控管理员端点（令牌必须针对该 org 且角色 ≥ admin）。
- **一个身份离开时带走其调用方拥有的状态（`delete_membership`）。** 一个指向一个调用方（`user_id` 已设）的 `DenyRule` 在该调用方消失后变得毫无意义，且它滞留在 Policy 表中指名一个无人能解析的用户 id。`remove_member`、`leave_org` 与 `revoke_agent` 清扫该 `(user_id, org_id)` 的规则；`admin_delete_user` 清扫该用户 **每个 org** 的规则，因为 `DenyRule.user_id` 是一个外键，一个存活的行会悬空(dangle)——Postgres 直接拒绝，而 SQLite 只因不强制 FK 而隐藏它（因此只有测试套件无法捕获它）。ORG 级规则（`user_id` NULL）永不被触碰：它们关于团队，而非关于一个调用方。同一个辅助函数在删除成员资格之前删除键到它的 `IdempotentCall` 行；那些是重放缓存，而非审计历史，且吊销后不再有有效调用方。该外键也使用 `ON DELETE CASCADE` 作为数据库级后盾。这封堵了那个生产故障：吊销一个做过幂等付费调用的 agent 返回 500 并回滚其令牌吊销。镜像 `delete_project` 如何把其删除的 id 从每个 `project_access` 中清扫出去。
- **Org 管理：** `set_member_role`（`PATCH /orgs/{id}/members/{user}`，**仅所有者** 经 `_require_owner_of`；一个 `_count_owners` 的末位所有者守卫阻止降级唯一所有者——所有权转移 = 提升另一个人为所有者，然后退下）、`leave_org`（`POST /orgs/{id}/leave`，自我移除，同样的末位所有者守卫）、`delete_org`（`DELETE /orgs/{id}`，仅所有者，通过 `cascade_delete_org` / `ORG_SCOPED_MODELS`（位于 `domain/governance/teams.py`）级联每个 org 限定行——包括任何待定的 `AdConversion`：一个排队的转换属于它会被归因到的团队、`Media`：托管的引用文件否则会在 TTL 之前比团队活得久，以及 `HubListing`/`HubTool`：一个 maker 已发布的工具与搜索列表随拥有它们的团队一起走）。Workbench `TableDoc` 条目在其 `TeamDatabase` 映射之前被移除；远程资源清理见 [存储边界](workbench-storage.md#management-metadata)。**那个列表是唯一的**，外加一个具名例外：`cascade_delete_org` 也在那次清扫之前删除每个 `caller_org_id == org.id` 的 `HubRun`，因为一个运行通过那个外键命名调用(CALLED)的团队，而 maker 只按数字命名——一个调用方的痕迹随调用方走，一个 maker 的删除保留调用方历史 intact。所有者删除、管理员强制删除、落地沙箱收割器(reaper)与演示重置都经过它；`test_org_delete_clears_EVERY_org_scoped_table` 遍历 models 模块寻找任何携带 `org_id` 的东西，并也拒绝一个保留私有副本的收割器。沙箱收割器直到 2026-09-02 都如此，它的副本从未了解 `IdempotentCall`（它引用一个 Membership），且每个沙箱铸造都在外键处 500，直到它被修复。
- **邀请生命周期：** 一次性 **且** 有时间界限——`Invite.expires_at`（默认 `INVITE_TTL_DAYS`），`accept_invite` 在过期后返回 `410`。`list_invites`（`GET /orgs/{id}/invites`，admin+）与 `revoke_invite`（`DELETE /orgs/{id}/invites/{invite}`，admin+）；过期码由 `health.gc_expired_invites` 垃圾回收（在列出时机会主义地、在健康运行中周期性地）。

## 加固(Hardening)（被强制的不变量）

- **邮件是大小写不敏感的身份。** `_norm_email`（strip + lowercase）应用于每个身份门与每个邀请比较，因此 `Bob@X.com` 与 `bob@x.com` 是一个用户/一个个人 org，且一个邀请无论键入何种大小写都总是可兑换。
- **邀请卫生(Invite hygiene)。** `create_invite` 拒绝邀请一个已经是成员（409，无死胡同邀请）的邮件，并 **取代(supersede)** 该邮件的任何先前待定邀请（每个被邀请者一个活跃码）。`revoke_invite` 只删除仍 `pending` 的邀请。管理员不得签发 `admin` 邀请（仅所有者，镜像 `set_member_role`）。被挂起的用户/org 既不能查看也不能接受。
- **治理永不蒸发(Governance never evaporates)。** `admin_delete_user` 在移除一个 org 的唯一所有者时，把最早加入的幸存者提升为所有者；接受/创建路径在成员资格/slug 唯一性竞争(race)时返回干净的 `409`（非 500）（`create_org` 用新鲜的 `_unique_slug` 重试）。
- **Slug 对 id。** `_resolve_org` 先按 slug 解析 `X-Treg-Org`（一个全数字的 slug 如 `2024` 是可产出的，绝不能被重新解释为初级键），然后按 `previous_slug`，然后按 id。
- **重命名(Rename)。** `PATCH /orgs/{id}`（admin+，`teams.rename_org`）改变 `name` 和/或 `slug`。slug 被烘焙进签名团队密钥、`~/.treg`、MCP pins 与 agent 地址，因此 slug 变更把旧的退休到 `previous_slug`，而非吊销每个复制的密钥：它仍可解析，且没有其他团队可以占用它（`_slug_taken` 检查两列）。只有一个别名；第二次重命名覆盖它。Slug 被验证为它们自己的 `_slugify`，3–40 字符，绝不 `sbx-`（沙箱形态）。Stripe 元数据与分析分组键保留它们被盖戳时的 slug。
- **保留名(Reserved names)。** `teams.reserved_reason(text, extra)` 拒绝一个 *读作* 像 treg 自身、像「official」/「verified」、或像一个目录供应商/平台的名字或 slug（一个 hub tool 的可调用 id 是 `<team slug>.<name>`，因此一个被 squat 的 slug 可以把一个陌生人的 tool 冒充成我们的或某个供应商的）。匹配按文本如何读，而非其字节：NFKC-fold、映射形近(lookalike) 的 Latin/Cyrillic/Greek 字母与 leetspeak 数字（`teams._LOOKALIKE`）、剥去分隔符，然后比较单词——因此 `trеg-hub`（西里尔 е）、`t-r-e-g`、`apol1o` 与 `Hunter.io data` 都会被抓住。`signup.reserved_team_names()` 提供目录派生的 `extra` 集合（供应商 slugs 精确或前缀、平台 slugs `=` 标记为仅精确单词匹配）。在 `create_org`、``register_user`` 的默认团队名、与 `rename_org`（`PATCH /orgs/{id}`）处检查；超级管理员可以绕过它（`allow_reserved`）。

## Schema 所有权(Schema ownership)

Alembic 拥有多租户 schema。0.14.x 采用发布转换并盖戳了遗留数据库；当前发布拒绝一个非空未盖戳数据库，并把运营者导向那个下限(floor)。`db.verify_db()` 检查修订兼容性，而不创建或修复租户表。

> 健康（`run_all`）接受一个 `org_id` 过滤器，因此 `/health/run` 绝不泄露其他 org 的凭据，且告警解析所有者的每 org 成员资格 webhook。参见 [auth-secrets](auth-secrets.md)。

## 调用方标签与固定(pinned)读取作用域

调用方提供的 `X-Treg-Meta` 标签仍是归属标签：一个未固定的 org 令牌可以选择任何有效值。一个受限制的 agent 的 `Membership.pinned_tags` 由服务端强制；一个冲突的 header 是 403。一个未固定的 operator 保留全 org 视图与共享余额。

`domain.governance.access.pinned_tag_predicates` 要求存储标签中的每个固定键/值。`/calls`、`/calls/{id}/result`、`/calls/{call_ref}`、`/runs` 与 `/activity` 在分页或加载存档 body 之前应用该作用域。一个已知外部或未归因 id 是 404，就像一个未知 id 一样。`POST /reviews` 通过同样的谓词解析其调用，因此一个固定调用方既不能评分也不能探测另一个 pin 的调用。每个审计写入者存储 pin、被路由的父行，以及路由器的拒绝回退包含在内。一个反馈报告快照该报告者的 pin（`Feedback.tags`，也在修订 `0042` 中）：`GET /feedback/{id}` 通过它读取，且一个固定报告者的 `call_ids` 只对照其自身 pin 的行验证。匹配按 pin 而非当前成员资格：两个有相同 pin 的身份共享那个视图。改变一个成员资格的 pin 不会重新标记其更早的记录。

`AsyncTaskRecord.tags` 与 `AsyncResourceRecord.tags` 在它们自己的事务中快照有效提交标签，独立于有损的审计队列。被一个终端轮询或 worker 发现的资源继承原始任务的标签。共享供应商轮询/获取所有权检查使用那些快照以及 org、供应商与资源身份；一个固定拒绝是 404。未固定的 403 契约不变。BYOK 与 own-tool 上游访问仍遵循既有的凭据与 tool ACL：这些读取作用域不分割一个团队自己的供应商账户。

预留账本(reserve ledger)条目在 `meta.tags` 中冻结权威标签；`/calls/{call_ref}` 因此即使审计被丢弃且 hold 已释放，也能提供一个授权的仅账本历史。缺失的历史归属绝不从当前成员资格或可变的花费计数器推断。修订 `0042` 给 run/task/resource 记录添加可空标签，而不回填猜测。旧的未标记行仍可被未固定 org 成员读取，但不可被固定身份读取。一个较旧的二进制可以运行于增量 schema，但不强制新的读取边界。

两个 run 审计写入者都存储成员资格 pins。两个历史源（在 `/runs` 中）与全部三个（在 `/activity` 中）都在其限制之前过滤。Run 在此变更中不会获得调用方提供的元数据解析。

Treg 的重放键包括完整 pin 以及既有的主标签作用域，因此改变一个次要 pin 无法暴露一次旧重放。在共享供应商凭据上，被转发的幂等标签还按完整 pin 分区；未固定的转发逐字节不变。普通 BYOK 标签保持原样。公开媒体 URL 仍是供供应商获取的「凭持有即授权(bearer-by-possession)」链接；过滤历史防止通过那些已认证读取被发现，而非阻止已经持有一个 URL 的人访问。

`TagBudget` 仍是 org 共享余额的上限(ceiling)，绝非一个子账户。`TagSpend` 与 `TagBudget` 在 `domain.governance.teams.ORG_SCOPED_MODELS` 中仍按 org 限定作用域，且 `TagSpend` 先于它引用的账本/hold。固定读取作用域不改变预算并发或结算。

- **共享供应商异步对象是按 org 限定作用域的。** 平台密钥轮询与结果获取工具调用必须在联系上游之前通过一个 org 拥有的 `AsyncTaskRecord` 或 `AsyncResourceRecord` 解析其 id。`_one_resource_value` 从查询字符串读取 id，或当目录描述符指名一个 body 参数（`in: body`）时从 JSON body 读取——无论哪种都必须恰好提供一个值。一个 body 可以是一个对象或一个供应商的任务对象数组（DataForSEO 的 `[{"id": ...}]`）；每个元素必须指名同一个 id，因此一个拥有的首个任务无法在第二个中携带另一个团队的 id。一个 `produces` 路径可以用 `*` 取每个列表项（`tasks.*.id`）：一次提交多个任务拥有它们中的每一个。BYOK 调用保留对团队自己供应商账户中 id 的访问。
- **共享供应商持久对象是按 org 限定作用域的。** 一个平台密钥托管资源调用在联系供应商之前针对 `ProviderResource` 验证每个标量或数组 id。一个 `use` tool 还可以声明一个只读公开查找：一个不在所有权表中的 id 只有在供应商在无数据库连接被持有时确认目录谓词后才被接受。任何分配给另一个组织或被 tombstoned 的 id 在本地被拒，且绝不经该查找发送。所有成员可以创建、列出、使用、重命名与删除他们团队的对象；拥有它们的是组织边界，而非创建者。BYOK 绕过此表。dashboard 的 Team resources 清单显式请求 `source=platform`；因此一个已连接的 BYOK 账户绝不替换或拓宽组织的持久资源清单。

## 注册分析边界(Signup analytics boundary)

`find_or_create_user` 可选地收集它在一次成功 flush 后实际插入的 ID；一个并发插入失败者返回既有用户而不标记为新建。邮件 OTP 与 GitHub/Google 认证在它们的提交 **之后** 把那个收集传给 `track_signup`，仅为新账户发出 `signup_completed`。可选的入口表面 cookie 是分析元数据，由 `analytics.funnel_surface` 允许列表化；它绝不影响认证或团队访问。

## 已发布 CLI 兼容性(Released CLI compatibility)

未修改的 PyPI CLI 0.16.0 与 0.19.0 可以使用既存的已保存令牌、完成浏览器登录，并用 `org use` 交换 Default 密钥。它们的邮件流程丢弃浏览器 cookie 并会保存一个受限的 bootstrap 令牌。它们的建团队与身份模式邀请流程在选择了新团队后保留先前的令牌。一个受作用域限制的 Default 密钥仍必须拒绝那个不匹配。

`routers/auth_helpers.require_managed_cli` 在签发邮件凭据、创建团队或消费一个邀请之前，以 HTTP 426 停止这些已知的旧客户端请求。该响应告诉用户运行 `treg update` 并重试。当前 CLI 请求发送 `X-Treg-Key-Protocol: 1` 并保存返回的团队密钥。遗留客户端暗示是已发布 CLI 的 `python-httpx/` User-Agent 加上 `ngrok-skip-browser-warning: 1`，没有那个协议标记。它是一个兼容性检查，而非授权边界或通用客户端版本检测器。浏览器与通用 API 客户端保留它们的 API 行为；省略或伪造该暗示绝不放松令牌限制。

既存的未限定作用域令牌保留它们旧的建团队行为。带类型凭据的新鲜邮件登录与团队变更在受影响路径上需要更新后的 CLI。这是一个受控升级要求，而非对旧客户端中所有新鲜登录流程的完全支持。已发布 wheel 测试 `test_released_cli_compat` 检查拒绝是否保留配置字节与先前的可用团队。
