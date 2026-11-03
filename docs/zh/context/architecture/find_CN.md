---
title: Find tools for a job - /catalog/find, 按工作召回并做一次裁判请求
status: building
sources:
  - src/treg/application/catalog_find.py
  - src/treg/domain/catalog/find_recall.py
  - src/treg/application/find_index.py
  - src/treg/infra/embed.py
  - src/treg/bootstrap.py
  - tests/test_find_index.py
  - tests/test_embed.py
  - src/treg/alembic/versions/0055_find_v2_log.py
  - src/treg/alembic/versions/0056_searchlog_verdict.py
  - scripts/find_bench.py
  - tests/fixtures/find_bench.yaml
  - tests/test_find_bench.py
  - tests/test_find_recall.py
  - tests/test_catalog_find.py
  - tests/test_search_queries.py
  - tests/fixtures/search_queries.yaml
  - frontend/src/state/find.js
  - frontend/src/components/FindAnswer.vue
  - frontend/src/pages/SearchPage.vue
  - frontend/src/components/CatalogSearch.vue
  - frontend/e2e/catalog-find.spec.ts
related:
  - architecture/search-experiment.md
  - architecture/catalog.md
  - interface/dashboard.md
---

# Find tools for a job（为某项工作找工具）

`GET /catalog/find?q=`（`application/catalog_find.py`）回答一个描述他们想做什么的人：仪表盘的 Catalog 搜索框（敲击 Enter，或输入停顿）以及公开的 `/search` 页面。它是发现实验的机制（[search-experiment](search-experiment.md)：一个宽松的召回，由一次 `infra.judge` 请求裁决，以 `search_judge_keep` / `search_judge_high` 分桶）并服务于人。下面的 v2 引擎也以实验的 `v2` 模式回答 MCP `catalog_search`，由 `application/catalog_search.py` 为 agent 布局（[search-experiment](search-experiment.md)）；`/catalog/search` 回答来自已发布的秩排序器（或，用 `engine=agent`，CLI 的搜索，与 MCP 相同的用例）。这里没有东西触碰 `store.search` 的打分或证据重排；两者只共享 `store.provider_focus`，即读取查询中命名的供应商（下）。

## 两个引擎，一个开关

`find_engine` 选择答案，也是发布与回滚：

| 值 | 服务 | 记录 |
|---|---|---|
| `v1`（默认） | 端点召回（下） | 一行 `SearchLog`，`engine=v1` |
| `v2` | 按工作召回（下） | 一行，`engine=v2` |
| `shadow` | v1 | 两者：v2 在 v1 旁运行，它的裁判请求并行，且绝不到达页面 |

两者流式传输相同的两个 NDJSON 事件——召回一算好就发 `candidates`，裁判一回答就发 `judged`——因此页面在第一个事件上动画化等待。裁判弃权而非失败；一个明确的供应商名仍打开该供应商的工具，而其他弃权回退到关键词页面（`store.rank_band`，25 行，未裁决，verdict `keyword`）。`admit` 速率限制每 IP 与每部署通过 `ratestore` 在一个会话提交并在调用裁判前关闭，且证据读取（下）发生在裁判回答之后：没有请求在 Jev 思考时持有一个连接。

## v1：端点召回

`store.candidates`（每个命中一个必需 token 的具体端点，字典序，在 `find_candidates` 处截断）由一次裁判请求读取；一个候选问题携带 `FIT_CRITERIA`，其 `false` 侧包含"该任务只命名了一个产品、公司或平台"，且同一请求多问一个 Noul，文本是否仅仅是一个名字。裁决：`strong`（一行在 high 或之上）、`closest`（被保留的行，无 strong）、`none`、`keyword`，或 `name`（无 strong 匹配且裁判读到一个名字，或它恰好是一个平台的名字：其 label 包含它的平台，否则一个供应商的端点，未裁决）。

它的弱点是单位。一个由三十个供应商售卖的工作要么花掉裁判三十个座位要么一个都不花，且页面只列出字典序恰好到达的供应商。

## v2：按工作召回

`domain/catalog/find_recall.py`，纯函数，每个 `Catalog` 构建一次并缓存在其上（`Catalog._find_index`，`_search_fields` 模式）。三种单位：

- **job**：一个能力。它的卡片是该 id 的单词、描述、平台的 label 以及成员们常用的名字。一个单位携带每个供应商。
- **representative**：一个成员端点，其自身卡片在某些渠道中得分高于它的 job。独立裁决：供应商的措辞比 job 的更接近查询，因此该 job 可能不是它所做的（一个个人邮箱 finder 归档在 work email 下）。一个单供应商 job 没有 representative。一个做了另一项工作的成员的长期修复是它自己的能力。
- **uncatalogued endpoint**：无能力；它自己的单位。

只有浏览界面（`store.browsable`，无路由父级，无暂停供应商：`store.paused`，见 catalog.md § Paused providers）。一个第一方端点可能共享它能力的 id，因此索引把 job（`job_pos`）与端点（`pos`）分开。

**渠道。** 一个词汇渠道用其卡片作为整个单词持有的每个查询单词的 idf 为每个单位打分：折叠（NFKD，去重音，保留 CJK）、丢弃停用词与单字母、轻度词干提取（一个动词的各种形式一致，"scraping" 与 "scrape"）、`aliases.yaml` 短语在它们所有单词都匹配时匹配、命名一个平台的单词计双倍。一个平台由它整个名字作为 token 序列命名，来自它的 slug 单词与它的 label 的短形式，最长优先（"tiktok ads library" 命名 TikTok Ads，而非 TikTok；"search console clicks" 命名 Search Console）。一个五个字母或更多字母的单词也可能是一个单词的前缀，位于一个单位 id、平台或供应商名字中，权重减半（"scrap" 启动每个 Scrapecreators 行）。一个语义渠道用其卡片向量与查询的余弦为每个单位打分（下），且对一个向量不在那里的查询关闭。每个渠道对一个 job 跨其成员取最大池并记录哪个成员胜出；平局归于自身卡片得分更高的单位，因此一个常见单词不会让仅仅有一个成员提到它的 job 占座。

**融合与座位。** 每个渠道的前 300 个按倒数秩（reciprocal rank，k=60）融合：词汇渠道只接纳有命中的单位，语义渠道接纳它最相似的 300 个无论符号，因此一个没有任何卡片上单词的查询仍按含义填满它的座位。座位：查询命名的供应商上的 job 最先（`find_platform_seats` 每个），然后是它命名的平台上的 job（`find_platform_seats` 每个），然后最好的 job 到 `find_jobs`，然后那些 job 按融合顺序的 representative（`find_delta`），然后未编目的端点（`find_raw`）。`?platform=` 保留一个货架的单位。

**裁判。** 一个请求（`judge_v2`）：一个 job 读取 `infra.judge.job_view`（id、描述、平台、供应商计数、几个名字）并被问及做该 job 的工具是否完成任务，在 `JOB_CRITERIA` 下；一个端点保留 v1 的问题与视图。两个额外问题顺便带上：v1 的 name Noul，以及一个货架外的 Choice 覆盖平台加 `none`（`platform_question`）。绝不第二次模型请求；Choice 只分类并记录。一个没有单位的召回仍发送两个额外问题（一个仅额外请求），因此一个空召回被区分成 catalog 缺口或非任务，而非默认到 `not_task`。

**名字表**（`find_recall.name_of`）是字符串查找，因为名字是查找而非裁决：一个平台（恰好它的名字或 slug，与其他匹配该名字的并列列出：精确优先，然后一个名字以查询开头的，然后货架的特色顺序，然后最多 job；或从四个字母起，一个平台名字的精确前缀——唯一匹配，或唯一一个其自身名字被查询开始但不作为它整个单词的平台："instagra" 是 Instagram 尽管 Meta Ads 的 label 提到 Instagram），否则一个供应商（它的名字在任何长度精确，"exa"；或从四个字母起，恰好一个供应商名字的前缀），否则一个产品或模型名。几个平台或供应商共享的一个单词（"video"、"search"、"ads"、"goog"）不命名它们任何一个，且被裁决的答案读取它。产品名来自 `AI generation` 平台上的端点名字：那些名字共享的两个或更多单词且其他地方很少使用的名字（"gemini"、"seedance"、"flux"；不是 "image"），或在单端点平台上，它名字中其他名字不使用的单词（"jev"），减去 `aliases.yaml` 的键（"tts" 是说一个 job 的方式而非产品），以及它们相邻的成对（"nano banana"），匹配时空格与连字符折叠掉。在一个货架上只有那里的供应商计数。

**一个带任务的供应商命名**（`Focus`，来自 `store.provider_focus`）："exa search"、"people data labs company enrichment"。一个供应商由它的 id 或它整个显示名作为 token 序列命名，最长优先，在功能词被丢弃之前匹配：一个域是名字的一部分（"you.com"、"apollo.io"），而单独的 "you" 或 "context" 是一个单词。一个作为平台名字的名字（"tiktok"）命名该平台，而仅由短或功能词组成的（"x"）不命名任何东西。查询的其余部分是召回、语义渠道与裁判读取的，因此名字自身的单词（"people"）不能把答案拉到另一个 job；该供应商的 job 取前排座位，它的未编目端点排第一，且在页面上它的行领导每个 job（绝不折叠掉），它的 job 领导页面且没有一个路由行领导（调用方选择了该供应商）。focus 仅在该供应商的一行匹配其余的一个单词时成立（`store.provider_focus`，关键词页面自身的决策，因此两个页面不能分歧）："does perplexity mention my brand" 是关于该 AI 引擎的问题，按原样读取。一个裸名字是名字表的。

## v2：语义渠道

`application/find_index.py` 为每个 catalog 持有一个 float32 矩阵，每行一个单位，且 `infra/embed.py` 是 OpenAI 兼容的 `/embeddings` 客户端（`find_embed_url`，默认 OpenRouter；`find_embed_model`，`voyageai/voyage-4-lite`）。每次 find：查询的向量（按模型与折叠文本在进程内缓存一小时，`find_embed_timeout_s`）、一次矩阵乘积，且 `recall` 把它与词汇渠道融合。该客户端绝不抛出：超时、非 200、畸形 body 或错误大小的向量是一个 `embed_error`，且 find 继续走词汇。

构建从进程开始（`warm`，每个角色生命周期的一个后台任务，随它取消；catalog 的解析与索引的构建在事件循环外运行），或从那里未完成时，从 catalog 上的第一个 v2 find 开始；find 在它完成前以词汇方式回答。每个卡片的向量从归档的对象存储下以 `find-vectors/<model slug>/<sha256 of the card>` 读取，只有缺失的卡片被嵌入（96 的批次），且那些被写回。存储在其他地方是内容寻址的；这些命名对象是唯一的例外，它们的名字由 treg 从已验证的 slug 与摘要构建，且每个 body 携带自身的卡片哈希与大小（`MAGIC`、`dim`、hash、floats）而非内容检查。一个瞬态失败的批次（超时、429、5xx）在构建放弃前以短退避再试两次；一个被拒绝的 key 或错误大小的向量不被重试。无存储时向量仅存于进程；无 API 时渠道保持关闭且失败的构建在五分钟后重试。一个新模型是一个新前缀，因此两个模型的向量绝不混合，且另一个大小的缓存向量不被使用。无锁：两个实例构建相同的新的卡片都嵌入它们。构建不持有数据库连接。

键是 `find_embed_api_key`；与 OpenRouter URL 一起留空时，使用 treg 自有的 OpenRouter key（`platform_key_openrouter`）。numpy（the `[server]` extra）做矩阵乘积。

## v2：裁决

`decide`，第一个成立的规则：

| # | 条件 | verdict |
|---|---|---|
| 1 | 裁判弃权 | `keyword`，原因为裁判的错误 |
| 2 | 查询恰好是一个名字，或一个名字的前缀且名字 p >= `find_name_min` | `name`（名字胜过 strong） |
| 3 | 无 strong 匹配，至多三个单词，名字表匹配 | `name`（一个输入的词缀） |
| 4 | 无 strong 匹配，名字 p >= `find_name_min`，无名字匹配，什么都没保留 | `none`，原因 `gap` |
| 5 | 平台 Choice 是 `none` 且置信度 >= `find_gap_min` | 低于 0.6 的顶部：`none`，`gap`；否则 `closest`，绝不 strong |
| 6 | 在 high 或之上的匹配 | `strong` |
| 7 | 在 keep 或之上的匹配 | `closest` |
| 8 | 什么都没保留，平台 Choice 命名一个置信度 >= `find_gap_min` 的平台 | `none`，原因 `gap`：catalog 有该平台，不是该 job 在它上面（发布到 Threads，而只列出读取它） |
| 9 | 否则 | `none`，原因 `not_task`（`decide` 的 `not_task` 命名该 verdict：一个 agent 的搜索请求 `keyword`，[search-experiment](search-experiment.md)） |

规则 5 位于 strong 规则之前：一个自信的"没有平台提供这个"封顶答案。在一个货架上（`?platform=`）不询问平台 Choice 且任何 `none` 是原因 `scope`：该 find 读取一个货架，因此它不能说什么 catalog 缺少，且其 SearchMiss 行说 `scope`。

**行**（`expand_groups`，每个保留单位一个组；`expand` 展平它们）。单位最好优先。一个在 high 或之上的 job 列出每个供应商，在证据重排的顺序中（`store.rerank`： measured success、core、price），每行携带该 job 的 fit 与 `fit_from: job`；页面把一个 job 显示为带其供应商计数的一行，因此没有供应商被截断。一个在 keep 与 high 之间的 job 按供应商折叠：它的前五个供应商每个一行，且 `children_hidden` 在它的第一行上计数该 job 不在页面上的其他供应商（因此"30 个中的 4 个"加到裁判被展示的供应商计数）。一个在 keep 或之上的端点单位是它自己的行带它自己的 fit，`fit_from: endpoint`；一个独立裁决的成员在它自身的 fit 在 keep 之下时把它自己的 fit 保留在它的 job 内并被排除。一个名字的页面（`name_page`）是命名的平台的端点以及该名字也匹配的（12 个平台，每个 40 行）、一个供应商的，或每个端点按平台携带该产品名，job 优先，未裁决。证据（每个端点的 measured success）仅由路由的 `EndpointObservationReader` 为 strong 或 closest 答案读取，在裁判之后。

**事件。** 第一个 `candidates` 事件是词汇召回，在查询被嵌入之前发送，因此它保持即时；当查询的向量改变读取的内容时，第二个 `candidates` 事件携带融合的单位（页面只是替换列表），且 `judged.read` 计数那些。它获得 `units: [{kind, id}]`（它的 `candidates` 列表是单位到达的每个端点，因此页面点亮正确的平台与供应商）；`judged` 获得 `reason`（在 `none` 上）、`platform: {choice, confidence}`、`engine: "v2"`，且行获得 `fit_from` 与 `children_hidden`。`named` 是 `platform`、`provider` 或 `product`。

## 记录什么

`SearchLog`（模式 `find`，来源 `web-find`，无身份）带 `engine`；v2 也写 `verdict`（冒号后的原因：`none:gap`）、`platform_choice`、`platform_conf`、`name_p`、`recall_ms`，以及 `units` 为 `[kind, id, p]`；`baseline_ids` 是单位到达的每个端点，`judged` 是保留的单位。`embed_ms` 与 `embed_error` 记录查询的向量（无 key 为 `off`，卡片向量构建时为 `not_ready`，否则为客户端的原因）。`judged` 事件携带与 `embed: {ms, error}` 相同的东西。`SearchMiss` 获得 `reason`（`gap`、`not_task`、`judge_off` 对一个空关键词回退、`scope` 对一个货架的 `none`）与 `engine`。只有被服务的引擎记录一个 miss：在 `shadow` 中 v1 记录，且 v2 的空答案只在它的 SearchLog 行中显示，因此一个 find 绝不在 miss 中被计数两次。迁移 0055 与 0056。通过 `audit` 即发即忘，如同那里的每一行。

## 页面

`state/find.js` 从答案保留 `reason` 并随 `search_answered` 发送 `engine`、`reason` 与 `platform_choice`。一个 job 组的 fit 说它来自哪里（`findFitTitle`），它的供应商计数说"30 个中的 4 个"当服务器折叠其余时（`findProvidersText`），且 `/search`（把供应商布局为卡片）为每个折叠的 job 添加一行带到其货架上完整列表的方式。一个空答案说它是哪种：一个缺口（"treg 还没有这种数据或动作"），带一个请求链接，或不是一个 job（"尝试描述你想要的数据"），不带链接。在一个货架上一个空答案是一行，"<platform> 中没有…"，带"搜索所有工具"（`findEverywhere`）：Catalog 页面，它的框持有相同的单词，非作用域地询问。一个货架绝不提供一个请求，因为它不能知道该工具缺失。

Catalog 框在输入在至少两个字符上暂停时自己询问；该答案位于仍被过滤的货架之上，因此一个正在输入的姓名既过滤又被回答，且当读不到或找不到时收缩为一行。Enter 仍请求完整答案（见 [dashboard](../interface/dashboard.md)）。

## 度量它

`scripts/find_bench.py` 针对带标签的查询为一个引擎打分：一个针对单位与能力 id 的黄金正则表达式、可接受的 verdict、以及对于一个名字它必须命名什么。`recall` 层什么都不调用（黄金单位是否在候选中；黄金 job 的供应商候选到达多少）；`judge` 层运行整个答案并报告按层级的 verdict 准确度、假 strong、假 none、top-1 与 MRR、tokens、延迟与**job 覆盖率**——一个有两个或更多供应商的黄金 job，页面显示多少（micro、macro、完全覆盖）。覆盖率是第一数字：它衡量一个人得到什么。裁判答案按（model、query、单位 id、问题）在磁盘上缓存，带它们花费的延迟与 tokens 实时，且查询向量在它们旁边，`--baseline` 逐一比较两个运行，`--engine v2` 在设置了嵌入 key 时先构建卡片向量（缓存在 `<cache>/find-vectors/` 下），且 `--engine logged` 对 JSONL 案例的 find 日志记录的打分。CI 在合成 `tests/fixtures/find_bench.yaml` 上运行 recall 层；一个不再匹配 catalog 的标签停止运行。带标签的真实查询位于本仓库之外，且在规则被确定的集合上的分数乐观。

## 不在这里

- 无生成的卡片扩展、仓库中无向量、进程中无加载的模型。
- 每次 find 无第二次模型请求，且不向 agent 展示概率。
