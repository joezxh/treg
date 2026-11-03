# Treg（工具的 OpenRouter）

![treg — 你的 agent 的工具目录](docs/assets/treg-hero.png)

**OpenRouter，只不过对象从模型换成了 agent 工具。** 给 agent 一个 base URL、一个 token，它就能干活：**一份精选目录，覆盖多家供应商的成千上万个端点** —— SEO 与外链、社交与趋势、人物与公司画像补全、广告、抓取、图片与视频生成 —— **按次计费，最低一美分起**，
无需在供应商处注册。再加上你团队自己的密钥、技能与 CLI，每位队友的 agent 都能调用，而凭据永远不会离开服务端。

**说出任务，而不是工具。** 你不需要知道哪家厂商卖外链数据，也不需要在他们那里开户。搜索你想做的事，看一眼价格，直接调用。

为 Superdesign 团队构建，线上服务在 [treg.to](https://treg.to) —— 任何人都可以自托管。

## 为什么会有它

agent 干活所需的工具，大多藏在没人会为了一次运行而购买的订阅后面 ——
Semrush $139/月、Moz $99/月、Crunchbase $99/月、Apollo $59/席位 —— 藏在注册墙后面，或者干脆没有公开 API（邀请制、合作伙伴制、需应用审核）。treg 持有这些账号，并按每次调用几分钱计费。

## 两类工具，一个 token

- **目录（catalog）** —— treg 可以用自己的密钥提供服务、或通过已验证的公共路由（无需供应商密钥）提供的外部端点。使用自有密钥的调用消耗团队的预付费余额；匿名调用免费。无需在供应商处开户。新验证账号在创建合格团队时可获得**一次性 $1.00 赠送金**。
- **你自己的工具** —— 队友注册的任何东西：付费 API 账号、OAuth 连接、厂商 CLI、一份 `SKILL.md`。**你自己的密钥永远优先于 treg 的，且这些调用从不计量计费。**

后半部分的术语表：

- **tool（工具）** = 注册表用组织凭据替你调用的东西。两种：
  - **endpoint（端点）** —— 一个上游 `base_url` + 凭据**绑定**（每条绑定把一个密钥注入请求；一个请求可以携带多条，例如同时注入 OAuth bearer *和* `developer-token` 头）。
  - **CLI** —— 在注入凭据后运行的厂商二进制文件（`stripe`、`gh`、`vercel` 等）。
- **skill / bundle（技能／套件）** = 一份配方（`SKILL.md`）+ 它的密钥 + 它的工具，一起注册。

**唯一规则：**代理**只转发、绝不建模**上游，并且**在服务端注入认证** —— 因此上游 API 改动不会波及调用方，调用方也永远不持有密钥。

---

# 第一部分 · 使用注册表

访问 [**treg.to**](https://treg.to)（托管在 Render）—— 控制台、
登录以及下面所有 URL 都在那里。

## 快速开始

与控制台**入门指南**相同的流程：

```bash
# 1. 安装 CLI —— 同时把它指向注册表
curl -fsSL https://treg.to/install.sh | sh

# 2. 登录（默认 GitHub · --email 用一次性验证码 · --token 给 agent/CI 用）
treg login

# 3. 立刻干点有用的事 —— 无需密钥，无需注册任何东西
treg catalog search "backlinks for a domain"     # 按工具「能做什么」来找
treg call tikhub.tiktok.user.profile --query uniqueId=tiktok
treg balance                                     # 看看刚才花了多少

# （或者用 `treg onboard` 走引导式演示）
```

Fish Audio 提供 S2.1 Pro 语音合成、公开音色发现与私有音色克隆。
语音是二进制 stdout，所以要重定向到文件。发现的音色的 `_id` 或团队音色 id 就是 TTS 的 `reference_id`；在 treg 的 Fish 账号上创建的音色是持久的团队资源：

```bash
treg call fishaudio.tts.s2-1-pro --method POST --header model=s2.1-pro \
  --data '{"text":"Hello from treg","format":"mp3"}' > speech.mp3
treg call fishaudio.voices.discover --query self=false --query licensed=false --query language=en
treg resources list --provider fishaudio --kind voice
```

使用你自己的 Fish 密钥时，请求仍然是不受限制、不计量的上游转发，账号边界由 Fish 自己掌握。

目录工具的输入由 `treg catalog get <id>` 描述。标有 `strict_query` 的工具会拒绝未声明或重复的查询参数、不支持的取值以及请求体。

你的 token 在每次调用时标识你的身份（`X-Treg-Token` 头），且对所有工具都相同。
查看团队共享了什么：`treg tool ls` · 检查凭据健康度：`treg health`。

### 或者作为 Claude Code 插件安装

```
/plugin marketplace add superdesigndev/treg
/plugin install treg@treg
```

无需 token、无需配置即可安装 treg 技能与 treg 的工具。运行 `/mcp`，选择 treg 并登录；之后工具就会出现。其他 agent：`npx skills add superdesigndev/treg -s treg`
（其余见[工作流技能](#工作流技能)）。
参见 [docs/CLAUDE-PLUGIN.md](docs/CLAUDE-PLUGIN.md)。MiniMax Code / MiniMax Agent 用户：同一份技能也通过 MiniMax 插件市场提供（[docs/MINIMAX-PLUGIN.md](docs/MINIMAX-PLUGIN.md)）。

### 工作流技能

开箱即用的配方，你的 agent 端到端执行，每一次调用都走 treg：

| 技能 | 你的 agent 能做什么 |
|---|---|
| [`treg`](skills/treg/SKILL.md) | 查找并调用目录中的任何工具，以及你自己的工具 |
| [`web-access`](skills/web-access/SKILL.md) | 当 agent 自带的联网工具不够用时，无需本地爬虫就能读取实时网页：先用免费的搜索与页面读取，再针对社交、商店、评论、地图与论文走合适的平台任务，某个厂商失败时 treg 自动回退到下一个 |
| [`lead-signals`](skills/lead-signals/SKILL.md) | 从公开信号（投诉、职位变动、招聘、融资、工具采用）中发现有购买意向的买家，并为主题、竞品或客户名单持续监控（[treg.to/leads-signals](https://treg.to/leads-signals)） |
| [`recruit`](skills/recruit/SKILL.md) | 把一条 LinkedIn 招聘帖变成排序后的候选人短名单：从帖子中提取标准、搜人、带理由的筛选、一句话说明为何匹配、在每位候选人的花费上限内附上引用证据（帖子、GitHub、演讲、任职时长、职位变动），最后给出经过校验的个人邮箱与电话，并输出一份记录每位候选人调用次数、证据与厂商轨迹的运行文件 |
| [`make-ugc`](skills/make-ugc/SKILL.md) | 制作 AI UGC 视频：热门钩子、一个虚拟主播、口播片段、字幕（[treg.to/ugc](https://treg.to/ugc)） |
| [`jev-memory`](skills/jev-memory/SKILL.md) | 给 Claude Code 一份记忆：一个 Claude Code 模组，Jev 在每轮之后评判每条提示并保留你的长期偏好，可现成安装或由一条提示生成（[该模组](examples/claude-code-mods/jev-memory)） |

`install.sh` 只安装 `treg` 并列出其余技能；用 `sh -s -- --skills lead-signals,recruit` 指定你想要的（或 `--skills all`；需主动选择的 `jev-memory` 与 `rea-growth` 永远不在该集合中）。在 Claude Code 中，每个技能也是 treg 市场里独立的插件：`/plugin install recruit@treg`，或从 `/plugin` 里挑选。若要加到已有的 agent 上（[skills.sh](https://skills.sh) CLI）：

```bash
npx skills add superdesigndev/treg                        # 所有公开技能
npx skills add superdesigndev/treg --skill lead-signals   # 只要一个
treg skill bootstrap --skills all                         # 安装器的集合，配合你已有的 treg CLI
```

工作流技能运行在 treg 之上，所以先把它配好（上面的快速开始，或把你的 agent 指向 [treg.to/llms.txt](https://treg.to/llms.txt)）。

### Claude.ai 连接器

Claude 连接器目录的接入面是 `https://treg.to/mcp/v2/`。它只暴露精选的目录端点，不含图片、视频或音频生成，并把读调用与写调用分开，以便 Claude 收到准确的安全信号。原有的 `/mcp/` 接入面继续供目录端点、团队自有工具与导入技能使用。边界与实现见 [MCP 与 OAuth 架构](docs/context/architecture/mcp-oauth.md)，发布门槛见
[提交操作手册](https://github.com/superdesigndev/treg-internal/blob/main/docs/distribution/CLAUDE-CONNECTOR-SUBMISSION.md)。

## 调用一个你没有密钥的工具

目录按端点**做什么**分组：关键词与排名追踪、外链与权威度、
AI 可见度、趋势与发现、发布到社交平台、人物与公司画像补全、广告管理与素材、效果度量。

```bash
treg catalog                                    # 所有平台，按热度排序
treg catalog search "find a work email"         # 按任务找，而不是按厂商
treg catalog search --new                       # 最近 30 天新增的工具，最新在前
treg catalog get hunter.people.email.find       # 参数、价格、示例响应
treg call hunter.people.email.find --query domain=reddit.com --query full_name="Alexis Ohanian"
```

**一次目录调用是如何被服务的** —— 凭据阶梯，按顺序：

1. 你的团队为该供应商注册了自己的工具 → 用那个工具、那把密钥；
2. 你的团队存了该供应商的密钥 → 通过虚拟工具注入；
3. 两者都没有，且该端点有已验证的公共路由 → **无需供应商密钥**，免费；
4. 否则 → **treg 自己的密钥**，计入团队的预付费余额。

匿名价格假定调用方没有发送供应商凭据头。忠实转发会保留调用方的头，因此调用方自带的供应商密钥可以消耗该密钥的额度。
你自己的凭据永远胜过 treg 的，所以接上你已经在付费的密钥会让这些调用不再消耗余额，而不是重复计费。treg 没有公布价格的端点会被**拒绝**，而不是免费提供 —— 你会被告知去接自己的密钥。当多家供应商都能提供同一能力时，`treg catalog search` 会把它们连同价格并排展示；**选择权在你** —— treg 不会替你静默挑选或在供应商之间切换。（当 treg 自己在该供应商的账号额度耗尽时，它可能通过 treg 自有的中继账号提供*同一个*端点，并在响应中披露；团队可以选择退出。）你自己选择加入的那个例外：`treg.<capability>` 路由端点，由 treg 替你挑供应商并告知是哪个。对于常见任务（抓取页面、网页搜索、Google 结果、找邮箱），请从路由端点开始，例如 `treg.web.extract` 或 `treg.web.search`，而不是你记得名字的某个供应商。在 `treg.people.email.find` 与 `treg.people.phone.find` 上，`X-Treg-Route-Verify: true` 还会在同一次调用中校验找到的地址或号码，作为独立的一笔费用，并说明校验结果。

```bash
treg balance          # 剩余额度、在途调用、近期消费
treg topup            # 充值，或设置自动充值
```

余额不足是 HTTP **402** `error: insufficient_balance`，携带 `balance_micro`、`estimated_cost_micro` 和一个 `topup_url`，
agent 无需阅读任何说明文字即可据此行动。

**Enrich Arena** 位于 `/enrich-arena`，在控制台之外。把各家补全答案连着各自的成本与速度一起对比，
一键为最佳答案投票，或观看顺序瀑布流。能力兼容的异步供应商也可参与；Arena 在内部处理提交与轮询。浏览是公开的；提交需要登录，计费的尝试消耗团队额度。参见
[Arena 指南](docs/context/interface/enrich-arena.md)。

**Web Arena** 在 `/web-arena` 对比 Web Search、Web Fetch 与 Sitemap 供应商。
Battle 让选定的供应商对同一输入同时开跑；Waterfall 按顺序依次尝试。
实时排行榜结合直接的供应商调用命中率与响应时间，以及滚动 30 天窗口内经过校验的 Web Arena 质量结果。这些页面在功能开启时出现。参见
[Web Arena 指南](docs/context/interface/web-arena.md)。

## 共享并使用你自己的工具

零思考的路径 —— 把 treg 指向一个项目，它自己判断哪些可共享：

```bash
treg scan     # 只读预览：上传会注册的密钥、技能与 CLI
treg upload   # 注册它们（服务端加密）；幂等，--replace 用于更新
```

`treg upload` 扫描 `.env`（把键名与约 80 个已知供应商比对）、每个技能子目录，以及已安装的目录 CLI。有三类东西会进入注册表 —— 下面分别说明如何共享与使用：

### 1. 端点（HTTP API）

**共享** —— 一个可以用已存密钥调用的上游 URL，或者从 `.env` 批量导入：

```bash
treg secret add STRIPE_KEY --value sk_live_123
treg add stripe --base-url https://api.stripe.com --secret STRIPE_KEY

treg upload env --select openai,stripe,resend     # 或直接从 .env 导入
```

**使用** —— agent 原生的用法：构造**真实的**上游请求，在前面加上代理前缀。
treg 按 host 解析工具，注入凭据，其余一切忠实转发
（你的 `X-Treg-Token` 在上游看到之前就被剥离了）：

```
真实请求：   GET https://api.intercom.io/conversations?per_page=5
经由 treg：  GET https://treg.to/call/https://api.intercom.io/conversations?per_page=5
                    header:  X-Treg-Token: <your token>
```

或者用 CLI 简写 —— 还有 `treg calls` 查看审计日志：

```bash
treg call intercom conversations --query per_page=5
treg call stripe v1/balance
```

### 2. CLI

**共享** —— 自动：`treg upload` 检测已安装的目录 CLI（`stripe`、`gh`、`vercel` 等）
并注册它们；只有配方的目录 CLI 技能（例如 `stripe-cli`）也会自动变为可运行。

**使用** —— `treg run` 以**注入组织凭据**的方式执行厂商 CLI，所以你既不持有密钥也不需要登录：

```bash
treg run stripe -- get /v1/balance
treg run gh -- pr list
```

`--local`（默认）在你自己的机器上运行。服务端 CLI 执行（`--server`）已全局禁用。
若要整场会话都生效，`treg shell start` 会打开一个子 shell，其中每个已注册 CLI 都会自动注入 —— 正常用 `stripe`、`gh` 即可；`exit` 后恢复。`treg runs` 是审计日志。

### 3. 技能

**共享** —— 一个技能是一整套能力（`SKILL.md` 配方 + 它的密钥 + 它的工具），
一起注册，让整个团队运行同一份技能，在一处维护：

```bash
treg upload skills --dir ~/.claude/skills --all   # 一次性注册一整个技能目录
```

**使用** —— 把任何共享技能拉进你的 agent；它的 API 调用会带着你的 token 走 treg，
所以密钥留在服务端，永远不在技能里：

```bash
treg skill install seo-blog-writer      # 写入 ./.claude/skills/  （--all 拉取整个库）
```

### 手动注册 —— 当启发式规则判断不出来时

```bash
# 多凭据工具（例如 google-ads：OAuth bearer + 一个 developer-token 头）
treg tool add google-ads --base-url https://googleads.googleapis.com \
  --bind "secret=<oauth-id>,injector=oauth" \
  --bind "secret=<dev-id>,name=developer-token,format={secret}"

# 一个技能，分步完成
treg skill init --dir ./my-skill          # 起草 treg.json（猜测 base_url、找出密钥）
treg skill add  --dir ./my-skill          # 原子化注册配方 + 密钥 + 工具

# 通过浏览器走 OAuth（铸造第一个 token，treg 持有它并自动刷新）
treg oauth connect gsc --client-secret client_secret.json \
  --scopes https://www.googleapis.com/auth/webmasters.readonly
```

每条命令的完整选项：[`USAGE.md`](USAGE.md)。

在使用 treg.to 时，CLI 会向 PostHog 发送匿名命令使用情况（不含参数与凭据）。
用 `TREG_TELEMETRY=0` 或 `DO_NOT_TRACK=1` 关闭。
参见[分析说明](USAGE.md#anonymous-usage-analytics)。

## 团队

一个账号最多可拥有 10 个团队。以成员身份加入其他团队不计入此上限。

一切都以**组织（org）**为作用域：一个 token = 一个 `(用户, 组织)` 成员关系，每个密钥、工具
与技能都属于当前激活的组织。角色：**owner / admin / member / viewer**。

```bash
treg org create "Acme"                        # 创建团队，成为 owner
treg org invite teammate@acme.com             # 按邮箱邀请（选择角色 + 工具访问权限）
treg org join <code> --email you@acme.com     # 接受邀请（若你是新用户会创建账号）
treg org ls | use <slug> | members            # 切换组织、查看名单
treg org access <member> --tools a,b          # 按成员设置工具访问权限（admin+）
```

团队 owner 可在控制台的 **Team → SSO** 标签页启用企业 SSO。WorkOS 连接公司的身份提供方；owner 可邀请其 IT 管理员完成配置。员工可在任何登录对话框输入公司邮箱，或使用团队的直接登录链接。treg 保留自己的团队角色与 API key。目录同步（Directory Sync）方案会移除已离职员工的团队访问权限。参见
[企业 SSO 配置](docs/enterprise-sso.md)。

## 深入

- **反馈：** `treg feedback submit friction "The pagination example is unclear."`
  提交问题或建议，不要包含私密信息。参见[反馈说明](https://treg.to/feedback.md)。
- **评价：** `treg review CALL_ID useful`
  在使用结果后为一次受邀的目录调用打分；`not_sure` 也可以。省略私密数据，继续你的任务。

- [`USAGE.md`](USAGE.md) —— 完整的 `treg` CLI 参考。
- [`/llms.txt`](https://treg.to/llms.txt)：agent 的入口，采用 [llms.txt](https://llmstxt.org)
  格式：treg 是什么、各类 agent 的接入方式、搜索-阅读-调用循环与规则，并链接到
  [`/skill.md`](https://treg.to/skill.md)（操作指南）了解其余内容。
- **控制台**在 [treg.to](https://treg.to) —— 完整 CRUD、引导式教程（Help → Tutorial），以及可复制的 agent 配置说明。
- **API** —— CLI 做的一切都是普通 HTTP；交互式 OpenAPI 文档在 `/docs`。
  代理端点是 `/call/{...}`；所有端点都接受 `X-Treg-Token` 头。

---

# 第二部分 · 自托管与开发

## 本地运行

一条命令（需要 `tmux` + [`uv`](https://docs.astral.sh/uv/)；它会自己同步虚拟环境）：

```bash
scripts/dev-local.sh up        # 服务跑在 http://localhost:18790，开发安全配置
```

这会在 tmux 中以热重载运行服务，使用自带的 sqlite 数据库（`treg-dev.db`），并开启邮箱 OTP 开发模式（登录码直接显示在页面上 —— 不需要邮件发送器）。日常操作：

```bash
scripts/dev-local.sh cli login   # 沙箱化 CLI：永远不会碰你真实的 ~/.treg/config.json
scripts/dev-local.sh logs        # 服务输出          · status / restart / down
scripts/dev-local.sh reset       # 清空开发数据库 + CLI 沙箱，重新开始
```

或者不用 tmux，直接运行服务：

```bash
bash scripts/build-dashboard.sh # 需要 Node 22.12+ 与 npm；构建控制台
uv sync                        # 依据 uv.lock 创建虚拟环境（拉取开发所需的服务端依赖）
uv run python -m treg upgrade  # 准备 schema + 执行幂等的发布任务，不启动服务
uv run python -m treg          # 在 0.0.0.0:18790 提供服务（开发可加 --reload）
uv run python -m treg keygen   # 打印一把新的 Fernet key 用于 TREG_SECRET_KEY
```

> **安装以运行服务（而非从源码运行）：**基础包**只有 CLI**。要运行一个注册表，请安装 server extra —— `pip install "tools-registry[server]"` —— 它会加上 FastAPI、数据库驱动与加密库。只装 `pip install tools-registry` 则仅得到用于与已有注册表对话的 `treg` 命令。

官方托管服务在 `treg.to`。其生产拓扑与线上配置维护在私有的[运维手册](https://github.com/superdesigndev/treg-internal/blob/main/docs/production/deploy.md)中。

## 配置

环境变量（前缀 `TREG_`，从 `.env` 读取）：


| 变量                                       | 默认值                         | 用途                                                                                                                                                                    |
| ----------------------------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TREG_DATABASE_URL`                       | `sqlite+aiosqlite:///./treg.db` | 数据库 URL（开发用 SQLite，生产用 Postgres）                                                                                                                                  |
| `TREG_READ_DATABASE_URL`                  | *(空)*                       | 可选的 SQLite / PostgreSQL 只读数据源；为空则复用主库。要求调用方主动接入；现有查询行为不变。参见[只读数据源配置](docs/context/ops/deploy.md#optional-read-replica)。 |
| `TREG_SECRET_KEY`                         | *(空)*                       | 静态密钥加密用的 Fernet key；为空 → 临时铸造一把（重启后密钥不保留）                                                                                                       |
| `TREG_PUBLIC_URL`                         | `https://treg.to`  | treg 的公开基址，用于构造 OAuth 回调 URI                                                                                                                   |
| `TREG_SESSION_SECRET`                     | *(空)*                       | 签署控制台会话 cookie；回退到 `TREG_SECRET_KEY`。生产环境请设置真实值                                                                                                 |
| `TREG_GITHUB_CLIENT_ID` / `_SECRET`       | *(空)*                       | GitHub OAuth 登录（回调 `<public_url>/auth/github/callback`）；为空则隐藏按钮                                                                                              |
| `TREG_GOOGLE_CLIENT_ID` / `_SECRET`       | *(空)*                       | Google OAuth 登录（重定向 `<public_url>/auth/google/callback`）；为空则隐藏按钮                                                                                            |
| `TREG_WORKOS_API_KEY` / `_CLIENT_ID` / `_WEBHOOK_SECRET` | *(空)* | WorkOS 企业 SSO；按[企业 SSO 配置](docs/enterprise-sso.md)配置回调与带签名的目录 webhook |
| `TREG_ENTERPRISE_SSO_BUNDLE_ONLY` | `true` | 默认只展示 SSO + 目录同步方案；设为 `false` 则同时提供两种月付方案。 |
| `TREG_ENTERPRISE_SSO_BUNDLE_PRICE_ID` / `TREG_ENTERPRISE_SSO_ONLY_PRICE_ID` | *(空)* | 与 `TREG_STRIPE_SECRET_KEY` 同一账号下的可复用月付 Stripe Price ID；未设置或不可用的 Price 会隐藏对应方案。展示金额与 Checkout 收费由 Stripe 的 Price 提供。 |
| `TREG_ENTERPRISE_SSO_BUNDLE_MIN_PRICE_USD` / `TREG_ENTERPRISE_SSO_ONLY_MIN_PRICE_USD` | `0` | 各月付 Stripe Price 的可选整美元下限；低于该价格会被隐藏并在 Checkout 时被拒绝。 |
| `TREG_INSTAGRAM_CLIENT_ID` / `_SECRET`    | *(空)*                       | 用于直接 Instagram 登录的 Instagram App ID 与 secret（重定向 `<public_url>/oauth/callback`）                                                                           |
| `TREG_META_CLIENT_ID` / `_SECRET`         | *(空)*                       | 用于 Facebook 主页、Meta 广告以及可选 Instagram `page-tools` 的 Meta 应用凭据                                                                                     |
| `TREG_OAUTH_REVIEW_PENDING`               | `instagram-login,page-messages` | 逗号分隔的注册表审核项 key，其相关能力必须保持受限；托管状态下的审核进度由私有仓库维护。                                                                   |
| `TREG_RESEND_API_KEY` / `TREG_EMAIL_FROM` | *(空)*                       | 通过 Resend 发送事务邮件（OTP 码 + 邀请）；发件人必须是 Resend 已验证的发件地址                                                                                              |
| `TREG_BLOCKED_EMAIL_DOMAINS`              | *(空)*                       | 逗号分隔的邮箱域名，在所有注册/登录入口以及创建团队时被拒绝（含子域名，不区分大小写）。为空则不拦截任何域名 —— 代码内不内置任何名单 |
| `TREG_CLIENT_IP_HEADER`                   | *(空)*                       | 一个只有你的边缘节点能设置的头，用作所有按 IP 限制的客户地址（Cloudflare 后用 `cf-connecting-ip`） |
| `TREG_TRUSTED_PROXY_HOPS`                 | `1`                             | 在没有该头时：取 `X-Forwarded-For` 中从右往左数这么多跳的那一项（即最近的代理追加的那一项）；客户端直连时设为 `0`。第一项是客户端可写的，永不信任 |
| `TREG_REQUIRED_EXTENSIONS`                | *(空)*                       | 逗号分隔的策略扩展（`treg.extensions` 入口点），必须已安装，否则启动失败。treg.to 以这种方式运行一个私有的滥用策略扩展；它只能收紧限制（[策略扩展](docs/context/architecture/policy-extensions.md)） |
| `TREG_TURNSTILE_SITE_KEY` / `_SECRET`     | *(空)*                       | 每个邮箱登录表单上的 Cloudflare Turnstile；任一为空即关闭。site key 由 `/captcha.js` 提供，secret 只用于 siteverify |
| `TREG_TURNSTILE_MODE`                     | `observe`                       | `observe` 记录每次结果但不改变任何行为；`enforce` 对缺失或无效 token 的验证码请求予以拒绝，并在 Cloudflare 无法应答时不发放注册赠金 |
| `TREG_TURNSTILE_HOSTNAMES`                | *(空)*                       | 逗号分隔的、token 必须在其上完成验证的主机名；为空则用 `TREG_PUBLIC_URL` 的主机（及其已知别名） |
| `TREG_ADMIN_TOKEN`                        | *(空)*                       | 跨租户的**超级管理员** bearer；授权所有 `/admin/*` 端点。为空则关闭环境变量这条路（只有 `is_superadmin` 用户能访问 `/admin`）。请设置得足够长且保密。 |
| `TREG_EMAIL_DEV_MODE`                     | `false`                         | 为 true 时，`/auth/email/start` 在响应中直接返回 OTP（不需要邮件发送器）—— **仅用于开发/本地**，生产绝不可开启。                                                |
| `TREG_KV_URL`                             | *(空)*                       | 共享键值存储（Redis 协议），用于所有 worker 必须一致的计数器，目前是每团队的评价邀请额度。为空则使用进程内回退，单 worker 下够用 |


本地开发不需要 `.env` —— 每项设置都有可用的默认值（临时密钥、sqlite）。

> **⚠️ 迁移或重新部署前请先备份：**Fernet key（`TREG_SECRET_KEY`）与数据库（生产是 Postgres；本地 sqlite 运行是 `treg.db`）。丢失 Fernet key，所有已存密钥都无法恢复。

## 架构

**`/call` 的请求流程：**解析工具（按 URL host + 最长 `base_url` 前缀，或按名称）→
解密其密钥 → 应用每条绑定的注入器 → 流式转发到上游 → 发后即忘的审计记录。基础设施层的转发器不带业务逻辑地流式搬运字节。调用应用层会把需要结算或所有权证据的响应缓冲到 8 MiB；更大的响应返回 502 且不计费，而不是返回一个被截断的成功结果。内联媒体（Gemini 图片）的端点声明 `spooled_response`：其计量响应改为读到一个临时文件，依据上报的用量结算，然后整体转发。已授权且不需要响应体证据的免费最终下载会整体流式返回，自有密钥与自有工具的响应也是如此。

**模块地图**（`src/treg/`）：


| 模块                                     | 职责                                                                                                             |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| `proxy.py`                                 | `relay()` —— 一个函数就是整个产品：忠实的流式代理                                        |
| `injectors.py`                             | 认证形态的接缝：`env`、`cli_auth`、`secret_file`、`oauth` 把密钥放进 header/query                |
| `oauth.py`                                 | token 新鲜度（单飞式刷新）+ 连接流程（同意 URL、code 交换）                          |
| `health.py`                                | 凭据健康：刷新 oauth、探测工具、对任何失效项的拥有者发 webhook                              |
| `convert.py`                               | 把一个技能目录脚手架化为可注册的套件清单                                                   |
| `api.py`                                   | API —— 唯一的大脑；CLI 与技能都是其上的瘦客户端                                                   |
| `cli.py`                                   | `treg` CLI                                                                                                   |
| `models.py`                                | SQLModel 表：`Org`、`User`、`Membership`、`Invite`、`Secret`、`Tool`、`Bundle`、`PendingOAuth`、`CallRecord` |
| `crypto.py` `config.py` `db.py` `audit.py` | Fernet 加密 + token · 设置 · 异步数据库 · 延迟审计写入器                                         |


**4 种认证形态**（按绑定的 `injector`）：`env`（普通字符串 / API key）· `secret_file`（JSON token 文件，取一个字段）·
`oauth`（JSON OAuth token，可刷新时自动刷新）·
`cli_auth`（从某个 CLI 的钥匙串中取出的材料）。

**忠实转发契约：**代理只改动**三样**东西，其余一律原样：

1. 逐跳传输头（每跳重新推导），
2. treg 自己的控制头与边缘转发头（`x-treg-token`、`x-treg-org`、
`ngrok-skip-browser-warning`、`x-forwarded-*`、`via` 等）以及 treg 的会话 cookie —— 全部剥离，
绝不泄漏到上游，
3. 被注入的凭据。

**OAuth，获取第一个 token 的三种方式：** *手动上传*（直接放入一个 `token.json`）·
*自动刷新*（如果 token 带 `refresh_token` + 客户端凭据，treg 会保持其新鲜，你无需重新上传）·
*托管连接流程*（`treg oauth connect` → 浏览器同意 → treg 自己捕获 token）。

**健康检查：**给工具一个可选的探测（`{method, path, expect_status}`）；周期性运行
（按需或通过 cron）校验每条凭据、刷新 OAuth，并对任何失效项的拥有者发 webhook。

深度设计文档在 [`docs/context/`](docs/context/README.md)（按子系统分的片段）。

## 测试

```bash
uv run --with pytest-xdist pytest -n auto -q   # 日常本地默认（与 CI 同形态）
uv run --frozen python -m pytest -q            # 串行：调试单个测试，或与顺序有关时
```

覆盖范围：代理的走查骨架、所有注入器形态、按用户的认证 + CRUD + 审计、技能组合器、
URL 直通 + 忠实转发、OAuth 刷新 + 连接流程、健康检查、`treg run`/shell、
上传/扫描、组织与邀请、控制台 API、CLI。

## 贡献与文档

```
treg/
├── src/treg/            # 包本体（api, cli, proxy, injectors, oauth, health, convert, models, …）
│   └── web/             # 控制台、落地页、教程、llms.txt、skill.md、install.sh
├── tests/               # pytest 套件（CI 与本地默认：pytest-xdist -n auto）
├── docs/
│   ├── context/         # 设计片段（codemap 系统）+ 生成的索引
│   └── ONBOARDING.md    # 首次引导
├── USAGE.md             # 完整的 treg CLI 参考
└── pyproject.toml
```

按子系统的设计文档是 `docs/context/` 中的**片段**，每份都标注了它对应的 `src/treg/*`
源码。在这个仓库里与 AI agent 一起工作？`/tools-registry-context` 技能会为你正在改动的部分加载正确的片段并保持文档同步 —— 推送前运行
`/tools-registry-context sync`。

**路线图：**MCP 支持 · 更细粒度的权限层级 · 静态密钥管理加固 · 可能合并
Loopni。

## 许可证

Apache 2.0 附加条款（[`LICENSE`](LICENSE)）：可自由使用 —— 包括商业使用，
在你自己的组织内部使用（鼓励自托管你自己的注册表）。限制是：未经书面许可
（`jason@superdesign.dev`），不要把代码再分发给第三方，作为竞争性的托管/代管注册表服务。**在你自己的产品中使用托管的 treg.to API** ——
通过 `X-Treg-Meta` 与 `usage/by-tag` 做透传计费 —— 是无需许可的；
那是在调用我们的 API，而不是再分发我们的软件。

### 固定的客户读取作用域

对于受限的客户 agent，`treg org agent-new bot --pin customer=cust_A` 会强制归属，
并把调用/运行历史、归档结果以及共享供应商异步任务所有权的读取范围限定到该 pin。
外来或未归属的 id 返回 404；未固定 pin 的操作者保留组织级视图与共享余额。BYOK 账号访问与公开媒体 URL 维持其原有权限。关于多个 pin、迁移与重放行为，参见
[多租户契约](docs/context/architecture/multi-tenancy.md#caller-tags-and-pinned-read-scopes)。
