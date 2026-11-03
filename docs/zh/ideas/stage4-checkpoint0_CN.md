# Stage 4 检查点 0：application.call 契约与拆分方案

状态：待评审的设计草案。本文件仅为评审产物，不得提交（commit）。

本说明的依据：

- 当前 `refactor/phase3-identity` 的 HEAD `b924ced`
- `docs/REFACTOR-PLAN.md` 的第 1.2、1.6、4、5 节
- 当前 `src/treg/api.py`，共 4,676 行
- 已发布的 API、proxy、money、auth/secrets、multi-tenancy、landing sandbox 的上下文片段
- `src/treg/bootstrap.py`、`proxy.py`、`injectors.py`、`ledger.py`、`oauth.py`、`health.py`
- `tests/callmatrix/` 下的 31 个测试，以及当前的 pool-discipline（连接池纪律）测试

下面的行号针对 `b924ced`。代码工作必须在 PR #210 合并之后，在一个新分支上开始，并且必须先针对该合并结果重新解析每一段行范围，再切分符号。真正作为迁移锚点的是符号名，而非这些临时的行号。

## 0. 执行建议、已冻结的决策，以及修订提案

把 Stage 4 拆成两个叠放的 PR。

- **4a，控制面边界（control-plane perimeter）：** 迁移应用级的（app-wide）中间件归属、计费（billing）、余额（balance）、推荐（referrals）、上手（onboarding）、landing sandbox 管理，以及它们的 HTTP 路由。沿用 Stage 3 的 A/B 模式。调用专属的 sandbox 执行分支留给 4b。
- **4b，调用内核（call kernel）：** 冻结并实现 `CallContext`，迁移调用路由与辅助函数，确立 governance/money/connections/upstream 各归属方，并把用例拆成 resolve（解析）、authorize/caps（鉴权/配额）、reserve（预留）、relay（转发）、settle/release（结算/释放）几个阶段。

这个拆分是合理的。它把 Stripe、onboarding 的 HTML/JSON 翻译、demo 数据播种（seeding）、以及公开 feed 状态都挡在 call-kernel 评审之外。同时它也让 4b 的 diff 更容易审计那三条硬性约束。PR 4b 应基于 4a，而非独立开发。

我建议对提议的 4a 边界做两处小的扩充：

1. 在 4a 中把 `/referrals` 和 `/referrals/code` 作为独立职责迁移过去。它们与 billing 块交织在一起，billing 会调用推荐奖励发放，把它们留在 `api.py` 里会保留一条恰好穿过 4a 正在清理区域的"仅控制"桥梁。它们最终的路由是 `routers/referrals.py`，而非 `routers/billing.py`。
2. 在 4a 中偿还现有的 `resources_routes._enforce_sandbox_cap` 桥梁。该策略属于一个小型的 governance sandbox 策略归属方，而 `application.onboard` 负责编排 mint/reset/export 等旅程。

### 0.1 已冻结的检查点决策

1. **接入（Intake）是一个真正的"预解析（pre-resolve）"阶段。** 保持标签预算（tag-budget）预检、幂等（idempotency）声明、解析，再是其余鉴权的当前时间顺序。字面意义上的"先解析"重写被否决。
2. **数据面（Dataplane）的自动充值（auto-top-up）保持不变。** `billing.maybe_schedule_autotopup()` 在请求路径上只做一次内存中的资格检查，并 `create_task`。派生的任务自己开会话去写。这是计划 §1.6 枚举中遗漏的既有行为，而非新写操作的许可。最终的架构测试把它枚举为一种数据面派生的后台写，受影响的上下文片段会记录它。引入 outbox 会改变行为，不在 Stage 4 范围内。
3. **DB 宕机语义保持不变。** 在 DB 可用时，每一条进程内终态路径都会在结束前关闭它的 hold（预留）。在 DB 不可用或进程死亡时，已提交的 hold 加上惰性回收器（reaper）就是保证。响应不得为最终化（finalization）而阻塞，超出当前的重试行为。
4. **取消补偿（Cancellation compensation）是一项已批准的、4b 之前的修复。** 一次被取消的计量调用以 `reason=call_cancelled` 释放。它落在一个独立的、4b 之前的小 PR 里，而非作为 4b 的一次提交。它的回归测试是一次真实客户端的、已付费计量调用的 E2E 取消，且必须在 Postgres 上运行；仅 SQLite 的覆盖无法证明 asyncpg 取消行为。这个 PR 加固了那条不变式，4b 的每次提交都要据此评估，且它保持独立可二分（bisectable）。

### 0.2 对计划第 0.6 节的修订提案：重构期修复策略

以下文本是对归属方批准的、明确的修订提案，而非从已冻结计划中的推断。重构中发现的微小修复在以下守卫下是被允许的：

- 绝不要把一个修复折叠进 A 类纯移动（pure-move）或 B 类边界抽取（boundary-extraction）提交；使用独立的 `fix:` 提交，并附带回归测试
- 把修复放在任何触及同一区域的移动之前
- 限制其影响范围为有限的波及半径，不改变客户端解析的 API 表面，且同一次提交内带有回归测试
- 每个 PR 最多允许三个 fix 提交
- 每次修复落地后，重新解析每一个源行锚点；后续任何提交信息都不得引用修复前的行号
- 对与并发或金钱相邻的修复，要求一次基于 Postgres 的 E2E 回归

金钱语义、API 表面变更、以及并发架构仍需要独立的 PR。每一个 Stage 4 的 PR 描述都包含一个**有意的行为变更（Intentional behavior changes）**章节，详尽列出每个 fix 提交，或明确声明没有。这是唯一的行为变更清单：凡未枚举于其上的，都被要求行为一致（behavior-identical）。

### 0.3 类型化失败策略

失败类型以机制（mechanism）为键。一个独立的 `blame`（责任归属）字段在一个代码点被赋值，且仅取以下值：

- `caller`
- `treg`
- `upstream`
- `org_connection`

第 2.7 节冻结了详细的取值钉死（pin）。特别地，502 族使用稳定的机制种类而非 `detail` 前缀。头部富化（header enrichment）不在 Stage 4 契约之内。

## 1. 范围与归属

### 1.1 PR 4a：控制面边界

#### 来自 `api.py` 的上手与 landing sandbox 符号

| 当前行 | 符号 | 目标 |
|---:|---|---|
| 1001-1032 | `OnboardIn`、`onboard_demo`、`onboard_skip`、`onboard_reset` | A：`routers/onboard.py`；B：编排在 `application/onboard` |
| 1039-1041 | `SANDBOX_HIT_NS`、`SANDBOX_RATE_MAX`、`SANDBOX_RATE_WINDOW_S` | `application/onboard` 限流策略 |
| 1064-1070 | `_enforce_sandbox_cap` | A：共享移动；B：`domain/governance/sandbox.py`，带一个语义化限制错误 |
| 1097-1112 | `demo_sandbox_mint` | A：`routers/onboard.py`；B：`application/onboard` |
| 1116-1122 | `demo_sandbox_live` | `routers/onboard.py`，调用一个只读的上手查询 |
| 1127-1143 | `stripe_webhook` | A：`routers/onboard.py`；B：landing-demo 的 webhook 用例，位于 `application/onboard` |
| 1147-1153 | `landing_stripe_feed` | `routers/onboard.py`；框架中立的 feed 留在 HTTP SSE 适配器之后 |
| 1157-1164 | `demo_sandbox_skill` | A：`routers/onboard.py`；B：`application/onboard` |
| 1168-1174 | `skill_samples` | A：`routers/onboard.py`；B：上手样例查询 |
| 1178-1190 | `skill_install` | 路由校验 HTTP/查询形态；application 产出脚本文本 |
| 1193-1224 | `TeammateIn`、`onboard_seed_tool`、`onboard_accept_teammate` | A：`routers/onboard.py`；B：`application/onboard` |

1045-1061 的公开 demo 调用限流器不属于 4a。它是执行策略，在 4b 中迁移。同理，4374-4401 的 sandbox 分支以及 4168-4186 的 `_relay_live_demo` 仍属 call-kernel 工作。

当前的各根模块是混杂的：

- `demo.py` 是仅控制面的 seed/reset 行为，可在 4a 中机械地移入 `application/onboard` 包。
- `pubfeed.py` 是仅控制面的进程状态，被 landing webhook/SSE 旅程使用，可在 4a 中机械地移入 `application/onboard`。
- `sandbox.py` 并非完全是控制面。`is_sandbox`、`is_live_tool`、`visitor_name`，尤其是 `synthesize` 都被 `/call` 消费。不要把这个模块整体搬进 `application.onboard` 并让 `application.call` 去 import 一个兄弟用例。在 4a 中拆分它的控制函数，保留兼容导出（compatibility exports），直到调用侧的函数得到它们的 4b 归属方。

#### 来自 `api.py` 的计费、余额、推荐符号

| 当前行 | 符号 | 目标 |
|---:|---|---|
| 1237-1291 | `org_balance` | A：`routers/billing.py` 的 `balance_router`；B：被该路由调用的 money 读查询 |
| 1298-1309 | `TopupIn`、`AutoTopupIn` | `routers/billing.py` |
| 1312-1327 | `_billing_org`、`_return_base` | HTTP/鉴权部分留在路由；框架中立的组织门控/结果输入进入 application |
| 1331-1344 | `billing_get` | A：路由；B：`application.billing.get_state` |
| 1348-1371 | `billing_topup` | A：路由；B：`application.billing.start_topup` |
| 1375-1406 | `billing_autotopup` | A：路由；B：`application.billing.configure_autotopup` |
| 1410-1422 | `billing_history` | A：路由；B：使用 money 行与 Stripe 文档端口的 application 查询 |
| 1426-1439 | `billing_portal` | A：路由；B：`application.billing.create_portal` |
| 1447-1468 | `my_referrals` | A：`routers/referrals.py`；B：推荐摘要/sweep 用例 |
| 1472-1482 | `mint_referral_code` | `routers/referrals.py`，调用推荐领域命令 |
| 1486-1509 | `billing_stripe_webhook` | A：路由；B：签名事件的 application 用例 |

注册顺序以独立的挂载点保留，而非一个重新分组的 include：

1. `balance_router` 替换当前 `org_balance` 的位置，位于 `org_routes.tag_controls_router` 之前。
2. `billing_router`、`referrals_router`，以及 billing webhook 块，按当前顺序追加到 `tag_controls_router` 之后、`member_management_router` 之前。
3. `onboard_router` 替换位置 98-109，作为一个连续的路由块。

现有的 `billing.py` 把 Stripe SDK 调用与 application 编排混在一起。目标不是把这种混合物重命名：

- `infra/stripe.py` 拥有 Stripe SDK、签名校验，以及网络调用。
- `application/billing.py` 拥有 top-up、auto-top-up、portal/history 组合、webhook 编排，以及它的事务边界。
- `domain/money` 仍是 money 表的唯一写方。
- `treg.billing` 在单独批准的删除阶段之前，仍是面向既有 import 与测试的临时兼容外观（facade）。新的运行时代码直接 import 归属方。

把旧模块整体搬进 `application.billing` 可以作为一次 A 提交，但紧接着的那个 billing 边界提交必须把具体的 Stripe SDK 从 application 层移除。不要在 4a 结束时留下这种中间形态。

### 1.2 PR 4b：来自 `api.py` 的调用内核符号

#### HTTP 出口与共享调用门控

| 当前行 | 符号 | 目标 |
|---:|---|---|
| 633-650 | `_pool_saturated` | 应用级的 HTTP 处理器，由 bootstrap 拥有；通过调用服务或窄回调委派调用簿记 |
| 653-678 | `_stamp_call_exit` | 调用拥有的最终化与出口元数据，位于 `application.call`；bootstrap 的处理器适配器施加 HTTP 头部 |
| 681-691 | `_refusal_kind` | `application.call` 的拒绝分类，由 bootstrap 适配器调用 |
| 694-711 | `_mark_treg_own_errors` | 应用级的 HTTP 处理器，由 bootstrap 拥有；调用专属的盖章由 `application.call` 注入 |
| 888-931 | `_tool_allowed`、`_require_tool_access`、`_project_allowed`、`_tool_usable`、`_require_tool_use` | A：`domain/governance/access.py`；B：语义化拒绝，而非 `HTTPException` |
| 983-986 | `_now_ms` | 调用时钟辅助函数，最好是注入的单调时钟，位于 `application.call` |
| 1045-1061 | `PUBLIC_DEMO_HIT_NS`、`PUBLIC_DEMO_RATE_MAX`、`PUBLIC_DEMO_RATE_WINDOW_S`、`_enforce_public_demo_ip_cap` | `domain/governance/publicdemo.py`，由调用 authorize/caps 消费 |
| 1078-1089 | `_enforce_daily_cap` | `domain/governance/usage.py`，由调用与两个 run 层级消费 |

627-630 的 `_id_out_of_range` 是通用 HTTP 行为，并非调用工作。它只有在 4a 执行了 bootstrap 处理器清理时才随应用级处理器一起移动。它不属于 `application.call`。

#### 解析与 marketplace 定价

| 当前行 | 符号 |
|---:|---|
| 2066-2189 | `_resolve_call` |
| 2210-2255 | `_catalog_endpoint_for`、`_enforce_catalog_status`、`_marketplace_secret` |
| 2259-2287 | `MarketplaceCall` |
| 2293-2345 | `_PLATFORM_PAGE_DEFAULT`、`_PLATFORM_PAGE_MAX`、`_LIMIT_PARAMS`、`_body_limit`、`_platform_estimate_micro` |
| 2355-2550 | `_usd_to_micro`、`_truthy`、`_json_object`、`_input_count`、`_credit_modifiers`、`_marketplace_pricing`、`_oauth_billed_provider`、`_billed_endpoint_match`、`_post_has_link`、`_oauth_billed_estimate` |
| 2553-2692 | `_billed_marketplace`、`_params_hash`、`_platform_bindings`、`_platform_offer`、`_capability_alternatives`、`_marketplace_no_credential` |
| 2695-2720 | `_VALID_PERCENT_ESCAPE_RE`、`_marketplace_upstream` |
| 2723-2754 | `_enforce_capability_pin` |
| 3110-3178 | `_resolve_marketplace_call` |
| 3181-3187 | `_may_have_body` |
| 3191-3242 | `catalog_endpoint_access` |

这些落在 `application.call` 包的 resolve 与 authorize 模块中。HTTP 端点 `catalog_endpoint_access` 得到一个薄薄的 `routers/call.py` 包装。目录数据留在窄只读端口之后；调用 application 不得 import Catalog 管理路由。

#### 接入、调用方元数据、幂等、以及预算

| 当前行 | 符号 |
|---:|---|
| 2757-2759 | `IDEMPOTENCY_WINDOW_S`、`IDEMPOTENCY_HEADER`、`_IDEM_MAX_KEY` |
| 2767-2793 | `META_HEADER`、`_META_MAX_KEYS`、`_META_MAX_HEADER`、`_META_MAX_VALUE`、`_META_VALUE_RE`、`DEFAULT_PRIMARY_DIM`、`_MAX_TAG_VALUES`、`CallMeta`、`_NO_META` |
| 2796-2907 | `_tag_telemetry`、`_validate_tag_pair`、`_parse_call_meta`、`_primary_dim_of`、`_budget_dims_of` |
| 2910-3107 | `_idempotency_key`、`_IDEM_SCOPE_SEP`、`_scoped_idempotency_key`、`_idem_display`、`_request_fingerprint`、`_replay_idempotent`、`_release_idempotent_claim`、`_claim_idempotent`、`_store_idempotent` |
| 3246-3376 | `_effective_daily_cap`、`_enforce_trial_allowance`、`_enforce_platform_daily_cap`、`_month_start_utc`、`_resolve_tag_budget`、`_tag_budget` |
| 3388-3467 | `_enforce_tag_budgets` |

`_parse_call_meta` 的 HTTP 解析一半变成针对原始头部值的路由适配器。策略与预算原语属于 `domain/governance/budgets.py`。幂等是 application.call 的状态，拥有自己的短事务。审计遥测构造仍是针对审计端口的 application 编排。

#### 预留、响应证据、转发支持，以及最终化

| 当前行 | 符号 |
|---:|---|
| 3470-3530 | `_platform_reserve` |
| 3541-3564 | `_NOT_THE_CALLERS_FAULT`、`_platform_billable`、`_PLATFORM_BODY_MAX` |
| 3569-3616 | 所有错误证据的限额与正则/头部常量 |
| 3619-3808 | `_secret_renderings`、`_safe_secret_renderings`、`_basic_credential_parts`、`_decode_error_body`、`_caller_request_snippet`、`_redact_snippet` |
| 3812-4015 | `_brightdata_record_count`、`_observed_cost_micro` |
| 4018-4088 | `_buffer_response`、`_peek_stream_head`、`_error_response_evidence` |
| 4091-4137 | `_platform_settle` |
| 4140-4165 | `_record_first_call` |
| 4168-4186 | `_relay_live_demo` |
| 4193-4598 | `call_tool` |

那些庞大的供应商成本与证据函数并非路由逻辑。它们落在 `application.call.settle` 与 `application.call.evidence` 之下。live-demo 适配器落在上游适配器旁边，其仅 sandbox 的选择仍是 application 策略。`call_tool` 先机械地移到 `routers/call.py`，再变成一个构建 `CallInput`、调用用例、并包裹 `UpstreamResponse` 的薄适配器。

以下邻近符号明确在 4b 之外：

- 1534-1625 的能力 pin CRUD 仍是控制/目录职责；只有调用时的 pin 消费被迁移
- 940-945 的 `_require_local_run` 仍是 local-run 的 HTTP 守卫
- 959-966 的 `GrantIn` 与 `RunReportIn`，以及 1667-1851 的本地 grant/report 处理器，仍是 `application.run` 工作
- 1859-1991 的 call/run 活动读仍是后续的审计/读路由清理
- 4602-4663 的 `/run` 与 `RunIn` 仍是 `application.run`
- 419-473 的 `LOCAL_ORG_NAME` 与 `_bootstrap_single_user` 仍是 bootstrap 启动工作，因为启动清单会调用它们
- 通用的 meta/providers/tool-request 路由仍在 Stage 4 之外

### 1.3 中间件归属

全部三种中间件实现应在 4a 中移出 `api.py`，由 bootstrap 拥有：

| 当前行 | 符号 | 归属方 |
|---:|---|---|
| 488-534 | `_LEGACY_HOSTS`、`_REDIRECT_PATHS`、`_REDIRECT_ALWAYS`、`_LegacyHostRedirectMiddleware` | `bootstrap_http.py` 或 `bootstrap/middleware.py` |
| 537-561 | `_SecurityHeadersMiddleware` | 同上 |
| 564-624 | `_BODY_ENC_HEADER`、`_decode_request_body`、`_BodyDecodeMiddleware` | 同上 |

`bootstrap.create_app` 已经拥有它们具体的注册与确切顺序。这些是应用级的 ASGI 策略，而非路由处理器或用例。把实现放在组合根（composition root）旁边，可移除工厂对 `api.py` 中装配细节的依赖。如果把 `bootstrap.py` 改造成一个包所带来的兼容动荡大于价值，就用 `bootstrap_http.py`；`treg.bootstrap:create_app` 必须保持不变。

应用级的异常处理器遵循同样的归属规则。`_pool_saturated` 与 `_mark_treg_own_errors` 由 bootstrap 在 `bootstrap.py:443-445` 注册，因此它们的 HTTP 适配器实现位于组合根旁边。`_stamp_call_exit` 与 `_refusal_kind` 是 `application.call` 拥有的调用专属行为。Bootstrap 通过构建好的调用服务或窄的、框架中立的回调把它们接入处理器。两个方向都不要求 `application.call` 去 import bootstrap 或 Starlette。

## 2. CallContext 与 application.call 契约

### 2.1 包与窄端口

推荐的终态包：

```text
src/treg/application/call/
  __init__.py       execute_call 与公开契约
  types.py          CallInput、CallContext、UpstreamResponse、failures
  intake.py         元数据、标签预检、幂等
  resolve.py        自有工具与 marketplace 解析/定价
  authorize.py      ACL、拒绝、成员/公开-demo 配额、能力 pins
  reserve.py        花费配额、预留排序、money 错误翻译
  relay.py          刷新、上游调用、缓冲/peek 策略
  settle.py         可计费性、观测成本、settle/release、首调标记
  evidence.py       脱敏与失败证据
```

窄端口，由 bootstrap 或小型适配器提供：

- `SessionFactory`：为一个有界的 DB 阶段开启一个全新的 `AsyncSession`
- `UpstreamPort`：发送一个框架中立的请求并返回 `UpstreamResponse`
- `OAuthRefreshPort`：在不带 DB 会话的情况下执行外部 token 刷新
- `MoneyPort`：来自 `domain.money` 的公开 `reserve`、`settle`、`release` 命令
- `RateStorePort`：公开-demo 速率状态
- `AuditPort` 与 `AnalyticsPort`：尽力而为的观察，绝不影响金钱正确性
- `Clock`：单调时长加上 UTC 边界
- 当前读取某个具体全局变量的目录/供应商/配置读端口

Bootstrap 在 `app.state.http` 存在之后创建调用服务，并把它存在 app state 上。路由适配 HTTP 输入并调用该服务。`application.call` 不 import 任何 FastAPI、Starlette，或具体的 httpx 客户端。

### 2.2 输入

路由构建这个框架中立的输入：

```python
@dataclass(frozen=True)
class CallInput:
    method: str
    raw_rest: str
    raw_headers: tuple[tuple[bytes, bytes], ...]
    query_items: tuple[tuple[str, str], ...]
    raw_query: str
    body: RequestBody
    caller: CallerSnapshot
    client_ip: str

class RequestBody(Protocol):
    def stream(self) -> AsyncIterator[bytes]: ...
    async def read(self) -> bytes: ...
```

`RequestBody` 在 `read()` 之后可重放（replayable）。这保留了当前的幂等与小错误 body 路径，而无需向内传递 Starlette 的 `Request`。`raw_rest` 由 ASGI 的 `raw_path` 在路由中推导出，以便编码后的斜杠仍保持字节忠实。 `raw_headers` 与 `query_items` 保留重复项与顺序。

`CallerSnapshot` 仅包含在请求会话被释放之后所需的值：membership/user/org 的 id、email、role、访问列表、public-demo/demo 标志、org slug、balance-policy 字段，以及首调状态。application DB 阶段结束之后不允许任何 ORM 懒加载。

### 2.3 内部可变上下文

`CallContext` 是一次调用的内部状态，而非一个 HTTP 请求对象：

```python
@dataclass
class CallContext:
    input: CallInput
    call_ref: str
    meta: CallMeta
    idempotency: IdempotencyClaim | None = None
    target: ResolvedTarget | None = None
    marketplace: MarketplaceCall | None = None
    credentials: tuple[CredentialSnapshot, ...] = ()
    reservation: Reservation | None = None
    finalization: FinalizationState = FinalizationState.NONE
    audit: AuditSnapshot | None = None
```

上下文存储的是拷贝的值，而非活跃的 ORM 实例。`Reservation` 使用 `call_ref` 作为已知的 hold id，并有一个进程内的状态转移 `NONE -> PENDING -> OPEN -> FINALIZING -> FINALIZED`。DB 的 hold 声明仍是跨进程的权威。一次重复的 settle/release 看不到 hold，也不会动钱。

在 await reserve 之前设置 `PENDING`。在取消屏蔽（cancellation shielding）之下运行 reserve 提交本身，以便在补偿决定是按 `call_ref` 释放之前，其结果是已知的。如果 reserve 已提交，则在屏蔽下运行 release；如果它回滚了，就没有 hold 可释放。屏蔽缩小了普通任务取消的窗口，但无法让 DB 网络故障变得明确，也无法在进程死亡时存活。在这些情况下，已提交的 hold 与 reaper 仍是恢复保证。

### 2.4 输出

唯一成功/重放/合成的結果形态是：

```python
@dataclass
class UpstreamResponse:
    status: int
    raw_headers: tuple[tuple[bytes, bytes], ...]
    body_stream: AsyncIterator[bytes]
    close: Callable[[], Awaitable[None]]
```

规则：

- `close` 是幂等的，且总是恰好关闭底层上游响应一次。
- body 迭代器有一个调用 `close` 的 `finally`。路由也把 `close` 安装为响应的后台动作。两条路径可能任一条先触发；幂等性使得断开、完整消费、以及异常都安全。
- 计量响应在被结算之前被排空（drained），并以一个单块 body 迭代器返回，带有 no-op/已完成的 close。缓冲最多保留 `_PLATFORM_BODY_MAX = 8 MiB`：超大的 body 保留当前的截断前缀，并把 `content-length` 重写为缓冲后的长度（`api.py:4027-4041`）。非计量响应保留流式。
- 对未计量失败的 peek 包裹原始迭代器，并转移同一个 close 回调。
- 路由构建 Starlette 的 `StreamingResponse`，拷贝 `raw_headers`，并翻译语义化失败。没有任何 Starlette 响应对象进入 application 或 infra。

### 2.5 按时间顺序的阶段与当前行范围

冻结的时间顺序契约包含一个在五个计划阶段之前的独立**接入（intake）**步骤。这保留了既有行为。

| 阶段 | 当前 body 行 | 工作 | DB 边界 |
|---|---:|---|---|
| intake | 4199-4247 | 调用 id、原始路径、元数据校验、标签被封/调用配额预检、标签预算自动建行、幂等重放/声明 | 一个或多个短事务；位于 4223 的 `_tag_budget(create=True)` 可能创建并在 3375 提交；不存在 hold；声明被显式提交或回滚 |
| resolve | 4249-4290、2066-2720、3110-3178 | 自有工具或目录端点、供应商/凭据层级、上游 URL、定价估算、被消费的参数 | 读事务；拷贝的结果；在下一个外部等待前关闭 |
| authorize/caps | 4291-4298，加上当前解析内部的 capability pin | 工具/项目 ACL、拒绝规则、成员配额、公开-demo 配额，以及调用时 capability pin | 有界的读/速率状态工作；拒绝时不产生金钱 hold |
| reserve | 4300-4465、3246-3467 | trial/platform/tag 花费配额（位于 3482-3484 的 `_platform_reserve` 内）、证据安全的请求快照、位于授权与凭据加载之间的 4374-4401 sandbox 终态短路、凭据加载、在 4427 的 `_billed_marketplace` 之后的 marketplace/oauth-billed 分类与估算、reserve | 花费门禁保持在当前的 reserve 序列内；reservation 是最后一个网络前的变更；application 提交并关闭它的会话 |
| relay | 4466-4504、4168-4186、当前的 `proxy.relay` | 刷新过期的 OAuth token、注入、SSRF 检查、发送、流式或缓冲/peek | 在每一次外部请求与响应 body 读取期间，零个被检出（checked-out）的 DB 连接 |
| settle/release | 4505-4598、3541-4165 | 故障时释放、按状态/成本结算/释放、证据、审计、首调标记、幂等存储/释放 | 每个正确性关键的写都拥有自己的、application 拥有的短事务 |

当前源码刻意地把标签封禁/调用计数门禁放在幂等重放之前，可能在那个预检期间创建一个标签预算行，并在解析工具之前声明一个幂等键。不要仅仅为了获得一个视觉上纯粹的"先解析"管道而重排这些操作。接入是冻结的预解析阶段。字面上的"先解析"实现被否决，因为它改变了哪个错误胜出，以及被封禁的调用方能否收到缓存的响应。

### 2.6 事务与补偿（compensation）契约

通用规则：

1. application 用例开启每一个会话，且是唯一提交或回滚的层。
2. 领域 money 函数变更所提供的会话，但不提交。
3. 一个会话绝不跨越对 Stripe、OAuth token 端点、供应商转发、DNS/网络适配器，或 body 流的调用。
4. 在第一个外部字节之前提交 reservation。结算/释放开启一个新会话。
5. 幂等声明释放独立于金钱最终化，并在每一次不成功的退出上运行。
6. 取消清理被屏蔽。普通的取消不得中途打断上游 close、hold 释放，或幂等释放。

OAuth 刷新当前违反了规则 3：`oauth.ensure_fresh` 持有 `db`，调用 token 端点，然后持久化。目标序列是：

1. 在一个短 DB 事务下拷贝加密的刷新输入/版本并关闭它
2. 通过 `OAuthRefreshPort` 不带 DB 连接地调用 token 端点
3. 重新开启一个事务，并针对旧的密文/版本条件式地持久化
4. 拷贝获胜的凭据值并在供应商转发之前关闭

保留当前的单飞（single-flight）锁与跨进程的条件更新语义。刷新失败仍持久化 `last_error`，然后以 `call_failed_502` 释放一个既有 hold。

#### 失败与金钱表

| 失败/结果 | Hold 动作 | 幂等动作 | 上游 close |
|---|---|---|---|
| 畸形元数据、鉴权、解析未命中、已退役端点、reserve 前的 ACL/拒绝/配额拒绝 | 无 | 释放一个既有声明（若存在） | 无 |
| 幂等声明之后、reserve 之前的取消 | 无 | 在屏蔽下释放声明 | 无 |
| reserve 期间余额不足 | reserve 事务回滚；无 hold | 释放声明 | 无 |
| reserve 提交结果不确定时的取消 | 按已知 `call_ref` 在屏蔽下幂等释放 | 在屏蔽下释放声明 | 若已创建则 close |
| reserve 后的 SSRF 拒绝 | 用映射的调用失败原因无计费地释放 | 释放声明 | 无；不发送任何供应商请求 |
| 完整答案之前的 OAuth 刷新、注入、连接、读超时，或上游流失败 | `release(reason=call_failed_<status>)` | 释放声明 | 恰好一次 |
| reserve 后的意外 application/infra 异常 | `release(reason=call_crashed)` | 释放声明 | 恰好一次 |
| reserve 后的调用方/任务取消 | `release(reason=call_cancelled)` | 释放声明 | 恰好一次 |
| 当前 `_platform_billable` 规则下的上游 2xx | 结算观测到的成本或估算回退 | 结算后存储计量重放 | 缓冲 body 前/后恰好一次 |
| 可计费的上游 4xx | 结算观测到的成本或估算回退 | 立即释放幂等声明；不存储重放；标签可复用 | 缓冲 body 前/后恰好一次 |
| 上游 5xx | `release(reason=provider_failed_<status>)` | 失败的标签保持可复用 | 恰好一次 |
| 其他不可计费的上游状态 | `release(reason=not_billable_<status>)` | 保留当前可复用标签行为 | 恰好一次 |
| 未计量响应 | 无 hold | 按当前幂等行为丢弃/存储 | body 迭代器或后台关闭它 |

最终化器必须消费内存中的 reservation 一次，但它必须只在 DB hold 声明达到一个终态结果之后才把它标记为 `FINALIZED`。`domain.money` 已经有正确的跨进程原语：`_claim_hold` 使用一个条件删除，因此竞态中的 settle、release、cancellation 与 reaper 无法两次移动金钱。

DB 失败行为被冻结：

- 在 DB 可用时，每一条进程内终态路径都必须在完成前不留下任何打开的 hold。
- 在进程死亡或 DB 不可用时，没有任何请求处理器能保证一次立即的写。已提交的 hold 是持久的恢复记录，惰性的 reaper 最终会释放它。

当前的 `_platform_settle` 重试一次 pool 超时，记录日志，返回响应，并把 hold 留给 reaper。Stage 4 保留该行为。它绝不能为了让最终化成功而阻塞响应，也不得声称屏蔽消除了 DB/网络与进程死亡的情况。

### 2.7 框架中立的失败

Application 与领域代码抛出以机制为键的类型化语义失败，携带稳定的 HTTP 翻译数据，以及晚期绑定的 `blame: caller | treg | upstream | org_connection`。该契约有六个钉死点：

1. **供应商响应是数据。** 每一个供应商响应，包括 4xx 与 5xx，都被忠实转发，且绝不被表示为异常。类型化失败仅在 treg 拒绝调用，或供应商没有产生完整响应时才存在。
2. **Blame 是一个字段，而非继承根。** 由一个映射点赋值。OAuth 刷新失败是 `org_connection`；幂等等待 409 与不匹配 422 共享一个机制但映射到不同的 blame。
3. **502 机制是显式的。** 它们稳定的种类与兼容映射被一起定义：

   | 种类 | Blame | 账本释放原因 | HTTP 状态 | B 提交期间的 `X-Treg-Error` |
   |---|---|---|---:|---|
   | `refresh_failed` | `org_connection` | `call_failed_502` | 502 | 字面量 `1` |
   | `injection_failed` | `treg` 或 `org_connection`，由单一映射点赋值 | `call_failed_502` | 502 | 字面量 `1` |
   | `ssrf_refused` | `treg` | `call_failed_502` | 502 | 字面量 `1` |
   | `connect_failed` | `upstream` | `call_failed_502` | 502 | 字面量 `1` |
   | `read_timeout` | `upstream` | `call_failed_502` | 502 | 字面量 `1` |
   | `stream_interrupted` | `upstream` | `call_failed_502` | 502 | 字面量 `1` |

   这个表是推导账本原因、HTTP 状态、以及错误头部的唯一来源，因此这三个表面不会漂移。
4. **SSRF 是它自己的种类。** 它是 reserve 之后的 treg 拒绝，总是释放 hold，从不计费，且绝不会到达供应商。
5. **可计费性与 blame 保持独立。** `_platform_billable` 加上 `_NOT_THE_CALLERS_FAULT` 回答谁被计费；blame 回答谁必须修复失败。一旦供应商已经响应，任何调用方可见的金钱错误都不得替换那个响应。结算溢出（overage）由账本策略吸收，绝不能在转发之后变成 402。
6. **兼容头部保持字面量。** 在 B 提交期间 `X-Treg-Error` 保持字面量 `1`。用种类富化它，或添加 `X-Treg-Refused-By`，都会改变一个客户端解析的 API 表面，并需要单独裁决。`refused_by` 从类型化失败推导而来，且必须对每一个既有状态保持相同。

示例机制类型包括 `ResolutionFailed`、`AuthorizationFailed`、`CapacityExceeded`、`InsufficientFunds`、`IdempotencyFailed`、`GatewayFailed(kind, ...)`，以及 `CallPoolSaturated(retry_after=2)`。路由把它们映射到既有的状态、detail、JSON key 顺序、`Retry-After`、`X-Treg-Call-Id`，以及 `X-Treg-Cost-Micro`。领域包不 import `HTTPException`。

## 3. 第 5 节目标映射调和

### 3.1 `proxy.py -> infra/upstream`

当前的不匹配：

- `proxy.relay` 接受 FastAPI 的 `Request` 并返回 Starlette 的 `StreamingResponse`。
- 它 import 具体的 `httpx`、`crypto`、models、injectors、settings，并懒加载根 `health`。
- 上游 close 隐藏在 Starlette 的 `BackgroundTask` 中，而非在计划的结果中暴露。

目标：

- `infra/upstream/relay.py` 接受原始请求 DTO 与凭据快照，使用共享的 httpx 客户端，并返回 `UpstreamResponse`。
- HTTP 适配与 Starlette 包裹位于 `routers/call.py`。
- SSRF 依赖指向 `infra/upstream/ssrf.py`，而非根 `health`。
- `treg.proxy` 在兼容期间可保持为直接再导出外观，但没有任何新的运行时归属方 import 它。

这是一次 A 类纯移动，随后是一次 B 类契约转换。不要把框架移除与文件移动合并。

### 3.2 `injectors.py -> infra/upstream`

代码已经是框架中立的，适合逐字节地移动到 `infra/upstream/injectors.py`。它被 relay、health 探针、sandbox synthesis、资源校验，以及 `localrun.py` 消费。

目标映射遗漏了一个重要的打包约束：`localrun.py` 是一个轻量 CLI 模块，在模块导入时就 import `_token_from_json`。因此 `infra.upstream.__init__` 不得热切地 import relay、FastAPI、SQLAlchemy、SQLModel、或 server models。`httpx` 本身是一个允许的基底依赖。要么 `localrun.py` 直接 import 叶模块 `infra.upstream.injectors`，要么既有的 `treg.injectors` 外观保持轻量。运行时的轻导入子进程测试与 import-linter 契约必须证明这一点。

### 3.3 `ledger.py -> domain/money`

映射在方向上是正确的。当前的不匹配是：

- 文件仍在根目录
- 公开操作会提交，并有时在内部回滚
- 根的 billing、referrals、signup、org 读、call，以及测试都 import 旧路径

建议：在 4b 中移动 `ledger.py`，但作为一次在 call 阶段抽取之前的、专门的早期提交。使用一个 `domain/money` 包，并在 A 提交中逐字节保留每一个 money 符号，仅做模块/import 调整，并提供一个薄的 `treg.ledger` 兼容外观。更新 import-linter 的 money 契约以指向真正的归属方。

不要把这次移动与移除提交合并。4b 事务的 B 提交把面向调用的 reserve、settle、release 路径转换为 application 拥有的事务，并在顺序、并发、失败、以及取消的调用下证明余额/块/hold/账本的不变式。这个范围包括 `reap_stale_holds`，它唯一的调用点在 `ledger.reserve` 的第 227 行。惰性 reap 在 reservation 余额门禁之前保留它持久的事务边界：每一次 reap 释放都独立提交，既独立于其他 reap 释放，也独立于新的 reserve 结果，因此一个后来的 402 与第 240 行的回滚都无法撤销陈旧 hold 的退款。于是 application 拥有的 reserve 编排给每个陈旧释放它自己的短提交阶段，再在一个独立事务中运行新的 reservation。

grant 与 top-up 的事务转换，包括所需的 signup、referrals、billing 调用方变更，被命名为后续债务 `money-funding-transactions`。在 4b 之后、Stage 5 之前偿还它；不要把 4b 的架构测试扩大到来假装那些调用方已经迁移。4a 的 billing 边界为那次后续偿还做了准备。

金钱纪律保持绝对：A 移动中的所有符号逐字节一致，`domain.money` 是 `CreditBlock`、`Hold`、`LedgerEntry`、`TagSpend`，以及 money 拥有的 `Org` 字段的唯一写方，且 application 与 routers 都不直接发布 money 表的更新。

### 3.4 `oauth.py` 刷新 -> domain/connections

当前的不匹配：

- 不存在 `domain/connections` 包
- `ensure_fresh` 把刷新规则、具体的 httpx I/O、行刷新、条件持久化、提交，以及进程内锁混在一起
- call、连接健康、connect 旅程，以及 server/local run 都消费它

目标拆分：

- 纯过期/可刷新性与刷新状态转移规则位于 `domain/connections/refresh.py`
- 条件式密钥持久化命令位于同一领域归属方，不带提交
- 外部 token 端点交换在 `OAuthRefreshPort` 之后，由 infra 实现
- 编排位于 `application.call`、`application.connect`，以及后续的 `application.run`

第 5 节的映射遗漏了具体 token 端点适配器的目标，以及 run/health 消费者。在代码落地时把它们记录在上下文更新中。保留 `treg.oauth` 的兼容导出，因为测试与懒加载的 `localrun` import 使用那个路径。

### 3.5 `health.py` 的 SSRF 部分 -> upstream

`safe_webhook_url`（28-53 行）与 `host_is_public`（56-73 行）逐字节移动到 `infra/upstream/ssrf.py`。`health.py` 的其余部分是凭据健康行为，不随它们一起移动。

映射中"SSRF check -> upstream"的目标是正确，但它的调用方描述不完整。这些守卫也被资源注册、signup 告警 URL、OAuth 客户端元数据校验，以及连接健康所使用。来自 `health.py` 的兼容再导出可避免一次广泛的、单提交猴子补丁（monkeypatch）破坏，而新的归属方直接 import `infra.upstream.ssrf`。

在纯移动期间保留当前的同步 DNS 语义。任何后来的非阻塞解析器或 IP 钉死（pinning）变更都是一个独立的安全变更，而非 Stage 4 清理。

### 3.6 发现的其他映射遗漏

- `sandbox.py` 在第 5 节中被标为控制面，但 `/call` 在数据面用它做 sandbox 检测、synthesis，以及 live-wire 指纹。它必须按工作负载拆分，而非整体移动。
- `billing.maybe_schedule_autotopup` 被数据面 reserve 路径调用。请求路径执行一次内存检查并调度一个派生的后台任务；那个任务通过自己的会话执行 Stripe 与 DB 工作。这个既有行为是第 §1.6 枚举的遗漏，保持不变。
- 位于 1055-1058 的、用于公开-demo 与 sandbox 限制的 ratestore 命中记账写，从 4297-4298 与 4381-4382 触及。这些既有的数据面派生写保持不变。
- 4159-4161 的 `_record_first_call` 调用 `adsconv.queue`，它插入一行 `AdConversion` outbox 行。这个既有的数据面派生写保持不变。
- `injectors.py` 有一个轻 CLI 消费者，因此 infra 包必须保留一个轻叶 import。
- OAuth 刷新有 call、connect、health、local-run，以及 server-run 消费者，而非仅 call/connect。

最终的架构允许列表（allowlist）测试显式地命名 auto-top-up、两条 ratestore 命中路径，以及 `AdConversion` outbox 写。它们的当前状态上下文片段在实现落地时记录它们。它们不授权额外的数据面写。不要在这个检查点期间编辑已冻结的计划；被批准的差异属于当前状态片段，或一个单独请求的计划修订。

## 4. Stage 3 债务偿还

### 4.1 `org_routes` 的八个过渡绑定

当前的八个绑定分散在 1516-1517 与 3380-3385：

```text
org_routes._META_MAX_KEYS
org_routes._validate_tag_pair
org_routes._primary_dim_of
org_routes._budget_dims_of
org_routes._effective_daily_cap
org_routes._tag_budget
org_routes.PUBLIC_DEMO_RATE_MAX
org_routes.PUBLIC_DEMO_RATE_WINDOW_S
```

前六个赋值在 3380-3385；两个公开-demo 常量绑定在 1516-1517。在 4b 的第一批 governance 边界系列中偿还全部八个。前六个落在 `domain/governance/budgets.py`。`routers/orgs.py` 与 `application.call.authorize/reserve` 直接 import 那个归属方。该模块拥有预算维度、校验、有效配额，以及预算行的读/变更，因为第 1.3 节把用量限制与预算分配给了 governance。它不得 import routers、application，或 `api.py`。

`PUBLIC_DEMO_RATE_MAX` 与 `PUBLIC_DEMO_RATE_WINDOW_S` 与底层的 `PUBLIC_DEMO_*` 常量及限流器一起落在 `domain/governance/publicdemo.py`。org 控制视图与调用鉴权都 import 那个归属方；调用侧的 ratestore 命中仍是一个被显式允许的数据面派生写。

一次 A 提交逐字节移动既有符号。一次 B 提交用语义化 governance 错误替换 HTTP 异常，并使提交归属明确。只有当两个消费者都使用归属方时才移除这八个赋值。如果需要，添加或扩展 governance 的 import-linter 契约。

### 4.2 `resources_routes` 的 ACL 桥梁

位于 1632-1633 的当前绑定：

```text
resources_routes._tool_usable
resources_routes._require_tool_use
```

在同一批早期 4b governance 边界系列中偿还它们，在移动 `_resolve_call` 之前。把完整的 ACL 家族 `_tool_allowed`、`_require_tool_access`、`_project_allowed`、`_tool_usable`、`_require_tool_use` 移动到 `domain/governance/access.py`。Resources、application.call，以及两个 run 路径都直接 import 它。一次 B 提交引入一个语义化访问错误，并把 HTTP 翻译留在每个接口处。

有一个相关的、任务中未命名但已在 1634 标记为 Stage 4 的桥梁：`resources_routes._enforce_sandbox_cap`。在 4a 中把它偿还给 `domain/governance/sandbox.py`；否则所述的 4a onboard 抽取是不完整的。

## 5. 提交序列与验证

每一次 A 提交都是字节级的移动。既有的装饰器、注释、docstring、变量名、折叠，以及函数体保持完全一致。新的模块 docstring/import，以及不可避免的相路径锚点，是唯一的候选例外，且需要提前评审。每一次 B 提交都是一个行为等价的边界抽取，没有新的业务规则。

### 5.1 PR 4a 提议的提交

1. `refactor(bootstrap): move app-wide HTTP middleware`
   - A 类纯移动，针对三个中间件家族。
   - 验证四个快照逐字节一致、中间件单元测试、legacy-host E2E、body 编码 E2E、完整 SQLite、drift。
2. `refactor(onboard): move onboarding routes`
   - A 类移动，把 1001-1032 与 1193-1224 移入 `routers/onboard.py`，保留原始挂载点。
   - 验证符号文本、装饰器、monkeypatch 目标、onboarding E2E、四个快照、完整 SQLite。
3. `refactor(onboard): extract onboarding application journeys`
   - B 类薄路由抽取，application 拥有的会话/提交。
   - 验证 seed、复用、skip、reset、teammate 接受、失败文本/状态、SQLite 加 PG 子集。
4. `refactor(onboard): move landing sandbox routes`
   - A 类移动 sandbox mint/live/webhook/feed/export/sample/install 路由与速率常量。
   - 验证符号文本、路由顺序、webhook 签名/重放测试、sandbox E2E、快照。
5. `refactor(onboard): move sandbox management primitives`
   - A 类仅字节移动控制侧 `demo.py`、`pubfeed.py`，以及位于兼容外观之后的 sandbox 管理符号。调用侧 sandbox 符号留在当前归属方，直到 4b。
   - 验证每个符号逐字节一致、新旧身份、live-wire 调用测试，以及轻导入。
6. `refactor(onboard): extract sandbox management journeys`
   - B 类 application 边界与类型化错误；偿还 sandbox-cap 桥梁而不混入其机械移动。
   - 验证 sandbox 永不网络测试、cap/TTL/速率测试、live-wire 测试、轻导入契约。
7. `refactor(billing): move balance and billing routes`
   - A 类移动，带上独立的原始位置路由。
   - 验证所有移动符号逐字节一致、Stripe webhook 路由顺序、monkeypatch 目标扫描、快照。
8. `refactor(billing): move billing orchestration`
   - A 类移动当前根 billing 符号，位于兼容外观之后。无事务或 SDK 行为变更。
   - 验证符号文本、新旧 import 身份、billing 套件、referrals 套件、ledger 套件。
9. `refactor(stripe): isolate the Stripe adapter`
   - B 类窄 infra 端口与 application 拥有的编排。无 SDK 调用、错误、幂等，或提交顺序变更。
   - 验证 checkout、portal、documents、签名 webhook、重投、auto-top-up 并发与失败测试。
10. `refactor(billing): extract billing application journeys`
    - B 类薄路由、类型化错误、会话归属、analytics/referral 编排。
    - 验证完整 billing/referral 旅程、PG webhook/幂等子集、四个快照、完整 SQLite、lint。
11. `refactor(referrals): move referral routes and domain primitives`
    - A 类仅路由与领域移动，保留兼容导出与原始挂载点。
    - 验证字节身份、referral 奖励 hold/sweep、top-up 交互，以及 import 契约。
12. `refactor(referrals): extract referral application journeys`
    - B 类薄路由与 application 拥有的摘要/sweep 编排。
    - 验证 referral 发放时机、重投、billing 交互、SQLite 与 PG 旅程。

如果评审偏好更少的提交，只合并符号共享同一目标的独立 A 移动。不要把一次 A 移动与一次事务、外部 I/O，或错误翻译的 B 变更合并。

### 5.2 PR 4b 提议的提交

被批准的取消修复不在此列表中。它独立的、基于 Postgres 的 E2E PR 必须在 4b 切分之前合并，且下面所有行锚点要在之后重新解析。

1. `test(call): freeze the application call contract`
   - 在移动行为之前，添加 DTO/端口契约测试与失败/最终化表。
   - 验证无路由或快照变更。
2. `refactor(governance): move call access and budget policies`
   - A 类字节移动针对 Stage 3 桥梁家族，所有公开-demo 策略常量与限流器置于 `domain/governance/publicdemo.py`。
   - 验证 AST/文本相等、切换前的桥梁身份、governance 契约、resource/run/call ACL 测试。
3. `refactor(governance): expose framework-neutral call policies`
   - B 类语义化错误与提交归属；删除八个 org 与两个 resource 的 ACL 赋值。sandbox 桥梁已在 4a 偿还，使 Stage 3 债务总数达到十一个。
4. `refactor(money): move the ledger into domain money`
   - 专门的 A 类字节级移动，带旧路径外观与更新后的 import-linter 契约。
   - 验证每个 ledger 符号文本、新旧对象身份、所有 money/referral/billing/call 测试、PG 竞态。
5. `refactor(call): move the call HTTP surface`
   - A 类移动 `call_tool`、`catalog_endpoint_access`，以及它们的挂载块到 `routers/call.py`。Bootstrap 拥有应用级处理器，并从 `application.call` 接入调用专属的出口分类。临时协作者可从归属方注入，绝不从 `api.py` import。
   - 验证移动后的文本/装饰器、四个快照、`treg.api` 再导出身份、monkeypatch 扫描。
6. `refactor(call): move intake and idempotency helpers`
   - A 类仅字节移动，保留标签行创建、声明顺序，以及兼容导出。
   - 验证辅助文本/身份、畸形元数据优先级、重放/声明竞态，以及快照。
7. `refactor(call): extract intake and idempotency`
   - B 类用例抽取，带有限的 application 拥有的事务。
   - 验证畸形元数据优先级、重放/声明竞态、每个预转发失败的标签释放。
8. `refactor(call): move target resolution helpers`
   - A 类仅字节移动解析、marketplace 定价，以及 capability-pin 消费辅助函数。
   - 验证文本/身份、编码路径、定价 fixtures、以及兼容 import。
9. `refactor(call): extract target resolution`
   - B 类框架中立结果与错误翻译。
   - 验证自有工具歧义、目录 fallthrough、编码路径、供应商层级选择、访问预检。
10. `refactor(call): move authorization helpers`
    - A 类仅字节移动 ACL、拒绝、成员/公开-demo 门禁。花费配额仍是 reserve 辅助函数。
    - 验证文本/身份、原始门禁顺序、公开-demo ratestore 写，以及快照。
11. `refactor(call): extract authorization`
    - B 类针对 ACL、拒绝、成员/公开-demo 门禁与 pin 消费的、类型化策略边界。
    - 验证拒绝状态/detail/审计、无上游命中、无 hold，以及保留的门禁顺序。
12. `refactor(call): move reservation and spend-cap helpers`
    - A 类仅字节移动 `_platform_reserve`、trial/platform/tag 花费门禁，以及它们面向调用的协作者。
    - 验证辅助文本/身份、402 负载、配额顺序，以及 auto-top-up 调度。
13. `refactor(call): make reservation application-owned`
    - B 类事务变更，限于调用 reserve。application 提交 reserve 并在外部工作之前关闭会话。每个惰性的陈旧 hold 释放在余额门禁之前仍是一个独立的已提交阶段；grant/top-up 事务转换仍是第 3.3 节中命名的债务。
    - 在 SQLite 与 Postgres 上运行 pool-discipline 与完整的 callmatrix。重新把每个移动的 `treg.api` monkeypatch 或断言新旧协作者身份，使 pool 测试无法守卫一个未使用的对象。
    - 同时验证确切的并发余额门禁、回滚行为、402 负载，以及不变的 auto-top-up 任务。种入一个已过期的 hold，强制后续 reserve 返回 402，并断言陈旧 hold 退款在失败时新 reservation 不留 hold 的情况下仍保持已提交。
14. `refactor(upstream): move relay, injectors, and SSRF guards`
    - A 类纯移动，带兼容外观与轻量 injector 叶。
    - 验证字节相等、relay 保真套件、轻 CLI import 测试、SSRF 测试、新旧身份。
15. `refactor(connections): move OAuth refresh rules`
    - A 类仅字节移动，带旧路径外观，且所有既有消费者在同一个对象上。
    - 验证文本/身份、刷新竞态/失败，以及 health/connect/local-run import。
16. `refactor(connections): separate OAuth refresh I/O from persistence`
    - B 类端口抽取。保留单飞、CAS、`last_error`，以及所有刷新消费者。
    - 验证刷新竞态/失败、health/connect/local-run 调用方，以及 token HTTP 期间无 DB 检出。
17. `refactor(call): return framework-neutral upstream responses`
    - B 类转换 infra relay 与路由包裹。保留原始头部顺序/重复项、cookies、HEAD/无 body 的 content length、流式、CSP/nosniff、body 帧，以及 close 语义。
    - 在 SQLite 与 Postgres 上运行 pool-discipline 与完整 callmatrix。在接收绿色测试之前，重新把移动的 `treg.api` relay monkeypatch 定向，或断言新旧对象身份。
18. `refactor(call): move settlement and evidence helpers`
    - A 类仅字节移动观测到的成本、可计费性、缓冲、证据，以及最终化辅助函数。
    - 验证文本/身份、8 MiB 截断与 content-length 重写、证据脱敏，以及快照。
19. `refactor(call): make settlement application-owned`
    - B 类单一归属方最终化器与 application 拥有的 settle/release 提交。取消行为已被前置修复 PR 冻结，此处不变。
    - 在 SQLite 与 Postgres 上运行 pool-discipline 与完整 callmatrix。把结算 monkeypatch 从 `treg.api` 重新定向，或证明兼容导出是同一对象。
    - 同时验证每个可计费性类别、超时/连接/流错误、取消、双重最终化竞态、DB 宕机响应行为，以及 DB 可用时无任何 hold。
20. `refactor(call): complete the staged use case`
    - B 类薄路由与 `CallContext` 编排，删除兼容绑定，迁移首调/审计逻辑。
    - 验证 31 个 callmatrix 测试不变、pool 纪律、完整 SQLite、定向 PG、快照、lint、drift。
21. `test(architecture): enforce the call runtime boundary`
    - 激活 application/domain/infra 的 import 契约、启动清单分离，以及一个显式包含 auto-top-up 任务、公开-demo/sandbox ratestore 命中，以及 `_record_first_call` 的 AdConversion outbox 写的数据面写允许列表。
    - domain-money 的 no-commit 架构测试仅覆盖调用 reserve/settle/release，包括 reserve 的惰性陈旧 hold reap。grant/top-up 及其受影响的 signup/referrals/billing 事务转换仍是 `money-funding-transactions`，在 4b 之后、Stage 5 之前到期。
    - 验证变更测试能在注入一个被禁止的边/写/提交时让每个契约失败。

对于每个提交：

- 使用 `uv run --frozen`；绝不触碰 `uv.lock`
- 四个 JSON 快照必须逐字节一致，且不得为通过而重新生成
- 使用 checkout 私有的 `TMPDIR` 用于完整 SQLite 套件
- 运行 `lint-imports` 与 `drift.sh`
- 在同一已提交变更中更新当前状态上下文片段，不带变更叙述
- 保持 docs/ideas 与 REFACTOR-PLAN 文件未跟踪（untracked）

## 6. 停止线（Stop-line）条件

若出现以下任一情况，停止并请求裁决：

1. **接入顺序。** 若一次阶段拆分会把标签封禁、调用配额、元数据校验、标签行创建，或幂等声明/重放相对于解析移动，则停止。先接入（Intake-first）已被冻结；字面上的"先解析"不是一个可用的实现选择。
2. **数据面派生写。** Auto-top-up 仍是一个内存检查加带自己会话的后台任务。Ratestore 的公开-demo/sandbox 命中与首调的 AdConversion outbox 插入也保持。若抽取它们会改变调度、持久化、请求延迟，或添加任何未被显式枚举的写，则停止。
3. **DB 宕机最终化。** 在 DB 可用时，终态路径在结束前关闭 hold。在 DB 不可用或进程死亡时，已提交的 hold 加 reaper 是保证，且响应保持当前的非阻塞最终化行为。若一次抽取会阻塞响应或削弱 reaper 恢复，则停止。
4. **取消前置条件。** 独立的取消修复 PR 必须在 4b 开始之前合并，并通过基于 Postgres 的、已付费计量调用取消 E2E。若任何 4b 提交改变了 `call_cancelled` 行为或使该测试失效，则停止。
5. **能力 pins。** 按 Stage 3 裁决，把能力 pin CRUD 留在 `api.py` 给目录阶段。只移动 `_enforce_capability_pin` 作为调用时消费者。若避免反向 import 似乎要求现在就移动 CRUD 或定义一个新的目录写归属方，则停止。
6. **Sandbox 归属。** 不要把调用 synthesis/live-wire 选择放在 `application.onboard` 之后，也不要把整个 sandbox 模块标为仅控制面。若纯移动无法在不改变行为的情况下拆分控制与执行符号，则停止。
7. **OAuth 刷新顺序。** 保留 reserve-before-refresh、刷新失败释放、进程锁、CAS 写，以及 `last_error` 时序。若"网络期间零 DB"要求改变哪个凭据赢得竞态，则停止。
8. **Ledger 事务转换。** 4b 仅改变调用 reserve/settle/release 的事务归属。Reserve 包括惰性陈旧 hold reap；每个陈旧释放必须在余额门禁之前独立提交，使得一个后来的 402 无法回滚任何退款。若一次抽取合并了那些事务，或要求静默转换 grant/top-up 或它们的 signup/referrals/billing 调用方，则停止。那项工作属于 4b 之后、Stage 5 之前的 `money-funding-transactions`。
9. **结算 vs 流式。** 计量响应保持缓冲，未计量响应保持流式。不要在结算之前流式传输计量 body，或缓冲成功的未计量 body。
10. **断开时的上游 close。** 若框架适配器无法证明在完整读取、部分读取、异常，以及取消情况下恰好一次的 `close`，则停止。
11. **数据面写允许列表。** 任何在 reserve/settle/release、幂等、OAuth 刷新、审计/遥测、标签预算记账、已批准的容量标记、公开-demo/sandbox ratestore 命中、`_record_first_call` 经由 AdConversion outbox，以及已批准的 auto-top-up 后台任务之外的被观测写，都会停止该移动。
12. **角色清单（Role manifests）。** `/run` 仍被排除在数据面之外；任何路由重组都不得改变角色路由键、启动检查，或后台任务。
13. **框架中立边界。** 若 `application.call` 或 `infra.upstream` 需要 FastAPI/Starlette 类型，或若一个路由开始拥有金钱、重试、补偿，或定价决策，则停止。
14. **轻 CLI。** 若移动 injectors/oauth 兼容路径会让 import 任何轻量 CLI 模块加载 Pydantic、FastAPI、SQLAlchemy、SQLModel、Alembic，或 crypto 实现，则停止。`httpx` 仍被允许。
15. **兼容表面。** 若需要任何路由键/函数名变更、`treg.api:app` 变更、快照变更、无法安全重定向的 monkeypatch 目标，或旧公开 import 删除，则停止。
16. **重构期修复。** 若发现的问题超出第 0.2 节的守卫、会变成一个 PR 中的第四个 fix 提交，或在无独立 PR 与 Postgres E2E 回归的情况下触及并发/金钱，则停止。在任何已批准修复之后，继续移动之前重新解析所有行锚点。

## 7. 退出标准与证明计划

### 7.1 31 个 callmatrix 测试保持不变

当前清单是 `test_matrix.py` 中 30 个矩阵用例，加上 `test_journey.py` 中从 signup 到 topup 的恢复旅程。它们已经证明：

- 自有工具 GET/POST 转发与 platform/自有凭据选择
- 余额、成员配额、拒绝、ACL、公开-demo 拒绝
- 幂等重放、碰撞、不匹配，与失败释放
- 供应商 4xx/5xx 可计费性、读/连接/流失败
- 观测到/畸形/压缩的成本处理
- 重复查询顺序、编码斜杠、cookie 擦洗
- 并发余额竞争与类型化 pool 饱和
- 已完成调用的响应、账本、审计、上游命中，以及空 hold 账目

保持全部 31 个测试函数与期望值不变。在 SQLite 与 Postgres 上运行它们。在矩阵之外添加新测试是允许的；不要为匹配一次重构而重写矩阵。

### 7.2 上游飞行期间零 DB 连接

既有覆盖有用但不充分：

- `test_call_pool_discipline` 在 `relay` 进入计量与自有 key 调用时采样 `pool.checkedout()`。
- 20 次调用的屏障（barrier）测试证明当前 pool 不会死锁。
- `tests/test_call_pool_discipline.py` 当前通过 `treg.api` 在第 65、129、151 行打补丁协作者。每次相关移动之后，重新把那些补丁定向，或断言兼容导出是同一对象。一个针对未使用旧对象的绿色测试不是证据。

缺失的证明：

1. 一个带延迟上游与 pool 插装的 PG 测试，记录在 `relay_started` 与 `relay_finished` 之间（包括响应 body 排空）的每一次 checkout/checkin 事件，并断言计数保持为零。
2. 针对 OAuth 刷新 HTTP 的同一测试，因为当前实现在持有其会话期间执行那个网络请求。
3. 一个单槽 PG pool 测试，带 N 个并发计量调用与一个门控供应商，断言全部以供应商速度完成且每个 hold 都关闭。
4. 一个未计量流式测试，在 body 保持打开的同时，一个独立的 DB 请求通过唯一的 pool 槽成功。

该测试必须检查实际绑定到调用服务的引擎，在 `finally` 中恢复绑定，并处置临时引擎。一个移除预转发提交、或在网络期间重新引入 DB 支持的刷新的变更必须让它失败。

### 7.3 无悬空 hold 与恰好一次最终化

既有覆盖有用但不完整：

- 每个 `assert_outcome` 都检查 `holds == []`
- 超时、连接错误、计量流中断、供应商失败、报告成本，以及并发都被覆盖
- 账本 `_claim_hold` 已使 settle/release 跨进程幂等

添加这些测试：

1. **取消 E2E：** 为一个真实计量调用注资，在 reserve 之后阻塞供应商，取消客户端任务，然后断言上游响应/客户端被关闭、余额被恢复、零 hold 残留、恰好一个 release 条目存在、其原因为 `call_cancelled`，且幂等标签可复用。这使用针对 Postgres 的真实客户端，并落在独立的 4b 前修复 PR 中。
2. **reserve 提交时的取消：** 门控提交，在不确定的边界取消，并断言无论 reserve 事务提交还是回滚，释放都安全。这也落在独立的 4b 前修复 PR 中，且必须演练 asyncpg，而非仅 aiosqlite。
3. **双重最终化对抗测试：** 让成功结算与取消/释放针对一个调用 id 竞速。断言一个终态账本条目、一个余额效应，且无 `TagSpend` 分歧。
4. **reserve 后的意外异常：** 在刷新、转发、缓冲，以及证据准备中注入一个非 HTTP 异常，并断言立即释放加上上游关闭。
5. **close 契约：** 统计成功流式完成、部分消费者断开、计量缓冲、读取期间超时，以及取消情况下的 `close` 调用次数。每个案例恰好一次。
6. **结算 pool 重试/宕机：** 保留既有的单次 pool 重试测试。对于持续的 DB 失败，断言响应保持当前的非阻塞行为，且已提交的 hold 对 reaper 保持持久。
7. **架构事务测试：** 仅拒绝领域拥有的提交/回滚针对面向调用的 reserve/settle/release 路径，并验证每个 application 阶段在调用外部端口之前关闭其会话。把 reserve 的惰性 reap 视为范围内，断言每个陈旧释放都有独立的 application 拥有的提交，并证明一个后来的 402 回滚无法撤销任何被 reap 的释放。不要断言 grant/top-up 及其 signup/referrals/billing 调用方已经转换。

最终的 Stage 4 实时检查仍是登录、连接、调用、计费（charge），以及 top-up。对于调用腿，使用一个真实的流式上游，并在飞行期间检查 DB pool。对于 charge/top-up，验证调用的 hold 到达一个终态账本动作，且控制面的 top-up 路径仍恰好贷记一次。

## 8. 评审清单

修订后的检查点冻结或请求归属方批准这些实现门禁：

- 4a/4b 拆分，referrals 与 sandbox-cap 债务在 4a
- 接入作为预解析阶段；无字面上的"先解析"重写
- 花费配额在 reserve 内，而 authorize 拥有 ACL/拒绝/成员/公开-demo 与调用时 pin 策略
- 供应商响应作为忠实转发的数据；以机制为键的失败，带单一晚期绑定的 `blame`
- 稳定的 502 种类/释放/状态/头部映射、SSRF 作为 reserve 后的不可计费拒绝，以及供应商响应之后无 402
- 仅 2xx 的计量重放；被计费的 4xx 保持立即可复用且不加入重放
- 持续 DB 失败保留当前响应行为与持久的 hold/reaper 保证
- 独立的 4b 前取消修复 PR，使用 `reason=call_cancelled`，带真实客户端 Postgres E2E 证明
- 数据面派生写枚举：auto-top-up 任务、公开-demo/sandbox ratestore 命中，以及首调的 AdConversion outbox 插入
- 十一个 Stage 3 桥梁债务：八个 org 绑定、两个 resource ACL 绑定，以及 sandbox-cap 桥梁
- 应用级中间件与 `_pool_saturated`/`_mark_treg_own_errors` 处理器在 bootstrap 下，而调用专属的 `_stamp_call_exit`/`_refusal_kind` 由调用归属方提供
- ledger 专门的 A 移动在 4b；no-commit 强制限于调用 reserve/settle/release；命名的 `money-funding-transactions` 偿还在 4b 之后、Stage 5 之前
- 严格的 A 后 B 提交分离、双引擎 pool/callmatrix 门禁，以及三个最危险边界上的实时 monkeypatch 目标
- sandbox 模块拆分、轻 injector 打包、能力 pin CRUD 留给目录阶段，以及显式排除的 local-run/启动符号
- 第 0.2 节中提议的计划 §0.6 修订的归属方批准：每个 PR 最多三个 fix 提交、详尽的 PR 行为变更清单、修复后的行锚点刷新，以及针对并发/金钱相邻修复的 PG E2E

在评审此清单且 PR #210 合并之前，不开始任何代码、被跟踪文档、lockfile，或提交工作。
