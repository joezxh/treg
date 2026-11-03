---
title: Super-admin — 跨租户读取 + 控制
status: shipped
sources:
  - src/treg/api.py
  - src/treg/routers/admin.py
  - src/treg/application/evidence_retention.py
  - src/treg/domain/identity/access.py
  - src/treg/config.py
related:
  - architecture/multi-tenancy.md
  - interface/cli.md
---

# Super-admin（组织之上的平台视图）

其他一切都是组织作用域的；super-admin 是唯一一个能**跨所有组织**看到的能力。它刻意与组织角色分离。

## 授权（`domain.identity.access` 中的 `require_superadmin`）— 混合式
一个调用方是超级管理员，当且仅当满足**任一**条件：
- 所呈现的 `X-Treg-Token` 等于环境变量 `admin_token`（`get_settings().admin_token`，来自
  `TREG_ADMIN_TOKEN`），用 `hmac.compare_digest` 比较 → 主体 `"env-admin"`；或
- 该令牌解析为一个 `Membership`，其 `User.is_superadmin` 被设置（且未 `suspended`）→
  主体 = 该用户的邮箱。

否则 403。env 密钥用于引导；然后 `POST /admin/users/{id}/superadmin` 把该标志授予具名用户（因此一个 web 门户可以用任一种方式登录）。返回一个主体字符串（用于审计）。

该依赖位于 `domain.identity.access`，且每个消费者都从那里 import 它；过渡性的 `api.py` 再导出已随其余 stage-3 兼容表面一起退役。

**在管理主连接池上。** 该门控接受 `Depends(get_admin_session)`，由使用主库的 Handler 共享，带一个与 API 的池分开的有界池（`ops/deploy.md` § Database pools）。成功的授权在返回之前提交，释放主连接。选择加入的报告随后可以使用 `get_admin_read_session`：配置的读数据库，或在没有读 URL 时原来的管理池。两条路径都不使用 API 池。一个配置好的读库失败绝不重试主库。授权总是检查主库，因此复制延迟不会拖延暂停或权限撤销。

跨租户的读取、变更，以及对账 Handler 位于 `routers.admin` 中有序的三块中。变更块与 `routers.orgs` 共享组织删除与成员规则清理辅助函数。

## 暂停执行（在 `require_member` 中）
两个标志把门控置于**组织作用域**路径：`require_member` 在 `user.suspended`（"account suspended"）或 `org.suspended`（"org suspended"）时抛出 403。由下面的管理端点设置。超级管理员端点不受影响（它们使用 `require_superadmin`）。

## 端点（全部在 `/admin/*` 下，由 `require_superadmin` 门控）

- **反馈：** `GET /admin/feedback`（`routers.feedback.admin_feedback`）返回私有报告，按可选类别过滤，带 `limit` 与降序 ID 的 `before` 分页。它与超级管理员门控共享 `get_admin_session`。见 [feedback](feedback.md)。
- **读取：** `admin_stats`（总计、`tools_by_injector`/`tools_by_host`、`credential_health` 汇总、调用量 + 成功率、`growth` 计数——在进程内针对小结果集计算）、
  `admin_orgs`（每个 org + member/role/tool/secret/bundle 计数）、`admin_org_detail`、
  `admin_users`（+ 它们的成员关系）、`admin_tools`、`admin_calls`、`admin_share`（过去 `minutes` 内按工作：被问的请求，以及调用方按供应商得到的答案：其适配器未判定为未命中的直接调用的 2xx，以及仅一个成功路由父级最后一次尝试；`teams` 给出每个团队相同的答案：按供应商服务的团队、跨团队平均的份额，以及直接和路由的团队计数）、
  `admin_health`（非 `ok` 的 secret）。
- **失败证据：** `admin_errors`（`?days=7&limit=100&provider=&status=&tier=`）— 每个凭据层级的失败调用，包括纯自有工具（`tier: null`），带 `CallRecord.error_request` /
  `error_response`、调用方所发与供应商所答的脱敏捕获（见 [data-model](data-model.md)）。`tier` 过滤一个精确的 marketplace 层级；空值选择纯自有工具。是超级管理员而非组织管理员，因为行内持有客户的请求内容；`GET /calls` 刻意**不**暴露这些列，且它推迟它们以便甚至不被获取。该路由是只读的：证据与组织名查询使用 `get_admin_read_session` 且可能反映复制延迟。14 天保留清理（把两列清空为 `'<expired>'`）是 `treg-worker admin purge-evidence` cron（`application/evidence_retention.py`），以有界批次进行。一个超出窗口的行在 cron 触及之前就已列为 `expired` 且无证据。
- **对账（Phase 5）：** `admin_reconcile_drift|spend|repeats`（`?since_days=30`）— 跨组织对平台层级花费的聚合，因此超级管理员而非组织管理员：每个端点的价格漂移、按供应商结算的花费（发票比较），以及重复查询率。针对既有行的查询时报告；无调度器。逻辑在 `src/treg/reconcile.py`；`scripts/provider_balances.py` 是读取供应商自有余额的手工伴侣。异步任务结算报告遵循同样的超级管理员与专用管理池边界。
- **变更（Phase 2）：** `admin_set_superadmin`、`admin_suspend_user`、`admin_delete_user`（先移除成员关系，然后对任何零成员的 org 做 `cascade_delete_org`（位于 `domain/governance/teams.py`），并在任何没有所有者的 org 中**提升一个幸存者为所有者**）、`admin_suspend_org`、`admin_delete_org`（强制、跨租户）。组织删除与所有者的 `delete_org` 共享 `cascade_delete_org`（位于 `domain/governance/teams.py`）（一个级联辅助函数：tools、secrets、bundles、pending-oauth、call records、memberships，然后 org）。
- **最后超级管理员底线：** `require_superadmin` 返回主体（`"env-admin"` 或用户的邮箱）；当降级/暂停/删除会把活跃（`is_superadmin and not suspended`）用户计数降到零时，三个破坏性用户操作拒绝（`409`）——因此一个超级管理员不能把自己锁在 `/admin/*` 之外。env 令牌绕过该底线（它总能恢复）。
- **组织积分：** `admin_credit_org`（`POST /admin/orgs/{org_id}/credit`）— `scripts/manual_grant.py` 的 HTTP 等价物。通过 `money.grant()` 给一个组织发放促销余额，保留余额 = sum(blocks) - sum(holds) 的不变式。要求 `amount_usd`、`ref`（幂等键——同一 org 的重复 ref 返回 409），以及 `reason`。总是使用 `kind="promotional"` 以便积分在购买之前被消耗（不可退款的营销开销）。该脚本对离线 / 直连 DB 操作仍然有效，而该路由免去打开 Render Postgres IP 允许列表的需要。

## 模型 + 迁移
`User` 增加 `is_superadmin` + `suspended`；`Org` 增加 `suspended`（布尔值）。这些列是 Alembic 基线 schema 的一部分；一个在运行的 DB 通过显式的 `python -m treg upgrade` 发布阶段获取 schema 变更，绝不在重启时。

## CLI（`interface/cli.md`）
`treg admin login --token`（保存 env 密钥）、`admin stats|orgs|org <id>|users|tools|calls|health`、
`admin grant|revoke|suspend-user|rm-user|suspend-org|rm-org`，以及
`admin credit <org_id> --amount-usd <n> --ref <ticket> --reason <text>`。`_admin_client` 发送保存的
`admin_token`（若存在），否则发送活跃组织令牌（对一个 `is_superadmin` 用户有效）。

独立授予脚本使用配置的数据库会话且不管理托管网络访问。运营者必须使用与目标 schema 匹配的 checkout。
