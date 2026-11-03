# 阶段 3 身份与控制设计

**状态：**检查点 0 草稿。本文件仅为审阅产物，不得提交。

本设计所读的事实来源：

- `/tmp/treg-phase3-brief.md`
- `docs/REFACTOR-PLAN.md` 第 1.1、1.2、1.3、1.6、1.7 节、阶段 3，以及第 5 节
- 当前的 `src/treg/api.py`、`src/treg/routers/dependencies.py`、`src/treg/session.py`、`src/treg/mcp_oauth.py`、`src/treg/bootstrap.py`，以及 import-linter 配置
- `tests/snapshots/routes.json`、`openapi.json`、`composition.json`、`lifespan.json`
- 相关 context 片段：composition、import boundaries、MCP OAuth、multi-tenancy、super-admin、API、dashboard

分支为 `refactor/phase3-identity`，提交 `5636794`。被跟踪的工作树最初包含一次意外的 `uv.lock` 重写。它只含锁文件格式的 timestamp/wheel 展开，没有预期的项目依赖变更，因此按 brief 的指引被精确还原。只有已知被忽略的本地产物保持未跟踪。

## 0. 代码移动前需确定的决策

检查点 0 发现两处事实来源冲突与三处范围歧义。本文档未解决它们。代码工作必须等待审阅来选择边界。

### 0.1 `session.py` 的角色与运行中的依赖图不符

第 5 节说 `session.py -> domain/identity`，角色 `control`。当前 dataplane MCP 路径在 `mcp._oauth_claims` 与无效 token 守卫里导入 `mcp_oauth`，`mcp_oauth._key()` 导入 `session._key()`。因此 dataplane 需要 session 签名密钥实现来验证一个 MCP access token，即便它不运行浏览器登录。

供审阅的修正提议：目的地仍为 `domain/identity`，但其运行时角色为 `both`（both），其中浏览器会话签发仅由 control 使用，而共享的 token 签名验证由两者共用。除非审阅明确批准该措辞，否则本 PR 不得编辑计划。

### 0.2 逐字节移动与一层薄的 `application/auth` 边界冲突

多步认证实现当前就是 FastAPI 端点函数本身。它们的源码包含 `@app.*` 装饰器、`Depends`/`Cookie`/`Form` 参数、HTTP 异常与响应对象，以及数据库提交。硬性规则说被移动的符号（含其装饰器）必须逐字节一致。第 1.1 节说 router 翻译 HTTP 且是薄的；brief 说多步登录、CLI 配对、以及 OAuth 授权服务器流成为 application auth 用例。

这些约束无法在一次机械移动中全部达成：

1. 把确切的装饰函数移到 `routers/auth.py` 保留了字节与界面，但把编排与提交留在了 router 里。
2. 把它们确切移到 `application/auth.py` 需要一个 `app = APIRouter()` 装饰目标，并使 application 层依赖 FastAPI，所以它不是目标 application 边界。
3. 抽取一个框架中立的 application 函数、留下一个薄的 router 包装，会改变原始处理器源码。它可以行为等价并经测试，但它不是逐字节的符号移动。

推荐的审阅选择：尽管通用的一移动措辞，对每个认证旅程使用两个提交。第一个机械地把完整的装饰块移到 `routers/auth.py`；下一个仍限定于同一旅程，抽取一个新的 application 函数，并只把已移动的 router 改成薄包装。第二个是行为中立的重构，而非行为变更，且必须携带同样的 E2E 旅程加全部四份快照。如果预期标准是每个旅程总共一个提交，审阅必须把选项 1 批准为阶段 3 的中间架构。

### 0.3 `resources` 没有第 5 节的一行，因为 `api.py` 被刻意省略

第 1.1 节命名了一个 `routers/resources` 目的地，但第 5 节说 `api.py` 不重复。路由快照在位置 156 到 174 给出了一块明显的核心块：secrets、tools、local-run 的 grant/report、skills、bundles。两条边不显然：

- `POST /tools/{name}/grant` 与 `POST /tools/{name}/run-report` 是资源形态的 URL，但执行 `application/run` 关注点并写入审计行。提议归属：在 runner 抽取之前留在 `api.py`，除非审阅把 `resources` 定义为在阶段 3 包含它们。
- `GET /calls`、`GET /calls/{call_ref}`、`GET /runs` 紧接资源块之后，但是审计/活动视图。提议归属：留给 call/run 阶段。

本文档其余部分把资源 CRUD 视为位置 156 到 164，技能/bundle 视为 167 到 174，把 165、166、175 到 177 留在 `api.py` 待审阅。

### 0.4 能力 pin 未被分配到治理域（domain matrix）

路由 149 到 151 位于 org 策略路由之间，但 `CapabilityPin` 选择一个 Catalog 供应商。第 1.3 节把团队、成员、project、deny 规则、limit、budget 分配给治理（governance），并把能力/价格选择分配给 catalog。提议归属：把能力 pin 路由留在 `api.py` 待 catalog 阶段。如果阶段 3 的意思是每个当前的 org 前缀控制路由，审阅必须显式把 pin 分配给治理。

### 0.5 旧模块导入路径需要兼容性裁决

测试与运行时代码直接导入 `treg.session` 和 `treg.mcp_oauth`。与 `treg.api:app` 不同，brief 没有明确要求这些路径保持公开，但删除它们会是一个可观测的导入变更。提议方法：本阶段在这两条路径上保留薄的重新导出垫片，而所有运行时所有者导入 `treg.domain.identity.session` 与 `treg.domain.identity.mcp_oauth`。第 5 节目的地因此是真实的，但旧路径仍是兼容外观。`routers/dependencies.py` 不同：阶段 3 明确要求删除，所以不提供垫片。

## 1. 对照目的地地图与快照

### 1.1 目的地包形态

`domain/identity` 必须是一个包，而非一个 `identity.py`。`session.py` 与 `mcp_oauth.py` 都含不同的 `_key`、`_b64`、`_unb64` 符号，所以合并它们会强迫重命名并违反字节规则。提议形态：

```text
src/treg/domain/
  __init__.py
  identity/
    __init__.py      公开的身份导出
    session.py       当前 treg/session.py 的确切体
    mcp_oauth.py     当前 treg/mcp_oauth.py 的确切体
    access.py         Caller、解析、角色、auth 依赖

src/treg/application/
  __init__.py
  auth.py             多步身份证明、配对、OAuth AS 编排
  signup.py           身份供给与首团队创建/授予排序
  connect.py          OAuth/key 连接工作流

src/treg/routers/
  auth.py
  orgs.py
  resources.py
  connections.py
```

`routers/auth.py` 与 `application/auth.py` 之间的确切拆分受阻于第 0.2 节。

### 1.2 `session.py -> domain/identity`

确切符号：

- 常量：`TTL_SECONDS`、`COOKIE`、`_EPHEMERAL_KEY`
- 函数：`_key`、`_b64`、`_unb64`、`make`、`read_claims`、`read`

当前导入者：

- 运行时：`api.py`、`routers/dependencies.py`、`routers/web.py`、`mcp.py`、`mcp_oauth.py`
- 测试：`test_auth.py`、`test_login_page.py`、`test_token_revocation.py`、`test_mcp_oauth.py`、`test_legacy_host_redirect.py`、`test_bughunt_server.py`、`test_single_user.py`

对账结果：目的地一致，角色不一致。见 0.1。本模块不拥有任何 lifespan 任务。路由快照间接通过每个 auth 依赖与 MCP 挂载依赖它。

### 1.3 `mcp_oauth.py -> domain/identity` 的 grant/refresh 族

确切既有符号：

- 常量：`ACCESS_TTL_SECONDS`、`_TOKEN_TYPE`、`_CIMD_TIMEOUT_S`、`_CIMD_MAX_BYTES`、`_CIMD_REFRESH_S`
- token/resource 函数：`_key`、`_b64`、`_unb64`、`mcp_resource_url`、`mcp_resource_audiences`、`normalize_resource`、`read_access_token_any`、`protected_resource_metadata`、`authorization_server_metadata`、`make_access_token`、`looks_like_access_token`、`read_access_token`、`verify_pkce`
- 客户端函数：`valid_redirect_uri`、`redirect_uri_allowed`、`fetch_client_id_metadata`、`new_client_id`

第 5 节的短语"grant/refresh 族"也把当前 `api.py` 的这些原语映射到 identity：

- `_ensure_grant`
- `_family_org`
- `_refresh_is_live`
- `_issue_refresh`
- `_revoke_refresh_family`

`_refresh_grant` 是编排：它检查一个呈现的 token，轮换或杀死一个 family，提交，并构造一个 HTTP 响应。它属于 `application/auth`，而非 identity 叶子。OAuth 路由处理器通过这些 domain 原语经由 application auth 调用。

当前导入者是 `api.py`、`mcp.py`、`tests/test_mcp_oauth.py`、`tests/test_mcp.py`、`tests/test_legacy_host_redirect.py`。没有 monkeypatch 指向 `mcp_oauth` 符号。两个测试 patch `health.safe_webhook_url`、`health.host_is_public`、`httpx.AsyncClient.get`，仍然有效，因为 `fetch_client_id_metadata` 在调用时执行那些惰性导入。

对账结果：路由位置 67 到 75 与 92 到 93 在 control 上用这个族；位置 72 与 `/mcp` 挂载在 dataplane 上验证它。该文件当前不写任何数据库行；第 5 节点名的 `oauthclient`、`oauthgrant`、`oauthrefresh` 写入仍在 `api.py`，这解释了而非矛盾于目的地措辞。

要记录的层债（不要在一次纯移动中修复）：`fetch_client_id_metadata` 从一个 domain 函数内部导入具体的 `httpx` 与根 `health` 模块。它今天不创建兄弟域边，但它不是第 1.4 节描述的终极 infra-port 形态。

### 1.4 过渡性依赖解散

移动到 `domain.identity.access`，逐符号逐字节一致：

- `Caller`
- `_membership_by_token`
- `_user_from_session`
- `_resolve_org`
- `require_identity`
- `_user_from_identity_token`
- `require_member`
- `require_superadmin`
- `_role_at_least`
- `_norm_email`
- `PUBLIC_DEMO_DOMAIN`、`AGENT_DOMAIN`
- `_is_agent_email`、`_is_machine_email`

HTTP cookie 辅助不是身份域规则，且不能创建未来的 `identity -> referrals` 兄弟边：

- `_is_https`、`OAUTH_RETURN_COOKIE`、`_remember_oauth_return`、`_take_oauth_return` 随 auth 接口辅助模块移动。
- `REFERRAL_COOKIE`、`REFERRAL_COOKIE_MAX_AGE`、`_remember_referral`、`_take_referral` 移动到一个小的、被 `routers.web` 与 signup 编排使用的 router/共享 signup-cookie 模块。它们不能居于 `domain.identity` 之下，因为 `_take_referral` 调用 `referrals.normalize_code`。

`api.py` 可以在分阶段的移动期间重新导出身份名字，但所有新的 `Depends(...)` 站点必须直接从 `domain.identity` 导入。`routers/admin.py`、`routers/catalog.py`、`routers/web.py` 必须在身份提交里更新。最终，全仓库 `rg routers.dependencies` 必须返回零个 Python 导入，且 `src/treg/routers/dependencies.py` 被删除。那条过渡路径刻意没有兼容垫片。

### 1.5 路由对账与注册点

当前相关的路由顺序是：

| 快照位置 | 关注点 | 阶段 3 处置 |
|---:|---|---|
| 24-38 | 社交登录、CLI 配对、登录页、auth/me/logout、邮箱 OTP、邀请登录 | auth |
| 39-66 | 已移动的 web 路由 | 不变分隔符 |
| 67-75 | OAuth 客户端注册、authorize、revoke/token、discovery/challenge | auth |
| 76-87 | 已移动的公开文档与静态挂载 | 不变分隔符 |
| 88-89 | CLI token 与 token 撤销 | auth |
| 90-91 | 遗留用户注册与 org 创建 | signup/governance |
| 92-93 | OAuth grants 列表/团队移动 | auth |
| 94-97 | org 列表与邀请创建/接受/列表 | governance |
| 98-110 | onboard/demo/Stripe/skill 样本 | 留在 `api.py` |
| 111-123 | 邀请、成员、用量/设置/budget | governance，但 money 所有权保留 |
| 124-131 | billing/referrals | 留在 `api.py` |
| 132-148 | 成员访问/生命周期、机器身份、project | governance |
| 149-151 | 能力 pin | 提议留待 catalog，需审阅 |
| 152-155 | deny 策略 | governance |
| 156-164 | secret 与 tool CRUD | resources |
| 165-166 | local grant/report | 提议留待 runner，需审阅 |
| 167-174 | skills 与 bundles | resources |
| 175-177 | calls 与 runs 活动 | 留在 `api.py` |
| 178-189 | OAuth connect、connections、discovery/resource 选择、health | connections |
| 190-197 | 既有 admin 读 router | 不变 |
| 198-202 | admin 身份/org 变更 | identity/governance control |
| 203-206 | 既有 admin 报告 router | 不变 |
| 207-210 | 访问预检、call、run、MCP | 不变 |

每个目标 router 导出多个有序的 `APIRouter` 块，且 `api.py` 用既有的直接附接约定把每个块附在确切的原始点。不允许任何 `include_router()` 重新分组。计划的附接形态是：

```text
routers.auth
  login_router       24..38
  oauth_server_router 67..75
  token_router       88..89
  grants_router      92..93

routers.orgs
  signup_router      90..91
  org_entry_router   94..97
  org_detail_router  111..123
  org_control_router 132..148
  policy_router      152..155
  admin_mutations_router 198..202

routers.resources
  crud_router        156..164
  skill_router       167..174

routers.connections
  router             178..189
```

这保留了与阶段 2 router、onboarding、billing、admin reads/reports、以及 call/run 的每一个交错。堆叠的 discovery 装饰器保留其原始文本，从而保持当前的快照顺序：在渲染的路由列表里 `/oauth-protected-resource/mcp` 在 `/oauth-protected-resource` 之前。

### 1.6 Lifespan 对账

`lifespan.json` 没有 auth、governance、或 resource 任务。它有一个阶段 3 connection 拥有的启动写入：

- `treg.api._backfill_provider_extra_tools`

该函数属于 connection 供给，但快照与三份角色启动清单都点名兼容路径。把它的确切体移动到 application connect，并从 `api.py` 重新导出同一个函数对象；不要改变快照字符串或角色清单。它在阶段 5 到期之前，保留在所有、control、dataplane 启动下的第 1.6 节过渡写入特例里。不允许新的启动写入加入它。

## 2. 提议的移动单元与提交顺序

顺序遵循导入：先身份叶子，然后 auth、governance、资源所有权，最后 connections（其自动供给依赖资源辅助）。每个被移动的函数/类保留其确切源码。常量与块注释随其块移动。新的模块文档字符串、导入块、router 别名、附接注释、兼容重新导出是仅有的机械脚手架例外。

下面的 auth 排序假设审阅批准第 0.2 节的两步法。如果审阅选择中间-router 法，省略每个 `application` 后续提交，并记录薄-router 目标被推迟。

### 提交 1：身份叶子与过渡依赖删除

归属：

- `domain.identity.session`：1.2 中每个符号
- `domain.identity.mcp_oauth`：1.3 中每个既有符号加 `_ensure_grant`、`_family_org`、`_refresh_is_live`、`_issue_refresh`、`_revoke_refresh_family`
- `domain.identity.access`：1.4 中的身份/访问列表
- auth/referral HTTP cookie 辅助移动到 1.4 中描述的非域之家
- 更新所有导入者并删除 `routers/dependencies.py`
- 可选的 `treg.session` 与 `treg.mcp_oauth` 兼容垫片，取决于决策 0.5

同一提交中的 import-linter：加 `Identity is a domain leaf`，带 `source_modules = ["treg.domain.identity"]`、`as_packages = true`，以及显式禁用的兄弟包 `governance`、`connections`、`tools`、`catalog`、`capacity`、`money`。该契约必须在提交前对照 import-linter 2.13 测试；如果不存在的禁用模块被拒绝，则在提交 7 引入第一个兄弟包时创建该契约，而不是加假的占位域。需要审阅批准，因为 brief 要求在抽取提交里激活。

旅程：依赖行为被完整的 `tests/test_router_dependencies.py` 钉住，外加 `tests/test_auth.py::test_session_scopes_by_x_treg_org` 与 `tests/test_mcp_oauth.py::test_our_own_token_is_accepted_and_carries_the_team`。

### 提交 2：邮箱 OTP 登录旅程

来自 `api.py` 的符号：

- `EmailStartIn`、`EmailVerifyIn`
- `EMAIL_CODE_TTL`、`MAX_OTP_ATTEMPTS`、`OTP_NS`、`OTP_START_NS`、`OTP_START_WINDOW_S`、`OTP_START_MAX_PER_EMAIL`、`OTP_START_MAX_PER_IP`
- `auth_email_start`、`auth_email_verify`
- `_find_or_create_user` 与 `_client_ip` 作为上游用例辅助

确切的装饰端点先移动到 `routers.auth.login_router`。Application 抽取（若批准）把身份确认/限流/会话排序放在 `application.auth`；首次身份创建仍是共享的 signup 命令，而非跨 OAuth 门复制。

旅程：`test_auth_email.py::test_first_login_registers_user_with_no_org_then_reuses_identity` 覆盖 start、dev code、verify、会话/token 签发与复用。限流与一次性码测试保留在同一文件。

### 提交 3：CLI 配对旅程

来自 `api.py` 的符号：

- state/常量：`CLI_TOKEN_TTL`、`HANDSHAKE_TTL`、`CLI_APPROVE_MAX_TRIES`、`_PAIR_ALPHABET`、`_cli_pending`、`_cli_results`、`_LOGIN_ID_RE`
- `CliApproveIn`、`_prune_handshakes`、`_norm_pair_code`、`_orgs_brief`
- `auth_cli_start`、`auth_cli_poll`、`auth_cli_orgs`、`auth_cli_approve`、`login_page`、`_login_page_html`
- 确切的登录页常量 `_AUTH_HEAD`、`_LOGIN_CSS`、`_LOGIN_JS`

`_same_origin` 与 logout 和 OAuth 批准共用，所以它在这些单元之前一次性移动到 auth 接口辅助。`_auth_page` 由社交登录、邀请登录、OAuth connect 回调共用，且保留为一个共享的 auth 呈现辅助而非被复制。

旅程：`test_login_page.py::test_email_door_completes_the_handshake` 证明 邮箱 start -> verify -> CLI start -> approve -> poll。配对守卫由 `test_approve_requires_a_started_login_and_matching_code` 与 `test_wrong_code_attempts_are_capped` 分别钉住。

### 提交 4：GitHub/Google 浏览器登录旅程

来自 `api.py` 的符号：

- `auth_github`、`auth_github_callback`、`auth_google`、`auth_google_callback`
- `_finish_oauth_login`、`_auth_page`、`_login_callback_base`
- `auth_me`、`auth_logout`、`_intercom_user_hash`

旅程：`test_auth.py::test_github_login_creates_user_session_but_no_auto_org` 与 `test_google_login_creates_user_session_but_no_auto_org`；`test_bad_state_rejected` 与 `test_google_bad_state_rejected` 钉住 CSRF 拒绝。

### 提交 5：邀请登录认证旅程

来自 `api.py` 的符号：

- `_live_invite_by_email_token`
- `auth_invite_signin`、`auth_invite_signin_confirm`

该单元在治理邀请读取存在之后，经由一个窄的命令/读取函数导入它。因为 auth 必须在 governance 之前移动以满足 identity-first 顺序，首次机械移动可以继续直接读取共享模型；不要创建 `identity -> governance` 边。

旅程：`test_invites_mine.py::test_email_link_post_signs_in_once_and_lands_on_invite_org`，外加该文件中的重放与挂起用户测试。

### 提交 6：MCP OAuth 授权服务器旅程

来自 `api.py` 的符号：

- DTO/常量：`OAuthClientRegistration`、`GrantTeamIn`、`AUTH_CODE_TTL_S`、`REFRESH_TTL_S`、`_CONSENT_CSS`
- 客户端/authorize 辅助：`_resolve_oauth_client`、`_consent_page`、`_wrong_resource`、`_same_mcp_resource`、`_oauth_error`、`_authorize_request`
- refresh 编排：`_refresh_grant`
- 端点：`oauth_register`、`oauth_authorize`、`oauth_authorize_approve`、`oauth_revoke`、`oauth_token`、`oauth_protected_resource`、`oauth_authorization_server`、`openai_apps_challenge`、`oauth_grants`、`oauth_grant_set_team`

身份 grant/refresh 原语已活在提交 1 中。auth application 单元拥有会话与事务排序。路由块附在 67 到 75 与 92 到 93。

旅程：`test_mcp_oauth.py::test_the_whole_flow_end_to_end` 证明 register -> authorize -> approve -> exchange -> MCP 验证。Refresh 轮换/重放与团队移动测试对本提交仍强制要求。

### 提交 7：CLI token 签发与用户 token 撤销

来自 `api.py` 的符号：

- `auth_cli_token`、`auth_revoke_tokens`
- `_is_last_active_superadmin` 在提交 13 之前与 admin 控制共享

旅程：`test_token_revocation.py::test_revoke_kills_old_identity_token_and_issues_a_fresh_one` 与 `test_auth.py::test_cli_token_bakes_the_active_org_and_works_as_a_BARE_bearer`。

### 提交 8：signup 与团队创建

来自 `api.py` 的符号：

- DTO：`UserIn`、`OrgIn`
- 辅助：`_slugify`、`_unique_slug`、`_make_org_membership`、`_grant_signup_promo`、`_ad_attribution_from`、`_utm_attribution_from`、`_stamp_utm`、`_redeem_referral`
- 端点：`register_user`、`create_org`、`list_orgs`

application signup 单元拥有多域促销授予与提交。Org slug 与成员规则属于治理。第 4 节列出的既有提交/回滚在移动期间保留。

旅程：`test_orgs_mgmt.py::test_create_org_returns_a_working_token`；邮箱优先的零团队创建也由 OTP 旅程覆盖。

### 提交 9：邀请生命周期

来自 `api.py` 的符号：

- `InviteIn`、`AcceptIn`、`INVITE_TTL_DAYS`
- `create_invite`、`accept_invite`、`my_invites`、`accept_my_invite`、`list_invites`、`revoke_invite`

随本单元移动的依赖：`_require_admin_of`、`_known_access_names`、`_normalize_tool_access`、`_normalize_project_access`。如果这些规范化器会创建过早的 governance-to-tools 写入边，则只把它们作为对共享 schema 的验证读取暴露。

旅程：`test_orgs_mgmt.py::test_invite_and_accept_new_user`，外加 `test_invites_mine.py::test_invite_seen_and_accepted_without_code`。

### 提交 10：成员管理与限制

来自 `api.py` 的符号：

- DTO：`RoleIn`、`CapIn`、`AccessIn`
- `_require_admin_of`、`_require_owner_of`、`_count_owners`、`_known_tool_names`、`_known_access_names`、`_normalize_tool_access`、`_used_today_by_user`、`count_today`、`_day_start_utc`、`_drop_member_deny_rules`
- `list_members`、`set_member_cap`、`set_member_access`、`my_usage`、`remove_member`、`set_member_role`、`leave_org`、`delete_org`、`_cascade_delete_org`

旅程：`test_orgs_mgmt.py::test_transfer_ownership_then_demote`、`test_access.py::test_set_access_validates_and_collapses`、`test_orgs.py::test_org_delete_clears_EVERY_org_scoped_table`。

### 提交 11：机器身份旅程

来自 `api.py` 的符号：

- `AgentIn`、`_public_demo_email`、`_agent_email`、`_agent_name`
- `create_public_token`、`delete_public_token`、`create_agent`、`list_agents`、`agent_checkin`、`list_observed_agents`、`revoke_agent`
- `_norm_client` 与 `_client_of` 移动到一个中立的横切调用者元数据模块，因为 call 与 run 仍用它们。治理导入那个中立模块，而非一个兄弟域。

旅程：`test_agent_identity.py::test_agent_can_call_but_cannot_act_as_a_user` 与 `test_agent_identity.py::test_rotate_kills_the_previous_token`。

### 提交 12：project、policy、settings、usage、budget

来自 `api.py` 的符号：

- project：`ProjectIn`、`_project_view`、`_normalize_project_access`、`_resolve_project`、`create_project`、`list_projects`、`delete_project`
- deny：`DenyRuleIn`、`_deny_view`、`_deny_match`、`_org_deny_rules`、`_enforce_deny`、`create_deny_rule`、`list_deny_rules`、`list_cli_deny`、`delete_deny_rule`
- org 设置/用量：`OrgSettingsIn`、`get_org_settings`、`set_org_settings`、`org_usage`、`_usage_rollup`、`list_tag_keys`、`usage_by_tag`
- budget：`TagBudgetIn`、`_tag_budget_view`、`list_tag_budgets`、`set_tag_default`、`set_tag_budget`、`delete_tag_budget`

call/runtime 消费者从新域导入公开的治理读取与门禁。调用函数 `_primary_dim_of`、`_budget_dims_of`、`_effective_daily_cap`、`_validate_tag_pair`、`_tag_budget` 留在它们当前执行处，直到阶段 4，除非移动它们需要避免一个反向导入。如果需要，停下审阅而非创建 `domain.governance -> api`。

旅程：`test_projects.py::test_project_scope_gates_listing_and_calling`、`test_deny_rules.py::test_deleting_the_rule_restores_the_call`、以及 `test_tag_billing.py` 中的 org 设置/budget 旅程。

### 提交 13：admin 身份与 org 控制

来自 `api.py` 的符号：

- `BoolIn`、`_is_last_active_superadmin`、`_cascade_delete_org`、`_drop_member_deny_rules`
- `admin_set_superadmin`、`admin_suspend_user`、`admin_delete_user`、`admin_suspend_org`、`admin_delete_org`

router 块附在既有 admin 读与既有 admin 报告之间，在 198 到 202。共享的治理/身份命令被直接调用；admin router 不导入 `api.py`。

旅程：`tests/test_admin.py` 中相应的变更测试，含 last-active-superadmin 与删除级联覆盖。

### 提交 14：secret CRUD 资源旅程

来自 `api.py` 的符号：

- DTO：`SecretIn`、`SecretUpdate`
- `create_secret`、`list_secrets`、`update_secret`、`delete_secret`
- `_require_not_live_demo_secret`、`_validate_bundle_id`、`_secret_view`、`_visible_secret_ids`、`_can_manage`、`_require_can_register`

`_can_manage` 与 `_require_can_register` 是治理/身份授权规则，应该是已从抽取域中公开出来的命令，而非复制到 resources。

旅程：`test_step3_crud_auth_audit.py::test_secret_crud_and_owner_stamp` 与 `test_step3_crud_auth_audit.py::test_cannot_delete_secret_in_use`。

### 提交 15：tool CRUD 资源旅程

来自 `api.py` 的符号：

- DTO：`ToolIn`、`ToolUpdate`
- 辅助：`_host_of`、`_normalize_scheme`、`_flat_binding`、`_require_not_live_demo_tool`、`_require_public_base_url`、`_validate_bindings`、`_require_secret_ownership`、`_validate_cli_profile`、`_validate_cli_secrets`、`_allowed_server_bins`、`_tool_view`
- 端点：`create_tool`、`list_tools`、`get_tool_by_name`、`update_tool`、`delete_tool`

治理 ACL 读取 `_tool_allowed`、`_project_allowed`、`_tool_usable`、`_require_tool_access`、`_require_tool_use` 保持公开的治理规则，因为 call 运行时也消费它们。如果审阅把资源授权分配给 `domain.tools`，当那个包出现时激活允许的 `tools -> connections` 边。

旅程：`test_step3_crud_auth_audit.py::test_tool_crud_and_duplicate_name`，外加证明列表不拓宽的 project/access 测试。

### 提交 16：技能与 bundle 资源旅程

来自 `api.py` 的符号：

- DTO：`BundleUpdate`、`SkillSecretIn`、`SkillToolIn`、`SkillIn`、`SkillFileIn`、`SkillAnalyzeIn`、`SkillImportIn`
- `_sanitize_bundle_files`、`_register_skill_bundle`、`_check_upload_size`、`_materialize_skill_files`、`_scan_uploaded_skills`、`_bundle_allowed`、`_bundle_view`
- `register_skill`、`analyze_skill_folder`、`import_skill_folder`、`list_bundles`、`get_bundle_by_name`、`get_bundle`、`update_bundle`、`delete_bundle`

旅程：`test_skill_upload.py::test_import_registers_recipe_and_tool` 与 `test_skill_upload.py::test_reimport_is_idempotent_not_500`。

### 提交 17：OAuth 与粘帖 token 连接建立

来自 `api.py` 的符号：

- DTO：`OAuthStartIn`、`TokenConnectIn`
- `_free_connection_name`、`_provider_bindings`、`_autoprovision_provider_tool`、`_upsert_provider_extra_tools`、`_provider_tool_examples`、`_record_connected_identity`、`_dig`
- `oauth_providers_list`、`oauth_start`、`oauth_callback`、`connect_with_token`、`oauth_status`
- `_backfill_provider_extra_tools`，带 lifespan 要求的 `api.py` 兼容重新导出

application connect 用例拥有会话与提交序列，并调用公开的 tools 与 connections 命令。启动回填仍是一个单独命名的启动操作，而非在 dataplane 请求处理上加写入的借口。

旅程：`test_connections.py::test_registry_connect_autoprovisions_a_callable_tool` 与 `test_oauth_connect.py::test_callback_exchanges_code_and_creates_oauth_secret`。

### 提交 18：连接资源、额外凭据、撤销与 health

来自 `api.py` 的符号：

- DTO：`ResourceRefIn`、`ExtraCredentialIn`
- `_owned_connection`、`_enrich_resource_labels`
- `list_connections`、`connection_resources`、`set_connection_resource`、`set_extra_credential`、`revoke_connection`、`run_health`、`get_health`

旅程：`test_connections.py::test_set_and_read_back_the_selected_resource`、`test_connections.py::test_revoke_removes_the_connection`、`test_connection_health.py::test_a_failed_refresh_records_why`。

## 3. 导入者与兼容策略

### 3.1 `api.py`

`api.py` 仍是有序路由表宿主与 `treg.api:app` 兼容入口点。在序列期间它导入每个 router 块并附在旧位置。它可重新导出有已知测试/运行时导入的符号，但被移动的 router 与域从不导入 `api.py`。

已知要保留或刻意更新的直接兼容名字：

- `api.Caller`、`api.require_identity`、`api.require_member`、`api.require_superadmin`，以及被 `tests/test_router_dependencies.py` 钉住的其余
- 被 `tests/test_deny_rules.py` 导入的 `api._deny_match`
- 被 `tests/test_usage_caps.py` 导入的 `api.count_today`
- auth 测试内部导入的 OTP 与 CLI 常量
- 被 bootstrap 清单与 `tests/test_connections.py` 调用的 `api._backfill_provider_extra_tools`
- 不可协商的 `api.app`

兼容重新导出仅是接线。新代码直接导入所有者模块。

### 3.2 留在 `api.py` 的 call/runtime 消费者

这些被移动的治理/资源符号仍服务于后来的 call 阶段，因此需要直接所有者导入进 `api.py`：调用者解析、tool/project ACL、deny 执行、可见 secret id、每日上限、客户端归属、tool/secret 视图、资源 URL 验证、以及连接供应商绑定辅助。这个允许的方向是 legacy API -> domain/application，绝不可逆。

### 3.3 Router 导入规则

既有的 `Routers do not depend on the legacy API module` 契约必须全程保持绿色。每个新 router 直接导入 identity、application、domain、DB/模型类型或中立辅助。不允许回绑到 `api` 函数的回调。

## 4. 会话纪律审计

当前代码在许多阶段 3 流中违反了目标纪律。这里只是记录，而非作为机械移动的副作用来修复。

当前接收请求会话并在处理器/辅助内部提交或回滚的 auth/application 函数包括：

- `auth_github_callback`、`auth_google_callback`
- `auth_email_start`、`auth_email_verify`、`auth_invite_signin_confirm`
- `oauth_register`、`_resolve_oauth_client`、`oauth_authorize_approve`、`_refresh_grant`、`oauth_revoke`、`oauth_token`
- `auth_revoke_tokens`、`oauth_grants`、`oauth_grant_set_team`
- `_find_or_create_user` 在唯一性竞争上回滚

提交 7B 在 `revoke_identity_tokens` 内部按 id 重新加载已认证用户。那个窄窗口里的并发用户删除会抛出 `IdentityLookupError`；旧的共享会话处理器可能从它陈旧的 ORM 对象铸造一个 token。拒绝是更可取的，且微秒级的竞争不需要兼容路径。

有同样债务的治理/资源/连接函数包括：

- `register_user`、`create_org`、创建/接受/列表/撤销邀请路径
- org 设置、budget、成员访问/生命周期、公开 token、agent、project、pin、deny 规则
- secret/tool/bundle 写入与 `_register_skill_bundle`
- OAuth start/callback、连接 discovery/资源写入、token 连接、额外凭据、撤销
- `_backfill_provider_extra_tools`

移动引入的 domain 函数不得获得新的提交/回滚调用。既有提交应留在 application/router 编排里，直到一个专门的、行为中立的事务抽取被批准。特别是，`_refresh_grant` 不能移进 identity 叶子，因为它会提交。

## 5. Monkeypatch 与源码比较审计

使用的全仓库扫描：

- `monkeypatch.setattr` / `monkeypatch.delattr`
- `mock.patch` / `patch(...)`
- 对 `treg.api`、`treg.session`、`treg.mcp_oauth`、`routers.dependencies` 的导入

当前没有对阶段 3 处理器/辅助符号的 monkeypatch 目标，除了下面指出的兼容模块消费者：

- 连接测试导入 `treg.api as A` 并调用 `A._backfill_provider_extra_tools`；在连接提交里保留或更新那个目标。
- MCP OAuth 元数据测试 patch `health.safe_webhook_url`、`health.host_is_public`、`httpx.AsyncClient.get`，而非一个被移动模块属性。它们的惰性导入目标仍然有效。
- 许多 call 测试 patch `api.relay`、`_resolve_call`、`_secret_renderings`、call billing 辅助；没有一个是本阶段 3 移动中的，且都不可变更。
- `test_single_user.py` 与安全测试 patch `api.get_settings`；单用户 bootstrap 不是阶段 3 单元，保持不动。

每次提交前，对每个被移动名字重复一次符号级扫描，而非仅本检查点扫描。对于确切源码审阅，从父提交捕获每个 AST 函数/类节点（含装饰器），并与目的地比较。常量与承重注释作为原始块文本审阅。仅允许的差别是新的模块文档字符串/导入与显式审阅过的接线别名。

## 6. 移动前的 E2E 旅程门禁

全部五个候选旅程在任何阶段 3 移动之前都已经存在：

| 旅程 | 既有移动前测试 |
|---|---|
| 开发模式下的邮箱 OTP | `test_auth_email.py::test_first_login_registers_user_with_no_org_then_reuses_identity` |
| CLI 配对 start/poll/approve/token | `test_login_page.py::test_email_door_completes_the_handshake` |
| MCP OAuth register/authorize/token/validate | `test_mcp_oauth.py::test_the_whole_flow_end_to_end` |
| Org 创建与成员管理 | `test_orgs_mgmt.py::test_create_org_returns_a_working_token` 外加邀请/成员测试 |
| 连接建立 | `test_connections.py::test_registry_connect_autoprovisions_a_callable_tool` |

不需要旅程准备提交。在提交 1 之前，在父提交上一起运行这些确切测试并记录绿色结果。每次移动提交前后，在同一数据库后端运行上面分配的旅程。完整 SQLite 与约定的 Postgres 子集仍是提交审阅门禁。

## 7. 域导入矩阵激活

Identity 是一个叶子，不导入任何兄弟域。当后来的阶段 3 包出现时：

- 治理可导入身份
- tools 可导入 connections
- 每条其他兄弟边都被禁止
- connections 不可导入 tools，所以连接自动供给必须经由 `application.connect` 组合，而非反向调用一个 tools 域实现

逐步激活契约：

1. 提交 1 的身份叶子，取决于不存在模块的行为决策
2. 治理出现时的治理契约，仅允许 `governance -> identity`
3. tools/resources 出现时的 tools/resources 契约，仅允许 `tools -> connections`
4. connections 出现时的 connections 契约，无任何兄弟导入

import-linter 契约不能替代表写入所有权。阶段 3 context 更新必须记录治理拥有 org/成员/project/deny/设置/budget 写入，connections 拥有 secret 凭据状态，tools 拥有 tool/bundle 写入，而既有的 money 与审计例外保留。

## 8. 快照与验证契约

阶段 3 中四份文件都不可变：

- `tests/snapshots/routes.json`
- `tests/snapshots/openapi.json`
- `tests/snapshots/composition.json`
- `tests/snapshots/lifespan.json`

不允许重新生成命令。每次提交在内存中渲染全部四份并与已提交文件比较字节。一个 diff 意味着路由附接顺序、装饰器元数据、依赖身份、角色所有权、或 lifespan 兼容性发生了变化，且设计是错的。

每次提交：

1. 移动前运行该单元的既有 E2E 旅程
2. 仅执行逐字节符号移动
3. 在同一提交里更新 monkeypatch/导入目标
4. 移动后运行同一 E2E 旅程
5. 运行 `uv run --frozen lint-imports`，预期保留计数随批准的域契约上升
6. 运行完整 SQLite 与阶段 3 Postgres 子集
7. 在同一提交里更新 `architecture/composition.md`、`interface/api.md`、以及每个源码所有者片段；为地图没有所有者的 application/domain 包加新片段
8. 推送前运行 context drift 脚本

`bootstrap` 路由所有权键保持基于路径/方法/函数名，且不可变更。如果移动一个处理器让一个键变更显得必要，停下审阅。部署的 `treg.api:app` 仍是 all-role 入口点。任何快照变更都不是可接受的结果。

## 9. 平行 main 合并约束

PR #205 改了 `bootstrap.py` 中的 `_legacy_host_redirect`、`_security_headers`、以及三行中间件注册。没有一个属于阶段 3 移动单元。当它落地时，按 brief 指引把 `main` 合并进本分支，不要 rebase，并通过完好保留 main 的中间件实现来解决。恢复下一个单元之前，重新运行全部四份内存快照比较。
