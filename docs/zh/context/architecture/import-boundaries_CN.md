---
title: Enforced import boundaries（强制执行的导入边界）
status: shipped
sources:
  - pyproject.toml
  - .github/workflows/ci.yml
  - src/treg/application/__init__.py
  - src/treg/application/call/__init__.py
  - src/treg/application/call/access.py
  - src/treg/application/call/authorize.py
  - src/treg/application/call/idempotency.py
  - src/treg/application/call/overflow.py
  - src/treg/application/call/route.py
  - src/treg/domain/catalog/routing/__init__.py
  - src/treg/application/call/intake.py
  - src/treg/application/call/resolve.py
  - src/treg/application/call/reserve.py
  - src/treg/application/call/settle.py
  - src/treg/application/call/evidence.py
  - src/treg/application/call/service.py
  - src/treg/application/call/types.py
  - src/treg/client_identity.py
  - src/treg/domain/__init__.py
  - src/treg/domain/governance/__init__.py
  - src/treg/domain/governance/access.py
  - src/treg/domain/governance/budgets.py
  - src/treg/domain/governance/publicdemo.py
  - src/treg/domain/governance/teams.py
  - src/treg/domain/governance/usage.py
  - src/treg/domain/identity/__init__.py
  - src/treg/domain/connections/__init__.py
  - src/treg/domain/connections/authorization.py
  - src/treg/domain/connections/oauth_flow.py
  - src/treg/domain/connections/refresh.py
  - src/treg/domain/money/__init__.py
  - src/treg/domain/feedback/__init__.py
  - src/treg/domain/asynctasks/__init__.py
  - src/treg/domain/capacity/__init__.py
  - src/treg/infra/upstream/__init__.py
  - src/treg/infra/upstream/injectors.py
  - src/treg/infra/upstream/relay.py
  - src/treg/infra/upstream/aggregators/__init__.py
  - src/treg/infra/upstream/limiter.py
  - tests/test_call_architecture.py
  - tests/test_import_lightness.py
related:
  - architecture/composition.md
  - architecture/money.md
  - interface/cli.md
---

# Enforced import boundaries（强制执行的导入边界）

Import Linter 读取 `pyproject.toml` 中 `tool.importlinter` 下的契约。主 CI `test` 作业用 `uv sync --locked`（在陈旧 lock 时失败）安装 lock，然后在测试套件之前运行 `uv run --locked lint-imports`。把该检查放在这个作业中复用了开发环境，并为快速静态架构检查避免了第二次安装。R2 SDK（`obstore`）只通过 `[server]` 安装，并禁止轻量 CLI 导入。`infra.object_store.open_r2` 惰性加载它；bootstrap 组装具体的客户端或注入的内存实现。调用写允许列表包含归档 body PUT 链，因为它在没有任何 DB 事务之外持久化已付费响应，以及转发后 provider-resource 的 register/rename/tombstone 调用，因为共享 key 的资源所有权必须由收到供应商成功响应的调用建立或推进。

独立的 `test-postgres` 作业针对 Postgres 16 运行其数据库敏感子集，每个 xdist worker 一个数据库；它使用无缓冲 Python 输出与一个 15 分钟作业预算，因此一个慢测试仍可被诊断。该子集包含 agent 归因、托管 API-key 生命周期与并发、凭据健康、本地运行报告，以及 ads-conversion 覆盖，因此朴素 UTC 假设被 asyncpg 而非被 SQLite 宽松的适配器隐藏。

必需的 `gitleaks` 作业用 `--log-opts="HEAD"` 扫描从已 checkout `HEAD` 可达的完整历史。在拉取请求上，checkout 提供合并提交，因此 base 与 proposed 分支历史都被包含。已删除的密钥仍可被检测；无关的已获取分支尖端不阻塞此 PR。检测规则与允许列表不变。

第 1 阶段激活了前两个契约：

- 显式的轻量 CLI 模块列表不能直接 import 任何 server-extra 包，包括 FastAPI、SQLModel、SQLAlchemy、Alembic、数据库驱动、MCP、Stripe，或 cryptography。由 `TYPE_CHECKING` 守卫的导入全局排除，因为它们不能在运行时加载。此契约允许间接导入，因为可选的代理依赖可能出现在惰性执行的内部模块中；具名的 CLI 模块自身必须保持没有直接的服务端导入。
- `treg.domain.money` 不能 import `treg.audit`。金钱正确性绝不流经尽力而为的审计路径，其写可能在负载下被丢弃。

第 2 阶段添加第三个契约：完整的 `treg.routers` 包不能直接或间接 import `treg.api`。`as_packages = true` 让源覆盖每个当前与未来的路由子模块。`api.py` 仍是兼容导出器与有序路由表宿主，因此允许的方向是 API 到 routers。

异步任务域与 capacity 有相同的仅向内边界：它不能 import API、routers、application 编排或尽力而为的审计。`tests/test_call_architecture.py` 钉住该规则以及一个证明守卫拒绝一条被禁边的突变。

第 3 阶段在包出现时添加领域契约。完整的 `treg.domain.identity` 包不能 import `treg.api`、`treg.routers`，或 `treg.application`。Identity 现在作为一个叶子拥有会话签名与验证、MCP 令牌与 grant 族原语，以及 caller/access 解析。兄弟领域边在兄弟出现时添加；因此 identity 也禁止 governance。Governance 可以 import identity 但不能 import API、routers，或 application 层。未来的兄弟契约在它们的包存在之前一直缺失，因此没有占位领域让未来的边界看起来活跃。Governance 拥有共享工具/项目 ACL、标签预算规则，以及公开-demo 速率策略。该包也禁止直接 FastAPI 与 Starlette 导入；语义策略错误由每个 HTTP 接口翻译。调用 application 包拥有框架中立的分阶段用例：请求接入、幂等状态、目标解析、catalog 定价与访问决策、鉴权、预留、转发编排，以及最终化。HTTP 适配器捕获一个 `CallInput`、翻译类型化失败，并包裹返回的 `UpstreamResponse`。客户端名称规范化位于一个中立叶子，因此 application 路径不加载 Request 感知的 caller 元数据适配器。

完整的 `treg.domain.connections` 包也是一个面向内的领域包。它拥有供应商中立的授权方法选择、同意 URL 构建，以及刷新状态变更。它不能 import API、bootstrap、routers、application 层、FastAPI，或 Starlette。供应商注册表数据可以通过遗留兼容模块调用这些规则，而 HTTP 交换适配器留在 `treg.infra` 且工作流协调留在 `treg.application`。

两个运行时契约让那个边界可执行。`treg.application.call` 不能 import 遗留 API、bootstrap、routers、FastAPI，或 Starlette。`treg.infra.upstream` 不能 import 那些 HTTP 适配器或框架。对 application 拥有的请求与响应 DTO 的直接导入仍是用例与转发共享的端口。突变测试注入代表性的被禁边并断言检测。同一测试模块也钉住金钱事务边界：所有五个 `domain/money` 原语（预留/结算/释放分段体加 `grant` 与 `topup`）被扫描 `db.commit` / `db.rollback` 且必须只做暂存，带一个突变自检以检测被注入的提交；惰性的陈旧 hold 回收保留它文档化的独立提交边界。

两个直接边是精确的例外。`cli.ensure_proxy_dependency` 只在用户调用可选代理功能之后 import `cryptography`，并先提供安装代理额外包。`localrun.render_grant` 只在服务端执行 grant 路径时 import SQLModel。Import Linter 把函数局部导入当作普通直接边，因此两者都出现在 `ignore_imports`；不匹配的忽略是错误，确保被移除或重命名的边不能留下陈旧的例外。

一个 ignore 覆盖整个模块边，因此不能检测有人把任一惰性导入移到模块作用域。`tests.test_import_lightness` 通过启动一个隔离的 Python 子进程、导入每个轻量模块，并断言没有任何服务端依赖根出现在 `sys.modules` 来关闭那个缺口。httpx 与 questionary 等基础依赖仍被允许。

异步任务域（`treg.domain.asynctasks`）是一个**与轻 CLI 共享的仅标准库叶子**：`cli.await_async_task` import 它的 `json_path`、`classify_terminal` 与 `artifact`，因此等待方与结算 worker 对"完成"意味着什么绝不能分歧。两个守卫让它轻量：该模块在 `test_import_lightness` 的列表上，且一个 import-linter 契约禁止它每个服务端根（`treg.models`、`treg.infra`、`treg.config`、SQLModel、pydantic、yaml、httpx）。

表格域（`treg.domain.table`，[table](table.md)）是同类叶子：解析的答案进、行列出。它的契约禁止每个外层、每个兄弟域，以及 web、数据库与设置库，因此转换器仅基于保存的答案就可测试。

capacity 域（`treg.domain.capacity`，plan step B）是一个像 identity 的叶子：它不能 import `treg.api`、`treg.routers`、`treg.application`、`treg.bootstrap`、`treg.audit`、FastAPI 或 Starlette。它读配置且只写它自己的表与 ratestore 键，来自 worker-profile 命令（`treg-worker`，一个独立的 console 脚本，因此轻 `treg` CLI 永不获得 DB 导入）。调用 application 向内 import capacity 域（`resolve` → `view`、`settle` → `signatures`/`marks`）；该域绝不反向 import；`application.call.overflow` 组合 capacity 域、聚合器信封与金钱原语，且聚合器适配器保持纯信封代码；`routers.catalog` 读 capacity 域的 `routes_view` 用于 overflow 价格披露（通过调用路径使用的同一进程内副本对 worker 拥有的表的一次读，绝非写）；`application.call.route` 在规划之前读两个 capacity 视图，以便一个耗尽但有启用 overflow 路由的供应商到达普通的 child 阶梯，并组合纯 `domain.catalog.routing` 包（契约、适配器、排名）与调用用例自身。聚合器信封位于 `treg.infra.upstream.aggregators` 且继承上游契约（无 HTTP 适配器、无 routers）；capacity 域的 `verify` 模块可以 import 它们，因为它们是纯信封代码，而非 web 框架。

catalog 域的契约也禁止 `treg.oauth_providers`，它 import `domain.connections`：否则间接导入允许会让 catalog 通过它看不见地到达一个兄弟域。搜索只需要一个供应商的显示名，且 `bootstrap` 交给它（`configure_provider_labels`）。

feedback 域（`treg.domain.feedback`）拥有持久的报表插入与查询。它的契约禁止直接 import API、bootstrap、routers、application 编排、兄弟域、尽力而为的审计、FastAPI，与 Starlette。共享模型与 SQLAlchemy 仍可用；事务提交与调用引用验证属于 `treg.application.feedback`。
