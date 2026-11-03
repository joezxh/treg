# 在 treg 上架你的 API

treg 是面向 AI agent 的工具目录：约 2,600 个端点，覆盖约 40 家供应商，按*能力*（"获取某域名的反链摘要"）而非厂商名称被发现。Agent 搜索目录，按价格 / 实测成功率 / 速度把供应商并排对比，并通过 treg 的代理调用你的 API，凭据在服务端注入。

**上架能给你带来：**

- **被发现** —— 每个接入某个 treg 部署的 agent，在搜索你的 API 所能完成的任务时，都能找到你的端点，并和（且与）你的竞争对手并排对比。
- **零摩擦的客户** —— 连接自己密钥到你的 API 的团队会直接调用你；你保留计费关系。treg 永远不插在你和客户账号之间。
- **计量平台流量（可选）** —— 如果你的定价已公布且可被机器校验，treg 可以用*它自己的*密钥提供你的端点，按团队预付费余额逐次计量。这意味着从未在你这里注册的团队也会产生付费调用。见下方"平台资格"。

## 资格

你需要满足**全部**这些条件。它们之所以存在，是因为每个上架都要*实测*，而不是照抄：

| 要求 | 原因 |
|---|---|
| **自助 API 密钥** —— 注册、拿密钥、无需销售电话 | 整个上架流程在一个会话内完成；销售门槛限制的 API 无法被验证 |
| **密钥走 header 或 query 参数** | treg 以 header（首选）或 query 参数注入凭据。嵌在 URL 路径里的密钥不被支持 |
| **一个免费（或近乎免费）的探测端点**，对合法密钥返回 2xx，对非法密钥返回可区分的失败 | 连接时校验。我们会真的往你的 API 发一个垃圾密钥并观察它被拒绝 —— **接受任何密钥的 API 无法上架** |
| **已公布的定价**，且有稳定的 URL | 目录里的成本带有来源信息（`source_url`、`checked`、`confidence`）；"联系销售"的价格无法作为数字上架 |
| **核心端点的准确文档**：参数名、类型、必填标记，以及*示例*取值 | 每个上架的端点都会跑一次真实的测试调用；没有示例取值的文档无法被验证 |

强烈推荐（每一条都会直接改善你的上架）：

- **一个稳定 URL 上的 OpenAPI 规范** —— 让我们以机器方式生成你的*完整*端点面作为"扩展层级"（数百条路由），而不只是手工精选的核心 8–15 个。
- **一个机器可读的价格卡端点**（一条返回你当前各端点价格的 API 路由）—— 我们所能拥有的最强成本溯源，也是通往平台资格的最快路径。
- **按成功计费**（错误免费）—— 让验证和重试变便宜，并意味着坏掉的调用永远不会向 treg 用户收费。
- **已记录的速率限制**，包含按路由的限制，而不仅是账号级的限制。

## 需要发给我们什么

最快的路径：把控制台 Catalog 页面上 **"List as vendor"** 按钮的提示粘贴进你的编码 agent —— 它会遵循 [`/vendor-listing`](https://treg.to/vendor-listing) 上托管的说明并替你开 PR。或者你自己在本仓库开一个 issue 或 PR，包含：

0. **PR/issue 描述里的联系邮箱**（例如 `Contact: partnerships@yourapi.com`）—— 我们用它来安排一次测试凭据做实测验证；没有它的 PR 无法被验证或合并
1. `service` slug（小写）、展示名，以及一句话说明 agent 能**做什么**
2. `base_url`、认证机制（header 名 + 格式，或 query 参数名）
3. 探测端点路径 + 确切的错误密钥行为（状态码，或翻转的 JSON 字段）
4. 定价页 URL + 计费模型；如果你有的话，价格卡端点
5. 文档 URL；若已发布则附 OpenAPI 规范 URL
6. 你的 8–15 个核心端点，每个都带示例参数取值和一个廉价的测试目标
7. 一份测试凭据（或一小笔赠金），在我们联系后私下发送 —— **绝不要放在 issue/PR 里** —— 这样我们才能跑实测验证
8. **一份自我验证账本**：提交前，针对你自己的账号跑一遍每个 `test_request` 实测，并为每个端点记录 HTTP 状态、你的 YAML 声称的成本，以及你的计量器实际收取的成本（charge 字段、价格卡端点或余额增量），并注明日期。文档会漂移；计量器不会 —— 一份真实提交里，文档转录的价格比计量器实际收取的少了 5 倍。刻意未命中的测试目标必须明确标注，并附上在真实目标上观测到的一次命中价格。
9. **一份完整能力面地图**：每个有文档记载的操作，标注为已编目或已排除（含理由）—— 包括免费的计数/预览路由和你最便宜的操作层级，这些正是 agent（和审阅者）最先寻找的。

下面的示例是一个完整上架的形态。

## 实现示例 —— "Acme SEO"

一家虚构的供应商：Acme SEO 在 `https://api.acmeseo.example/v1` 售卖反链数据，密钥放在 `X-Api-Key` 头，有免费的 `/account` 路由，每次成功请求 $0.002，定价在 `https://acmeseo.example/pricing`。

### 1. 注册表条目 —— `src/treg/oauth_providers.py`

团队如何连接密钥，以及 treg 如何验证它是真实的：

```python
ACMESEO = OAuthProvider(
    service="acmeseo",
    display_name="Acme SEO",
    auth_kind="key",
    token_label="API key",
    token_placeholder="your Acme SEO API key",
    token_header="X-Api-Key",
    token_format="{secret}",
    setup_url="https://acmeseo.example/dashboard/api-keys",
    setup_action_label="Get your Acme SEO API key",
    setup_steps=(
        "Sign in to Acme SEO and open Settings → API Keys.",
        "Copy your API key.",
    ),
    setup_note="Backlink queries are billed per successful request; the account check is free.",
    auth_uri="", token_uri="",
    scopes={},
    client_id_setting="", client_secret_setting="",
    category="SEO",
    summary="Backlink profiles, referring domains and anchor texts for any domain or URL.",
    base_url="https://api.acmeseo.example/v1",
    docs_url="https://docs.acmeseo.example",
    probe_path="/account",  # free — a bad key gets a 401 here
)
```

……加入 `REGISTRY` 元组，外加 `src/treg/web/logos/acmeseo.svg` 里的一个中性字母标，以及两处测试列表的增加（`test_every_provider_is_registered`、`test_key_providers`）。

如果你的 API 即便对错误密钥也返回 HTTP 200，则条目改为命名那个能区分它们的 body 字段（`token_verify_field`、`token_ok_field`/`token_ok_value`，或 `token_reject_field`）—— 告诉我们确切行为，由我们选对的那一个。

### 2. 核心目录文件 —— `src/treg/catalog/acmeseo.yaml`

Agent 能做什么，带价格且可验证：

```yaml
provider: acmeseo                  # 必须等于注册表条目的 `service`
source:
  docs: https://docs.acmeseo.example
  openapi: https://api.acmeseo.example/v1/openapi.json
  curated: 2026-08-12
limits: "60 requests/minute per key"
pricing_url: https://acmeseo.example/pricing
endpoints:
  - id: acmeseo.web.backlinks.summary
    capability: web.backlinks.summary     # 跨供应商的连接键，来自 capabilities.yaml
    platform: web
    scope: any_account                     # 关于任何对象的数据，而非调用方自己的账号
    method: GET
    path: /backlinks/summary
    name: "Backlink summary"
    summary: "Aggregate backlink profile of a domain or URL"   # 厂商的原话，逐字
    input:
      queryParams:
        target: {type: string, required: true, note: "domain or full URL", example: "moz.com"}
        mode:   {type: string, required: false, note: "one of domain | url", example: "domain"}
    test_request:                          # 验证重放的廉价调用
      queryParams: {target: "moz.com", mode: "domain"}
    cost:
      type: per_success                    # 错误免费
      value: 0.002
      currency: USD
      source: docs
      source_url: https://acmeseo.example/pricing
      checked: 2026-08-12
      confidence: documented
    docs_url: https://docs.acmeseo.example/backlinks-summary
  # ……还有 7–14 个端点，形态相同
```

`capability` 字段决定了你被放在哪个对比货架上：一个 agent 请求 `web.backlinks.summary` 时，会看到每个实现了它的供应商，价格并排。如果你的 API 做的是分类体系里缺少的一项工作，该文件在 `proposed_capabilities:` 下提出它。

能力优先，对每个端点都如此：在写这个字段之前，先在 `capabilities.yaml` 和其他供应商文件里搜索这项任务，复用已有的 id 而不是近似重复的那个。只有当没有任何东西覆盖这项工作时才提出新的；如果另一家供应商已经有一个做这件事却未映射的端点，在 PR 里点名那个端点，让两者都挂上。重叠正是重点：共享一个能力的端点才是 agent 对比并在之间路由的对象。

### 3. 合并前我们会跑什么

你的自我验证账本能加速这一步，但永远不能取代它：供应商 PR 里的每一个声明 —— 价格、探测行为、证据 —— 都会用我们掌控的一份**独立**实测凭据重新核对。`verified:` 戳记与示例响应由我们添加到我们观察成功的东西上。一份与自己 YAML 不符的账本会退回 PR；一个与我们的计量器不符的价格会按观测到的收费更正。

```bash
# 1. 实时垃圾密钥测试：一个垃圾密钥 POST 到 /connections/token 必须被拒绝返回
# 2. 每个端点的 test_request 实时验证（用来自 env 的测试凭据）
TREG_CATALOG_CRED='<key>' uv run python scripts/catalog_verify.py acmeseo.yaml
# 3. Schema + 引用完整性
uv run python scripts/catalog_validate.py     # 必须退出 0
# 4. 完整测试套件
uv run --frozen python -m pytest -q
```

每个端点行还会携带 `added:`（它进入目录的 UTC 日期）。开 PR 前运行
`uv run python scripts/catalog_added.py`：它会给每个没有日期的行写上今天的日期。一个已有工具的日期永不改变。

通过验证的端点会得到一个 `verified:` 日期，以及一段被截断、已脱去 PII 的真实示例响应，提交到 `src/treg/catalog/examples/` —— 那段示例正是说服 agent 在供应商之间做选择的东西，所以通过验证就是上架的主要资产。

## 平台资格 —— 从 treg 自己的密钥获得付费调用

除了被发现，treg 还可以用其**自己的**密钥提供你的端点，按调用向调用团队扣预付费余额。一个端点符合资格当：

- 它的成本可用 USD 机器计算（一个具体的 `value`，或一个可换算的 credit/unit 费率），
- 价格的 `confidence` 是 `verified`（已观测计费，或从你的实时价格卡读取）或 `documented`（从你公布的定价转录），且
- 它不是一个 own-account 或账号管理路由。

资格是必要但不充分的 —— treg 还必须持有一个在你的平台上已充值的账号，并把你的服务加入允许名单，这是一个按供应商做的运维决策。最快的方式：发布一个价格卡端点、按成功计费，并给我们一笔验证赠金。

## 会被拒绝的情况

来自过往审阅、有记录的拒绝原因，以免有人白费一轮：

- API 接受任何密钥（无法校验连接）
- 密钥嵌在 URL 路径里
- 销售门槛限制 / 仅企业可访问
- 法律或关停风险；已弃用或被收购的产品
- 只有 UI、没有 API 的产品

## 保持你的上架健康

- **价格变了？** 告诉我们或在 PR 里改 `cost` 块 —— 过期价格在 90 天后会被标记。
- **路由变了？** 如果你发布了 OpenAPI，重新摄取会从规范重新生成你的扩展层级；精选核心文件是手工更新的，所以那里有破坏性变更需要提前告知。
- **成功率是公开的。** treg 会跨所有调用方聚合每个端点的实测成功率与延迟，并把它们和你的价格并排展示。可靠性就是你的排名。
