# tools-registry — 动手教程

整个注册表，端到端。每一步都展示**确切命令**、**预期输出**，以及**该注意什么** —— 所以它可以独立阅读。把每条命令复制到你的终端里跟着做。

这份同样的走查有两个配套版本，由一个源（`src/treg/web/tutorial.js`）生成：

- **在控制台里** → 在 `https://treg.to/` 登录并打开 **Help → Tutorial**。
- **独立版** → `https://treg.to/tutorial`。

### 两个聚焦的深入教程

这个主走查覆盖整个注册表。有两个特性有各自详细的教程 —— 要看完整的逐步处理请读那些（每个都展示确切命令、真实输出，以及它是如何被测试的）：

- **导入与 shell** → `https://treg.to/tutorial-import-shell.md` —— 把你机器上已有的 CLI 用一条命令变成团队工具（`treg upload clis`），并打开一个 shell（`treg shell`），其中 `stripe`、`gh`、`gcloud` …… 带着团队 key 注入就能直接用。包含本地运行的**安全沙箱**（CLI 以一个被锁定的用户运行，只能访问它自己的 API，且不能把 key 留在磁盘上）。
- **团队访问控制** → `https://treg.to/tutorial-access.md` —— 选择**每个成员可以使用哪些工具**，以及他们是否可以**本地**运行 CLI —— 在邀请时设定，随时可改。

---

## 概念（读一次）

- **邮箱就是你的身份。** 你*就是*一个已验证的邮箱。三扇门证明它 —— **GitHub**、一封邮件发的**一次性验证码**（OTP），或者一个**邀请码**。你第一次证明一个邮箱时你被*注册*；此后的每次证明都是一次*登录*。没有单独的注册（也没有 `treg register` 了）。
- **代理 = 一个银行柜员。** 你*通过*注册表调用真实的 upstream API。它把你的工具引用换成真实的 secret 并在服务端注入。key 从不落在你的机器上；你的 token 授权这次调用。
- **一个 token = 一个 (你, 组织) 对。** 一个 **User** 是一个身份；一个 **Org** 是拥有资源的团队；一个 **Membership** 用一个角色把它们连起来。你的**身份 token**（来自 `treg login`）在你所属的每一个 org 上都有效 —— `treg org use <slug>` 选择当前激活的那个。（agents/CI 可以用一个每 org 的 token 代替。）
- **邀请绑定到邮箱。** 一个 owner/admin 邀请一个*邮箱*。证明那个邮箱（任何一扇门）邀请就是你的，可以接受 —— 不需要码。码是一个便捷的带外捷径，不是要求。
- **工具与技能。** 一个 **tool** = 一个 upstream `base_url` + 一组凭据 **bindings**（一次请求可以携带多条）。一个 **skill / bundle** = 一份配方（`SKILL.md`）+ 它的 secret + 它的工具，通过一个 `treg.json` 契约从一个文件夹注册。
- **用工具的两种方式。** `treg call` 代理一个 HTTP **API** —— secret 在服务端注入，没有任何东西落在你的机器上。`treg run` 运行一个供应商的**命令行工具**（stripe、gh、gcloud…），凭据在本地注入。owner 先为每项工具选择加入；`treg runs` 是审计日志。服务端 CLI 执行对所有人禁用：`--server` 返回 HTTP 503。

### 角色一览

| 动作 | viewer | member | admin | owner |
|---|:--:|:--:|:--:|:--:|
| 调用工具、读清单 | ✅ | ✅ | ✅ | ✅ |
| 注册 secret / 工具 / 技能 | ❌ | ✅ | ✅ | ✅ |
| 编辑 / 删除自己的资源 | ❌ | ✅ | ✅ | ✅ |
| 编辑 / 删除 org 内任何资源 | ❌ | ❌ | ✅ | ✅ |
| 邀请 / 移除成员 | ❌ | ❌ | ✅ | ✅ |
| 改角色、删除 org | ❌ | ❌ | ❌ | ✅ |

---

## 准备 —— 在一台机器上模拟三个人

我们通过在每个人自己的 `HOME` 上玩三个人，这样每个人得到一个指向注册表的隔离的 `~/.treg/config.json`。真实情况下每个人在自己机器上，去掉 `HOME=` 前缀即可。

```bash
for u in tom bob alice; do
  mkdir -p ~/.treg-personas/$u
  HOME=~/.treg-personas/$u treg config --base-url https://treg.to
done
```

**注意：** 给任何命令加 `HOME=~/.treg-personas/<name>` 前缀就以那个人身份操作。

---

# 第一部分 —— 目录（无密钥，无配置）

这部分之后的所有内容都需要一个团队、一个 secret 和一个已注册工具才能发生。目录不需要其中任何一个 —— 它是从"装好"到"拿到真实数据"最短的路径，也是 treg 现在主打的东西。

## 步骤 1 —— 按它"做什么"找一个工具

Tom 刚装好 CLI。没有团队、没有 key、什么都没注册 —— 而且他已经能干活了。他不需要知道哪家厂商卖反链数据；他按**任务**搜索，每次命中都显示要花多少钱。

```bash
treg catalog search "backlinks for a domain"
```

```
76 matches for "backlinks for a domain" — showing 25

  ENDPOINT                              PLATFORM   PROVIDER     COST
  dataforseo.web.backlinks.summary      web        DataForSEO   $0.024/call
  moz.web.backlinks.summary             web        Moz          $0.013334/call (2 quota rows)
  majestic.web.backlinks.list           web        Majestic     $0.02/call (5000 analysis units)
```

> 通常几家供应商以不同价格提供同一项能力。treg 把它们并排展示 —— **选择权在你**；它不会静默替你挑选或故障转移。

## 步骤 2 —— 花钱之前先读价格

每个被编目的端点都带有它的价格、参数和一个示例响应。期望一个 agent 在花掉团队的余额*之前*读这个并告诉人成本。

```bash
treg catalog get tikhub.tiktok.user.profile
```

```
tikhub.tiktok.user.profile
Public TikTok profile by username (uniqueId) or secUid

  provider  TikHub (tikhub)
  call      GET /api/v1/tiktok/web/fetch_user_profile
  cost      $0.001/success
            charged on 2xx only
  verified  2026-07-28
```

> 一个 treg 没有公布价格的端点会被**拒绝**，永远不会免费提供 —— 你会被告知去连接自己的 key。

## 步骤 3 —— 调用它，任何地方都没有 key

在 TikHub 没有账号、没有注册、机器上也没有 key。treg 持有凭据，在服务端注入，并把调用计到团队的预付费余额上。新验证的账号在创建合格团队时会一次性收到 **$1.00 免费**，以这个价格足够覆盖数百次调用。

```bash
treg call tikhub.tiktok.user.profile --query uniqueId=tiktok
```

> 如果团队已经有自己的该供应商 key，它会自动胜出 —— 而且那些调用永远不被计量。

## 步骤 4 —— 看清它到底花了多少

余额是一个只追加的账本，以整数微美元（一美元的百万分之一）计，所以花费几分之一美分的调用会被精确记录，而不是被舍入掉。余额不足是一个 HTTP **402**，带着 agent 可以据此行动的那些数字。

```bash
treg balance
```

```
  Balance  $0.9990   (999000 micro-USD)

  RECENT
  settle   -$0.0010   tikhub.tiktok.user.profile
```

> 只有走 treg 的 key 的调用才花费余额。你自己的 key、你自己的工具、供应商 CLI 都不在其中。

# 第二部分 —— Tom 创立 Superdesign

## 步骤 5 —— Tom 登录（邮箱门）

没有 `register`。Tom 用一个一次性验证码证明他的邮箱 —— 而且因为这是第一次，同一个动作**创建**了他加一个个人 org（所以永远不会是空状态）。验证码被**发邮件**给他；他查收收件箱并输入它。

```bash
HOME=~/.treg-personas/tom treg login --email tom@superdesign.dev
```
```
We sent a 6-digit code to tom@superdesign.dev.
Enter code: 429641
✓ Logged in as tom@superdesign.dev. Active org: tom-superdesign-dev
```

**注意：** 查收收件箱里的 6 位验证码，然后输入它。Tom 现在持有一个**身份 token**，在他加入的每个 org 上都有效 —— 没有每 org 的 token 要 juggle。（一台开发机可以设 `TREG_EMAIL_DEV_MODE=true`，把码直接打印出来而不是发邮件。）

## 步骤 6 —— Tom 创建团队

他的个人 org 只是他自己的。现在他拉起共享团队并成为其 **owner**；他的激活 org 切到它，所以之后的所有内容都在那里运行。

```bash
HOME=~/.treg-personas/tom treg org create "Superdesign"
```
```json
{
  "org": "superdesign",
  "org_id": 2,
  "name": "Superdesign",
  "role": "owner",
  "token": "<per-org token — for agents/CI; a human doesn't need it>"
}
```

**注意：** 个人 org 在登录时自动创建；**团队用 `org create` 显式创建**。

---

# 第三部分 —— Bob 经由邮箱门加入

## 步骤 7 —— Tom 邀请 Bob

Tom 用**邮箱**邀请一个队友。邀请绑定到那个邮箱，Tom 拿到一个他*可以*递过去的一次性码 —— 但 Bob 甚至不需要它。

```bash
HOME=~/.treg-personas/tom treg org invite bob@superdesign.dev --role member
```
```json
{
  "code": "<one-time-invite-code>",
  "email": "bob@superdesign.dev",
  "role": "member",
  "org_id": 2,
  "expires_at": "2026-07-09T…"
}
```

**注意：** 邀请是待接受的，寄给 Bob 的邮箱，有效期 7 天（`--expires-days` 可改）。

## 步骤 8 —— Bob 以他自己身份登录

切到 Bob。他用同样的方式证明他的邮箱 —— 而且因为这是第一次，这也**创建**了他，带着他自己的身份 token 和个人 org。他从来没碰过邀请码。

```bash
HOME=~/.treg-personas/bob treg login --email bob@superdesign.dev
```
```
We sent a 6-digit code to bob@superdesign.dev.
Enter code: 512740
✓ Logged in as bob@superdesign.dev. Active org: bob-superdesign-dev
```

**注意：** 和 Tom 同一扇门 —— 码落到 Bob 的收件箱，他输入它。邮箱就是身份 —— 门（GitHub / 码）只是你证明它的方式。

## 步骤 9 —— Bob 看到他的邀请（无码）

因为邀请绑定到 Bob 现已证明的邮箱，他可以直接问有什么在等他。这是个完整的循环：证明邮箱就揭示出寄给它的每个邀请。

```bash
HOME=~/.treg-personas/bob treg invites
```
```json
[
  {
    "id": 1,
    "org": "superdesign",
    "org_id": 2,
    "name": "Superdesign",
    "role": "member",
    "invited_by": "tom@superdesign.dev",
    "expires_at": "2026-07-09T…"
  }
]
```

**注意：** 没有码，没有从 Tom 那里复制粘贴 —— 被证明的邮箱就是证明。

## 步骤 10 —— Bob 接受

Bob 通过命名 org 加入 Superdesign。没有码 —— 他已证明的身份就是证明。他的激活 org 切到 Superdesign。

```bash
HOME=~/.treg-personas/bob treg accept superdesign
```
```json
{
  "org": "superdesign",
  "org_id": 2,
  "name": "Superdesign",
  "role": "member"
}
```

**注意：** Bob 现在是 Superdesign 的 **member**。

## 步骤 11 —— Bob 的两顶帽子

一个身份，两个成员关系 —— 个人 org 的 owner，Superdesign 的 member。同一个身份 token 在两者都有效。

```bash
HOME=~/.treg-personas/bob treg org ls
```
```
  bob-superdesign-dev    bob@superdesign.dev    owner
* superdesign            Superdesign            member   (active)
```

**注意：** `*` 标记激活的 org。随时用 `treg org use <slug>` 切换。

---

# 第四部分 —— Alice 经由码门加入

## 步骤 12 —— Tom 邀请 Alice 作为 viewer

另一扇门：那个**码**。先 Tom 邀请 Alice 作为 **viewer** —— 她能读和调用，但不能注册任何东西。

```bash
HOME=~/.treg-personas/tom treg org invite alice@superdesign.dev --role viewer
```
```json
{
  "code": "ZTeW5ss-cXiyvzeMs3em-…",
  "email": "alice@superdesign.dev",
  "role": "viewer",
  "org_id": 2,
  "expires_at": "2026-07-09T…"
}
```

**注意：** 这次我们**保留码** —— Alice 下一步直接用它。

## 步骤 13 —— Alice 通过码加入（之前没有登录）

和 Bob 的对比：Alice **从不运行** `login`。码本身就证明她的邮箱，所以 `join` 创建她、把她加入 Superdesign、并保存她的 token —— 全在一次命令里。

```bash
HOME=~/.treg-personas/alice treg org join ZTeW5ss-cXiyvzeMs3em-… --email alice@superdesign.dev
```
```json
{
  "org": "superdesign", "org_id": 2, "name": "Superdesign", "role": "viewer",
  "token": "<alice's superdesign token>",
  "personal": { "org": "alice-superdesign-dev", "org_id": 4, "role": "owner",
                "token": "<alice's personal token>" }
}
```

**注意：** 一条命令创建了 Alice，给了她一个个人 org，并让她成为 viewer —— Tom 从未碰过她的 token。

## 步骤 14 —— viewer 角色是有牙的

Alice 能读和调用，但 viewer **不能注册**任何东西。看她被拦下。

```bash
HOME=~/.treg-personas/alice treg secret add testkey --value "nope"
```
```json
{
  "detail": "viewers can call and read, but cannot register"
}
```

**注意：** Alice 被授予的是*使用*，不是*写入* —— 角色门在履行职责。

---

# 第五部分 —— 一个经由代理的工具

## 步骤 15 —— Bob 注册一个 secret

和 Alice 不同，**member** 可以注册。Bob 加一个 API key —— 在服务端加密，它的值不再返回。

```bash
HOME=~/.treg-personas/bob treg secret add echo-key --value "sk-demo-secret-123"
```
```json
{
  "id": 1,
  "name": "echo-key",
  "kind": "env",
  "owner": "bob@superdesign.dev",
  "bundle_id": null
}
```

**注意：** 该 secret 是按 org 作用域的（活在 Superdesign 里），由 Bob 拥有。一个工具通过 `id` 绑定到它。

## 步骤 16 —— Bob 注册一个工具

一个工具 = 一个 upstream `base_url` + 如何注入凭据。我们指向 postman-echo 这样我们就能*看到*注入。一个单独的 `--secret` 默认是放在 `Authorization` 头里的 `Bearer` token。

```bash
HOME=~/.treg-personas/bob treg tool add echo --base-url https://postman-echo.com --secret 1
```
```json
{
  "id": 1, "name": "echo", "owner": "bob@superdesign.dev",
  "base_url": "https://postman-echo.com", "host": "postman-echo.com",
  "bindings": [
    { "secret_id": 1, "injector": "env", "location": "header",
      "name": "Authorization", "format": "Bearer {secret}", "secret_field": "access_token" }
  ]
}
```

**注意：** 对于多凭据的 upstream，用 `--bind` 增加更多 binding —— treg 在每次调用时应用每一条 binding。

## 步骤 17 —— Alice 调用它（没有 key）

treg 的整个意义。Alice 是一个**viewer**，机器上**没有 secret**。然而当她调用时，upstream 看到的是 Bob 的 key，在服务端注入。

```bash
HOME=~/.treg-personas/alice treg call echo /get
```
```json
{
  "args": {},
  "headers": {
    "host": "postman-echo.com",
    "authorization": "Bearer sk-demo-secret-123",
    "...": "..."
  },
  "url": "https://postman-echo.com/get"
}
```

**注意：** `authorization: Bearer sk-demo-secret-123` —— Bob 的 secret，Alice 从未拥有、看到或存储过。

## 步骤 18 —— 每次调用都有记录

代理为每次调用写一条审计行。owner 审阅 org 的活动。

```bash
HOME=~/.treg-personas/tom treg calls --limit 5
```
```json
[
  {
    "id": 1,
    "user_email": "alice@superdesign.dev",
    "tool_name": "echo",
    "method": "GET",
    "path": "https://postman-echo.com/get",
    "status_code": 200,
    "created_at": "2026-07-02T…"
  }
]
```

**注意：** 即使 Alice 用了 Bob 的 secret，账本记录的也是**谁**真正发起了调用。

---

# 第六部分 —— 调用形态与技能

## 步骤 19 —— 用完整 URL 调用（agent 原生）

一个 agent 常常已经知道真实的 upstream URL。与其 `call <tool> <path>`，不如把**整个 URL** 交给 treg —— 它把 host 匹配到一个已注册工具并注入 key。无需任何 treg 特定知识。

```bash
HOME=~/.treg-personas/alice treg call https://postman-echo.com/get
```
```
# 同样的 echo 响应，注入了 "authorization": "Bearer sk-demo-secret-123"。
# 注意：命令里没有工具名 —— 只有目标 URL。
```

**注意：** treg 按 **host** 解析工具，所以 agent 原生的完整 URL 形态直接可用。

## 步骤 20 —— 底层的裸 HTTP

`treg call` 是语法糖。在引擎盖下它是一个到 `<proxy>/call/<upstream-url>` 的普通 HTTP 请求，带你的 token 头 —— 任何语言、任何 agent、`curl`。

```bash
ATOK=$(python3 -c "import json;print(json.load(open('/Users/you/.treg-personas/alice/.treg/config.json'))['token'])")
curl -s -H "X-Treg-Token: $ATOK" \
  "https://treg.to/call/https://postman-echo.com/get"
```
```
# postman-echo 的 JSON 又回来了，"authorization": "Bearer sk-demo-secret-123" 被注入 ——
# 只是 curl，客户端没有 secret。
```

**注意：** 整个产品就在一行里：给任何 upstream URL 加上代理前缀，发送你的 token，treg 把真实凭据换进去。

## 步骤 21 —— 起草一个技能的注册

一个完整的技能文件夹（配方 + 凭据文件）可以通过一份 `treg.json` 契约一次性注册。`skill init` 扫描 `SKILL.md` + `.secret/` 目录并起草它 —— 猜出 base URL 并找到 secret。文件里不放任何值，只有引用。

```bash
HOME=~/.treg-personas/bob treg skill init --dir /tmp/skills/echo-svc
```
```
wrote /tmp/skills/echo-svc/treg.json
  auto: base_url=https://postman-echo.com | secrets=['echo-svc']
  review / fill:
    - base_url — heuristic guess, verify
    - health / examples — optional
```

**注意：** 它读了配方并正确猜出 `base_url` + 找到 secret —— 修掉它标记的任何东西，然后注册。

## 步骤 22 —— 上传整个技能

一条命令把文件夹变成一个在线工具：配方、secret（值从 `.secret/` 加载，绝不是 json）、以及工具 —— 全部作为**bundle** 原子化创建。

```bash
HOME=~/.treg-personas/bob treg skill add --dir /tmp/skills/echo-svc
```
```json
{
  "id": 1, "name": "echo-svc", "owner": "bob@superdesign.dev",
  "recipe": "# echo-svc\n…the SKILL.md…",
  "tools":   [{ "id": 2, "name": "echo-svc", "base_url": "https://postman-echo.com", "bundle_id": 1 }],
  "secrets": [{ "id": 2, "name": "echo-svc", "kind": "env", "bundle_id": 1 }]
}
```

**注意：** 所有东西共享一个 `bundle_id`，所以一个技能也作为一个单元删除。

---

# 第六部分 b —— 导入：魔法般的批量入口

上面的一切，但是一次性针对你的**整个环境**。这是填满一个团队注册表最快的方式。

## 步骤 22a —— 把你的整个 `.env` 变成工具

`treg upload env` 读你的 `.env`，把每个变量和 treg 认识的供应商匹配，并把你挑选的那些注册成随时可调用的工具。检测**只读取名字**；值只在你确认的 key 上加载。配置变量（`*_HOST`、`*_MODEL`、`*_PROJECT_ID`）和你 app 自己的 secret（`SECRET_KEY`、`SESSION_SECRET`、`DATABASE_URL`、`*_WEBHOOK_SECRET`）会被自动排除。

```bash
HOME=~/.treg-personas/bob treg upload env --select openai,stripe,resend
```
```text
Scanned .env: 6 key(s) to register, 1 OAuth, 4 other.
  ✓ openai         https://api.openai.com/v1   [Authorization: Bearer {secret}]
  ✓ stripe         https://api.stripe.com/v1    [Authorization: Bearer {secret}]
  ✓ resend         https://api.resend.com       [Authorization: Bearer {secret}]

Registered 3/3 tools.
```

**注意：** 一对 `CLIENT_ID`+`CLIENT_SECRET` 被检测为 **OAuth**，并提供一个引导式的 `treg oauth connect` 而不是一个会坏的 bearer key。其他认证形态也处理 —— 一个 API-key 头（`x-api-key`）、一个 query 参数 key（`?apiKey=`），或者一个 Basic 对（base64 `id:secret`）。

## 步骤 22b —— 导入一整个技能文件夹

把 `treg upload skills` 指向一个技能目录。对每个，它用已有的 `treg.json`，或者**从技能的脚本（base URL + 它读的 env 变量）构建一个** —— 把 API 技能注册为工具，把知识技能注册为仅配方的 bundle。整个团队库一次到位。

```bash
HOME=~/.treg-personas/bob treg upload skills --dir ~/.claude/skills --all
```
```text
Scanned ~/.claude/skills: 5 API-tool skill(s), 23 recipe-only.
  ✓ render          (tool)   [wrote treg.json]
  ✓ intercom        (tool)
  ✓ seo-blog-writer (recipe)
  …
Imported 27/28 skills.
```

随时重跑 —— 它会跳过已注册的（或用 `--replace` 来更新）。然后队友用 `treg skill install <name>`（或 `--all`）拉取其中任何一个，它会把配方写进他们的 `.claude/skills/`。裸 `treg upload`（没有 `env`/`skills`）对当前目录做**两件事**。

> **非交互安全：** 从 agent/CI（无 TTY）运行，且 upload 在没有 `--all` 或 `--select` 时会拒绝，所以凭据永远不会在无人值守时被意外注册。

---

# 第六部分 c —— 运行一个 CLI 工具

到此为止每个工具都是你 `call` 的 HTTP **API**。很多供应商也发布一个**命令行工具**（stripe、gh、gcloud…）。`treg run` 执行那个 CLI，注入组织的凭据 —— 所以一个队友使用它时*既不需要拥有 key 也不需要登录*。

## 步骤 22c —— 为一个 CLI 工具打开 `run`

因为一个 run 把凭据交给了机器，owner 先为每项工具选择加入（控制台的 **⌘ run** 开关是同一个开关）。这里 Tom 为 `stripe` 工具（其 id 来自 `tool ls`）启用它。

```bash
HOME=~/.treg-personas/tom treg tool update 4 --local-run on
```
```json
{
  "id": 4, "name": "stripe",
  "base_url": "https://api.stripe.com/v1",
  "cli": { "enabled": true }
}
```

**注意：** 默认关闭 —— 一个 run 比一个代理调用更强大，所以它是按工具选择加入的，而且只有 owner/admin 能切换。

## 步骤 22d —— 运行供应商 CLI（无登录，磁盘上无东西）

现在 Bob 通过 treg 运行 Stripe 真实的 CLI。所有在 `--` 之后的东西原样交给供应商工具。treg 仅为这次 run 注入凭据；Bob 从未登录 Stripe 或存储它的 key。默认档是 `--local` —— 它在 Bob 自己的机器上运行，在 Linux 上 key 被隔离在一个专用的 `treg-run` 用户下（用 `sudo treg setup-local-run` 安装一次；在 macOS 上是尽力而为）。服务端 CLI 执行被禁用；`--server` 返回 HTTP 503。

```bash
HOME=~/.treg-personas/bob treg run stripe -- get /v1/balance
```
```
{
  "object": "balance",
  "available": [{ "amount": 0, "currency": "usd" }],
  …
}
# Stripe 自己的 CLI 带着 org key 注入运行 —— Bob 从未登录或持有 key。
```

**注意：** CLI 用 `treg run <tool> -- <args>`；HTTP API 用 `treg call <tool> <path>` —— 同样的凭据，两种用法。

## 步骤 22e —— 每次 run 都有记录

像代理调用一样，本地 CLI run 也被审计。owner 用 `treg runs` 审阅；历史上的服务端 run 也仍可在那里读取。下面的例子是一个历史的服务端 run；新的服务端 run 已禁用。

```bash
HOME=~/.treg-personas/tom treg runs --limit 5
```
```json
[
  {
    "id": 1,
    "user_email": "bob@superdesign.dev",
    "bundle_name": "stripe",
    "argv": ["get", "/v1/balance"],
    "exit_code": 0,
    "duration_ms": 812,
    "created_at": "2026-07-02T…"
  }
]
```

**注意：** 助记符 —— `treg call` → `treg calls`；`treg run` → `treg runs`。两个动词，两个账本。

---

# 第七部分 —— Org 管理

## 步骤 23 —— 看团队

owner 列出每个人和他们的角色。改角色用一个 `user_id` 引用成员。

```bash
HOME=~/.treg-personas/tom treg org members
```
```json
[
  { "user_id": 1, "email": "tom@superdesign.dev",   "role": "owner"  },
  { "user_id": 2, "email": "bob@superdesign.dev",   "role": "member" },
  { "user_id": 3, "email": "alice@superdesign.dev", "role": "viewer" }
]
```

**注意：** 一条命令给出完整花名册。

## 步骤 24 —— 把 Bob 提升为 admin

只有 owner 改角色。让我们把 Bob 变成 **admin** —— 他能邀请/管理，但转移和删除仍是 owner-only。最后一个 owner 守卫阻止一个 org 变成无 owner。

```bash
HOME=~/.treg-personas/tom treg org set-role 2 admin
```
```json
{
  "user_id": 2,
  "role": "admin",
  "org_id": 2
}
```

**注意：** 一个原语（`set-role`）覆盖了提升、降级和所有权转移。

## 步骤 25 —— admin 权限实战

作为一个普通 member，Bob 不能邀请；作为一个 **admin** 他能。他邀请一个新队友。

```bash
HOME=~/.treg-personas/bob treg org invite dana@superdesign.dev --role member
```
```json
{
  "code": "<one-time-code>",
  "email": "dana@superdesign.dev",
  "role": "member",
  "org_id": 2,
  "expires_at": "2026-07-09T…"
}
```

**注意：** Bob 管理团队而不必是 owner。

## 步骤 26 —— 审阅待接受邀请

admin 看到 org 每个仍待接受的邀请。已接受、已撤销、已过期的被过滤掉。

```bash
HOME=~/.treg-personas/bob treg org invites
```
```json
[
  {
    "id": 3, "email": "dana@superdesign.dev", "role": "member",
    "invited_by": "bob@superdesign.dev", "expires_at": "2026-07-09T…"
  }
]
```

**注意：** 只有 Dana 显示 —— Bob 和 Alice 的邀请已接受，所以它们从列表里消失了。

## 步骤 27 —— 撤销一个邀请

计划有变 —— Bob 在 Dana 用之前杀掉她的邀请。这会硬删除那个码，让它永远不能被接受。

```bash
HOME=~/.treg-personas/bob treg org revoke 3
```
```json
{
  "revoked_invite": 3
}
```

**注意：** 在加入时：已过期 → `410`；已撤销 / 已用 / 未知 → `404 invalid or already-used invite`。

## 步骤 28 —— 角色门，从 viewer 这侧

Alice 是 viewer。她能调用工具，但她不能邀请 —— 那需要 admin+。她被拒绝。

```bash
HOME=~/.treg-personas/alice treg org invite eve@superdesign.dev --role member
```
```json
{
  "detail": "admin role in this org is required"
}
```

**注意：** 角色，干净地强制执行：**owner** > **admin** > **member** > **viewer**。

---

# 第八部分 —— 超级管理员

## 步骤 29 —— 成为平台运营者

超级管理员坐在 org *之上* —— 它读取并管理每一个租户。两种授权方式：平台 bearer `TREG_ADMIN_TOKEN`，或者一个被标记 `is_superadmin` 的用户。我们用 bearer，从 `.env` 读，所以它从不出现在屏幕上。

```bash
treg admin login --token "$(grep -E '^TREG_ADMIN_TOKEN=' .env | cut -d= -f2-)"
```
```
admin token saved
```

**注意：** 由 `require_superadmin` 把关，与 org 角色分离：普通 token → 403，无 token → 401。

## 步骤 30 —— 整个平台一览

一次调用给出跨每个租户的总计 —— 单个 org owner 看不到的图景。外加 `admin orgs / users / tools / health` 做跨租户清单。

```bash
treg admin stats
```
```json
{
  "totals": { "users": 3, "orgs": 4, "tools": 2, "secrets": 2, "calls": 1 },
  "...recent-activity + distributions...": "..."
}
```

**注意：** 门户就绪的 JSON：按 injector/host 的分布、凭据健康度汇总、调用量、以及增长计数。

## 步骤 31 —— 每个 org，跨所有租户

跨租户可见性：Superdesign 带着它的成员 + 工具，加上每个人的个人 org。

```bash
treg admin orgs
```
```json
[
  { "id": 2, "slug": "superdesign", "name": "Superdesign", "members": 3, "tools": 2 },
  { "id": 1, "slug": "tom-superdesign-dev", "members": 1, "tools": 0 },
  { "id": 3, "slug": "bob-superdesign-dev", "members": 1, "tools": 0 },
  { "id": 4, "slug": "alice-superdesign-dev", "members": 1, "tools": 0 }
]
```

**注意：** 一个支持控制台或账单门户之后所坐落的接缝 —— 同样的 JSON，只是被渲染出来。

## 步骤 32 —— 授予一个真实用户超级管理员

环境 bearer 做引导；然后你提升具名用户，让他们用自己身份 token 抵达 `/admin/*` —— 没有要传来传去的共享 secret。

```bash
treg admin grant 1
```
```json
{
  "user_id": 1,
  "is_superadmin": true
}
```

**注意：** 授予之后，Tom 普通的身份 token 就能在 `admin` 命令上工作 —— 而且控制台的 Admin 面板为他亮起。

---

# 第九部分 —— 控制台

## 步骤 33 —— 同一个注册表，在浏览器里

打开 **treg.to** 并用**邮箱码**门登录（和你在终端里用的同一个）：输入邮箱 → 点击 **Email me a sign-in code** → **查收收件箱**里的 6 位码 → 粘进去并 **Sign in**。你落到团队 org —— Tools 显示 `echo` 工具，Activity 显示那次调用，而且（因为 Tom 现在是超级管理员）出现一个 **Admin** 面板。

```bash
open https://treg.to/
```
```
# Sign in with email → land on Superdesign
#   Tools    → the echo tool (Copy a snippet · Try it live)
#   Activity → Alice's GET echo · 200
#   Admin    → cross-tenant stats + orgs (super-admin only)
```

**注意：** 控制台今天是读 + 调用；创建/邀请/注册留在 CLI（控制台写界面是第二阶段）。

---

# 第十部分 —— 清理

## 步骤 34 —— 删除工具

Bob（它的创建者，且是 admin）移除工具。绑定的 secret 留下 —— 只删工具。一个 member 不能删队友的资源。

```bash
HOME=~/.treg-personas/bob treg tool rm 1
```
```json
{
  "deleted": 1
}
```

**注意：** 删除顺序很重要：在它用的 secret 之前先删工具（或它的 binding）。

## 步骤 35 —— 删除 org（完整级联）

终章。删除一个 org 是 owner-only 且**按名确认** —— 你必须输入 slug，而且它必须是你的激活 org。级联移除所有成员关系、工具、secret、bundle、邀请和审计行。

```bash
HOME=~/.treg-personas/tom treg org delete superdesign
```
```json
{
  "deleted_org": 2
}
```

**注意：** Bob 和 Alice 保留他们的个人 org —— 它们从头到尾就是分开的租户。这就是完整的生命周期：登录 → 团队 → 邀请（两扇门）→ 角色 → 工具 → 代理调用 → 审计 → 管理员 → 拆除。🏁

---

## 附录 A —— 四种认证形态

| 形态 | 谁 | 如何 | 头 |
|---|---|---|---|
| **身份 token** | CLI 上的人 | `treg login`（GitHub）或 `treg login --email`（OTP） | `X-Treg-Token: <identity>` + `X-Treg-Org: <slug>` |
| **每 org token** | agents / CI | 在 `org create` / `org join` 时烤进一个 org | `X-Treg-Token: <org-token>`（org 是隐式的） |
| **会话 cookie** | 控制台 | GitHub 或邮箱码登录设置一个签名的 HttpOnly cookie | cookie + `X-Treg-Org: <slug>` |
| **Admin bearer** | 平台运营者 | `TREG_ADMIN_TOKEN`，或者一个被标记 `is_superadmin` 的用户 | `X-Treg-Token: <admin>` 在 `/admin/*` 上 |

## 附录 B —— 命令参考

```
treg login [--email you@x.com | --token <t>]   # 登录（默认 GitHub；邮箱 OTP；或原始 token）
treg logout                                     # 清除你的凭据
treg invites                                    # 寄给你的邀请（无码）
treg accept <org-slug>                          # 接受一个寄给你的（无码）

treg org create "<Name>"                        # 建一个团队，成为 owner
treg org ls | org use <slug>                    # 列表 / 切换激活 org
treg org invite <email> [--role viewer|member|admin] [--expires-days N]
treg org join <code> --email you@x.com          # 码门（如果是新的会创建你）
treg org members | set-role <user_id> <role>    # 花名册 / 改一个角色（owner）
treg org invites | revoke <invite_id>           # 列表 / 杀掉待接受邀请（admin+）
treg org leave | delete <slug>                  # 自行移除 / 删除（owner，按名确认）

treg secret add <name> (--value V | --file F | --dir D) [--kind env|oauth|...]
treg tool add <name> --base-url URL (--secret ID | --bind '...' | --binding '<json>')
treg secret ls | rm ID | update ID …            # tool ls | rm | update 同理
treg call <tool> <path>  |  call <full-url>     # 代理一次调用（具名或 agent 原生）
treg calls [--limit N]                          # 调用审计日志

treg run <tool> -- <cli args>                   # 在本地运行供应商 CLI 并注入 key（--server 已禁用）
treg runs [--limit N]                           # CLI run 审计日志
treg tool update <id> --local-run on|off        # owner 选择加入：允许/禁止一个工具的 `treg run`
sudo treg setup-local-run                       # 一次性：把本地 run 隔离在 treg-run 用户下（Linux）

treg skill init --dir D | skill add --dir D | skill ls | skill rm ID
treg admin login --token T | stats | orgs | users | tools | health | grant/revoke ID | …

全局：--org <slug> 在任何单条命令里运行于那个 org 而不是激活的那个。
```

`register` 命令已退役 —— `login` 既是注册也是登录。多用户 demo 用**邀请路径**（`org invite` → `login`/`invites`/`accept`，或 `org join <code>`）。
