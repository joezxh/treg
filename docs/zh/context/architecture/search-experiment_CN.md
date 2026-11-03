---
title: Discovery experiment — catalog 搜索背后的相关性裁判，按调用方下一步行为度量；服务于 agent 的工作优先答案
status: building
sources:
  - src/treg/application/catalog_search.py
  - src/treg/application/search_experiment.py
  - src/treg/domain/catalog/interleave.py
  - src/treg/infra/judge.py
  - src/treg/alembic/versions/0041_searchlog.py
  - src/treg/alembic/versions/0056_searchlog_verdict.py
  - scripts/search_experiment_report.sql
  - scripts/search_agent_bench.py
  - tests/test_search_experiment.py
  - tests/test_catalog_search.py
  - tests/test_search_agent_bench.py
related:
  - architecture/find.md
---

# Discovery experiment（发现实验）

`catalog_search` 是 token 匹配（见 [catalog — search scoring](catalog.md#search-scoring--most-words-must-match-and-the-rare-ones-decide)）。它是可复现且可解释的，且 SearchMiss 日志显示哪里不够：一个任务措辞的查询其单词是参数值（"apple stock closing prices for last year"）不放行任何东西，因为六个稀有单词必须大多匹配且其中三个命名一个 ticker 与日期范围而没有任何 catalog 行会包含；且一个单词恰好出现在无关行中的查询放行进错误的东西。两者都是语义失败。本实验把一个相关性裁判置于一个拓宽的召回之后，并询问它产生的页面是否更好——按行为度量，因为没有标签。

## 机制

三层，导入指向内部：

- **`domain/catalog/store.candidates`** — 裁判的召回：每个命中至少一个必需 token 的具体端点，词汇分数顺序，在 `search_experiment_candidates`（30）处截断。只有在这里没有任何东西在裁判答案之前展示时才敢这么宽松。路由父级被排除并由 `with_routed_parents`（与 `search` 共享）放回，因此被裁决的页面正好如基线那样转向 `treg.<capability>`。
- **`infra/judge.py`** — TypeSafe 的 System One API（Jev）。一个请求携带查询与每个候选作为 `state`，且每个候选一个 Noul 问题；答案是每行一个概率。它绝不抛出：超时、非 200、畸形 body 都返回 `probs=None` 带原因，且调用方服务基线。一个每个后续请求也会遇到的拒绝（401、402 无信用、403）是一个基线页面隐藏的中断，因此它以 ERROR 记录，到达错误追踪：每十分钟每状态至多一次。答案按（model、query、候选 id，以及任何 criteria 或额外问题）在进程内缓存。一个调用方可以给每个候选问题附加 Noul `criteria` 并添加关于同一状态的 `extra` 问题，Noul（一个概率）或 Choice（选项、它的置信度与每个选项的概率）；一个 `job_view` 形状的候选被问及整个 job，在 `job_criteria` 下（[find](find.md)）。实验不传递这些，因此它的问句与缓存键在运行期间不变。
- **`application/catalog_search.py`** — MCP `catalog_search` 在两个界面背后的搜索用例：已发布的秩排序器的页面（`store.rank_band` 在一个比页面更宽的带上、`store.rerank` 证据重排、按分数合并的已列出 hub 工具、路由组、截断到页面），然后实验对它的发言权，然后记录（`audit.record_search` 当实验开启时，`record_search_miss` 每当 LEXICAL 页面为空时）。hub 读取持有它自己的会话并在任何裁判请求之前关闭它。MCP 层解析谁在询问并塑造行。
- **`application/search_experiment.py`** — 实验。裁决候选，用与基线相同的收尾步骤构建被裁决的页面（证据重排、路由分组、截断到页面——用例传入该函数），对调用方发一个臂，决定展示什么，并交回一行给 `audit.record_search`。

被裁决的页面是**分桶的，而非按概率排序**：在 `search_judge_keep`（0.4）之下的行被丢弃，在 `search_judge_high`（0.7）或之上的行排第一，且在一个桶内保留词汇顺序——因此词汇上平行的行仍精确平局且 `store.rerank` 的证据桶保留它们的发言权。在到达调用方之前剥离通过分数优先重排分离桶的提升。

## 模式与臂

一个设置，`search_experiment`，也是杀死开关：

| mode | 谁看到什么 | 为什么 |
|---|---|---|
| `off`（默认） | 已发布的秩排序器，不变；这里什么都不运行 | |
| `shadow` | 基线；两个页面都被计算并记录 | 页面多久不同一次、生产环境中的裁判延迟与成本，以及对后来调用的反事实读取——在任一调用方看到改变的页面之前 |
| `interleave` | 大多数调用方：两个页面的团队草稿合并；两个保留（`search_experiment_holdout_percent` 每个）：一个纯基线页面与一个纯被裁决页面 | 合并廉价地给出成对偏好；纯臂给出绝对转化与延迟成本 |
| `v2` | 大多数调用方：工作优先答案（下）；同样的两种保留：纯基线页面与纯 v1 被裁决页面 | v2 针对它替换的东西与已发布的秩排序器读取；基线页面上的保留调用方仍有 v2 计算并记录，因此一个 `none` v2 本会给的被读取针对该调用方用词汇页面做了什么 |

臂按**调用方**发：按团队与登录邮箱（搜索解析它们时，`identity_key`），否则按 bearer 令牌的加盐哈希（`caller_key`）。一个 OAuth 授权的令牌每小时轮换；按令牌发，该调用方会随它改变臂。`search_experiment_salt` 重新发。一个未配置的裁判（`typesafe_api_key` 为空）让每个模式行为如 `off`。

**交织**（`domain/catalog/interleave.py`）是团队草稿：每轮一枚硬币决定谁先选，每边加入它最高排名但还不在页面上的行。分析时的信用只去到页面**分歧**处——一个只有一页携带的行，或它们排名不同的（更高排名胜）；两页都携带同排名的行是平局且对谁都不作证。两个页面相同的查询因此贡献零，这正确：裁判在那里什么也没改变。页面分歧的查询份额是 shadow 周报告的第一个数字，且低份额意味着赢得少与意味着收敛慢一样多。

## 工作优先答案，服务于 agent（`v2`）

`/catalog/find` 背后的引擎（[find](find.md)：按工作与按含义召回，一次带平台 Choice 的裁判请求，九条规则，一个合适 job 的每个供应商）在 `v2` 模式回答一个 agent 的搜索。`application/catalog_search.py` 在 agent 的预算下运行 `catalog_find.recall_with_meaning` 与 `answer_v2`（`typesafe_timeout_s` 给裁判，`find_embed_timeout_s` 给查询的向量），然后为一个页面布局答案（`agent_page`）：

- **按 job 的行，round-robin 发牌。** 答案的组（`expand_groups`：每个保留单位一个，一个 job 的供应商按证据顺序；一个名字页面的行按 job）是页面的组。一个被裁决的答案保留它最好的 `page_groups` job，每两行一个（八行页面上四个：在 agent 的搜索上度量，每页更少 job 提升被调用的行在上面的几率，更多提升它的 job 在上面的几率，且每两行一个把两者都保持在接近最佳）；页面取每个组的第一行，然后第二行，直到 `limit`，并按 job 连续布局它们。在一个 job 内，裁判独立评在 `search_judge_high` 或之上的成员领导（它自己的单词匹配查询限定词的供应商，证据顺序会把它埋在截断之外），然后是证据顺序。一个路由父级（`store.routed_parent`）当路由发现开启时领导它 job 的组（仅 strong 与 closest 答案；一个名字页面是该名字提供的）。一个其能力是一个保留 job 的已列出 hub 工具没有词汇门控地加入该组；没有加入空页面。
- **一行说什么。** `job`（它的能力）与，在一个 job 的第一行上，`more_providers`：该页面遗漏的该 job 的供应商（`expand` 的折叠加截断；同一 `hidden` 字段一个词汇路由组在截断子行上计数）。`score` 为 null：没有概率到达 agent。`jobs` 列出页面的 job 带它们的供应商计数与显示的行。
- **agent 看到的裁决。** `strong`、`closest` 与 `name` 如 find 给它们的，带一个只说下一步做什么的 `hint`（事实在 `jobs` 与行上）：对于一个合适的 job，在它有路由行处对其 `catalog_get`，否则对它的第一行，它列出做该 job 的其他。一个 catalog **缺口** 的 `none` 被作为一个空页面带 `reason: gap` 与一个提交 `catalog_request` 的 hint 服务，没有近似命中（其建议，删一个词并重试，是相反的）：那是一个停止 agent 重查询的答案。当裁判命名任务需要的平台时，hint 命名它：catalog 有 Threads，不是发布到它。"不是一个任务"不作为 `none` 服务：一个 agent 的输入总是意味着什么且该规则在人的查询上确定，因此 `decide` 在那里被问及 `keyword`（`not_task`），且词汇页面在它之下服务（记录 `keyword:not_task`）。一个弃权的裁判（`keyword:<它的错误>`）、一个失败的答案、或一个超过每调用方上限的调用方也服务词汇页面为 `keyword`。
- **每调用方上限。** 一个搜索不被计量，因此 `search_judge_max_per_caller_hour`（一个 `ratestore` 窗口在 `catalog_search` 下）是循环中的 agent 能在裁判上花费的唯一边界。它在 `v2` 模式中任何裁判之前守卫每个发出的调用方，按谁在调用方（团队与邮箱）；搜索不能解析的调用方共享一个桶，因为该工具读 catalog 而不验证每团队令牌且一个捏造的令牌否则每次搜索都是一个新的上限。开放的 HTTP 路由（`/catalog/search?engine=agent`，CLI 的搜索）知道调用方的地址，因此那里一个未解析的调用方按地址上限（`ip:<address>`）：一个脚本不能花费每个签出调用方的裁判。过去它该小时的搜索是词汇页面，记录 `keyword:rate_limited`。hub 读取、调用方查找与上限各自在裁判被调用之前打开并关闭它们自己的会话；路由自己的会话绝不被使用，且一个失败的调用方查找作为未解析搜索。

HTTP 路由与 CLI 仍从已发布的秩排序器回答；一旦路由的 hub 读取在裁判调用期间不持有会话且 CLI 发送它的令牌，它们就跟随。

## 记录什么

`SearchLog`（迁移 0041）— 当模式不是 `off` 时每个 MCP 搜索一行：查询、来源、调用方的团队与邮箱、模式、臂、基线页面、带概率的被裁决页面、服务的页面带每行的所有者、词汇匹配计数（`baseline_total`，0 = 门不放行任何东西——召回层）、页面是否分歧，以及裁判的延迟、tokens 与错误。每个 `shown` 中的服务行携带它的 job 作为第三个元素（`[id, owner, job]`，在每种模式下），因此报告可以把一次调用归功于页面显示的 job 的任何供应商。在 `v2` 模式臂是 `v2`、`baseline` 或 `judged`；一个 v2 行（臂 `v2`，以及 `baseline` 臂，针对反事实）也携带 find 的 v2 读取与 `verdict`（0055、0056：冒号后的原因，`none:gap`、`keyword:not_task`），且 `judged` 是保留的单位。通过 `audit.record_search` 即发即忘写；丢弃的行花费一个样本。

不同于 `SearchMiss`，该行携带身份：结果是调用方后来的 `call`（`CallRecord.org_id` + `user_email`），且一个匿名行没有结果可连接。因此 HTTP 搜索路由**不在**实验中——它是开放且匿名的。在 v1 模式中 `SearchMiss` 仍在**词汇**页面为空时写入，无论被裁决页面找到了什么：该日志度量已发布的秩排序器的覆盖率并供给 `aliases.yaml`，且一个被裁决命中是实验的结果，不是停止记录缺口的理由。一个服务的 v2 答案当一个缺口时记录一个 miss（`reason: gap`，`engine: v2`），或当它的关键词回退是一个空词汇页面时（`reason: not_task` 那是为什么）；词汇覆盖率在 `SearchLog.baseline_total` 保持可读。

同样的事实去 PostHog 作为 `catalog_search_judged`（不同 id = 调用方键）用于仪表盘。该管道按设计有损（`analytics.py`）；决定实验的数字从数据库读取。

## 读取它

`scripts/search_experiment_report.sql`（Postgres，只读；`-v mode=` 选择它读取其臂的模式）把 `searchlog` 按团队 + 邮箱在搜索后十分钟内连接到 `callrecord`，在服务的页面上的端点上：

1. 每臂的量与健康——分歧份额、空基线份额、裁判错误率、p50/p95 裁判延迟、tokens；
2. 每臂转化，**按**空 vs 非空基线分层（召回增益与排名增益是不同的主张）；2b，对于 `v2` 模式，按**job**每臂转化与裁决，其中对页面显示的 job 的任何供应商的调用计数（一个 v2 hint 把 agent 送到那里，在页面上或不在），且 `baseline` 臂的裁决是 v2 的反事实读取，因此一个仍转化的 `none` 是一个直接读取的假 none；2c，在一个 `none` 之后，调用方是否调用了任何东西；
3. 交织信用与分歧规则与二项 z；
4. 每臂与裁决的重查询率——两分钟内第二次搜索且之间无调用是一个没做好它工作的页面；一个告诉 agent 停止的答案降低它无论对错，因此它随 2c 读取。

量在很大程度是几个重调用方的，且没有块按调用方聚类它的错误；臂之间的小差异带着那被读取。

在一条规则改变到达 agent 之前，`scripts/search_agent_bench.py` 离线针对 agent 做出的搜索与它们接下来调用的东西（从该日志提取的 JSONL，保存在仓库之外）为 v2 答案打分：每带标签的案例被调用的端点是否做页面显示的 job 的一个（`job-hit`，主要数字：一个 v2 页面按 measured success 列出一个 job 的供应商并把 agent 送到其余），hit@limit，以及**假 none**，一个 caller 确实调用了某物时的缺口答案，按臂；加上每案例的裁决分布、tokens 与延迟。标签只能命名调用方被展示的，因此它比较的词汇与 v1 被裁决页面被偏袒且 v2 的数字是一个下界。

## 服务于人：为某项工作找工具

`GET /catalog/find` 是这个机制，另一端是人：仪表盘的 Catalog 框与公开的 `/search` 页面，匿名、速率限制、流式、且可切换到按工作召回（`find_engine`）。见 [find](find.md)。它的 v2 引擎是 `v2` 模式服务于 agent 的东西（上）；`/catalog/search` 从已发布的秩排序器回答。

## 护栏与刻意不在这里的

- 裁判最多给一次搜索加 `typesafe_timeout_s`（2.5 s）且绝不能让它失败。30 个候选的实时答案度量 1.2–1.5 s 与约 4.5k 输入 tokens；shadow 周从 `judge_ms` 读取真实分布。Shadow 模式仍在回答前 await 裁判，因此它的延迟成本与实时臂相同——一个非阻塞 shadow 是可能的后续。
- 面向 agent 的响应不携带裁判的概率，在任何模式。暴露它会改变 agent 选择方式并把实验变成另一个不同的实验。一个 v2 答案的裁决是一个词，且它的 hint 说用它做什么。
- 页面长度在每个臂中相同，因此"更多选项"不能伪装成"更好选项"。
- 一个最近添加的搜索（`added_within_days` 或 `sort=newest`，catalog.md 的 "`added`"）不是实验的一部分：`added_page` 无裁判无记录地服务它。没有那些输入 `catalog_search` 正好如之前运行实验。
- 这里没有东西触碰 `/call/`、金钱、或 HTTP 搜索路由（`/catalog/find` 是它自己的路由）。路由发现开关（`routed_discovery`）通过共享收尾函数应用于被裁决页面。
- 尚未构建：除了报告脚本外 `SearchMiss` 的读取路径、catalog 发现之外裁判的任何使用，以及把一个人接下来做的事归功于 `/catalog/find` 答案。
