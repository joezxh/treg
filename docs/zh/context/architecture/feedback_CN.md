---
title: Feedback - 问题与建议的私密 intake
status: shipped
sources:
  - src/treg/feedback_contract.py
  - src/treg/domain/feedback/__init__.py
  - src/treg/domain/feedback/reports.py
  - src/treg/domain/feedback/reviews.py
  - src/treg/domain/feedback/verdicts.py
  - src/treg/hints.py
  - src/treg/config.py
  - src/treg/routers/call.py
  - src/treg/application/call/invite.py
  - src/treg/infra/kv.py
  - src/treg/application/feedback.py
  - src/treg/routers/feedback.py
  - src/treg/alembic/versions/0025_feedback.py
  - src/treg/alembic/versions/0026_callreview.py
  - src/treg/alembic/versions/0030_feedback_handling.py
  - tests/test_feedback_handling_schema.py
  - src/treg/web/feedback.md
  - tests/test_feedback.py
  - tests/test_reviews.py
  - tests/test_endpoint_verdicts.py
  - tests/test_hints.py
  - tests/test_kv.py
related:
  - architecture/data-model.md
  - architecture/mcp-oauth.md
  - architecture/super-admin.md
  - interface/skill.md
  - interface/cli.md
---

# Feedback（反馈）

`FeedbackCategory` 是共享的四值词表：`quality`、`pricing`、`friction`、`other`。`FeedbackIn` 只接受 `category`、`message`（已修剪，1–2,000 字符）、可选的 `call_ids`（至多 100 个有界的、不透明引用，去重），以及可选的公开 `endpoint_id`。指引鼓励主动报告小的烦扰与观察到的摩擦，即便在成功的变通方案之后，且无需一个被证实的 bug。它引导 agent 把引用传入 `call_ids`（CLI 的 `--call-id`），而非仅散文，并在报告一次问题后继续任务。多余字段被拒绝。隐私指引要求调用方替换敏感值并省略原始负载；自由文本内容不保证匿名或自动净化。

`POST /feedback` 使用 `require_member`，包含 agent 身份与既有的公开-demo 写入限制。`application.feedback.submit` 在一个事务中提交报告与一个每团队限流命中，然后以 `feedback_id` 与 `status: received` 确认 HTTP 201。该 intake 允许每团队每小时 30 份报告。它不消耗余额、不调用供应商、也不使用尽力而为的审计写入器。存储失败不能产生一个成功确认。

`call_ids` 与 `endpoint_id` 仍是提交的声明。`verified_call_ids` 是在提交团队的 `CallRecord.call_ref` 或 `LedgerEntry.call_id` 中找到的子集；不运行跨团队查找。一个带有固定标签（`domain.governance.access.pinned_tag_predicates`）的调用方只对照携带它自己 pin 的行验证——在账本侧，只有 `reserve` 条目携带 `meta.tags`，因此那正是被固定调用方的声明所对照的行。提交的报告自身被打上调用方的 pin（`Feedback.tags`）。缺失或延迟的审计记录不会拒绝一份报告。被证实的来源不确立被报告的问题为真。Intake 不对供应商排名或调整费用。

`GET /feedback/{feedback_id}` 只把它自己的团队的报告返回；其他团队收到 404。一个固定调用方进一步收窄到携带它自己 pin 的报告，与 `/calls` 使用的同一作用域。`GET /admin/feedback` 使用 `require_superadmin` 与管理池，带分类过滤与有界的降序 ID 分页（`limit`、`before`、`next_before`）。它也返回内部归因。没有外部通知、issue 同步或公开 feed。`Feedback` 参与 `ORG_SCOPED_MODELS`，因此团队删除会移除它的报告。

CLI 的 `cmd_feedback` 把同样的 payload 发送到它配置的注册表，当 message 参数为 `-` 时从 stdin 读取一个准备好的消息（拒绝一个终端而不是阻塞）。`cmd_feedback_get` 通过同一团队作用域的 HTTP 读取检索一份报告。CLI 在本地拒绝空或超大消息，并发出结构化错误而不回显被拒绝的输入；传输失败让提交结果显式地保持未确认。团队的 `/mcp/` 用一个枚举在其输入 schema 中暴露 `feedback`，转发到同一个 HTTP intake，并声明一个非破坏性、非幂等的本地写入。`/mcp/v2/` 不暴露它：它的工具与 Claude 目录提交匹配。

`skill.md` 在其描述中提到反馈并链接到 `{BASE}/feedback.md`，由 `feedback_md` 用部署的基础 URL 提供。详细的语法与隐私指引位于那一个文档；CLI 帮助与 MCP 共享 `FEEDBACK_DESCRIPTION`。插件生成器把简短的 skill 指引传播到每个安装格式。自托管的提交停留在配置的注册表上。

## 内部处理存储

`models.py` 中的 `FeedbackHandling` 与 `FeedbackHandlingEvent`（修订 0030）把内部处理与原始 `Feedback` 分开保存。状态是每报告一行：`status`（`open`、`investigating`、`resolved`、`rejected`）、可空的 assignee 标签、版本与 UTC 更新时间。迁移不为报告回填；内部服务把缺失的状态视为 open、未分配、版本零。`(status, feedback_id)` 已建索引。

历史记录每个版本的 before/after 状态与 assignee、note、相关链接、actor、鉴权来源与 UTC 时间。`(feedback_id, version)` 唯一；数据库约束状态、正的事件版本、来源（`web` 或 `api`），以及进入一个关闭状态时的非空 note。两个表都通过 `ON DELETE CASCADE` 引用 `feedback.id`，因此删除一个报告或其团队也会移除它的内部历史。历史对 admin 角色是仅追加的，不豁免于报告的保留生命周期。

私有的 `treg-internal` admin 的处理存储是唯一运行时的写入方。它拥有原子的状态/历史事务、乐观版本检查、输入验证与窄作用域的 DB 授权。共享令牌鉴权记录 `shared-admin`，而非单个操作者的身份。本仓库只拥有模型与迁移；公开 intake、回执响应形态与调用运行时既不暴露也不使用这些表。在内部服务的授权与发布之前部署迁移。回滚该服务可以保留新表；降级 0030 会删除所有处理历史。

## 调用评审存储

`CallReview`（`callreview`，修订 0026）为每个唯一 `call_id` 保存一个评分，带团队与调用方身份、服务端归因的 endpoint/provider、可选的 `routed_via`、`invited`、请求 `client`、usefulness、可选的 reason 与创建时间。Endpoint/time 有一个复合索引。`ORG_SCOPED_MODELS` 为团队删除包含评审。评审绝不创建反馈报告。`ReviewUsefulness` 是 `useful`、`partly`、`not_useful` 或 `not_sure`；共享指引要求 agent 在使用结果之后评分并继续它的任务。

`application.feedback.submit_review` 拥有一个事务。它只在调用方团队的审计记录中查找调用引用，当它有一个 pin 时进一步收窄到调用方自己的 pin（一个外部引用是 404，而非另一个客户调用的预言机）；一个缺失的审计记录收到一个可重试的 404，包括仅账本的证据，它缺失状态/供应商/缓存归因。自有工具记录收到 400，且一个 maker 评审它自己已上架的 hub 工具也是如此（`HubTool.tool_id == endpoint_id` 在调用方的 org 中）——一个 maker 对自己工具的评审不是买家的意见。一个路由父级在存在时使用它成功的 child 的 endpoint/provider，把父级 endpoint 保留为 `routed_via`；否则它保留父级归因。`invited` 从一个 2xx、非缓存记录、带 `credential_tier == "platform"` 与当前评审采样率重新计算。路由与自有 key 的 catalog 调用仍可在未被邀请时被评审。每个面向 agent 的文本都说每次邀请一个评审：自愿的评审被接受并标记为 `invited=false`，但它们不被请求。一个评审一个批次中每个调用的 agent（在发布日生产环境见过）绝不能比一个团队权重更高，下面的已发布分数通过按团队而非按行计数来终结。重试返回原始 ID 与 `already_reviewed`；一个唯一索引也仲裁并发提交。它的 savepoint 保持打开直到 application 提交，避免 SQLite 延迟-BEGIN 的早期提交。唯一的写入方是 `domain.feedback.reviews`；被移动的 `reports` 模块保留反馈行为。

`hints.sampled(kind, sample_id)` 把 `kind:sample_id` 用 SHA-256 散列进两种 kind 相同的 64 位桶构造中。`TREG_REVIEW_SAMPLE_RATE` 与 `TREG_FEEDBACK_HINT_RATE` 是有界的 0..1 浮点，默认 0。采样在本地且在当前配置下是确定性的。采样决定哪些调用*有资格*；一个每团队预算决定一个团队实际被询问其中的多少（下一节）。因此评审行上的 `invited` 意为"已采样，故有资格"，在提交时重新计算；少数一个完整预算扣住的有资格调用在它们的 agent 自愿给出评审时计为已邀请。那个不精确是被刻意接受的：它让邀请事实保持无状态，且真实发送的邀请计数是 `hint_attached` 事件。

`POST /reviews` 使用 `require_member` 并在插入时返回 201（`review_id`、`status: received`），或在重试时返回 200。`ReviewIn` 拒绝额外字段，要求一个有界的 `CallReference` 与 usefulness 枚举，并修剪一个可选的 1–200 字符 reason 以及反馈的隐私规则。`GET /admin/reviews` 仅超级管理员可用，使用管理池，并提供带可选 `endpoint_id` 的有界降序 ID 分页。它被排除在 OpenAPI 之外；没有团队读取路由。

## 可选的评审与反馈邀请

一个决策，服务端：`application.call.invite.invitation(context, status, replayed)` 在流式响应被构建之后、在它开始流式之前，在 `routers.call.call_tool` 中运行，并返回 `review`、`feedback` 或空。路由把它写为 `X-Treg-Hint: review|feedback`（外加一个评审上较旧的 `X-Treg-Review: requested`，CLI 释放到 0.18 读取）并发出一个 `hint_attached` 分析事件，每个实际发送的邀请一个，带 `kind`、`call_id`、`endpoint_id`、调用方的 `X-Treg-Client` 与团队组。每个界面只翻译头部：普通 HTTP 调用方自己读取它，CLI 在计费行旁边为每个 kind 打印一行 stderr，团队的 `/mcp/` 把它渲染进它唯一的 hint 槽位，优先级为 replay > 402 > review > feedback。`/mcp/v2/` 没有 `review` 或 `feedback` 工具且不渲染任一邀请，如同 OpenAI 在 `/mcp/` 上的客户端；对那些调用方 `hint_attached` 计入一个 agent 从未看到的邀请。两种 MCP 传输都不对自己采样或记录任何东西。

一个**评审**邀请需要一个在 treg 自有 platform key 上服务的直接 catalog 调用（`context.marketplace` 存在且它的 `tier` 是 `platform`）、一个 2xx 状态、没有幂等重放、`context.cached == False`（服务从 `served_hit` 设置它当归档应答时）、一个已采样的调用引用，以及**预算**：`kv.store().take("review-budget:<org_id>", review_budget_per_hour, 3600)` 在一个从团队第一次邀请开始并持续一小时的窗口内计数每团队的邀请。`TREG_REVIEW_BUDGET_PER_HOUR` 默认 5。预算存在是因为每调用采样随调用量缩放：一个团队在二十分钟内 2,213 次调用在发布周以 5% 抽取了 93 个邀请，且该 agent 回答了每一个。低量团队从不达到上限，因此采样率单独设定它们的几率；高量团队最多被询问 `review_budget_per_hour` 次，无论它们命中多少端点。刻意没有每端点冷却：一个团队对一个端点的五次评分是 phase-2 加权问题，而非收集问题。路由父级与自有 key 的 catalog 调用仍可在未被邀请时被评审；一个自有工具绝不有资格，即便它的名字匹配一个 catalog 端点。

一个**反馈** hint 搭载任何其他成功的、非重放、非缓存调用（包含自有工具），以 `TREG_FEEDBACK_HINT_RATE` 采样进入。它什么也不要求，因此没有预算；一个其评审预算已耗尽的团队在采样时仍会收到它。

整个 hook 是尽力而为的：没有数据库或 body 访问，不改变调用服务的退出或写入，且任何地方的故障（含存储）只能丢失头部，绝不能丢失答案。存储是 `infra/kv.py`：Render Key Value（Redis 协议）在 `TREG_KV_URL`，或未设置时一个有界的进程内字典；两者都通过一个 `take(key, limit, ttl_s)` 应答，它是一次原子的 `INCR` + `EXPIRE NX`。共享 Redis 客户端的 socket 与连接超时默认一秒（`_TIMEOUT_S`）；URL 查询选项保留驱动的覆盖行为。计数器操作与健康 ping 保持一个独立的 200 ms 外部截止（`_OPTIONAL_TIMEOUT_S`）。路由在返回响应之前 await 采样的评审预算检查，因此这些可选检查绝不能继承更长的金钱租约预算。计数器**失败关闭（fail closed）**：一个无法应答的存储是一个已耗尽的预算，因此一次中断静默地扣住评审邀请而非淹没一个团队，且 `hint_attached` 事件降到零即是信号。`/admin/kv`（超级管理员）报告 `configured` 与 `reachable`；启动在配置的存储不应答时记录一条警告。可选的 [金钱准入](money.md#optional-admission-before-the-settlement-session) 是一个独立的租户，使用 `acquire_lease`、`renew_lease` 与 `release_lease`，带显式的争用、丢失所有权与不可用结果。它由所有者检查的 Redis 租约操作每次尝试有界在 1.5 秒（`_LEASE_ATTEMPT_TIMEOUT_S`）；续期与释放在一个共享的 2.5 秒每键预算（`_LEASE_RETRY_BUDGET_S`）内重试一次瞬时故障。获取不重试一个不可用结果：清理使用原始令牌即便 SET 回复未被观察到。续期在每次尝试前检查所有持有准入租约的最早确认过期。超时仍保持协作。本地计数器存储报告租约不可用而非声称跨进程排除。金钱准入在存储失败时回退到数据库保护，而邀请预算仍失败关闭。新租户添加窄方法，而非一个通用的 get/set 表面。

续期当确认有效性耗尽时返回 `deadline_expired`；这与存储不可用以及命令自身的超时预算都分开。

租约失败保留固定的 phase/type 计数与客户端观察到的最大经过时间在至多 21 个内存桶中。`kv.drain_lease_errors` 在每个报告窗口与 worker 退出时把这些交给既有的金钱诊断运行器一次；没有租约调用写日志或发送分析。异常消息、键、所有者令牌与存储 URL 绝不保留。见 [诊断传输与限制](data-model.md#product-analytics-writer-analyticspy)。

每个界面的服务端 `instructions` 字段也用一句话告诉 agent，在受邀调用后用 `review(call_id, usefulness, reason?)` 评分然后继续，每次邀请一个评审。MCP 服务端描述、`catalog_search` 描述、`skill.md` 与 `llms.txt` 通过 `catalog_store.headline_counts` 引用 catalog 的规模（`{ENDPOINTS}` / `{PROVIDERS}` 在 serve 时填充，以及生成时用于插件副本），绝非一个带类型的数字：六个手写副本已经漂移分开了。上游 body 未变。

配置驱动的采样器完全替代了 PostHog 标志轮询器；两个 MCP 生命周期只拥有它们的传输生命周期。附件不证明显示或读取。没有会话提醒上限或自适应采样被实现。

## 已知偏差

模型偏向 `useful`，评分常常在实际使用之前就发生，尽管有指引，且模型在如何使用该尺度上各不相同。一个分数只有在比较一个能力的兄弟端点时才有意义，因此它按端点发布且绝不按供应商汇总：一个供应商的平均值大多衡量它的工作有多难（关键词量比找一个人的电话更容易回答）。没有排名、不影响路由或 `catalog_get`、没有团队侧读取路由、也没有自适应每端点采样。

## 已发布的裁决

`domain.feedback.verdicts` 把最近 90 天的评审折叠进 `GET /catalog/platforms/{slug}` 与 `GET /catalog/providers/{service}` 作为 `reviews` 附加到端点的内容：`{teams, share: {useful, partly, not_useful}, samples}`，份额指向两个地方。`teams` 是计数落入的波段（`TEAM_BANDS`：5、10、25、50；它的下限），绝不是精确计数：在份额旁边一个精确计数会泄露一个小群体的选票，且一个从 5 变到 6 的计数会说出新团队如何投票。一个团队是每端点一票；一个团队的几次评审把它那票分裂到它给出的裁决中。这正是让自愿评审与受邀评审并排计数的原因：一个批量评分的 agent 移动它自己团队的票，而非端点的。

一个被少于五个团队评分的端点得不到 `share`：三个团队的份额是个轶事，且多一个团队会翻转标签。它确实得到它的引用，作为**早期评审**：`{teams: 0, samples}`，抽取方式与被计分的引用完全相同（每团队一个，它最新的，在团队投票的比例下，最新优先，至多三个）；只有份额被扣住。`teams: 0` 是第一个之前的波段，因此计数在这里也保持为波段。没有可引用的 reason 时，端点根本不带 `reviews`：一个没有东西可引用的早期表单什么也没说。一个 agent 对结果好或坏的说明，是页面在分数存在之前可以展示的信号，正是 Steam 页面在"评论不足以评分"下所做的。

`samples` 引用至多三个 reason，每团队至多一个（它最新的），在团队投票的比例下抽取（最大余数）而非按语气挑选，最新优先，每个带它的裁决、月份（绝不天）与评审的 `client`。一个 40 字符或更多的 reason 按原样引用，没有过滤：评审工具告诉 agent，reason 可能不带团队名被引在端点的页面上，且把私有数据排除在外。没有团队、用户或调用被识别。catalog 页面是公开的，因此引用也是；仪表盘标注该波段（"5+ 团队"，或"少于 5 团队"带中性词"Early"替代标签）。`GET /catalog/endpoints/{id}` 把同一个对象附加到端点与每个兄弟，因此 `catalog_get` 交给一个在供应商间选择的 agent 其他团队的 agent 说过什么，在 `observed` 旁边；一个兄弟携带 `teams` 与 `share`，且它的引用停留在它自己的详情。

`application.feedback.endpoint_verdicts` 在 API 池上每进程每五分钟读一次窗口。只有第一次折叠被等待（single-flight）；之后一个过期的折叠被服务，而下一个在后台任务中读取，因此没有 catalog 页面等待数据库，且一次失败的刷新为另一个完整周期保留之前的折叠。当根本没有折叠时路由不附加任何东西，因为一次富化绝不能让 catalog 宕机。

## 响应率查询

计数的分母是被 `kind = review` 的 `hint_attached` 事件：每发送的一个邀请一个，在每个界面，在预算之后。下面的 SQL 针对 `callrecord` 重放采样，因此计数*有资格*的调用；对于一个达到它预算的团队它高估了邀请并低估了响应率。当 PostHog 不可用或针对预算发布之前的窗口时使用它，并把它的结果读作一个下界。

对于 PostgreSQL，把 `:window_start`、`:window_end`、`:as_of` 绑定为朴素 UTC 时间戳，把 `:review_rate` 绑定为该窗口的配置速率。当速率改变时分割窗口：`invited` 反映提交时的速率，因此历史速率变化不能仅从那个标志重建。每个 org/引用第一个审计行构成调用队列。Child 引用包含 `:` 并被排除；重放不写一个新的调用记录。审计是尽力而为的，因此这个分母是观察到的有资格调用，而非每个邀请都被显示的证明。

分子是该队列受邀的评审行由 `:as_of` 提交，按原始调用的 `client` 分组（评审请求可能使用不同的运行时）。保持报告截止显式以允许延迟评分。这个响应率是 phase 2 的决策输入。

```sql
WITH calls AS (
  SELECT DISTINCT ON (org_id, call_ref) org_id, call_ref, client
  FROM callrecord
  WHERE created_at >= :window_start AND created_at < :window_end
    AND endpoint_id IS NOT NULL AND credential_tier = 'platform'
    AND status_code >= 200 AND status_code < 300
    AND NOT cached AND call_ref ~ '^[A-Za-z0-9_-]+$'
  ORDER BY org_id, call_ref, id
), hashed AS (
  SELECT calls.*, ('x' || substr(encode(sha256(convert_to('review:' || call_ref,
    'UTF8')), 'hex'), 1, 16))::bit(64)::bigint AS signed_bucket
  FROM calls
), invited_calls AS (
  SELECT * FROM hashed
  WHERE (CASE WHEN signed_bucket < 0
    THEN signed_bucket::numeric + 18446744073709551616
    ELSE signed_bucket::numeric END) < :review_rate * 18446744073709551616
)
SELECT c.client, count(*) AS invited_calls, count(r.id) AS invited_reviews,
       count(r.id)::numeric / NULLIF(count(*), 0) AS response_rate
FROM invited_calls c
LEFT JOIN callreview r ON r.org_id = c.org_id AND r.call_id = c.call_ref
  AND r.invited AND r.created_at <= :as_of
GROUP BY c.client ORDER BY c.client;
```
