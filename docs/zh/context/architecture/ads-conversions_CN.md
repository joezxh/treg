---
title: Google Ads 转化追踪 — 采集、outbox、上传
status: shipped
sources:
  - src/treg/adsconv.py
  - src/treg/application/signup.py
  - src/treg/web/adtrack.js
  - src/treg/web/gtag.js
  - src/treg/routers/auth.py
  - src/treg/alembic/versions/0075_ad_click_stash.py
related:
  - architecture/money.md
  - architecture/multi-tenancy.md
  - architecture/data-model.md
  - architecture/proxy-model.md
  - ops/deploy.md
---

> 范围说明：本片段是 **Google click-id** 路径（`treg_ad` → `Org.ad_*` → 转化上传）。通用流量来源归因——用于赞助链接、newsletter、目录的 `utm_*` 与 referrer——是 `web/sitetrack.js` 中独立的 `treg_utm` → `Org.utm_*` 路径，记录于 [data-model](data-model.md) 与 [api](../interface/api.md)。两者相互独立；一个带 utm 标签的 Google 广告点击会同时填充两者。

# Google Ads 转化追踪

除非 `google_ads_customer_id` 与 `ads_conv_refresh_token` 同时设置（`adsconv.enabled()`）否则关闭——让测试套件与自托管实例不会启动无法上传的机械装置。关闭时，`/adtrack.js` 是一个空的 no-cache 响应，且归因 cookie 被忽略，因此什么都不采集、排队或上传；整个功能是叠加式的。`google_ads_developer_token` 不在此门之内：Data Manager 没有 developer-token 头部，因此该设置只对读取侧 Ads catalog 调用（`oauth_providers.GOOGLE_ADS`）有意义，那是完全独立的凭据（见下）。

## 链路：采集 → 存储 → 触发 → 上传

1. **采集**（`web/adtrack.js`，一个第一方脚本）。它从 URL 读取 `gclid`/`gbraid`/`wbraid`——`gbraid`/`wbraid` 是 Google 在 iOS 流量上替换的，省略它们会静默丢弃一大部分移动转化——并把它们写入一个 `treg_ad` cookie（90 天，Google 点击归因窗口的长度；`SameSite=Lax` 因此它能存活广告点击所是的跨站顶层导航）。该 cookie 记录互斥的字段名及其值（`gclid|…`、`gbraid|…`、或 `wbraid|…`）；旧的 `CLICK_ID|landing` 形状作为遗留 GCLID 仍可读。每个页面（含已登录仪表盘）也加载 `web/gtag.js`——Google 的标签，采用 **advanced Consent Mode v2**：在附加标签脚本之前每个同意信号都作为 `denied` 排队，因此 Google 设置并读取不到任何广告 cookie，且只接收无 cookie 的 ping，正是这让它能为从未授予任何东西的访客**建模**转化（一个未加载的标签什么都不发送也不建模）。仪表盘用 `data-conversion-only` 包含它（`send_page_view: false`；Google 自己的无 cookie `ccm/collect` 同意 ping 仍无论何时都在加载时发出）并在第一个团队存在后恰好触发一个事件，`treg Signup (web)`（`AW-18392771132/0usqCIeQrO0cELzUrcJE`，动作 `7745505287`，SECONDARY 且排除在 Conversions 列之外，因此它绝不与下面的 outbox 重复计数），来自 `autoTeam()`（`frontend/src/state/onboarding.js`）在 `POST /onboard/team` 创建它之后，带 `transaction_id = treg-web-signup-<org id>` 以便重试不能把团队计数两次。未来的同意 UI 通过 `window.tregAdsConsent('granted')` 授予 cookie；没有其他东西依赖它。每个公开落地页面都必须加载 `adtrack.js`；没有测试扫描每个路由，因此一个新的落地页自己添加标签。见 `interface/seo.md` 了解逐页范围。`adtrack.js` 也在 URL 没有 click id 时恢复既有 cookie，用 `history.replaceState` 在当前 URL 上保留 id，并在委托的同源链接点击上携带它（含新链接与中键点击）。在那次访问期间它还包裹 `history.pushState`/`replaceState`，因此仪表盘重写自己的地址（例如到 `/app#start`）会为应用内浏览器的"在浏览器中打开"保留 id。外部链接、邮件链接、仅片段链接以及已携带任何 click-id 参数的链接不受影响。携带只针对当前 URL 的点击或该标签中来自更早 URL 捕获的匹配 `sessionStorage` 标记；仅 cookie 的回访不重写 URL。被屏蔽的 session storage 不妨碍直接 URL 捕获或携带。既有的 `utm_content` 约定携带原始落地值，优先于目标的 `data-page`；它只在需要保留该值才添加或替换。一个新的 URL 点击胜过 cookie。落地中的 `|` 在脚本与服务器解析器上都保留。仅恢复 cookie 不会续期其过期。`/login` 在仪表盘重定向上保留其查询，且 CLI 登录 shell 也加载捕获脚本。**短安装链接**覆盖了发生在一个广告从未触碰过的浏览器中的登录（一个 agent 的嵌入式浏览器持有自己的 cookie jar）。当 `/start` 看到 `treg_ad` cookie 时它向 `POST /i` 请求一个六字符代码（`signup.mint_ad_link`：Ephemeral 存储中哈希代码下的 cookie 归一化值，命名空间 `ad_link`，30 天，每地址每 10 分钟 30 个代码）并把复制的命令换成 `curl -fsSL {BASE}/i/<code> | sh && treg login`。`GET /i/<code>` 提供带代码模板的 `install.sh`，脚本把它留在 `~/.treg/ad-link`；`treg login` 把它作为 `/login?cli=…&ad=<code>` 发送，并在登录成功后删除文件；`/login` 兑换它（`signup.redeem_ad_link`）并在响应中设置 `treg_ad`，即脚本写入的形状，因此携带、暂存与两个注册门都不变地运行。一个代码兑换一次：第一个 `/login` 删除它，因此粘贴进 README 或 prompt 的命令不会把点击带给任何人。恢复的 cookie 存活到代码铸造后的 90 天，绝不是一个全新的 90 天，且已持有 `treg_ad` 的浏览器保留它自己的。未知的、过期的或已兑换的代码正好像 `/install.sh` 一样安装且不恢复任何东西。没有点击，或捕获关闭，意味着普通命令。CLI 绝不发送一个不是格式良好代码的值。

2. **存储**（`application.signup._ad_attribution_from`，在两个注册门读取：`register_user`（`POST /users`）与 `create_org`（`POST /orgs`），因为一个点击了广告的浏览器访客可能落到任一个）。该 cookie 被解码并持久化到新 `Org`：`ad_gclid`（历史列名，现在持有任何受支持的 click id）、`ad_click_id_type`、`ad_landing`（用例页面 slug 或 `ref`/`utm_content`）、`ad_click_at`。一旦设置，绝不覆盖——归因是"导致注册的第一个点击"，而非"最近的"。`stash_ad_click` 只在邮箱被证实后才观察有效 cookie：在成功的邮箱验证、Google 或 GitHub 回调之后。邮箱起步不暂存，因为任何人都可以在那里输入任何地址并把他们自己的点击绑到自己身上。`AdClickStash` 使用修剪、小写的邮箱作为主键（点与别名保持区分），上限并以百分号编码的 cookie 字段，以及朴素 UTC 创建/更新时间戳。一个原子的 upsert 替换先前的观察。捕获与查找随 `adsconv.enabled()` 禁用。`_ad_cookie_for` 在两个注册门只在请求 cookie 为空时回退到这个第一方暂存，且忽略超过 90 天的观察。一个在它的团队上存储了点击的注册在同一事务中删除该邮箱的行，`treg-worker admin purge-ad-clicks`（每天调度它）删除 `updated_at` 超过 90 天窗口的行，因此过期限制保留期也限制查找。此关联既不通过审计也不通过分析。暂存失败不导致登录失败；该警告省略邮箱、cookie 与异常文本（那可能包含 SQL 参数）。修订 `0075` 添加该表，没有回填或启动 schema 变更。隐私政策刻意不为 URL 携带或邮箱关联添加单独段落（一个所有者决策）；它既有的 `treg_ad` 小节即是披露。

3. **触发** — 三个堵塞点调用 `adsconv.queue(db, org, action, ...)`，它在 `SAVEPOINT`（一个嵌套事务，而非裸 flush 或 `db.rollback()`——这运行在 CALLER 的事务内，且一个重复上的普通回滚会回滚他们的工作，例如撤销一个重投 webhook 上的 Stripe 信用）内写一个 `AdConversion` outbox 行：
   - `application.signup._grant_signup_promo` 在 `ledger.grant()` 之前调用 `ACTION_SIGNUP`。
   - `api._record_first_call` → `ACTION_FIRST_CALL`，在该 org 的第一次成功 `/call/` 上。
   - `billing._credit` → `ACTION_PAID`，在该 org 第一次被贷记的 top-up 上，携带 `value_usd_micro`。
   `queue()` 在追踪关闭时、对于 demo 团队、以及——除非开启了 Leads 的增强转化（见下）——对于一个没有 `ad_gclid` 的 org 时 no-op（返回 `False`），因此默认转化侧保持仅广告归因，而它并肩的产品指标（`first_call_at`）为每个 org 设置。开启该标志时，每个有人类创建者的团队都被排队并以哈希邮箱而非 click id 标识。

4. **上传**（`adsconv.worker`，当 `adsconv.enabled()` 时从 `lifespan` 启动，每 300s 排空一次）。`drain_once` 选择到期行——既未上传也非终态、比 6 小时延迟更老，且超过 `next_attempt_at`——并把一批 POST 给 Google Ads API `uploadClickConversions`，带 `partialFailure`。载荷使用存储的 click-id 字段；一个 braid 绝不被误标为 GCLID。结果按操作索引确认：一个成功的兄弟被标记为已上传，一个失败的兄弟不被标记。`CLICK_CONVERSION_ALREADY_EXISTS` 也被确认，因为 Google 已经存储了它。HTTP 失败、批次/不可解析响应与显式瞬时的行错误以指数退避无限重试，上限 24 小时。其他索引的每行错误通过八次尝试重试，然后作为可见的死信（`failed_at` + `error`）保留该行。6 小时延迟的存在是因为 click id 可能在点击后不立即被接受；过早上传可能被拒绝。

## Leads 的增强转化：哈希邮箱标识符（2026-09-21）

没有 URL 携带或邮箱到点击关联，一个 click id 只把一次转化连接到同一个浏览器中的一次点击。YouTube in-stream 活动（24217105891）是 99.9% 的移动点击，针对一个第一步需要终端的产品，因此重要的旅程——在手机上观看或点击的前贴片、几小时后在笔记本上创建的团队——两端都没有 click id。该活动 14 天与 A$2,191 产生了零个携带 Demand Gen click id 的 org；那对点击通过是真实零，对其他一切是盲零。

`ads_conv_user_data`（默认 OFF）开启 Google 对此的答案：**Leads 的增强转化**。开启时，`queue()` 也记录没有 click id 的团队的注册/首次调用/付费行，只要该团队有一个**人类创建者**（`human_owner_emails`：按成员 id 最早的、地址不在 `AGENT_DOMAIN` 上的非 demo 成员——agent 身份不可路由且可匹配任何人，且 15% 的付费团队是 agent 持有的），且每个上传的事件携带 `userData.userIdentifiers[].emailAddress` = **归一化**地址的 SHA-256（`normalize_email`：修剪、小写，且对 gmail.com / googlemail.com 在本地部分丢弃点——Google 的规则，因为 Gmail 忽略它们）当有一个 click id 时紧挨着它，当没有时替代它。Google 把哈希与它自己已登录的账户匹配，那覆盖一个已登录 YouTube 观看者的互动观看或任意设备上的点击，无论有无广告拦截器。每个这样的事件也携带 `consent: {adUserData: CONSENT_GRANTED, adPersonalization: CONSENT_DENIED}`——Google 使用 EEA 用户标识符所需；treg 的基础是每个注册都接受的隐私政策（§07 与 Google Ads 处理者行命名这个确切披露），且个性化总是被拒绝，因为哈希是为测量而存在，绝不为受众。

邮箱在**上传**时解析（`drain_once` → `human_owner_emails`），绝不存储在行上：outbox 不持有任何地址，哈希与否。如果创建者在上传时已离开，改为上传该团队最早剩余的人类成员；一个已知的近似，因为 org 不记录创建者 id。一个既没有 click id 也没有人类成员的行以 `error = "outbox row has no attributable org: no click id and no human creator email"` 死信。一个在标志 OFF 时排空的没有 click id 的行每天停泊一次，绝不死信，因此把标志重新打开会把它上传。

**两个账户侧开关门控该标志**，都是仅 UI（API 读回它们但不能设置它们）：Ads 账户必须接受 *Customer Data Terms* 并启用 *Enhanced conversions for leads*（Goals → Conversions → Settings）。在那之前 Google 拒绝每个携带标识符的事件——2026-09-21 用 `validateOnly` 实时验证：仅点击的请求返回 200，且同一请求加 `userData` 返回 400 `events.events[0].destination_references[0]: The destination account hasn't agreed to the terms for enhanced conversions.`。该描述在 `_RETRYABLE_ROW_DESCRIPTIONS` 中，因此在点击之前排队的行保持重试（24 小时退避上限）而非在八次尝试后死信。同一探针发现任何携带 `userData` 的请求也必须携带顶层的 `"encoding": "HEX"`（`events.encoding: Required field is missing`）；`_payload_and_rows` 只在那时添加它，因此仅点击的 body 逐字节不变。

## 鉴权：一个平台凭据，而非客户的 OAuth 连接

两个不同目的曾在此被混淆，现在不再。`客户` 连接他们的 Google Ads 账户（`oauth_providers.GOOGLE_ADS`）以便他们的 agent 可以读取活动数据是一回事；**treg** 把自己的营销转化上传到自己的广告账户是另一回事。上传器不借用面向客户的 provider 或任何每 org `Secret`——它持有它自己的 PLATFORM 凭据，`settings.ads_conv_refresh_token`，由运营者通过 OAuth playground 带 scope `https://www.googleapis.com/auth/datamanager` 一次性带外获取。`_auth_headers` 直接针对 `https://oauth2.googleapis.com/token`（`grant_type=refresh_token`）交换它，用发出该 refresh token 的**同一个** client 兑换——`google_ads_client_id`/`_secret`，从读取侧 Ads OAuth client 复用而非新建一个——绝不用共享的 `google_client_id` 也绝不用客户的连接。`google_ads_customer_id` 是目标 Ads 账户。Data Manager 根本不接受 developer-token 头部也不接受 login-customer-id 头部：`google_ads_developer_token` 在这条路径上不起任何作用，且 manager（MCC）账户移入请求 BODY 作为 `destinations[].loginAccount`（`google_ads_login_customer_id`，去掉连字符）代替——仅当 manager 账户鉴权时设置；直接 client 鉴权让它未设置。（`Secret.resource_ref`，在它存在于一个无关的每 org 连接上时，绝不是此的来源——它命名一个发现的 target client，而非 manager。）

交换得到的访问令牌缓存在 `adsconv` **模块状态**（`_cached_access_token`、`_token_expires_at`）并复用直到接近它的 ~3599s 过期的 60 秒内。`worker` 每 300s 排空一次，因此大多数排空命中缓存；每遍都重新交换 refresh token 是浪费且有触发 Google 刷新速率限制的风险。`test_access_token_is_cached_and_not_re_exchanged_within_its_lifetime` 证明第二个同窗口排空产生零额外的令牌调用。一次失败的交换抛出 `RuntimeError`；`drain_once` 运行在 `worker` 的 try/except 内，因此那只是下一遍重试，而非崩溃循环。

在此重做之前，`oauth_providers.GOOGLE_ADS` 把 `datamanager` 与 `adwords` 一起携带，以便上传器可以借用客户的 OAuth 连接——但 `listing()` 向每个客户显示每个 provider，因此那把仅营销的权限无故放在每个同意屏上（`adwords` 单独经 `validateOnly` `userLists:mutate` 调用确认已覆盖受众/客户匹配写）。该 provider 回到了正好 `adwords`；`datamanager` 的 `SCOPE_LABELS` 副本保留（无害，且如果 scope 曾被真正请求则正确）。

## 幂等：outbox 的唯一约束，而非 check-then-insert

`AdConversion` 每个 `(org_id, action)` 一行（`uq_adconversion_org_action`）——这个，而非应用层检查，是让每个触发点在重试的注册或重投的 Stripe webhook 下安全的东西：`queue()` 尝试插入并把结果 `IntegrityError` 当作"已记录"，而非与并发插入竞争一个 SELECT。

## 持久的 outbox，刻意不是 audit.py 或 analytics.py

`audit.py` 与 `analytics.py` 都刻意**可丢弃**——`audit.py` 在超过其队列边界时丢弃行，`analytics.py` 设计上是有损的——因为丢失一个 `CallRecord` 或一个 PostHog 事件只损失一个指标。一个丢失的 `AdConversion` 不同：它是 Google 从未了解的转化，它用少计的数据静默地训练活动的出价，方向是让活动看起来比实际更糟。因此写是持久的（触发代码事务中的一行）且只有上传是尽力而为/重试的。`adsconv.py` 中没有任何东西经过 `audit.py`。

## `first_call_at` 不从 `CallRecord` 派生

`Org.first_call_at` 由 `api._record_first_call` 中的一个条件 `UPDATE` 设置，而非从审计表读取。`audit.py` 恰在让"首次调用"数据最有价值的负载下丢弃行——一次繁忙的发布——因此从 `CallRecord` 派生该标志会在流量最高时恰好少计。`_record_first_call` 运行在它**自己的会话**上，通过 `session_maker()` 全新打开，且绝不向 caller 的响应抛出。这是刻意的：一个更早的版本在请求自己的 `db` 会话中在结算中途提交（代理调用仍被计费）并破坏了 8 个计费测试，因为那从 `domain/money` 之外触达金钱事务——`money.md` 为账本写陈述的同一条规则在此扩展适用，即使 `adsconv.py` 自身从不碰余额。

## 原子性：三个触发点中两个与它们的事件原子，一个不是

- **`signup`** — 原子。`adsconv.queue()` 与 `ledger.grant()` 都在 `_grant_signup_promo` 中暂存，且它的一次提交在合格时把用户声明与信用连同转化一起落地。转化保持每团队，即使一个用户未验证、已声明、遗留不合格，或授予金额为零；一个转化不是已记信用余额的证据。
- **`first_call`** — 原子。`_record_first_call` 排队转化并在它自己的会话上提交一次。
- **`paid`** — **非原子**。`billing._credit` 先提交信用，然后排队 `paid` 转化并单独提交它。两次提交之间的崩溃永久丢失该转化：一个 Stripe webhook 重投找到支付已被贷记（`fresh` 为 `False`），且会排队转化的触发点再也不会运行。

  这个缺口在评审中发现，决策（2026-08-17）是**接受它并诚实地记录它**，而非重组 `domain/money` 让信用与转化成为一个事务。便宜的修复，如果该缺口在实践中曾重要：一个对拥有已贷记支付（一个 `CreditBlock`）与 `gclid` 但没有 `paid` `AdConversion` 行的 org 的对账扫描，形状如 `reconcile.py` 的其他只读报告。未构建。

## 固定 FX：1 AUD = 0.70 USD，设置 2026-08-17

`usd_micro_to_aud_micro` 以**常数**速率转换（`AUD_PER_USD_NUM=10, AUD_PER_USD_DEN=7`），刻意不是实时速率，因此报告的 ROAS 变化意味着业务移动了，而非货币市场移动了。全程整数算术（`usd_micro * 10 // 7`）——唯一允许的浮点是在 `build_payload` 的 JSON 边界，因为 Ads API 的 `conversionValue` 字段是一个线上的 double；到达它的值是来自已整数化的 micro 金额计算的，绝不反过来。outbox 存储原始的 USD 金额，绝不 AUD，因此未来的 FX 修正不需要重写历史——转换发生一次，在上传时。

## 转化配置

上传器记录 `signup`、`first_call` 与 `paid`。运营者提供他们自己的目标账户与动作配置。托管的账户 id、出价目标与验证证据位于私有的 [conversion runbook](https://github.com/superdesigndev/treg-internal/blob/main/docs/marketing/ads-conversions.md)。

## API 版本

上传器钉住 Google Ads API **v25**（`adsconv.API_VERSION`）。v21 于 2026-08-05 停止支持；该钉在 2026-08-17 跨每个硬编码版本的地方（``oauth_providers.GOOGLE_ADS``、``.agents/skills/google-ads/SKILL.md``、本仓库的 catalog yaml）移到 v25 —— 见 `architecture/auth-secrets.md` 了解完整的四处同时列表与两种失败模式说明（一个死的版本返回类型化的 `UNSUPPORTED_VERSION`，而非一个从不存在的版本返回的 HTML 404）。

## 测试：每个测试进程一个数据库

套件默认的 SQLite 文件位于 `$TMPDIR/treg-tests/`，每个测试进程一个（按 pid 命名，退出时删除），在仓库树之外以便文件监视器保持安静。因此一个 checkout 中的并发运行绝不共享一个文件。在此之前，对一个文件的两个运行在测试中途互相擦除对方的表并表现为误导性的 `no such table` 错误，那看起来像 flake。

## 未构建

- **无路由器/自动故障转移** —— 此处不适用（只有一个目标，Google Ads），但为与 catalog 其余部分一致而陈述：treg 不建模自动选择。
- **针对 `paid` 原子性缺口的对账扫描**（上）——命名为便宜的修复，未实现。
- **实时点击验证** —— 需要一个真实的广告点击，无法自动化，且在本文档落地之后、任何真实花费之前运行。
