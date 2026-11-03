---
title: Workbench 表格存储
status: foundational
sources:
  - src/treg/models.py
  - src/treg/alembic/versions/0077_workbench_table_metadata.py
  - src/treg/domain/governance/teams.py
  - tests/test_workbench_table_schema.py
  - src/treg/infra/workbench_store.py
  - tests/test_workbench_store.py
  - tests/test_workbench_store_lifecycle.py
related:
  - architecture/import-boundaries.md
---

# Workbench 表格存储

## 管理元数据

修订 `0077` 向既有的控制面数据库添加 `TeamDatabase` 与 `TableDoc`。它只创建空的管理表：不配置任何团队、不创建任何 Turso SQL 表，也不启用任何表 API 或运行时。业务行属于团队存储，而非这些记录。

`TeamDatabase` 每个 Org 与每个 Turso 资源引用唯一。`turso_database_ref` 标识固定的目标，包括其供应商组织，而不仅仅是显示名或被多个账户共享的裸数据库名。`connection_ref` 是一个指向可信连接配置的透明引用，包括独立的只读与读写凭据；绝不在此存储令牌。非空连接引用跨团队唯一。解析器仍必须验证目标与凭据范围：否则不同的引用可能指向同一个远程数据库。映射以 `provisioning` 开头并带一个可空的连接引用。`ready` 需要一个非空引用；验证远程资源及其访问仍是写方的责任。`database_generation` 从 1 开始且必须保持为正。它隔离一个被替换/恢复的数据库；它不是表 schema 修订。

`TeamDatabase.org_id` 与 `TableDoc` 的所有权引用刻意没有数据库外键。创建这些表不得获取既有 Org 表上的外键锁。参照完整性属于应用：未来的管理写方必须验证 Org 存在且一个表的数据库映射属于该 Org，包括在重新分配时。数据访问必须在已认证团队的_scope 内解析两个记录；一个未检查的数据库 ID 不是授权。这一仅 schema 的变更不实现那些写方或访问守卫。

`TableDoc` 保留一个稳定的表 ID、显示名与 SQL 名、创建键与指纹、列元数据，以及 schema/元数据修订。名称与创建键在一个 Org 内唯一；物理 SQL 名在一个数据库内唯一。该表以 `creating` 开头，没有确认的 schema 版本或已验证的数据库代次。`ready` 要求两者皆正。元数据修订也保持为正。应用写方必须在恢复重复创建之前比较请求指纹、在发布就绪之前验证物理 schema，并更新修订与时间戳。这些约束不实现配置、不可变创建操作，或恢复租约。

表 ID、名称与创建身份不能为空或仅空格。物理名必须匹配小写 ASCII 形式 `[a-z_][a-z0-9_]*` 且不能以 SQLite 保留的 `sqlite_` 前缀开头。这使它们的唯一性与 Turso 大小写不敏感标识符一致；DDL 写方仍必须引用标识符。SQLite 使用带 NUL 守卫的内置 GLOB 检查，PostgreSQL 使用 C 排序的正则表达式。列元数据使用 PostgreSQL JSONB 与 SQLite JSON；它的应用 schema 仍需要写方验证。

`TableDoc.database_generation` 记录物理表最后一次被验证所在的数据库代次。它没有默认值且保持为空直到验证；它绝不能在被恢复时自动跟随 `TeamDatabase.database_generation`。未来的数据访问必须要求两个记录都 `ready` 且它们的代次匹配。被恢复的表只有在物理身份与 schema 验证更新了它们记录的代次之后才有资格。缺失或未解析的表保留它们的旧代次并保持无资格。这些 schema 字段尚未实现访问守卫；配置、恢复与数据访问的写方/读方在添加时必须强制执行那一份契约。

`cascade_delete_org` 通过共同的 `ORG_SCOPED_MODELS` 列表在它们的 TeamDatabase 映射之前移除 TableDoc 记录，不依赖数据库级联。此路径之外的直接删除可能留下孤儿元数据。这只清理控制面元数据。远程资源清理必须在启用配置之前接通。一个应用回滚保留这些附加表；一个显式的 schema 降级会丢弃它们的元数据且不删除任何远程资源。

## 存储适配器

`infra.workbench_store` 是一个独立的基础设施边界，尚未接入产品路由或 bootstrap。`TursoStore` 使用基于 HTTP 的 SQL；`SQLiteStore` 使用文件支持的数据库用于本地开发与契约测试。两者都暴露 `read` 与一个异步 `transaction` 上下文，其 `execute` 返回 `StoreResult` 行与受影响行计数。既有的 PostgreSQL 存储不变。

## 调用方边界

调用方提供可信 SQL 与一个服务端选定的数据库位置；此模块不授权团队、不验证用户表定义，也不配置数据库。通过位置参数绑定值。数据库凭据与这些适配器属于 Treg 服务端，不在用户脚本内。在等待远程存储时不要持有一个 PostgreSQL 连接。

`TursoStore` 要求用于读与写的独立数据库范围的凭据。用 Turso 的 `--read-only` 权限配置 `read_auth_token`；服务强制执行读边界。调用方必须为同一数据库提供令牌并在过期前轮换它们。读永不回退到写令牌。不要依赖 `PRAGMA query_only = ON` 做远程读：Turso Cloud 可能拒绝该语句，且一个流水线在错误后仍可执行后续语句。

`SQLiteStore.read` 启用仅查询模式并以 `mode=ro` 打开文件，因此读取一个缺失的数据库会失败而不创建一个空文件。读与写连接使用配置的 SQLite busy 超时。一个事务拥有它的连接且只在成功上下文退出时提交。在 COMMIT 之前的错误与取消导致回滚；在上下文内捕获一个语句错误不会让事务再次可提交。一个失败的回滚保留原始错误。在离开上下文之前 await 所有操作。上下文拥有 BEGIN、COMMIT 与 ROLLBACK；调用方自己绝不能发出事务控制语句。

## 远程失败

`TursoStore` 使用 [Turso HTTP 协议](https://docs.turso.tech/sdk/http/reference)，在每次响应后轮换连接接力棒（baton）并在使用后关闭流。事务截止默认四秒，低于供应商文档化的五秒窗口。超时必须大于 0.5 秒且小于五秒。两个适配器都拒绝在剩余不到 0.5 秒时发送 COMMIT，返回 `transaction_expired` 并回滚。这一保留减少了可避免的不确定性；它不保证 COMMIT 会在截止前完成。保持批次短且不在事务内执行无关 I/O。本地适配器检查同一截止，但取消不会立即停止已排队在 SQLite 后台线程上的工作。

没有自动重试。一个传输失败或不可读的 COMMIT 结果抛出 `StoreError("outcome_unknown")` 并设置 `tx.outcome_unknown`：该写可能已经是持久的。COMMIT 期间的取消设置同一标志但传播 `CancelledError`，保留 `asyncio.timeout` 与 `TaskGroup` 行为。调用方必须在重放一个写之前解决那个不确定性；持久的写回执在此模块之外。一个显式的 COMMIT 语句错误保留它稳定的错误码（例如，一个延迟外键失败的 `constraint_violation`）。一个被确认的 COMMIT 结果不会被后续的关闭错误改变。其他错误暴露稳定的码，而非 SQL 值、数据库令牌或远程错误 body。

配置的远程 URL 必须使用 HTTPS（包括规范化的 `libsql://` 与 `turso://` URL）。HTTP 重定向被禁用且响应 `base_url` 值必须匹配配置的源站；主机名被规范化且默认 HTTPS 端口在比较前被省略。数据库凭据绝不被转发到一个服务端选定的不同主机。需要跨源路由的部署在使用前需要一个显式的可信路由策略。

每个读或事务拥有一个 HTTP 客户端；事务内的请求复用该客户端。跨操作池化被推迟到 bootstrap 拥有客户端创建与关闭。远程 BLOB 结果同时接受带填充与不带填充的标准 Base64：Turso Cloud 可能省略填充。无效的 Base64 仍作为 `invalid_response` 失败。

## 验证边界

`test_workbench_table_schema.py` 针对模型创建与迁移两种 schema 演练约束、外键缺失、pending/ready 转换、团队删除，以及升级/降级行为。一个 PostgreSQL 回归在升级 Workbench schema 时保持一个 Org 更新打开，因此添加一个会阻塞迁移的外键会让测试失败。PostgreSQL CI 运行相同的测试；完整的 Alembic drift 检查也比较部署的 schema 与模型。

`test_workbench_store.py` 与 `test_workbench_store_lifecycle.py` 针对文件支持的 SQLite 与一个由真实 SQLite 事务支持 HTTP 协议 fixture 运行同一存储契约。它们演练原子回滚、参数绑定、条件写、取消，以及丢失的 COMMIT 响应。这些测试不替代针对一个配置的 Turso Cloud 数据库的集成测试。在业务集成之前，验证所选云引擎上配置好的只读令牌：一个 SELECT 必须成功且通过 `read` 的变更必须失败而不改变数据。也验证事务回滚与显式的 COMMIT 错误。测试凭据必须留在仓库文件与日志之外。
