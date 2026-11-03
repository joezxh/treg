---
title: Application composition and deployment roles（应用组合与部署角色）
status: shipped
sources:
  - src/treg/bootstrap.py
  - src/treg/bootstrap_handlers.py
  - src/treg/bootstrap_http.py
  - src/treg/worker.py
  - src/treg/infra/money_trace_runner.py
  - src/treg/infra/money_admission_reporting.py
  - src/treg/call_surface.py
  - src/treg/application/connect.py
  - src/treg/domain/identity/mcp_oauth.py
  - src/treg/domain/identity/session.py
  - src/treg/routers/admin.py
  - src/treg/routers/auth.py
  - src/treg/routers/billing.py
  - src/treg/routers/call.py
  - src/treg/routers/connections.py
  - src/treg/routers/onboard.py
  - src/treg/routers/orgs.py
  - src/treg/routers/resources.py
  - src/treg/routers/referrals.py
  - src/treg/routers/web.py
  - scripts/dump_surface.py
  - tests/test_app_roles.py
related:
  - architecture/import-boundaries.md
  - interface/api.md
  - architecture/mcp-oauth.md
  - ops/deploy.md
---

# Application composition（应用组合）

独立的 [Enrich Arena](../interface/enrich-arena.md) 页面（`/enrich-arena` 与 `/enrich-arena/leaderboard`）与 `/arena/*` 路由是控制角色（control-role）面。付费交互式运行内部使用普通调用 application。关闭时它们在关闭共享上游客户端之前排空它们的进程内所有者。

`bootstrap.create_app(role)` 是 FastAPI 组合根。`api.py` 宿主有序的路由表，在兼容性敏感的注册点附加关注路由器，并在 EOF 调用工厂一次，因此部署的 `treg.api:app` 导入路径保持默认的 `all` 角色。它的最后一步加载已安装的 policy 扩展（`policy.load_extensions`，见 [policy extensions](policy-extensions.md)），因此扩展的 `install` 看到完成的 app。

工厂拥有具体的组装：三个核心纯 ASGI 中间件注册、可选的 V2 路径归一化器、六个异常处理器、静态挂载、可选的 MCP 挂载与生命周期、GET 到 HEAD 的加宽、隐藏隐含 HEAD 操作并为多方法路由的每个方法给出自己 operation id 的 OpenAPI 包装器、共享 HTTP 客户端创建、启动工作、关闭排空，以及 Ads 转化 worker。注册顺序就是兼容性行为。四个 stage-0 快照对 `role="all"` 逐字节一致，除非该组合有意变更。`dump_surface._composition` 从它与部署无关的快照中省略仅本地的 `_DevTitleMiddleware`；`tests/test_dev_title.py` 单独检查那个中间件。

当 archive 设置选择 R2 时，生命周期在 DB 验证之前验证对象存储配置，然后拥有异步客户端直到 archive 与分析排空完成。这个有条件的资源设置在启动时不做对象 I/O 且不添加 worker。测试可以供应 `create_app(..., archive_object_store=...)`；`configure_archive_object_store` 是共享的内存注入接缝，并把同一存储交给 find 的卡片向量（`find_index.configure`，见 [find](find.md)）；带一个嵌入 key 时生命周期也在每个角色启动一个后台任务构建那些向量（`find_index.warm`），在关闭时与其他 worker 一起取消。见 [archive](archive.md) 了解开关与队列行为。同一 `archive_object_store` 上下文拥有 Arena insights worker 的客户端；那个命令不启动 web 生命周期或其后台任务。

对于每个角色，工厂把 Catalog 观察端口接到一个进程局部的 `CachedEndpointObservationReader`，由短 `background_session_maker` 读取支持——缓存绝不在请求路径上 await 源（未命中返回空并调度一次刷新），因此那些 `callrecord` 聚合是离请求的（off-request）工作且属于 API 的池之外。`all` 与 `dataplane` 生命周期把那个精确实例注入两个已挂载的 MCP catalog 面；HTTP catalog 路由与 `all` 和 `control` 上的观察统计散文页面（用例与工作流）从 app state 读取该实例。这即使 HTTP 与 MCP 并发搜索也保持一个缓存与每个进程一个刷新 Task。刷新 Task 在命中时惰性启动，而非出现在角色总是运行的后台任务清单中。生命周期仍拥有它：关闭首先把它从 MCP 解绑，然后调用 `aclose()`，它在数据库与 HTTP 资源消失之前拒绝新的刷新并取消共享 Task。一旦故障处理器安装，生命周期发出 `analytics.capture_service_started(role)`，每个进程一个携带每个服务器事件都有的 `build` 与 `archive_config` 指纹的 `service_started` 事件（见 [data-model](data-model.md#product-analytics-writer-analyticspy)）。

Bootstrap 把根日志配置留给宿主与既有 MCP 初始化。[Org 流量](org-traffic.md) 与 [已发布流控](org-flow-control.md) 使用 scoped plain 事件处理器而不改变根 logger 或第三方 logger。共享调用面在进入调用 application 之前使用一个已发布的暂停与原子速率/并发准入快照；它不添加生命周期任务、环境设置或数据库写。

每个角色还拥有一个 `infra.money_trace_runner` 生命周期，独立于分析启用性。它抽样进程内金钱事务与事件循环唤醒延迟，并把有界的诊断记录发送到一个专门的日志线程。关闭在产生金钱的后台工作排空之后、在分析排空之前停止它。worker 命令分发器对每个命令（含异步结算）使用相同的生命周期；它最终的本地摘要有一个有界的关闭等待。同一运行器每分钟一次与在 worker 退出时排空固定基数的租约命令计时，到既有的本地日志汇与分析队列；它不添加租约探测任务或连接。此 [data-model](data-model.md#product-analytics-writer-analyticspy) 片段定义该 trace 的覆盖、隐私与损失计数。

既有的 web 金钱计时计时器也本地发出 `money_admission_gauge` 并到分析；它不添加后台采样器或每请求传输。`worker._run_command` 即使它的命令失败也发出最终的准入窗口，然后在 trace 运行器已排队它最终的租约/trace 摘要之后尝试至多一秒的分析排空。它在离开 trace 生命周期之前关闭共享 KV 客户端。短 worker 投递保持尽力而为，因此使用它的本地退出摘要来区分缺失的网络投递与缺席的工作。最终的 trace 摘要由它的生命周期单独发出。

`bootstrap_handlers.py` 拥有应用级的池饱和与 HTTP 异常适配器。`call_surface.split_call_path` 把 `/call/`、`/catalog/call/` 与 `/table/` 分类，以便那些适配器共享相同的 call-id、审计与幂等释放契约，同时保留 `call`、`catalog_call` 与 `table` 进入归因。组合根在注册之前从 `routers/call.py` 供应调用特定的 `_stamp_call_exit` 回调；该回调拥有 call id、拒绝分类、审计回退、异常调用遥测，以及幂等标签释放。在 caller 身份存在之后，池适配器在 `tool_called` 漏斗中报告 `failure_kind=db_pool`。身份解析期间的超时反而发出 `call_intake_failed`，没有团队或目标归因，因此它不改变已准入调用的总体。两者也在返回类型化 503 之前把基础设施异常发送到 `analytics.capture_fault`；普通 HTTP 拒绝保持响应，而非服务器故障。

`bootstrap_http.py` 拥有应用级的 HTTP 中间件实现。中间件栈是 `org_traffic.RequestLogMiddleware` -> `_BodyDecodeMiddleware` -> `_SecurityHeadersMiddleware` -> `_LegacyHostRedirectMiddleware` -> 路由/挂载。三个都是纯 ASGI。安全包装器在 `http.response.start` 用大小写不敏感的 setdefault 语义添加头部，重定向包装器要么发送与之前相同的 301/302 响应要么直接调用它的子级。在本地开发服务器（`Settings.local_dev`：环回 `public_url` 之后的本地 sqlite，同样的测试 `single_user_ok` 依赖）上，`_DevTitleMiddleware` 包裹栈并在每个 HTML 页面的 `<title>` 前缀 `[dev] `，以便它的标签与生产区分；它绝不在其他地方注册。让 `BaseHTTPMiddleware.call_next()` 离开这个栈对于流式传输与断开很重要：一个 MCP 客户端可能在它的无状态传输终止而不发送响应时关闭，那是已死连接的正常结束，而非服务器 500。外部流量观察器发出净化的 [Org 请求/流量日志](org-traffic.md)。all/dataplane 生命周期共享一个进程局部 60 秒报告计时器，在最后一个所有者退出时取消；这不是额外的 asyncio worker 任务且不使用分析或数据库。

纯 ASGI 不会让一个真正的缺失响应缺陷变静默。Uvicorn 的 `RequestResponseCycle.run_asgi` 检查一个返回时连接仍存活的 app，记录 `ASGI callable returned without starting response.` 并发送 500。它只在协议已标记客户端断开、无法投递任何响应时跳过该错误。响应完成也仍负责 Starlette 后台任务：`/call` 转发的 `StreamingResponse` 在它的 body 之后运行 `BackgroundTask(upstream_resp.aclose)`，且一个断言测试钉住共享 httpx 连接恰好被释放一次。移除两个 AnyIO 内存流跳变改变流式背压与调度但不改变中断语义，这是 callmatrix 流失败用例钉住的。

## 角色清单（Role manifests）

每个创建的 app 暴露 `app.state.role_manifest`，带显式的 `routes`、`background_tasks` 与 `startup_checks` 列表。`tests/test_app_roles.py` 钉住每个角色的所有三个列表，而调用架构测试单独钉住 dataplane/control 启动拆分与后台任务所有权。

| 角色 | HTTP 路由与挂载 | 后台任务 | 启动检查 |
|---|---|---|---|
| `all` | 完整面，含 `/run`、静态文件、`/mcp`，以及有标志的 `/mcp/v2` | 启用时的 Ads 转化 worker | 只读 DB 验证、HTTP 客户端、启用的 MCP 生命周期 |
| `dataplane` | `/call/{rest:path}`、`/catalog/call/{rest:path}`、`/table/{rest:path}`（见 [table](table.md)）、MCP 挂载，及其资源元数据；无 `/run`、静态文件、文档或 OpenAPI | 无 | 只读 DB 验证、HTTP 客户端、启用的 MCP 生命周期 |
| `control` | 除调用面之外的一切；含 OAuth 颁发、`/run` 与静态文件 | 启用时的 Ads 转化 worker | 只读 DB 验证、HTTP 客户端 |

没有角色生命周期写 schema、执行数据回填，或供应本地单用户。显式的 `python -m treg upgrade` 发布阶段拥有内容驱动的回填；默认的 `python -m treg` 服务路径在 Uvicorn 启动之前添加单用户供应。原始 ASGI 运营者必须在每个发布单独运行 upgrade 命令。`verify_db()` 只检查修订兼容性与 Fernet-key 守卫；确切的启动清单被钉到一个只读允许列表。

每个角色生命周期在只读 DB 验证之后调用 `analytics.install_fault_handler`。没有 PostHog key 时它是 no-op；否则 ERROR+ 根日志与 Uvicorn ASGI 异常记录喂入有界分析队列，直到生命周期在其外层 `finally` 移除该处理器。这只限于日志的可观测性：它不添加中间件、后台任务或数据库访问。

MCP 是调用流量（重构计划的角色表把 `mcp.py` 分配给 dataplane），因此未来的 dataplane 部署在两个入口点服务 agent。OAuth 令牌颁发——同意页与 `/oauth/*` 端点——留在 control；MCP 面只验证令牌，那是一个读。`domain.identity.session` 因此是一个双角色原语：control 签署浏览器与身份令牌，而两个角色通过 `domain.identity.mcp_oauth` 共享它的签名密钥验证。

`_CONTROL_ROUTE_KEYS` 与 `_DATAPLANE_ROUTE_KEYS` 把每个 `api.router` 路由分配给恰好一个所有者。App 创建在一个未分类、陈旧、重复或多重所有的键上失败，因此添加一个路由不能静默扩展 dataplane。角色分离在第 1 阶段是准备性的；只部署 `all` 角色。

`TREG_CLAUDE_CONNECTOR_ENABLED=true` 添加 `/mcp/v2` 并启动它的生命周期。当该标志为 false 或缺失时，只启动团队 `/mcp` 挂载。嵌套 V2 挂载先注册，以便父 `/mcp` 挂载不能消费它。

当 V2 启用时，`NormalizeDirectoryMCPPath` 在路由匹配之前把确切的 `/mcp/v2` 路径重写为 `/mcp/v2/`。Claude 可以从自定义连接器 URL 移除最后的斜杠。两种拼写必须留在 V2 传输与 OAuth audience 上。

## 路由克隆（Route cloning）

每个工厂调用必须产生一个独立的 app，其依赖覆盖属于那个 app。`_include_routes` 因此浅克隆每个 `APIRoute`，把它的依赖覆盖提供者指向新的 FastAPI 实例，并重建它的请求处理器。这也避免当前 FastAPI `include_router()` 实现添加的内部的 `_IncludedRouter` 包装器，那否则会改变路由检查与已提交的面的快照。

此后添加的公开路由：`/{INDEXNOW_KEY}.txt`（`indexnow_key`，`routers/web.py`）——IndexNow 密钥文件；列在所有权表中与 `/sitemap.xml` 旁边。见 `interface/seo.md` § IndexNow。

[tool hub](hub.md) 的管理与浏览面（`/hub/tools*`、`/hub/run`、`/hub/runs/{run_id}`、`/hub/{tool_id}`、`/app/runs/{run_id}`，以及 `/admin/hub/listings*` + `/admin/hub/updates*` 评审路由）与管理的其余部分一起加入 `_CONTROL_ROUTE_KEYS`；`/call/` 与 `/catalog/call/` 仍是一个 hub 运行自身步骤经过的唯一 dataplane 路由。遗留仪表盘的 `/app/legacy/assets/{path:path}` 挂载已消失——见 [dashboard](../interface/dashboard.md)。

不再有 web 进程收集 Arena 统计：`treg-worker arena insights`（一个 cron）收集，且 `/arena/insights`，一个 control 路由，只读取最后发布的快照。`ROLE_BACKGROUND_TASKS` 因此为 control/all 只列出 `adsconv.worker`。关闭取消并 await 每个已启动的后台 worker，然后排空 Arena、审计与分析或关闭共享客户端，因此数据库回滚/关闭在事件循环拆除之前完成。

`POST /reviews` 与 `GET /admin/reviews` 属于 control，与反馈 intake 与读取一起，如同 `POST /media` 与服务于托管引用文件的公开 `GET /m/{token}`。

archive 对象存储生命周期一次性归一化配置，选择 R2 工厂或注入的内存上下文，并在退出时重置存储。R2 验证在 DB 启动验证之前运行；一个过时的比较模式环境变量不再阻塞迁移 CLI 设置构造。
