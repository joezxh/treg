---
title: 已发布组织的并发请求准入
status: shipped
sources:
  - src/treg/infra/org_concurrency.py
  - src/treg/infra/kv.py
  - src/treg/config.py
  - src/treg/routers/call.py
  - src/treg/mcp.py
  - tests/test_org_concurrency.py
  - tests/test_org_concurrency_redis.py
related:
  - architecture/proxy-model.md
  - architecture/mcp-oauth.md
  - architecture/money.md
  - ops/deploy.md
---

# Organization concurrent-request admission（组织并发请求准入）

`routers.call.run_call_surface` 使用已发布的 `concurrency_limit.max_in_flight`，在可信的 `Caller` 解析与上下文创建之后、在 `execute_call` 能预留、进入金钱准入或调用一个供应商之前，准入一个根请求。共用该门的路由有 `/call/`、`/catalog/call/`、`/table/` 以及使用这些路由的 MCP 适配器。路由、验证、溢出（overflow）与 hub children 直接调用 application，因此它们不消耗额外的根槽位。鉴权 DB 工作仍先于该门；它不能保护身份查找免于饱和。这是一个根请求界限，而非对供应商扇出或数据库连接的界限。它适用于已配置组织的自有 key 调用，也适用于共享 key 调用，而不改变它们的计费行为。

**被排除的入口点：** 直接的 `POST /hub/run` 与 `/orgs/{org_id}/provider-resources` 请求不进入 `run_call_surface`；两者都能在此守卫之外执行供应商工作。MCP `resources_list` 工具使用 provider-resources 路由，也被排除。直接调用 `execute_call` 的 Arena/后台工作在这些被守卫的根之外。因此该设置不封顶每个 Org Web 请求或所有供应商工作。一个通过 `/call/` 的 hub 调用被它的一个根槽位覆盖，而一个直接的 `/hub/run` 调用则不是。扩展这些边界是一个独立的变更。

`org_concurrency.acquire` 在争用（contention）时立即以 HTTP 429、`Retry-After: 1`，以及 `detail.error=org_concurrency_limit` 返回。该拒绝包含有效的 `config_version`。既有的 HTTP 异常处理仍添加 `X-Treg-Error`、`X-Treg-Call-Id` 与一个审计拒绝。`mcp._call_impl` 与 `mcp._call_media_impl` 在它们的结构化结果中把该头部保留为 `retry_after`；拒绝 body 也包含整数 `retry_after_s`。Retry-After 是指导，而非对一个可用槽位的承诺。没有等待队列。一个已配置的 [Org 速率桶](org-flow-control.md) 与此槽位限制原子地检查；该拒绝既不消耗一个令牌也不消耗一个槽位。

争用发出 `org_concurrency rejected org_id=<trusted Caller.org_id> limit=<effective limit> status=429 config_version=<effective version>`。日志失败不改变拒绝。进程局部 [Org 流量日志](org-traffic.md) 把此请求包含在它们的到达/完成计数器中。

默认关闭的 [已发布流控读取器](org-flow-control.md) 返回一个有效的快照，用于暂停、速率与并发准入。一个活跃的暂停在速率/并发门之前拒绝。一个空并发字段意味着无并发限制；没有环境配置的回退。一个非空 `rate_limit` 即使并发为空时也强制执行；速率耗尽返回 HTTP 429 `org_rate_limit`，带令牌补充重试指导。

## 配置、迁移与回滚

共享流控开关默认关闭。在每个服务流量的 Web worker/实例上使用与发布者相同的 Redis 数据库。

```sh
TREG_ORG_FLOW_CONTROL_ENABLED=false
TREG_ORG_FLOW_CONTROL_REFRESH_S=2
# 在启用之前 privately 设置 TREG_KV_URL。
```

在完整的已发布配置中，使用 `"concurrency_limit":{"max_in_flight":8}` 设置一个合成限制，或使用 `"concurrency_limit":null` 移除它。限制必须是正整数，而非字符串、布尔或分数。租约（lease）是一个内部的 30 秒常量；争用重试指导是一个内部的 1 秒常量。Redis 读、初始化、命令与超时失败允许新工作在没有已确认槽位的情况下进行。没有进程局部并发回退。畸形或冲突的发布保留之前有效的快照；一个健康的缺失键清除有效的本地规则。见读取器片段了解有界刷新与缓存行为。

遗留的 `TREG_ORG_CONCURRENCY_*` 设置不再配置并发：它们的启用标志、限制、豁免、失败策略、租约与重试值不再控制此门。只有旧的重试名作为金钱准入重试下限的兼容别名保留；为那一个独立设置使用 `TREG_MONEY_ADMISSION_RETRY_AFTER_S`。没有旧并发环境值的自动转换。在授权的发布之前，一个运营者必须审查并分别批准、保存并发布一个等价的完整快照给每个预期的 Org，然后启用共享流控标志。仅保存不会激活一个快照。在部署之前审查已发布的非空速率与并发值：启用流控的 worker 会强制执行两个限制，外加暂停。一个空并发字段让并发无限制，即使遗留环境值仍存在。

实现变更本身既不发布快照也不改变运行中的部署配置；那些发布动作需要单独的授权。

要移除一个 Org 的并发限制，发布一个更高的完整配置版本，带 `concurrency_limit:null`。要禁用所有已发布的暂停、速率与并发准入，设置 `TREG_ORG_FLOW_CONTROL_ENABLED=false` 并应用正常部署流程。已准入的请求完成它们的续期/清理生命周期。不需要 key 删除或 DB 迁移。惰性的每 worker 刷新与滚动启用或禁用在进程间不是原子的；版本观察不确认每个 worker。降低一个限制在占用降到它以下之前停止新的准入；它不驱逐已接受的工作。

## 归属与生命周期

`kv.RedisStore.acquire_slot` 在没有配置速率时使用一个原子 Lua 操作；否则使用组合的速率/槽位操作。两者对每个 Org 使用相同的有序集合，跨 API key 与 worker 共享。每个请求拥有一个带 Redis 时间过期的随机令牌；脚本移除过期成员、检查基数，并只在已发布限制以下插入一个新所有者。既有的 `treg:org-concurrency:v1:<org_id>` 命名空间跨配置版本复用；一次规则更新绝不重置或替换已被占用的槽位。该键在它最新的所有者的截止时过期，因此一个更短的新的租约不能让另一个所有者的槽位过期。该命名空间与金钱的准入租约分开。当配置了速率时，脚本在插入所有者并扣减一个速率令牌之前检查两个限制。发布一个新的速率或并发版本绝不替换活跃所有者。

`Slot._renew` 每三分之一租约运行一次。`renew_slot` 只延长一个仍存活的令牌，且绝不在过期后重新创建；`release_slot` 只移除它自己的令牌。模糊的获取与取消加入有界的 Redis 尝试，并尝试所有者安全的清理。一个丢失的释放回复可能让占用保留到它的租约过期，暂时拒绝否则可准入的请求。仅槽位的获取、续期与释放有一秒的外部截止；组合的速率/槽位准入有 200 ms 截止。两条路径复用既有的 `kv.store()` 客户端。被一次成功准入消耗的速率令牌在此次清理期间不被退还，包括失败、取消或模糊的获取回复。

该槽位在 application 执行、`/table/` 转换、流传输、上游关闭，以及同步财务清理期间都保持持有。`_LeasedStreamingResponse` 也在发送错误与断连时（在 body 迭代之前）释放。清理通过重复的 task 取消与 Starlette 取消范围来接合。普通完成、异常与取消都释放同一个所有者。一个异步供应商提交在其响应与清理结束时释放它的 Web 槽位；供应商的远程作业在轮询之间不保留一个 Web 槽位。

## 租约失败限制

过期是一个无响应所有者的恢复手段，**而非请求已完成的证明**。一个进程暂停、Redis 宕机、驱逐、重启、丢失已确认写入的故障转移，或网络分区都可能让一个后继者在旧工作继续时获取。这里没有供应商/数据库围栏（fencing），因此在这些条件下不能保证严格的封顶。续期不确定性记录 `org_concurrency lease_uncertain` 并明确报告该封顶不被保证。获取/释放失败记录 `acquire_unavailable` / `release_unavailable` 而不带请求内容、凭据或所有权令牌。

已接受的工作与财务清理在租约丢失后继续；该守卫既不取消它们也不改变金钱锁、预留或结算。重试或紧急硬围栏策略需要独立的设计与批准。

`test_org_concurrency` 覆盖策略、配置、HTTP/MCP、流式与清理。`test_org_concurrency_redis` 通过 `TREG_TEST_KV_URL` 使用一次性回环 Redis，包括独立的客户端/进程、争用、过期与替换所有者安全。Redis 支持的 CI 作业包含这两个文件。不需要生产流量或凭据。
