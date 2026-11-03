# treg — CLI 用法

`treg` 是 **tools-registry** 的命令行客户端：调用团队共享的工具而无需持有其凭据，并把你本地的技能变成可共享的工具。它是 API（`https://treg.to`）之上的一个瘦客户端；API 才是唯一的大脑。

每条命令都读取 `~/.treg/config.json` 获取端点与你的 token。用 `treg <命令> --help` 查看单条命令的细节（例如 `treg secret --help`，而不是 `treg "secret add"`）。

## 安装（一次）

```bash
cd tools-registry
uv tool install --editable . --python 3.13     # 把 `treg` 放进 PATH，跟随开发源码
# 代码改动无需重装即生效；只有在依赖变化后才需要加 --reinstall 重跑
```

## 核心概念

**两类可调用工具，共用同一个 `/call/`。**

- **目录（catalogue）** —— 约 2,600 个精选外部端点，覆盖约 40 家数据供应商（TikTok、Instagram、
  Reddit、SEO 与 SERP 数据、画像补全、抓取等）。按**端点 id** 调用。如果团队里没人持有该供应商的密钥，treg 可以用**它自己的密钥**提供服务，按次从团队的预付费余额中扣费。无需在供应商处注册。
- **保险库（vault）** —— 你团队自己的工具。成员注册的任何 API key、OAuth 连接或厂商 CLI，都会变成所有队友及其 agent 可调用的工具，而密钥永远不会离开服务端。

保险库那半边的术语表：

- 一个 **tool（工具）** = 一个上游 `base_url` + 一组凭据**绑定**（每条绑定把一个密钥注入请求）。一个请求可以携带多条（例如 google-ads：OAuth bearer + 一个
  `developer-token` 头）。
- 一个 **skill / bundle（技能／套件）** = 一份配方（SKILL.md）+ 它的密钥 + 它的工具。
- 代理**只转发、绝不建模**上游，并且**在服务端注入认证**，所以调用方永远不持有密钥。你的 `X-Treg-Token` 在上游看到之前就被剥离了。

---

## 设置 / 身份

认证是**身份优先**的：先证明你是谁一次（GitHub 或邮箱验证码 —— 首次验证同时会注册你并创建你的个人组织），然后就可以在你的所有组织间工作。agent/CI 也可以直接出示一个按组织发放的 token。

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg` | `--json` | 不带参数：注册表、你的账号、当前团队与角色、余额、团队自有工具，以及接下来该跑的命令（`help[]`）。每一行都是尽力而为，且总是以 0 退出 |
| `treg config` | `--base-url URL` | 查看或设置端点（打印 base URL、邮箱、当前组织、是否已登录）—— 用 `treg org ls` 查看完整组织列表 |
| `treg login` | _(无)_ | GitHub 浏览器登录（注册或登录），保存一个身份 token |
| `treg login` | `--email EMAIL` | 邮箱一次性验证码登录（注册或登录）；提示输入验证码。若服务端要求进行浏览器校验，则改为在浏览器中完成登录 |
| `treg login` | `--token TOKEN` | agent/CI：直接使用一个按组织发放的 token |
| `treg logout` | — | 清除本地保存的凭据 |
| `treg onboard` | `--mode guided\|quick` · `--name N` · `--yes` · `--reset` | 绚丽的引导式首次运行 —— 选择 **guided build**（你一步步创建团队 + 邀请队友）或 **quick demo**（我们为你生成一个完整的演示团队 + 工具 + 活动记录），最后以一次无密钥调用收尾。首次登录后以 `[Y/n]` 形式询问；`--reset` 会移除演示用的队友 |

```bash
treg config --base-url https://treg.to
treg login                                 # GitHub；或者：
treg login --email you@example.com        # 邮件收到 6 位验证码（注册或登录）
```

## 团队 / 组织

一个 **org（团队）** 拥有工具与密钥。`treg login` 之后，CLI 在 `~/.treg/config.json` 中保存单个**身份 token**，并把你**当前激活的**组织作为 `X-Treg-Org` 发送；`treg org use <slug>` 用于切换。（用 `treg login --token` 时，则直接改用那个按组织发放的 token。）其他所有命令都在当前激活的组织中运行。角色：**owner > admin > member**（member 只能调用 + 管理自己创建的东西；admin/owner 可以管理组织内任何东西；admin 及以上可以邀请/移除成员）。

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg org create` | `"NAME"` | 创建新组织；你成为其 owner（新 token，自动激活） |
| `treg org ls` | — | 列出你的组织（标记当前激活的那个） |
| `treg org use` | `SLUG` | 切换当前激活的组织 |
| `treg org rename` | `--name "NAME"`，`--slug SLUG` | （admin+）重命名当前组织和/或改其 slug；已有密钥继续可用 |
| `treg org invite` | `EMAIL`，`--role member\|admin` | （admin+）创建一个一次性的邀请**码**用于分享 |
| `treg org members` | — | （admin+）列出成员与角色 |
| `treg org join` | `CODE`，`--email EMAIL` | 兑换邀请码：若你是新用户则注册，加入，并保存组织 token |

```bash
# owner 这边
treg org create "Team A"                       # 当前组织现在是 team-a
treg org invite bob@company.com --role member  # 打印出例如 inv_7Kd9x2LmQpR4 —— 发给 Bob

# Bob 这边（不会发送邮件；他通过 Slack/私聊拿到邀请码）
treg config --base-url https://treg.to
treg org join inv_7Kd9x2LmQpR4 --email bob@company.com   # 加入 + 铸造他自己的 token
treg tool ls            # 只看到 Team A 的工具
treg org use team-a     # 随时切换组织；每个组织一个 token，绝不混用
```

## 密钥（凭据 —— 只写；API 永不返回已存的值）

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg secret add NAME` | `--value V` \| `--file PATH`，`--kind env\|secret_file\|oauth\|cli_auth` | 上传一个凭据（一个字符串值，或某个文件的内容） |
| `treg secret ls` | — | 列出（名称 / 类型 / 拥有者） |
| `treg secret rm ID` | — | 删除（若有工具绑定它则被阻止） |

```bash
treg secret add posthog-key --value "$POSTHOG_API_KEY"
treg secret add gsc --file ./.secrets/token.json --kind oauth
```

## 工具

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg tool add NAME` | `--base-url URL`（必填） | 注册一个工具 |
| — 单绑定 | `--secret ID`，`--injector`，`--auth-in`，`--auth-name`，`--auth-format`，`--secret-field` | 常见情形 |
| — 多绑定（友好写法） | `--bind 'secret=ID,injector=,location=,name=,format=,secret_field='`（可重复） | 只有 `secret=` 是必填 |
| — 多绑定（原始写法） | `--binding '<json>'`（可重复） | 完整的绑定字典，进阶用法 |
| — 健康探测 | `--health '{"path":"me","expect_status":200}'` | 可选的校验探测 |
| `treg tool ls` | — | 列出工具及其绑定 |
| `treg tool rm ID` | — | 删除 |

单个 `--secret` 与每条 `--bind` 的**默认值**：
`injector=env`，`location`/`auth-in=header`，`name`/`auth-name=Authorization`，
`format`/`auth-format=Bearer {secret}`，`secret-field=access_token`。

```bash
# 单个凭据
treg tool add posthog --base-url https://us.posthog.com --secret 3
# 用 query 里的 key，而不是 bearer 头
treg tool add gsc --base-url https://searchconsole.googleapis.com --secret 3 \
  --injector oauth --secret-field token
# 一个请求上带两个凭据（google-ads）
treg tool add google-ads --base-url https://googleads.googleapis.com \
  --bind "secret=4,injector=oauth" \
  --bind "secret=5,name=developer-token,format={secret}"
```

## 目录（调用一个你没有密钥的 API）

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg catalog search` | `"你想做什么"`，`--new [DAYS]`，`--sort newest` | 按能力查找端点，用的是与 agent 相同的搜索（说出某个供应商名，如 "exa search"，可把它的工具排在前面）；`--new` 只保留最近 DAYS 天内新增的工具（不带数值时为 30，最大 365），`--sort newest` 按最新在前列出；用了任一选项时，搜索词可省略 |
| `treg catalog get` | `ENDPOINT_ID` | 文档、参数、**价格**，以及你会被如何服务 |
| `treg call ENDPOINT_ID` | `--query K=V`，`--data STR` 或 `--data @FILE` | 调用它 |
| `treg --json call ENDPOINT_ID` | 同上 | 供脚本使用：stdout 输出一行 JSON `{"result": <body>, "_treg": {http_status, call_id, charged_micro}}`，stderr 无输出 |
| `treg call ENDPOINT_ID --await` | `--timeout N`（默认 900） | 生成类调用（视频/图片）：提交、轮询供应商、打印最终响应 |
| `treg host FILE` | `--content-type T`，`--json` | 把一张参考图/音频/视频托管到一个供应商可抓取的公开 URL（30 MB，7 天 TTL，免费）；打印出的 URL 用于 `image_urls` / `audio_urls` |
| `treg catalog request` | `"缺什么"` | 搜过了但没有？提个需求 —— 需求会引导接下来补什么 |
| `treg resources list` | `--provider fishaudio --kind voice` | 在 BYOK 下列出 Fish 账号的音色，否则列出当前团队在平台上创建的音色 |

```bash
treg catalog search "instagram profile"
treg catalog search --new                            # 最近 30 天新增的工具，最新在前
treg catalog search phone --new 60                   # 最近 60 天新增的电话类工具
treg catalog get tikhub.tiktok.user.profile          # 在花钱之前就看到价格
treg call tikhub.tiktok.user.profile --query uniqueId=tiktok
```

**视频与图片生成**（`video-gen` / `image-gen` 平台）是异步任务：调用返回一个任务 id，`--await` 会轮询直到完成。stdout 只输出最终响应；stderr 得到任务 id、一条可续跑的 `treg call …` 命令、进度以及结果 URL。退出码 0 = 完成，2 = 供应商判定任务失败，3 = 超时（用打印出的命令续跑）。提交时预留费用，仅在成功时扣收；任务失败会释放预留。结果 URL 有时效（请及时下载；treg 从不存储媒体）。在编码 agent 中调用时，请调大 shell 工具的超时或把调用放后台 —— 一段视频要 1-5 分钟。`treg audit` 会显示每个任务的状态。

Fish Audio TTS 是同步的，直接返回音频字节。保持 stdout 干净并重定向：

```bash
treg call fishaudio.tts.s2-1-pro --method POST --header model=s2.1-pro \
  --data '{"text":"Hello","format":"mp3"}' > speech.mp3
```

用重复的 `--upload voices=@clip.wav` 分片加上 `treg catalog get fishaudio.voices.create` 中展示的固定私有字段来创建音色；然后用它的 id 作为 TTS 的 `reference_id`。平台创建的音色出现在 `treg resources list --provider fishaudio --kind voice` 中。在 BYOK 下，同一命令改为列出已连接的 Fish 账号。curl 调用方使用
`GET /orgs/{org_id}/provider-resources?provider=fishaudio&kind=voice`；它返回相同的归一化行，并带 `X-Treg-Resource-Source: byok|platform`。BYOK 用户也可以直接调用 Fish 原始的账号级列表。若要选用一个可复用的 Fish 官方音色，调用
`fishaudio.voices.discover` 并传 `self=false` 与显式的 `licensed=true|false`，然后把返回的 `_id` 作为 TTS 的 `reference_id`。`licensed=true` 选择 Fish 已取得权利保障的子集；
`false` 则包含更广的公开/社区音色库。在平台密钥下，treg 会在合成前校验非团队音色是否仍为公开。`treg catalog get fishaudio.tts.s2-1-pro` 会列出支持的生成、韵律、输出格式、比特率、采样率、延迟与分块控制项。

**一次目录调用是如何被服务的 —— 凭据阶梯，按顺序：**

1. 团队为该供应商注册了自己的工具 → 用那个工具、那把密钥；
2. 团队存了该供应商的密钥 → 通过虚拟工具注入；
3. 都没有 → **treg 自己的密钥**，按团队的预付费余额计量计费。

第 3 级只在 treg 同时持有该端点的密钥且公布了价格时适用；任何未定价的端点会被拒绝而不是提供服务，你会被告知去接自己的密钥。你自己的密钥永不向余额计费。

## 评价一次目录调用

`treg review <call_id> <useful|partly|not_useful|not_sure> [--reason "text"]` 在你使用过结果之后为一次目录调用打分。第一阶段只邀请那些由 treg 自有平台密钥服务的直接目录调用；被抽样的调用会在 stderr 打印一条邀请。路由调用与自有密钥的目录调用即使未被邀请也可以评价。无法确定时选 `not_sure` 即可。可选的理由在去除首尾空白后为 1-200 个字符。请勿包含私密数据与原始载荷。遇到任何令人困惑或错误的地方请用 `feedback`，然后继续任务。回执包含 `review_id` 与 `status`（`received` 或 `already_reviewed`）。
如果调用记录尚未写入，请稍后用同一个 call ID 重试。

## 反馈

`treg feedback submit <quality|pricing|friction|other> "message"` 在当前激活的团队下，向所配置的注册表提交一个问题或建议。可用时加上 `--call-id ID`（可重复）或 `--endpoint-id ID`。消息为 `-` 时从 stdin 读取一份已准备好的、脱敏的描述。该命令返回一个 `feedback_id`。请勿包含私密信息与原始请求、响应或日志。
用 `treg feedback get <feedback_id>` 取回报告。
详见 `treg feedback --help` 与你所用注册表的 `/feedback.md`。

## 余额与充值

只有跑在 **treg 密钥**上的调用（上面的第 3 级）才消耗余额。其他一切 —— 你自己的密钥、你自己的
工具、厂商 CLI —— 都不消耗它。

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg balance` | `--limit N`，`--json` | 剩余额度、在途调用、近期消费 |
| `treg topup` | | 充值，或设置自动充值 |

```bash
treg whoami                  # 账号、当前团队与你的角色、服务器
treg balance                 # 每个新团队起始有 $1.00 免费额度
treg balance --json          # 整数微美元（1e-6 USD）—— 账本使用的单位
treg topup
```

余额不足是 HTTP **402** `error: insufficient_balance`，携带 `balance_micro`、`estimated_cost_micro` 和一个 `topup_url`，
因此 agent 无需阅读任何说明文字即可据此行动。此外对 treg 密钥的消费还有按天上限，所以失控的 agent 影响范围是有界的。

如果 treg **自己**在某供应商的账号额度耗尽，计量调用会在预留任何费用之前以 HTTP **503**
`provider_capacity_unavailable` 被拒绝 —— 不产生任何扣费，响应体在已知时给出 `resets_at`，以及 `alternatives`（提供同一能力的其他供应商）。你自己的该供应商密钥永不受影响，且 treg 不会替你切换供应商。treg 约每分钟重新检查一次供应商，所以一分钟后的重试可能成功。一次刚好在 treg 账号额度耗尽时抵达供应商的调用，会按供应商的回答原样转发，并带
`X-Treg-Capacity: exhausted`；`treg call` 随后打印一条提示，说明该工具在 treg 侧不可用，而不是去透出供应商的钱包状况。

在开启了溢出中继的部署上，treg 可能改为通过一个 treg 自有的聚合账号提供**同一个端点** —— 同样的请求、同样的响应结构、中继的真实价格（0% 加价），
响应上带 `X-Treg-Served-Via: overflow:<name>`。`treg org overflow off` 让你的团队退出（此后调用会得到上面的 503）；`treg org overflow` 查看该设置。自有密钥从不被中继。

`treg org archive off` 让你的团队退出 treg 的答案归档：你的新调用既不会由已存答案应答，也不会被记入归档，因此计量调用失去重复价格（自有密钥照旧永远免费）。`treg org archive` 查看该设置；`treg org archive on` 重新加入。
团队已存的答案在团队被删除时或应请求被擦除；调用记录与异步任务完成证据照旧保留。

### 路由端点 —— 让 treg 替你挑供应商

`treg.<capability>` 端点（目前是 `treg.people.email.find`）由某个能力下适配器通过了验证的供应商生成。像其他端点一样调用：

```bash
treg call treg.people.email.find --body '{"full_name": "Patrick Collison", "domain": "stripe.com"}'
treg call treg.people.email.find --body '{"linkedin_url": "https://www.linkedin.com/in/patrickcollison"}' \
  --header "X-Treg-Route-Max-Cost: 0.05"     # 限制单次调用花费（默认上限 $1）
treg catalog get treg.people.email.find      # 带价格的排序方案 —— 不花任何钱
```

treg 运行最优的子调用 —— 先用你自己的密钥，然后是按命中计的预期最低成本 —— 并
返回 `{output, raw, _treg: {served_by, tried, charged_micro}}`，外加 `X-Treg-Served-By` 与
`X-Treg-Providers-Tried`。供应商报错会回退到下一个候选（最多两个额外候选）；厂商的 4xx 是你请求本身的问题，会停止。一次**未命中**也会尝试下一个供应商（瀑布流，默认开启），按成本从低到高，且不超过 `X-Treg-Route-Max-Cost`（默认每次调用 $1）；每次尝试按真实价格结算，按成功计费的供应商在未命中时免费。`X-Treg-Route-Waterfall: 0`
在未命中处停下。`X-Treg-Route-Prefer` / `X-Treg-Route-Exclude` 指定供应商。服务方无法应用的筛选条件会在 `X-Treg-Ignored-Filters`（以及 `_treg.ignored_filters`）中列出；`X-Treg-Route-Strict-Filters: 1` 则改为以 422 拒绝该调用（不计费）。当你传了 `domain` 且命中结果带邮箱时，`X-Treg-Domain-Match` / `_treg.domain_match` 说明邮箱域名是否匹配 —— 只提供 LinkedIn 的供应商常常返回前雇主；命中仍会计费，且地址不会被改动。厂商端点照旧逐字转发；只有 `treg.*` 这些行会建模一个 API。

`treg.people.email.find` 上的 `X-Treg-Route-Verify: true` 会在同一次调用中用 `treg.people.email.verify`
校验命中结果：先用自己的校验器密钥，然后 BounceBan，再按常规顺序。该校验是一次独立的调用、独立的费用，且计入同一个 `X-Treg-Route-Max-Cost`；`X-Treg-Cost-Micro` 是查找加校验的总和。答案会多出 `_treg.verification: {verdict, checked, served_by, cost_micro}`
（`valid` / `invalid` / `catch_all` / `risky` / `unknown`）。`checked: false` 加一个 `reason`
（`no_hit`、`over_cost_limit`、`checker_failed`、`no_checker`、`not_allowed`、`spend_limit`）表示没有跑校验，也不产生费用。未命中从不被校验：其 reason 是 `no_hit`。其他路由工具会拒绝该头（422，不计费）。

`treg.people.email.find` 上的 `X-Treg-Route-Confirm: true` 只在第二个供应商返回同一地址时才把一次命中算数。瀑布流在首次命中后继续，每次尝试按各自价格计入 `X-Treg-Route-Max-Cost`，所以一个被确认的答案通常要多花两次查找的费用。第一个地址无论如何都会返回，并带 `_treg.confirmation: {field, confirmed, confirmed_by}` 与
`X-Treg-Route-Confirmed: true|false`；当没人「同意」时，它以未确认的形式返回，而不是当作未命中。
漏过错误地址更少，代价是更高的价格与更慢的应答。它需要瀑布流：
配合 `X-Treg-Route-Waterfall: 0`，或在没有确认字段的路由工具上，该头会被拒绝（422，不计费）。一致不等于可投递：把它与 `X-Treg-Route-Verify` 结合使用，以便同时校验邮箱。

`treg.people.email.verify` 上的 `X-Treg-Route-Decisive: true` 只在答案能够定论时才算数：
`valid` 或 `invalid`。一个 `unknown`、`catch_all` 或 `risky` 的判定，或一次失败的尝试，会把校验继续交给最多两个供应商，各自按自己的价格计入 `X-Treg-Route-Max-Cost`；在部署有实测判定质量数据时按其排序，没有时按价格排序。全域接收（catch-all）域名通常是它最值钱的场景：大多数廉价校验器会拒答。答案带
`_treg.decision: {decided, decided_by, ordered_by}` 与 `X-Treg-Route-Decided: true|false`；
当没人能定论时，第一个答案原样返回。你自己的 `X-Treg-Route-Prefer` 顺序会被保留。配合 `X-Treg-Route-Waterfall: 0`，或在没有定论判定词的路由工具上，该头会被拒绝（422，不计费）。

在 `treg.people.phone.find` 上，同一个头会用 HLR Lookup 的实时网络查询
（`hlrlookup.people.phone.verify`）校验该号码：先用自己的 HLR 密钥，`usa_status` 仅对 `+1` 号码生效，且不读缓存。判定为 `live` / `dead` / `unknown`；线路可用并不能证明该号码属于这个人（`trestleiq.people.contact.verify` 会校验美国姓名）。未以国际格式书写的号码永不被发送，因为 HLR 会把开头几位当作国家码：原因为
`not_international`，不产生费用。

```bash
treg call treg.people.email.find --body '{"full_name": "Patrick Collison", "domain": "stripe.com"}' \
  --header "X-Treg-Route-Verify: true"
```

当某个路由子调用是异步的，treg 会在内部提交并轮询最多 60 秒。若仍在处理中，路由返回 HTTP 202 并带 `_treg.outcome: "pending"`、子调用引用与轮询描述符、`reserved_micro`，以及 `charged_micro: null`。该次尝试会中止瀑布流；在第一个供应商仍可能完成时启动另一个计费供应商是不安全的。

## 调用

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg call TOOL PATH` | `--method GET`，`--query K=V`（可重复），`--data STR`（或 `@PATH`、`@-`），`--file PATH` | 代理一次调用（具名形式） |
| `treg calls` | `--limit N` | 审计日志（谁在什么时候调用了哪个工具、状态如何） |

```bash
treg call intercom conversations --query per_page=5
treg call posthog api/projects --method POST --data '{"name":"x"}'
treg call dataforseo.google.keywords.volume --data @body.json   # @PATH 读文件，@- 读 stdin
```

一个看起来像 JSON 但解析不了的请求体会被拒绝而不是发出去：PowerShell 会剥掉引号内参数中的引号，所以请把请求体放进文件（`--file PATH` 或 `--data @PATH`）。带字节序标记保存的 JSON 文件（PowerShell 的 `>` 写的是 UTF-16）会作为 UTF-8 JSON 发送，并在 stderr 给出一条说明；其他任何文件都逐字节发送。传 `--content-type` 可以完全按所写内容发送请求体。

**Agent 原生（裸 HTTP）形式** —— 构造真实的上游 URL，在前面加上前缀；不需要 CLI：

```
GET https://treg.to/call/https://api.intercom.io/conversations?per_page=5
    + header:  X-Treg-Token: <your token>
```

treg 按上游 host 解析工具，注入凭据，并把其余一切
忠实转发（方法、所有查询参数含重复项、头、cookie、请求体）。

## 运行厂商 CLI

`treg call` 代理的是 **HTTP API**。`treg run` 是它的命令行补充：它运行一个**厂商
CLI**（stripe、gh、vercel、gcloud、flyctl 等），工具凭据在服务端注入，因此成员运行该 CLI
**永远不需要持有密钥或登录**。只有配方的目录 CLI 技能（例如一份 `stripe-cli` SKILL.md）会自动变为可运行 —— `treg upload` 会通过供应商目录识别它并接好凭据，所以不需要 `treg.json` 也能用 `treg run`。

工具拥有者按工具逐个选择是否允许**本地**运行（密钥会到达成员的机器）：控制台的 `⌘ run` 开关，或 `treg tool update <id> --local-run on|off`。**服务端**运行已全局禁用。工具的 `cli` 配置（`bin`、`inject`、`deny`、`enabled`）决定本地执行方式。

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg run TOOL -- <cli args>` | `--local`（默认） \| `--server`，`--timeout N`（仅 [--server]） | 以注入凭据的方式运行该工具的 CLI；`--` 之后的一切原样交给 CLI |
| `treg runs` | `--limit N` | CLI 运行审计日志（谁在什么时候运行了哪个工具、退出码） |
| `treg setup-local-run` | `--run-proof VALUE`，`--member USER` | （admin，Linux，`sudo`，一次）安装隔离的 `treg-run` 运行器 |

**两档：**

- `--local`（默认）—— 在成员**自己的机器**上运行。在 Linux 上，管理员**一次**运行 `sudo treg
  setup-local-run`，使 CLI 在一个专用的 `treg-run` 系统用户下运行，凭据永不接触成员自己的 uid；在 macOS 上是尽力而为（以成员身份运行，并给出警告）。成员可以运行其**自己拥有**密钥的工具；**共享**（队友/admin 的）密钥则需要隔离运行器**以及**服务端的 `TREG_RUN_PROOF`（安装时以 `--run-proof` 传入）。
- `--server` —— 全局禁用；`POST /run` 对所有调用方返回 503。`TREG_RUN_ALLOWED_BINS`
  无法重新启用服务端执行。

```bash
treg run stripe -- get /v1/balance          # 本地：CLI 在此运行，密钥被注入，你从不持有
treg run gh -- pr list
sudo treg setup-local-run --run-proof "$TREG_RUN_PROOF"   # Linux 管理员，一次
treg runs --limit 20
```

## 接管你自己的调用

`treg run` 覆盖厂商 **CLI**，`treg call` 覆盖你让 treg 发起的 HTTP 调用。但当一个程序自己向 `api.stripe.com` 发请求时，两者都帮不上忙 —— treg 对它而言是不可见的，而它也没有密钥。

### 常规方式：`treg <命令>`

把 `treg` 加在任何命令前面：

```bash
treg claude                  # 一个使用团队共享凭据的 Claude Code 会话
treg codex                   # Codex 同理
treg node server.js          # 你的应用，带着团队的密钥，却一个都不持有
treg python train.py
treg with -- npm test        # 显式形式，用于任何会让解析器困惑的命令
```

代理需要一个已编译的包（`cryptography`）来为本机生成证书颁发机构。`install.sh` 安装器已包含它；如果你是用纯 `pip` 安装的且缺少它，treg 会在你首次使用该功能时以适合你安装方式的方法帮你补上。

**这是按命令逐个选择加入的，而这正是重点。**treg 是父进程，所以该设置只作用于那条命令及其子进程。`treg claude` 使用团队的共享访问；而普通的
`claude` 完全不受影响，使用你自己的本地密钥。不会向任何配置文件写入东西，
因此没有需要撤销的东西，也不会有任何会话在你背后被改动。

运行期间，对**已注册**主机的 HTTPS 调用会经过注册表，由注册表**在服务端**加上凭据。其他所有地址 —— 包括你的 agent 自己对
`api.anthropic.com` 或 `api.openai.com` 的调用 —— 直接外发，我们无法读取。

如果已经有一个 `treg serve` 代理在跑，就直接用它且不去动它；否则 treg 会在操作系统选的一个端口上启动一个私有代理（这样两个会话永不冲突），并在你的命令退出时停掉它。

**如果你写 Node，有一个注意事项。**Node 内置的 `fetch` 在 **Node 24** 之前会忽略代理设置。在较老的 Node 上，纯 `fetch()` 不会被捕获，调用会在没有凭据的情况下发出。请使用会读取环境的客户端（`axios`、`got`、undici 的 `ProxyAgent`），或升级版本。curl、git、Python
`requests`/`httpx` 与 Deno 在任何版本都可用。[`examples/proxy-demo/`](examples/proxy-demo/) 里有一个可运行的示例演示了这两者，并说明了较老 Node 的变通办法。

### 子 shell：`treg shell --proxy`

`treg run` 覆盖厂商 **CLI**，`treg call` 覆盖你让 treg 发起的 HTTP 调用。但当 agent 自己写了个脚本直接跟 `api.stripe.com` 对话时，两者都帮不上忙 —— treg 对它而言是不可见的，而脚本也没有密钥。

`treg shell start --proxy` 补上了这个缺口。在那个 shell 里，对**已注册**主机的 HTTPS 调用会被路由经过注册表，由注册表**在服务端**加上凭据并原样返回厂商的回答。你的代码不需要密钥，也不需要任何 treg 特有的代码行：

```bash
treg shell start --proxy                 # 横幅会列出正在被捕获的主机
curl https://api.stripe.com/v1/balance   # 任何地方都没有密钥 —— treg 在服务端注入了它
python my_script.py                      # 脚本调用的任何东西同理
exit                                     # 代理随 shell 一起停止
```

工作原理：该 shell **仅为这个 shell** 设置 `HTTPS_PROXY` 与一份信任包，使用的是在你机器上生成的证书颁发机构（私钥 `0600`，两年有效，绝不共享）。
**系统信任库从不被修改** —— 该 shell 之外没有任何东西信任它，浏览器不会，操作系统也不会。

它**不会**碰的东西：所有非已注册工具的地址，包括你的 agent 自己对
`api.anthropic.com` 或 `api.openai.com` 的调用。那些会被隧道透传而不被读取，也永不会为它们生成证书。

| 选项 | 作用 |
|---|---|
| `--proxy` | 打开它（默认关闭） |
| `--proxy-port N` | 监听 127.0.0.1:18791 以外的地方 |
| `--renew-ca` | 启动前重新生成本机的证书颁发机构 |

### 作为后台服务（`treg serve`）

如果你更愿意保留自己的 shell 而不进入子 shell，可以把同一个代理作为服务运行：

```bash
treg serve start                  # 后台启动，并为你打印下一行
eval "$(treg serve env)"          # 把「这个」终端指向它（在其他终端里重复执行）
curl https://api.stripe.com/v1/balance
treg serve status                 # 端口、团队，以及正在被捕获的主机
eval "$(treg serve env --unset)"  # 在这个终端里停止使用它
treg serve stop                   # 停止服务
```

`treg serve start --foreground` 保持前台附着而不脱离，这正是服务管理器或查看日志（`~/.treg/proxy/serve.log`）时想要的。

一个值得知道的差别。`treg shell --proxy` 把访问 token 保存在子 shell 的环境里，两者一起消失。服务必须能被其他终端找到，所以它把端口与 token 写入 `~/.treg/proxy/proxy.json`（仅拥有者可读，模式 `0600`）。那个文件保存的是代理自己的 token，绝不是厂商密钥 —— 但它是磁盘上的一个文件，而子 shell 版本没有这个文件。请据此选择。

值得知道的限制：固定证书的客户端会拒绝这种拦截（那一个请用 `treg run` 或
`treg call`）；每个被捕获的调用都会多经过注册表一跳，所以注册表挂了它就会失败；**托管式** MCP 服务器是在别人的机器上发起调用的，因此不在覆盖范围内。如果一次调用失败了，treg 会用自己的话说明 —— 「此主机没有注册任何工具」、「去找管理员」 —— 而不是让你把裸 404 当成厂商的回答去读。

## 技能（套件）

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg skill scaffold DIR` | `--out FILE` | 走查一个技能目录 → 生成清单骨架（配方 + 发现的密钥；由你填 `base_url` + 绑定） |
| `treg skill push FILE` | — | 注册一份已完成的清单（原子化地创建套件 + 密钥 + 工具） |
| `treg skill ls` | — | 列出套件 |
| `treg skill rm ID` | — | 删除一个套件（级联删除其工具与密钥） |

```bash
treg skill scaffold ~/.claude/skills/intercom --out intercom.json
#   编辑 intercom.json：设置 base_url + 绑定
treg skill push intercom.json
```

## 批量上传（扫描 → 上传）

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg scan [env\|skills]` | `--dir D`，`--env-file F`，`--skills-dir D` | 只读预览：列出上传会注册的密钥与技能（不会有任何东西离开本机） |
| `treg upload [env\|skills]` | `--dir D`，`--select a,b` \| `--all`，`--replace`，`--no-oauth`，`--llm …` | 一次性注册一个 `.env` 里的供应商密钥和/或一个技能目录 |

```bash
treg scan                        # 本地有什么？（密钥 + 技能，只读）
treg upload --all                # 注册扫描发现的一切
treg upload env --select openai,stripe
treg upload skills --dir ~/.claude/skills --all
```

幂等 —— 随时可重跑（跳过已注册的；`--replace` 用于更新）。非交互式
（agent/CI）运行时若没有 `--all`/`--select` 会被拒绝。

## OAuth（连接流程）+ 健康

| 命令 | 选项 | 作用 |
|---|---|---|
| `treg oauth connect NAME` | `--client-secret PATH`，`--scopes S1 S2 …` | 浏览器同意 → treg 捕获第一个 token 并存为 oauth 密钥 |
| `treg connections connect --provider P` | `--key-stdin` | 基于密钥的供应商（Moz、Hunter 等）：隐藏输入提示你输入密钥，或用 `--key-stdin` 从 stdin 读取；treg 在存储前会向供应商验证它 |
| `treg health` | `--run` | 显示每个凭据的状态；`--run` 立即重新检查（刷新 oauth、探测工具、告警拥有者） |

```bash
# 一次性：把 https://treg.to/oauth/callback 加到你的 OAuth 应用的重定向 URI 中
treg oauth connect gads --client-secret ./client_secret.json \
  --scopes https://www.googleapis.com/auth/adwords
treg health --run
```

---

## OAuth：两种模式（treg 负责保持新鲜）

- **自动刷新** —— 如果 oauth 密钥带 `refresh_token` + `client_id` + `client_secret`，
  treg 会在其过期前刷新（你无需重新上传）。`oauth connect` 流程总是落在这个模式。
- **手动** —— 裸上传的 token 按原样注入；过期时由你重新上传。

存储相同；一个凭据可以从手动升级为自动，无需迁移。`treg health` 会标记任何失效的凭据并向拥有者发 webhook（如果注册时设置了 `webhook_url`）。

## 认证形态（按绑定的 `injector`）

- `env` —— 普通字符串（API key）
- `secret_file` —— 一个 JSON token 文件；取 `secret_field`
- `oauth` —— 一个 JSON OAuth token；取 `secret_field`（可刷新时自动刷新）
- `cli_auth` —— 从某个 CLI 的钥匙串中取出的材料（像字符串一样放置）

## `treg hub` —— 发布一个由工具组成的工具（在 `TREG_HUB_ENABLED` 之后）

一个 hub 工具是你的团队发布给别人的 agent 使用的工具：一份 JSON 步骤配方，或
沙箱里的一段脚本。每一步都通过你自己的工具与密钥运行；调用方支付被计量的步骤费用加上你设定的价格，而你设定的价格会作为收入计入你的余额。一经发布即可按 id `<team-slug>.<name>` 调用；分享页是 `/hub/<id>`。新工具在你将其上架之前不会出现在搜索中。

```
treg hub init <name> [--script] [--dir D]   写出这些文件：recipe.json、run.js（脚本类）、check.json、README.md
treg hub run <dir> --input k=v …            用你的 token 真跑一遍该目录；不存储任何东西；查看 trace
treg hub publish <dir>                      校验，用你的余额跑一次 check.json，通过即上线（一个新版本）
treg hub ls                                 你团队的 hub 工具、每个版本，带健康度与 30 天数据
treg hub earnings <id> [--days N] [--csv]   某个工具赚了多少，按天（仅销售；从不显示谁调用）
treg hub price <id> <usd>                   为之后的运行改价；不产生新版本；0 = 免费
treg hub retire <id>                        所有版本退出调用通路；历史与收入仍可读
treg hub list <id> · treg hub unlist <id>   申请进入目录搜索（treg 审批），或撤出
treg hub log <id> --public on|off           在分享页显示或隐藏运行日志（默认显示）
```

**上架与公开运行日志。**两者都不会产生新版本。`list` 是一次申请：treg 批准后，该工具会出现在 `treg catalog search` 与 `catalog_search` 中，标为 `hub` 并带上你的团队、
价格标签与 30 天成功率，按相关性排序且无加权。被拒会带一个理由（`treg hub ls`，以及控制台的 Listing 标签页）；再次 `list` 就是再次申请。上架归属工具本身；`unlist` 撤回它。在 recipe.json 里加上
`"capability": "<某个目录能力 id>"` 来说明你的工具做的是哪件事：一旦获批，
`treg catalog get` 在任何提供该项能力的供应商页面上都会把你的工具并列展示。新工具的
成功率从 90% 起算，按 5 次运行计，其他团队的真实运行会替换掉这个估计值。
工具一旦被上架，每个新版本与每次 `treg hub price` 都要等 treg 审核：发布应答为 `review`，调用方继续使用已批准的版本与价格，而你自己可以用 `<id>@N` 调用新版本。被拒的更新保留已批准的那个，并告诉你原因。这在
`unlist` 之后依然成立：一旦 treg 批准过某个工具，它就一直处于审核之下，而 `list` 会把它放回搜索且无需新的审核。名字读起来像 treg、像官方或已认证、或像某个目录供应商（包括形近字母）的团队不能发布。被 treg 拒绝的工具只能由其制作者的团队调用。check.json 可以放 `{"cases": [...]}`，最多 5 个样本，发布时全部执行。所有输出字段都为空的答案不支付卖家价格。未上架、
未获批、失败与已退役的工具永不出现。分享页的运行日志展示最近 20 次运行与 30 天内每天的运行次数：
时间、结果、耗时、步骤、计量单位与支付的价格，且永不显示谁调用、
输入或输出。控制台在 Hub → 某个工具 → Listing 下有同样的两个开关。

该目录还可以携带第五个文件 `data.csv`（≤ 5 MB）：脚本以 `ctx.data` 读取它。脚本可获得 `ctx.inputs`、`ctx.call(target, {method, query, body, headers})`、`ctx.charge(usd, note)`、
`ctx.csv(text)`、`ctx.data`、`ctx.log(text)`；`target` 可以是一个目录 id、你自己的某个工具（写作 `<tool>/<path>`），
或某个工具 base URL 之下的完整 URL。绝不把凭据粘贴进脚本：先注册它（`treg secret add`、`treg tool add`），在 `uses` 中列出该工具，再在 `ctx.call` 中指名它。
调用方用 `treg call <id> --data '{…}'` 运行它；用 `treg catalog get <id>` 读取其契约。

**定价。**那只是你的价格：供应商费用（目录步骤）由调用方另外支付，
而失败的运行不收任何费用。

| 类型 | recipe.json | 每次成功运行你赚得 |
|---|---|---|
| 步骤配方 | `"pricing": {"price_usd": 0.02}` | 一个固定价格 |
| 脚本 | `"pricing": {"max_price_usd": 0.05}` | run.js 中 `ctx.charge(usd, note)` 各行之和，永不超过上限 |

脚本的各行可以是一笔手续费（`ctx.charge(0.01, "fee")`）、按结果计（`rows.length * 0.002`）、
某次目录调用的加成（`r.cost_usd * 0.2`）或你自家供应商的成本。调用方在运行前就能看到上限。每个界面都会向调用方展示近期成功运行的成本，从低到高，把供应商费用与
你的价格一起列出。`treg hub price <id> <usd>` 为之后的运行设定配方的价格，或脚本的上限。

## 匿名使用统计

在使用 treg.to 时，CLI 会通过 PostHog 发送基本使用情况：命令名、成功/退出码、
耗时、CLI 版本与操作系统，并关联一个随机的本地安装 ID。它不发送命令参数、凭据、请求/响应内容、邮箱或团队标识。帮助信息与参数解析错误不被统计。统计在命令退出时最多增加 1 秒等待；
投递缓慢或离线时可能被丢弃。

用 `export TREG_TELEMETRY=0`（或 `DO_NOT_TRACK=1`）关闭它。自托管注册表默认不做统计；设置 `TREG_CLI_POSTHOG_KEY` 以及可选的 `TREG_CLI_POSTHOG_HOST` 可使用你自己的
PostHog 项目。那个随机 ID 保存在 CLI 配置文件旁的 `analytics-id` 中。
