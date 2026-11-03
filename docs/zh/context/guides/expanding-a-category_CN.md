---
title: 扩展一个目录分类 — 添加供应商的 playbook
status: guide
sources:
  - src/treg/oauth_providers.py
  - src/treg/domain/connections/authorization.py
  - src/treg/domain/connections/oauth_flow.py
  - src/treg/infra/oauth_exchange.py
  - src/treg/application/connect.py
  - src/treg/routers/connections.py
  - src/treg/config.py
related:
  - architecture/auth-secrets.md
  - interface/api.md
---

# 扩展一个目录分类（添加供应商）

我们如何把 **SEO**、**Enrichment** 与 **Advertising** 从寥寥几个条目各自增长到十个——之后 Enrichment 又一次性增加八个供应商（2026-08-20：companyenrich、oceanio、tomba、predictleads、findymail、branddev、icypeas、leadsforge）。这是可重复的过程——每当某个分类需要更多供应商时就照此执行。Creator/influencer 数据（influencers.club，2026-08-21）是第一个端到端在供应商上架 skill 下添加的供应商：注册表 + 15 端点的目录，每个价格都对照供应商自己的计费表核对过。

供应商定义与安装元数据位于 **`oauth_providers.py`**（`OAuthProvider` 条目的 `REGISTRY`）。可复用的授权与同意规则位于 `domain/connections`，token 端点的 I/O 位于 `infra/oauth_exchange.py`。连接、验证，以及自动开通一个粘贴密钥的供应商是 **`connect_with_token`**（`POST /connections/token`），位于 `routers.connections`，由 `application.connect` 支撑。这些部分记录在 [auth-secrets](../architecture/auth-secrets.md) + [api](../interface/api.md)；本片段讲的是*过程*，而非机制参考。

MillionVerifier（2026-09-08）走这条密钥供应商路径：`query` `api` 鉴权，用 HTTP-200 的 `error` 拒绝做免费额度探测，两个单主机目录作业，以及一个既有的邮件验证适配器。批量主机使用不同的鉴权参数，在 surface map 中被显式排除。实时额度证据与定价上限见 [catalog](../architecture/catalog.md)。

QuickEnrich（2026-09-08）走密钥供应商路径，使用 Bearer 鉴权与一个免费的、已认证的 Contact Finder 探测。全部六个数据工具与五个查询工具都做了实时检查；按月订阅容量使用 API 余额数据，与平台列表定价分开。测试扩展了既有的鉴权、容量与 marketplace 文件。见 [catalog](../architecture/catalog.md)。

## 两类供应商
- **API-key**（`auth_kind="key"`）— 用户粘贴一个密钥；自助式；**快路径**（研究 → 实现 → 实时测试在一个会话内完成）。这是主力，几乎全部增长都发生在这里。
- **OAuth**（`auth_kind="oauth"`）— treg 持有它自己注册的 app；**重**（需要 dev-app 注册 + 客户端凭据）。以**未配置（unconfigured）**条目添加（在本部署设置凭据之前它们列出 `configured:false`）。
- **token**（Slack）— 自带 bot token；通过 `uses_pasted_secret` 共享粘贴密钥路径。

## 快路径 — 添加一个 API-key 供应商

1. **策展（Curate）。** 挑选能填补该分类*空白*的供应商（而非近似重复）。使用下面的筛选启发式。一个研究子代理是合适的工具：把候选池 + 标准交给它，让它带着理由推荐 + 拒绝。
2. **获取每个供应商的精确规格** — `base_url`、鉴权（location / name / format）、一个**便宜或免费的探测端点**（有效密钥返回 200，无效密钥则**不**返回）、以及**坏密钥行为**（状态码，或标示无效的 JSON 字段）。`base_url` + 探测路径 + 坏密钥行为的准确性最为重要，因为你要**实时**验证它们。让研究代理说"unconfirmed"而不是去猜一个路径。
3. **添加注册表条目** — 在 `oauth_providers.py` 中加一个 `OAuthProvider(auth_kind="key", …)`；把它加入 `REGISTRY` 元组；如果分类是新的，把它加入 `CATEGORY_ORDER`。密钥供应商 `scopes={}`（无同意屏）；目录卡片使用 `summary`。
4. **占位 logo** — `web/logos/<service>.svg`（一个字母标；之后换成官方品牌 SVG）。缺少它的话保护测试 `test_every_provider_has_a_logo` 会失败。请勿复制真实品牌标识——中性的字母标才是占位符。
5. **测试** — 把 id 加入 `test_every_provider_is_registered`（test_oauth_providers_m3）以及 test_key_providers 中的可供给（offerable）循环。
6. **实时垃圾密钥测试 — 承载性的一步。** 启动服务，用一把*垃圾*密钥对着**真实** API `POST /connections/token`：
   - `422` "rejected …" → 正确（坏密钥被拒绝）。发布它。
   - `200` → 探测**没有**验证密钥 → 修复 verify（见工具箱），或丢弃该供应商。
   - `404`/`502` 在原因里 → 探测路径/主机错误 → 修复 `base_url`/`probe_path`。
   这单独一步就抓出了 Apollo（`is_logged_in`）、Akta（尾部斜杠）、Majestic（`Code`）、ScrapeCreators（接受任意密钥）。**绝不要发布一个你没亲眼看到它拒绝过垃圾密钥的密钥供应商。** 在一次性 org 中运行，之后删除它（测试用户是 `e2e-…@treg.local`）。
7. **运行测试套件，[同步文档](../../../.agents/skills/tools-registry-context/MAINTAINING.md)，提交 + 推送。**

## 验证工具箱 — 坏密钥行为对应哪个 `OAuthProvider` 字段

| 供应商行为 | 要设置的字段 | 真实示例 |
|---|---|---|
| 密钥在请求头中 | `token_header` + `token_format`（`Bearer {secret}` / `{secret}` / `Token {secret}`） | TikHub、Apollo、SE Ranking |
| 密钥在查询字符串中 | `token_location="query"` + `token_param` | Semrush、Diffbot、SpyFu |
| 密钥在 JSON 请求体中 | `token_location="json"` + `token_param`（JSON 字段名） | Adyntel `api_key` |
| 由 `login:password` 组成的 HTTP Basic | `token_format="Basic {secret}"` + `token_encode="base64"` | DataForSEO、Moz |
| `Basic ` 后跟一个 RAW token 的 HTTP Basic | `token_format="Basic {secret}"`，**不**加 `token_encode` | The Companies API |
| 在**不同主机**上最便宜的检查 | `probe_url`（绝对地址） | Semrush（余额主机）、Diffbot（账户主机） |
| 探测需要一个 POST body | `probe_method="POST"` + `probe_json` | Serpstat、Moz、Coresignal |
| 完全没有免费路径——最便宜的付费调用就是探测 | 在最便宜的缓存调用上 `probe_method="POST"` + `probe_json`；在 `setup_note` 中说明价格 | Exa `/contents`（针对 example.com，$0.001；`/v0/teams/me` 对每个密钥都 404，2026-08-27） |
| 坏密钥时返回 200；一个真值字段 = 有效 | `token_verify_field` | Slack `ok`、Apollo `is_logged_in` |
| 坏密钥时返回 200；某字段 == 某值 = 有效 | `token_ok_field` + `token_ok_value` | Majestic `Code=="OK"` |
| 坏密钥时返回 200；存在一个错误对象 = 无效 | `token_reject_field` | Serpstat `error` |
| 坏密钥时返回 200；一个 `ERROR …` 文本 body | 自动处理（文本错误守卫） | Semrush |
| 无免费探测；有效密钥在空 body 时 400，无效 401 | `probe_reject_statuses=(401,403)` | Coresignal |
| 供应商**自己的**"测试我的鉴权"端点对坏密钥也返回 200 带散文 | 改探测一个 DATA 端点 | Tiingo `/api/test`（2026-08-14；`/tiingo/daily/aapl` 干净地 403） |
| 坏密钥 302 重定向到一个 HTML 登录页（一个只在该被问时才说 JSON 的 Laravel 应用） | `probe_reject_statuses=(302, 401, 403)` **加上** 重定向所缺的 body 字段上的 `token_verify_field` | Findymail `/credits` → `email`（2026-08-20） |
| 两个头部凭据，都是每用户，且一个免费探测仅凭密钥即可应答 | `extra_credential_label`/`extra_credential_header`，`extra_credential_setting` 为空（用户通过 `POST /connections/{id}/extra-credential` 绑定另一半）；探测仅含密钥的路由 | Tomba `X-Tomba-Key` + `X-Tomba-Secret`，探测 `/v1/usage`（2026-08-20） |
| 两个凭据，但都不在头部传输 | `extra_credential_location`/`extra_credential_param`（query 或 JSON），与上面相同的配对流程 | Adyntel：key + `extra_credential_label="Account email"`，两者 `location="json"` |
| 两个凭据都在**同一个 JSON body** 中，且 API 无法仅凭密钥验证 | `token_location="json"` + `extra_credential_location="json"`，再加上针对探测"不完整配对"状态的 `probe_deferred_statuses`——connect 步骤以 `health_status="unknown"` 而非 pass/fail 存储密钥，待第二个凭据补齐后验证完成 | Adyntel `api_key` + `email`，探测 `POST /facebook` 在 email 提供前一直回答 `422` |
| 两个凭据，但 API 也接受标准 HTTP Basic `a:b` | 一个粘贴的 `key:token` 对，`token_format="Basic {secret}"` + `token_encode="base64"`——无需第二个槽位 | PredictLeads `api_key:api_token`（2026-08-20） |
| 一个对任意请求都返回 200 的第二主机（demo/免费层） | 固定到会拒绝的主机 | CoinGecko demo 主机（2026-08-14） |
| 在每个端点都接受任意密钥，包括付费端点 | **丢弃——无法发布** | Alpha Vantage（2026-08-14：`apikey=bogus123` 返回了真实行情数据） |
| 持续的工具健康检查 | `probe_path`（对 `base_url` 的一个便宜 GET） | 大多数 |

connect 验证仅在响应*是* JSON 时才解析 JSON（所以 CSV/文本 body 不会报错），默认按 HTTP 状态拒绝。

## 常见陷阱（来自真实供应商的 RCA）
- **坏密钥时 200。** 状态码在说谎；读一个 body 字段（`token_verify_field` / `token_ok_field`）。Apollo、Majestic。
- **尾部斜杠 307 重定向。** 我们不会带着密钥跟随重定向，所以只看到 307。把尾部斜杠放进 `probe_path`，这样它命中干净的 401。Akta。
- **CSV / 文本响应。** 不要做 JSON 解析；验证按 content-type 守卫。Semrush。
- **密钥在 URL PATH 中**（`/v3/{key}/…`）。我们的注入器只做 header/query——**不支持**。跳过该供应商（或加一个 path 注入器）。Adbeat。
- **无免费探测。** POST 一个空 body；有效密钥 400，无效 401 → `probe_reject_statuses=(401,403)`。Coresignal。
- **API 接受任意密钥**（对垃圾值返回成功）。你无法在 connect 时验证——**丢弃它**；不要发布一个密钥无法被检查的供应商。ScrapeCreators。
- **最便宜的检查在主机外** → `probe_url`。Semrush、Diffbot。
- **一个仍计费的网关 504。** influencers.club（2026-08-21）用 nginx 60s 上限挡在慢速增广前面：对一个 handle 的首次调用花了 54–61s，有几个以 504 HTML 页面返回，而后端还是跑完了——其中两个 504 被计费，一个没有。把它记录在目录文件头部（重试一次，2–5s 内出热答案）而不是把路由标记为 `unverified`；并给 `catalog_verify.py` 对超时的路由做第二遍，而不是放宽其超时。
- **Django 尾部斜杠。** influencers.club 无斜杠的路径以丢弃 body 的 301 返回；Akta 的修复（斜杠放入 `probe_path`）也适用于每个目录 `path`。
- **一个跨平台供应商需要自己的 platform slug。** influencers.club 通过一个 `platform` body 字段在 11 个网络中的任意一个上增广一个 handle，因此没有任何单一社交 slug 是诚实的；它得到了一个 Enrichment 货架上的 `creators` 平台（2026-08-21）。平台不能从供应商文件提出——把 slug 加入 `capabilities.yaml`，只提 capability。

## 筛选启发式（什么让一个供应商值得添加）
- **自助式 API-key 优先** — 注册、拿密钥，无需销售电话。这就是全部的速优势；任何销售把门的都会破坏快路径。
- **独特价值** — 填补该分类缺失的空白（电话、批量数据、知识图谱、技术栈、GDPR 邮件……）。跳过近似重复。
- **可靠性 / 合法性。** 果断地、*并带着记录的理由*拒绝：法律/关停风险（Proxycurl——2025 年 7 月被 LinkedIn 起诉关停）、已废弃/被吞并（Clearbit → HubSpot 把门）、只有 UI 没有 API（BigSpy/AdSpy）、企业销售把门（SimilarWeb、SensorTower、MediaRadar）。
- **自助式字段往往很薄**（尤其是广告——只有约 4 个真正的自助式广告情报 API）。当不存在 N 个干净选择时，**如实说明**，并用一个相邻但干净的备选（SerpApi 用于广告）或一个未配置的 OAuth 平台来凑数——不要强行塞入一个不匹配的供应商。

## 重路径 — 添加一个 OAuth 供应商

一个逻辑供应商可以有不止一个显式授权。使用 `authorization_methods`，配合 capability 归属与协议覆盖；不要复制供应商目录。把所选方法存储在 pending 流程与 secret 上。添加端点授权元数据，以便目录解析在比较共享的上游主机之前，先按供应商与授权身份选择。Instagram 直接 Login 加可选的 Facebook Page 工具是参考实现；见 [instagram-oauth](../architecture/instagram-oauth.md)。
1. treg 必须在该网络上注册它**自己**的 dev app → `client_id`/`client_secret` → 把这两个设置加入 `config.py`（`Settings`）以便从 env 加载；注册表条目通过 `client_id_setting`/`client_secret_setting` 引用它们。
2. 添加 `OAuthProvider`，带 `auth_uri`/`token_uri`/`scopes`/`base_url`/`token_endpoint_auth_method`，为每个 scope 一个 **`SCOPE_LABELS` 条目**（由 `test_every_requested_scope_has_a_label` 守卫），以及一个 logo。`write` 必须是 `read` 的超集（`test_default_capability_is_the_broadest`）——或只用一个 capability。
3. 未设置凭据 → 它列出 `configured:false`，因此**安全地以未配置方式添加**以达标数量；设置凭据后它即激活。
4. **怪癖（全部快照到 `PendingOAuth` 上）**：`extra_credential_*`（用于第二个头部，Google Ads / Microsoft Ads 的 `DeveloperToken`）、`auth_params={}`（用于拒绝 `access_type` 的非 Google 供应商）、`client_id_param`（TikTok 的 `app_id`/`client_key`）、`scope_separator`、`pkce`、`long_lived_exchange`、`token_endpoint_auth_method="client_secret_basic"`（X、Pinterest——**也**持久化进 token blob，使刷新说同一种方言）、`extra_tools`（用于把一个产品拆分到多个主机的供应商：GA4 的 admin/data 拆分——每个额外主机在同一 secret 上开通一个配套 Tool；通用的 `_backfill_provider_extra_tools` 发布升级流程会自动给既有连接补上新增的配套），以及
   `resource_example`，用于在用户选定其资源后把一个现成的调用盖到工具上。
5. **非标准 OAuth 不是免费的。** TikTok Ads（`app_id`/`auth_code`、JSON body token 交换、`code==0` 信封、`Access-Token` 头部而非 `Authorization: Bearer`）无法用标准的共享连接流程或 Bearer 自动开通绑定工作。把它作为**带标记的占位符**添加——在能运行之前它需要协议适配器与绑定工作。

## 对每个新供应商设卡的测试
- `test_every_provider_is_registered` — 加入 id。
- `test_every_provider_has_a_logo` — 加入 `web/logos/<id>.svg`。
- `test_default_capability_is_the_broadest` — OAuth：`write ⊇ read`（或单一 capability）。
- `test_every_requested_scope_has_a_label` — 每个 OAuth scope 一个 `SCOPE_LABELS` 条目（密钥供应商没有）。
- `test_key_providers` — 针对 `auth_kind="key"` 的可供给 + connect 流程覆盖。

ContactOut 走同样的粘贴密钥路径，使用 `token` 头部鉴权与一个免费的 `/v1/stats` 探测。它的垃圾 token 拒绝与有效连接都经过实时验证；其独立资源池保持信息性，监控与充值由指定的账户经理管理。
