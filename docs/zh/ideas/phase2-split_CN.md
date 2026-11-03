# 二期演示拆分设计

**状态：**检查点 0 草稿。本文件仅为审阅产物，不得提交。

本设计所读的事实来源：

- `docs/REFACTOR-PLAN.md` 阶段 2
- `docs/REFACTOR-PLAN.md` 第 1.1 节
- 当前的 `src/treg/api.py`、`src/treg/bootstrap.py`、角色清单，以及四份路由快照
- 与 API、dashboard、SEO、landing、composition、Catalog、super-admin 相关的 `docs/context/` 片段

意向变更仅为定义的移动。处理器体、依赖顺序、响应类型、错误处理、路由名、路由路径、方法、OpenAPI 可见性以及注册顺序均保持不变。`treg.api:app` 与三份角色清单保持不变。

## 1. 路由清单

下面的位置指任何二期移动之前的当前 `api.py`。快照位置指 `tests/snapshots/routes.json`，其中位置 0 到 2 是 FastAPI 内建的 OpenAPI 与文档路由。对于堆叠的装饰器，所列顺序是真实的快照顺序，而非自上而下装饰器文本的顺序。

### 1.1 `routers/catalog.py`

本模块归属开放的端点-Catalog JSON API。前 5 条路由构成快照位置 5 到 9、`api.py` 第 461 到 656 行一段不被打断的注册块。

| 快照 | 路由 | 处理器 | 当前位置与连续性 |
|---:|---|---|---|
| 5 | `GET /catalog/platforms` | `catalog_platforms` | 第 461–464 行，Catalog JSON 块的第一条路由 |
| 6 | `GET /catalog/platforms/{slug}` | `catalog_platform` | 第 467–521 行，紧接其后 |
| 7 | `GET /catalog/search` | `catalog_search` | 第 537–592 行，紧跟其辅助函数之后 |
| 8 | `GET /catalog/endpoints/{endpoint_id}` | `catalog_endpoint` | 第 595–644 行，紧接其后 |
| 9 | `GET /catalog/examples/{endpoint_id}` | `catalog_example` | 第 647–656 行，收尾该块 |

随这些处理器一起移动的 Catalog 辅助函数：

- `_provider_display`
- `_platform_rows`
- `_observed_or_empty`

HTML 路由 `GET /catalog` 与 `GET /catalog/{slug}` 归属 `routers/web.py`，而非本模块。它们虽渲染 Catalog 数据，但是呈现页。

一条路径形态的例外需要显式审阅批准：

- `GET /catalog/endpoints/{endpoint_id}/access`，处理器 `catalog_endpoint_access`，当前在第 10372–10424 行、快照位置 203，阶段 4 仍留在 `api.py`。尽管其 URL 与 GET 方法如此，其体却通过 `_resolve_call`、`_marketplace_secret`、`_platform_offer`、`_platform_estimate_micro` 与 `_enforce_catalog_status` 执行调用凭据阶梯。要移动它而不导入 `treg.api`，要么需要把调用业务辅助函数提前，要么需要加可变的回调接线 —— 两者都会把这次纯呈现移动扩张进调用边界。因此提议的分类是"调用访问预检"，而非开放的 Catalog API。如果阶段 2 仅因其前缀而要把这条路由纳入，请在本次设计审阅之后停下，并在改动代码之前修订计划。

也不属于端点-Catalog API 的：

- `GET /providers.json` 留在 `api.py`。它是 `treg upload` 消费的凭据/供应商注册表，而非 `catalog_store` 描述的端点 Catalog。
- `POST /tool-requests` 留在 `api.py`。它是一个变更操作，是更晚的 Catalog 接入用例。

### 1.2 `routers/web.py`

本模块归属纯呈现页、SEO 文档、被注册为路由的打包静态响应，以及公开的技能文档。它使用三个注册块，因为当前的路由表把 web 与 auth、OAuth 关注点交错在一起。

#### Web 块 A：Catalog 与 SEO 页

这是快照位置 10 到 18、当前第 899–1923 行一段不被打断的注册块。它紧接 Catalog JSON 块之后，并紧在 `POST /tool-requests` 之前。

| 快照 | 路由 | 处理器 | 当前位置 |
|---:|---|---|---|
| 10 | `GET /catalog` | `catalog_index` | 第 899–952 行 |
| 11 | `GET /catalog/{slug}` | `catalog_page` | 第 955–1021 行 |
| 12 | `GET /agents/{agent}` | `agent_page` | 第 1114–1320 行 |
| 13 | `GET /agents/{agent}.md` | `agent_page` | 同一堆叠处理器 |
| 14 | `GET /use-cases/{category}/{job}` | `use_case_job_page` | 第 1383–1768 行 |
| 15 | `GET /use-cases/{category}/{job}.md` | `use_case_job_page` | 同一堆叠处理器 |
| 16 | `GET /use-cases` | `use_cases_hub` | 第 1771–1812 行 |
| 17 | `GET /catalog.css` | `catalog_css` | 第 1815–1821 行 |
| 18 | `GET /docs` | `docs_page` | 第 1858–1923 行 |

承载性的排序在此块内被保留：位置 5 到 9 的所有 JSON Catalog 路由仍位于位置 11 的 `GET /catalog/{slug}` 之前。`_CATALOG_RESERVED` 仍作为第二道守卫。

#### Web 块 B：主站与打包文档

这是快照位置 35 到 62、当前第 2791–3237 行一段不被打断的注册块。它留在 auth 邀请确认路由与 `POST /oauth/register` 之间。

| 快照 | 路由 | 处理器 |
|---:|---|---|
| 35 | `GET /` | `landing` |
| 36 | `GET /app` | `dashboard` |
| 37 | `GET /app/marketplace/{service}` | `dashboard_marketplace` |
| 38 | `GET /app/skills/{name}` | `dashboard_skill_page` |
| 39 | `GET /app/tools/{name}` | `dashboard_tool_page` |
| 40 | `GET /llms.txt` | `llms_txt` |
| 41 | `GET /robots.txt` | `robots_txt` |
| 42 | `GET /sitemap.xml` | `sitemap_xml` |
| 43 | `GET /install.sh` | `install_sh` |
| 44 | `GET /selfhost.sh` | `selfhost_sh` |
| 45 | `GET /quickstart.md` | `quickstart_md` |
| 46 | `GET /tutorial.md` | `tutorial_md` |
| 47 | `GET /tutorial-import-shell.md` | `tutorial_import_shell_md` |
| 48 | `GET /tutorial-access.md` | `tutorial_access_md` |
| 49 | `GET /vendor-listing.md` | `vendor_listing_md` |
| 50 | `GET /vendor-listing` | `vendor_listing_md` |
| 51 | `GET /integrate.md` | `integrate_md` |
| 52 | `GET /skill.md` | `skill_md` |
| 53 | `GET /favicon.ico` | `favicon` |
| 54 | `GET /favicon.svg` | `favicon` |
| 55 | `GET /tutorial.js` | `tutorial_js` |
| 56 | `GET /legal.css` | `legal_css` |
| 57 | `GET /terms` | `terms_page` |
| 58 | `GET /privacy` | `privacy_page` |
| 59 | `GET /adtrack.js` | `adtrack_js` |
| 60 | `GET /resources` | `resources_page` |
| 61 | `GET /usecase.css` | `usecase_css` |
| 62 | `GET /use-cases/{slug}` | `use_case_page` |

`vendor_listing_md` 与 `favicon` 的堆叠装饰器顺序被精确拷贝，以免路由快照顺序翻转。

#### Web 块 C：公开技能文档与页

OAuth 发现与 OpenAI challenge 留在 `api.py`。以下块紧接 `GET /.well-known/openai-apps-challenge` 之后、`GET /auth/cli-token` 之前，位于快照位置 72–79、当前第 3988–4055 行。

| 快照 | 路由 | 处理器 |
|---:|---|---|
| 72 | `GET /.well-known/skills/index.json` | `well_known_skills_index` |
| 73 | `GET /.well-known/skills/treg/SKILL.md` | `well_known_skill_md` |
| 74 | `GET /connect-demo` | `connect_demo_page` |
| 75 | `GET /connect-demo/callback` | `connect_demo_callback` |
| 76 | `GET /help` | `support_page` |
| 77 | `GET /contact` | `support_page` |
| 78 | `GET /support` | `support_page` |
| 79 | `GET /tutorial` | `tutorial_page` |

`support_page` 的堆叠装饰器顺序被精确拷贝。

#### 刻意排除的呈现相邻路由

- `GET /meta` 留在 `api.py`。它是给 dashboard 用的运行时能力/配置 API，不是页渲染器。
- `GET /login`、两个 `/auth/invite-signin` 方法、GitHub 与 Google 登录页、两个 `/oauth/authorize` 方法随 auth 留在阶段 3。
- `GET /.well-known/oauth-protected-resource` 与 `GET /.well-known/oauth-protected-resource/mcp`、`GET /.well-known/oauth-authorization-server`、`GET /.well-known/openai-apps-challenge` 随 OAuth/MCP 协议处理保留。
- `GET /demo/sandbox/live`、`GET /landing/stripe-feed`、`GET /demo/sandbox/skill`、`GET /skills/samples`、`GET /skills/{name}/install.sh` 随接入/demo 保留。它们暴露数据或生成的接入产物，而非独立的页渲染。

### 1.3 `routers/admin.py`

admin 模块有两个 include 点，因为五个变更路由夹在读块之间。

#### Admin 块 A：跨租户读

这是快照位置 186–193、当前第 8939–9185 行一段不被打断的注册块。

| 快照 | 路由 | 处理器 |
|---:|---|---|
| 186 | `GET /admin/stats` | `admin_stats` |
| 187 | `GET /admin/orgs` | `admin_orgs` |
| 188 | `GET /admin/orgs/{org_id}` | `admin_org_detail` |
| 189 | `GET /admin/users` | `admin_users` |
| 190 | `GET /admin/tools` | `admin_tools` |
| 191 | `GET /admin/calls` | `admin_calls` |
| 192 | `GET /admin/errors` | `admin_errors` |
| 193 | `GET /admin/health` | `admin_health` |

重要的既有行为：`admin_errors` 是一条 GET 路由却不读库只读。它调用 `_purge_expired_error_evidence`，后者更新过期证据并在自己的会话上提交。路由与辅助函数一起移动，逻辑不变。在本设计中，"读路由"指的是既有的 GET admin 界面，而非零写入的承诺。

#### Admin 块 B：对账与推荐报告

这是快照位置 199–202、当前第 9280–9362 行一段不被打断的注册块。它留在五个 admin 变更操作之后。

| 快照 | 路由 | 处理器 |
|---:|---|---|
| 199 | `GET /admin/reconcile/drift` | `admin_reconcile_drift` |
| 200 | `GET /admin/reconcile/spend` | `admin_reconcile_spend` |
| 201 | `GET /admin/reconcile/repeats` | `admin_reconcile_repeats` |
| 202 | `GET /admin/referrals` | `admin_referrals` |

读专用的辅助函数与常量 `_tally`、`_ERROR_EVIDENCE_TTL_DAYS`、`_ERROR_EVIDENCE_EXPIRED`、`_purge_expired_error_evidence` 随 admin 处理器一起移动。

### 1.4 一切留在 `api.py` 里的东西

这些关注点明确不在阶段 2 之内，哪怕单个路由用到 GET：

- auth 与身份：GitHub、Google、邮箱 OTP、CLI 配对/token、邀请登录、treg OAuth 授权服务器、授予、token 撤销
- org 与治理：org CRUD、邀请、成员、角色、agent、project、pin、deny 规则、设置、预算、用量、公开 token
- 资源与连接：secret、tool、bundle、skill、OAuth 提供方/连接、health
- 接入与 demo：demo 团队、sandbox、feed、示例 skill、seed-tool、队友验收
- 计费与推荐：余额、充值、自动充值、历史、门户、Stripe webhook、成员推荐视图、推荐码创建
- 审计视图：calls、call 详情、runs
- 调用与运行：`/call/{rest:path}`、`/run`、调用解析、marketplace 凭据阶梯、hold、relay、结算、服务端执行
- admin 变更：`admin_set_superadmin`、`admin_suspend_user`、`admin_delete_user`、`admin_suspend_org`、`admin_delete_org`
- 装配：中间件、异常处理器、启动辅助、`router`、兼容的 `app`、最后的 `create_app()` 调用

这些区域中的路径、方法、处理器名或 bootstrap 所有权键均不改变。

## 2. 注册顺序保留

在末尾只用一次 `include_router(web.router)` 是不可接受的。它会按模块聚合关注点并重排当前的交错。它也可能把 `/catalog/{slug}` 挪到它的 JSON 兄弟之前。

因此每个目标模块导出多个有序的 `APIRouter` 块：

```text
routers.catalog
  public_router            快照 5..9

routers.web
  catalog_pages_router     快照 10..18
  site_router              快照 35..62
  public_docs_router       快照 72..79

routers.admin
  reads_router             快照 186..193
  reports_router           快照 199..202
```

`api.py` 把每个块精确附在对应装饰器当前执行的位置。既有的 `api.py` 路由保留在这些附接点之间。附接使用一个微小辅助函数，将该块的既有 `APIRoute` 对象按顺序追加到 `api.router.routes`。它不调用 FastAPI 的 `include_router()`，因为已安装的 FastAPI 版本会把被 include 的路由包进 `_IncludedRouter`；阶段 1 在 bootstrap 中已避免那个包装，因为它改变路由检查从而改变已提交的界面。直接有序附接仅是组合，保留每个路由对象的名、endpoint、依赖图与装饰器产生的顺序。

顺序断言是：

1. 在内存中渲染四份快照并比较其字节与已提交文件，不写入它们；
2. 断言 Catalog 子序列恰好是 JSON 路由、然后 `/catalog`、然后 `/catalog/{slug}`；
3. 保留 `tests/test_app_roles.py` 不变，证明每个路由键仍被分类、三份角色清单不变。

本阶段不含任何快照重新生成命令。

## 3. 共享辅助函数清单与去向

### 3.1 HTTP 依赖

`routers/admin.py` 需要 `require_superadmin`；被排除的 Catalog 访问路由是唯一被选中的 Catalog 形态路由中需要 `require_member` 的。Web 页需要会话身份查找。从 `treg.api` 导入这些是被禁止的，因此首个提交把既有的依赖族（体不变）抽取进 `src/treg/routers/dependencies.py`：

- `Caller`
- `_membership_by_token`
- `_user_from_session`
- `_user_from_identity_token`
- `_resolve_org`
- `_role_at_least`
- `_is_machine_email`
- `require_identity`
- `require_member`
- `require_superadmin`

`api.py` 导入并重新导出这些名字，使既有的内部引用与测试导入继续工作。这不是阶段 3 的 auth 用例抽取。它只是给接口模块一个无循环依赖的家，收纳既有的 FastAPI 依赖。

### 3.2 共享 HTTP 与时间辅助

以下辅助被移动过的 web 处理器和留在 `api.py` 的处理器共用：

| 既有依赖 | 去向 | 原因 |
|---|---|---|
| `_WEB_DIR`、`_LOGO_DIR`、`_MEDIA_DIR`、`_TOUR_DIR`、`_VENDOR_DIR` | `routers/web.py`，由 `api.py` 重新导出 | 呈现资产所有权随 web 移动；bootstrap 与测试保留兼容导入 |
| `_esc_html` | `routers/web.py`，由 `api.py` 重新导出 | 渲染辅助；其余 auth HTML 处理器用重新导出 |
| `_is_https` | `routers/dependencies.py`，由 `api.py` 重新导出 | auth 与 web 共用的 cookie 安全判定 |
| `_user_from_session` | `routers/dependencies.py`，由 `api.py` 重新导出 | web 与 auth 路由共用的共享 auth 依赖 |
| `_local_owner` | `routers/web.py` | 仅 dashboard 渲染用；`_bootstrap_single_user` 留在 `api.py` |
| OAuth 回返 cookie 读写辅助，以及 landing/dashboard 用的推荐 cookie 辅助 | `routers/dependencies.py`，由 `api.py` 重新导出 | 避免 web 导入 auth 实现，并把成对的 cookie 校验放在一处 |
| `_utcnow_naive`、`_as_naive` | 一个小的、中立的 `src/treg/timeutil.py`，由 `api.py` 重新导出 | admin 读与许多其余处理器共享精确的时间戳约定 |
| `get_session`、`session_maker` | 留在 `db.py`，直接导入 | 已经是无循环依赖的基础设施辅助 |

抽取提交必须为当前被用到的名字 `api._WEB_DIR`、`api._usd_short`、`api._platform_rows`、`api.use_case_job_page`、`api._utcnow_naive`、`api.Caller` 保留兼容性，通过把别名导入 `api.py`。重新导出不会把路由定义放回 `api.py`。

### 3.3 Catalog 与渲染辅助

- `_provider_display`、`_platform_rows`、`_observed_or_empty` 居于 `routers/catalog.py`。
- `routers/web.py` 从其兄弟 `routers.catalog` 导入那些辅助，绝不从 `treg.api`。
- 从 `_CATALOG_RESERVED` 直到服务端渲染的 Catalog、agent、use-case、sitemap、docs 渲染块的所有辅助，随其处理器移动到 `routers/web.py`。这包括 `_page`、`_spa_catalog_page`、`_usd_short`、`_price_label`、`_catalog_mtime`、`_USE_CASES`、`_SITEMAP_PAGES`。
- `api.py` 只重新导出当前有兼容用法的名字。它不复制体。

### 3.4 Admin 辅助

`routers/admin.py` 直接导入模型、SQLAlchemy 表达式、`get_session`、`session_maker`、settings、`reconcile` 与抽取的 `require_superadmin`。admin 处理器体与错误保留辅助函数原样移动。仅变更的辅助如 `_is_last_active_superadmin`、`_cascade_delete_org` 留在 `api.py`。

## 4. 避免循环导入

该不变量强于"无模块级导入"：任何 `treg.routers` 下的模块都不得导入 `treg.api`，无论是直接还是通过仅仅隐藏这条边的适配器间接导入。

本阶段后的导入方向是：

```text
api.py
  -> routers.dependencies
  -> routers.catalog
  -> routers.web -> routers.catalog
  -> routers.admin -> routers.dependencies
  -> bootstrap.create_app() at EOF

bootstrap.py
  -> api.py 仅在 create_app() 内部，与今天一样
```

Router 模块直接导入模型、config、DB 辅助、catalog 存储、reconcile、session 以及其他既有的低层模块。`api.py` 仍是兼容导出方与有序路由表宿主。Router 模块永不回指它。

这也解释了为什么 `catalog_endpoint_access` 提议留在原地：它当前的依赖由 `api.py` 的调用段定义，在该调用应用边界存在之前移动这条路由，会违反这条导入方向，或迫使把调用逻辑塞进一个纯呈现的 PR。

## 5. Import Linter

最终提交可激活该契约，因为提议的依赖抽取移除了所有 router 到 API 的边：

```toml
[[tool.importlinter.contracts]]
name = "Routers do not depend on the legacy API module"
type = "forbidden"
source_modules = ["treg.routers"]
forbidden_modules = ["treg.api"]
```

精确的 `as_packages` 设置会在编辑配置前对照 import-linter 2.13 校验，以便该契约覆盖 `treg.routers` 下的每个当前与未来模块。该契约必须捕获直接与间接边。不计划任何 ignore。`unmatched_ignore_imports_alerting = "error"` 保持启用。

本阶段不加入（未来 router 到 application 到 domain 的分层契约），因为 application 与 domain 包尚未迁移。

## 6. 提交计划与门禁

建议的四个提交仍是最干净的风险拆分：

1. `refactor(routers): extract shared HTTP dependencies`
   - 加上包骨架，只移动共享辅助/依赖；
   - 每个路由定义留在 `api.py`；
   - 保留兼容重新导出；
   - 更新 context 片段与生成的 context 地图。
2. `refactor(routers): move catalog routes`
   - 移动开放的 Catalog JSON 块及其辅助；
   - 使其附接紧在 web 块 A 之前；
   - 更新 API/Catalog 片段。
3. `refactor(routers): move web presentation routes`
   - 移动三个 web 块及其渲染辅助；
   - 在三个原始注册点附接；
   - 更新 API/dashboard/SEO/landing/composition 片段。
   - 阶段 3/4 后续：把 `docs_page` 改为使用 `request.app`，然后删除 `api.py` 末尾过渡性的 `web_routes.app = app` 绑定。
4. `refactor(routers): move admin read routes`
   - 在不变的变更块周围移动 admin 块 A 与 B；
   - 加上 routers 到 api 的 import-linter 契约；
   - 更新 super-admin/import-boundaries/API 片段。

每次提交之后：

- 运行四份快照断言，不重新生成文件；
- 校验 `git diff -- tests/snapshots/` 为空；
- 运行 `uv run --frozen pytest -q`；
- router 模块存在后运行 `uv run --frozen lint-imports` 一次；
- 运行 `bash .agents/skills/tools-registry-context/scripts/drift.sh`；
- 在同一提交中更新适用的 `docs/context/` 片段并重新生成其地图；
- 在开始下一次提交之前停下审阅。

Postgres 在本设计中不作为每提交门禁加入，因为请求的阶段 2 门禁指定的是完整的 SQLite 套件，且所有移动的行为都是路由定义的移动。任何既有的 CI Postgres 子集在最终 PR 上仍照常运行。

## 7. 代码前需确定的审阅决策

1. 确认 `catalog_endpoint_access` 在阶段 4 之前留在调用流里，而不是按 URL 前缀被分类为阶段 2 的 Catalog API。
2. 确认 `admin_errors` 随 admin GET 路由移动，尽管它有既有的保留-更新副作用。不提议任何行为变更。
3. 确认把 `/meta`、`/providers.json`、OAuth 发现/challenge、以及接入生成的技能响应留在 `api.py` 供其后续关注点移动的窄分类。
