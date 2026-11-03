# Claude Code 插件，以及它在哪里被上架

treg 以 Claude Code 插件的形式发布，由本仓库作为它自己的市场（marketplace）提供：合并的那一刻即上线，中间没有审阅者参与。它安装 treg 技能与 treg 的远程 MCP 服务器。

## 安装

```
/plugin marketplace add superdesigndev/treg
/plugin install treg@treg
```

然后 `/mcp`，选择 `plugin:treg:treg`，并验证身份。服务器被声明为仅 URL 形式，带 `type: "http"`；Claude Code 自己运行 OAuth，所以安装**不需要 token，也不需要配置**。在登录之前，服务器被列为"需要验证身份"，不提供任何工具，因此这段时间里没有任何东西会收到 401。

技能会先检查工具是否存在，并在缺失时把人引导到 `/mcp`。CLI（`curl … install.sh | sh`、`treg login`）仍然是可选的：插件路径从不要求 agent 运行一个下载下来的脚本，而 Claude Code 的 auto 模式默认会拦截这种行为。

## 什么东西在哪

```
.claude-plugin/marketplace.json          使本仓库成为它自己的市场：treg 加工作流插件
plugins/treg/.claude-plugin/plugin.json   Claude Code 读取的清单，内联 MCP 服务器
plugins/treg/.cursor-plugin/plugin.json   Cursor（与 Grok Bot）读取的清单
plugins/treg/mcp.json                     Cursor 的仅 URL MCP 配置
plugins/treg/skills/treg/SKILL.md         GENERATED —— 插件自带的技能
plugins/workflows/<name>/                 GENERATED —— 每个工作流技能一个可选插件
skills/treg/SKILL.md                      GENERATED —— 供 `npx skills add` 与 ClawHub 使用的裸技能
skills.sh.json                            skills.sh / Hermes' Skills Hub 的分类分组
```

Claude Code 与 Cursor 通过各自的清单安装**同一个文件夹** `plugins/treg/`。
市场的 `source` 必须保持 `./plugins/treg`：若 source 为 `./` 会把仓库根目录当作插件，从而把整个仓库以及 `skills/` 下的每个工作流技能都随包发出去。

工作流技能（`lead-signals`、`recruit`、`make-ugc`、`web-access`、`jev-memory`）是同一市场里的独立插件，由 `scripts/build_plugin.py` 生成各自的清单与市场条目，所以 `/plugin` 会一个一个地提供它们，而不是和 treg 一起安装。插件的技能会告诉 agent，当任务匹配时去提供其中一个。

MCP 服务器内联在 Claude 清单里，而不是指向 `mcp.json`，因为 Claude Code 会拒绝一个带 `url` 却没有 `type` 的服务器（它会记录"Invalid MCP server config"且什么都不注册），而 `mcp.json` 对读取它的那些宿主保持仅 URL 形式。

被服务页面的一节会根据 agent 拥有什么来分支：treg 的 MCP 工具、treg CLI，或都没有。只有最后一种会安装任何东西，且只在人要求配置时才装。所以仓库根的裸技能就是那份服务页面（原样），而插件前面加的提示只说它的工具正在等待 `/mcp` 登录。

**永远不要编辑 `skills/treg/SKILL.md`。** 改 `src/treg/web/skill.md` 然后重新生成：

```bash
uv run python scripts/build_plugin.py            # 重新生成每个插件
uv run python scripts/build_plugin.py --check    # 任何一个过期就失败（也是一项测试）
```

## 上架操作手册

按顺序排列，以便所有自助渠道都在任何排队渠道之前上线。

### 1. 自有市场 —— 合并即上线

无需提交任何东西。合并到 `main` 就发布它；上面的安装指令开始生效。

把 `pyproject.toml` 与每个清单的 `version` 一起提升：`test_plugin_version_tracks_the_package` 把所有版本固定到同一个值。

### 2. ClawHub (clawhub.ai) —— ✅ 已上线，自助，基于 CLI

**发布于 2026-08-14：[clawhub.ai/superdesigndev](https://clawhub.ai/superdesigndev) · `treg@0.11.0`
· owner `@superdesigndev` · MIT-0。** 通过把它从注册表重新安装到一个临时目录来验证 —— 交付的 `SKILL.md` 与本仓库里的 `skills/treg/SKILL.md` 逐字节一致。

发布者组织是用
`clawhub publisher create superdesigndev --display-name "Superdesign dev, Inc."` 创建的。用个人 handle 发布本来也行 —— `--owner <handle> --migrate-owner` 之后可把技能迁走 —— 但公司 handle 读起来像产品上架，而不是副业项目。


`https://clawhub.ai/submit` **返回 404**（Hermes 的 CLI 仍指向那里；它的 `--to clawhub` 是个桩）。可用的路径是 npm CLI：

```bash
npm i -g clawhub
clawhub login                     # 设备流；打开浏览器（--no-browser 打印 URL + code）
clawhub whoami                    # 发布前确认

clawhub skill publish "$PWD/skills/treg" \
  --slug treg --name "treg" --version 0.11.0 \
  --changelog "..." \
  --topics "api,seo,serp,backlinks,enrichment,scraping,agent-tools,web-search" \
  --source-repo superdesigndev/treg \
  --source-commit "$(git rev-parse HEAD)" \
  --source-ref main --source-path skills/treg \
  --dry-run                       # 去掉 --dry-run 即真实发布

# 发布分两个阶段。上面的命令只 SUBMIT —— 该版本停在
# `pending.publication`，在所有公开界面不可见，直到一个 scan 被附加到它上面：
clawhub scan --slug treg --version 0.11.0 --update    # 约 37 分钟；让它跑完
```

**不要跳过第二条命令，也不要在它运行时就断定发布失败。** 这是关于 ClawHub 最不显然的一件事，而且不在它们的文档里。`clawhub skill publish`
报告 `"status": "pending-publication"` 然后退出；没有别的会自动发生。`scan --update`
（"把已发布的扫描结果写回所选版本"）不是可有可无的便利 —— 它是完成发布的那个步骤。盯着审核记录翻转：

```bash
curl -s -H "Authorization: Bearer $(clawhub token)" \
  https://clawhub.ai/api/v1/skills/treg/moderation
```

| | `scan --update` 之前 | 之后 |
|---|---|---|
| `legacyReason` | `pending.publication` | `scanner.llm.review` |
| `reasonCodes` | `[]` | `["review.llm_review"]` |
| 公开的 `GET /api/v1/skills/treg` | 403，隐藏 | 返回该技能 |

注意 `package publish` 有 `--wait` 标志，会轮询到确定状态；**`skill publish` 没有**，而且 `/api/v1/publish/attempts/<attemptId>` 对 skill 尝试返回 404。所以技能根本没有任何进度指示 —— 运行 `scan --update` 然后等它跑完。

已对照 clawhub CLI **v0.23.3** 验证 —— 已发布的文档比真实的 `--help` 要薄，所以请读 CLI：

- **传一个绝对路径。** 相对的 `./skills/treg` 会因 `Path must be a folder` 失败，因为路径是相对 `--workdir` + `--dir`（默认 `skills`）解析的，于是它去找 `skills/skills/treg`。`"$PWD/skills/treg"` 是可靠的形式。
- **`--source-*` 这些标志值得填。** 它们把上架链接回一个 GitHub 仓库、commit 和路径。那是一个注册表所能提供的唯一溯源信号，而它自己的审查历史正是 Hermes 把每个 ClawHub 技能标记为 `community` 信任的原因。
- **`--categories` 接受公开 API 不枚举的 slug**（`/api/v1/categories` 返回 404，列表返回时 `categories` 为空）。不要自创一个 —— 用 `--topics`，它是自由格式的，直到能从一个实际上架读到真实分类 slug。
- `--dry-run --json` 会在不发布的情况下打印解析出的 slug、版本、文件数与指纹。`latestVersion: null` 表示该 slug 未被占用。
- 发布不是不可逆的：`clawhub delete` 软删除一个技能或撤回某个版本，还有 `clawhub hide` / `undelete`。所有权之后可以用
  `--owner <handle> --migrate-owner` 转移，所以现在用个人 handle 发布不会把这个技能挡在日后的 `superdesigndev` 组织之外。

生成的技能已经满足的要求：frontmatter 的 `name` + `description` + semver `version`，且 `name` 与父目录（`treg`）匹配。发布后运行一次安全扫描；被标记的发布会从公开目录隐藏，但仍留在你的控制台。

⚠️ **ClawHub 强制每个技能用 MIT-0，且没有按技能覆盖的选项。** 本仓库是 Apache-2.0 加一个托管服务限制。`SKILL.md` 是散文 —— 它记录一个托管服务而不是实现它 —— 所以宽松地授权这一个文件与"希望它被到处复制"是一致的。这是一个有意为之的选择，不是疏忽；不要让它漂移成对服务端代码的声明。

这里上架也会自动喂给 Hermes 的 Skills Hub。注意 Hermes 在 2026 年 2 月"ClawHavoc"事件（341 个恶意技能）之后，把所有 ClawHub 技能硬编码为 `community` 信任，所以这是一个发现渠道，而不是信任信号。

#### 两种裁定，只有一种控制可见性

不要混淆这两者 —— 搞错了其中一种的代价是一天时间：

- **Moderation**（`/api/v1/skills/treg/moderation`）是隐藏或显示技能的东西。我们的是
  `verdict: "clean"`、`isSuspicious: false`、`isMalwareBlocked: false`、空的 `reasonCodes`。读 CLI 源码可知：`isSuspicious` 只打印一个安装时警告，`--force` 可绕过；只有
  `isMalwareBlocked` 会硬屏蔽。
- **`clawscan`**（`clawhub scan`）是一个作为**上架上的建议**发布的 LLM 评审。它把 treg 评为 `suspicious` —— 而这丝毫没有改变可见性。

v0.11.0 的建议对 `SKILL.md` 提出了四项发现。三项重申了有意为之的产品决策；**有一项值得按其本身的是非来权衡，与 ClawHub 无关**：

| id | sev | 它说了什么 |
|---|---|---|
| `PE3` | **HIGH** | `cli_auth` 消费来自 CLI 钥匙串的材料并转发它 —— "在没有强而显式的同意边界的情况下扩展了 agent 的凭据访问面……"。建议的修复：在使用钥匙串派生的凭据前按工具选择加入，并优先用有作用域的服务 token。 |
| `SQP-1` | MEDIUM | frontmatter 的 `description` 足够宽泛，会让技能被松散相关的任务选中 |
| `SQP-2` | MEDIUM | `curl … \| sh` 执行远程代码，没有校验和或签名 |
| `EA2` | MEDIUM | "问一次，而不是每条命令都问"的指引不鼓励按命令批准 |

`EA2` 和 `SQP-2` 是 treg 有意为之的权衡。**`PE3` 是对一个真实功能的真实描述**，值得做一个决策而不是草草否定 —— 见 `docs/context/architecture/` 了解 `cli_auth` 是如何绑定的。静态分析与 VirusTotal 都返回干净。

### 3. Skill Store (aiskillstore/marketplace) + skills.sh

**不要对 `aiskillstore/marketplace` 开 pull request。** 它的 README 写得很明白 —— *"添加技能的 PR 会被关闭"*；该仓库由平台自己的审查流水线写入，而不是由贡献者写入。请通过表单提交：

> <https://skillstore.io/submit> —— 一个必填字段，且它接受一个**目录**，所以给它：
> `https://github.com/superdesigndev/treg/tree/main/skills/treg`

GitHub 认证是可选的（它只增加审查通知）；允许匿名提交。那边的审计是**仅报告** —— 一个风险发现不会阻止发布。这仍然值得做，因为 `aiskillstore/marketplace` 是 Hermes 的 `KNOWN_MARKETPLACES` 里仅有的两个仓库之一，所以它进入 Hermes 的 `claude-marketplace` 来源成本最低。注意 `npx skillstore` 是只装不提 —— 没有 CLI 提交路径。

**skills.sh / `npx skills` —— 永远传 `-s treg`：**

```bash
npx skills add superdesigndev/treg -s treg     # ✅ 只要 treg 这一个技能
npx skills add superdesigndev/treg             # ❌ 安装了九个技能
```

在临时机器上验证过：裸形式会扫描整个仓库，找到 `.agents/skills/*` 和 `skills/treg/`，并把这个仓库的**内部开发技能**（`dev-local`、`tools-registry-context`、`write-provider-skill`、`add-oauth-provider`、`vendor-listing`、三个 Google 供应商技能）和 treg 一起装进用户的 agent。这是我们的布局泄漏进了一个产品安装。`skills.sh.json` 无法阻止它 —— 它只提供分类标签。

`-s treg` 把它限定到一个技能，也是我们所发布的每条安装指令都必须带的。带上它，那一条命令仍能覆盖 Claude Code 之外的 70+ 个编码 agent。

### 4. anthropics/claude-plugins-official —— 排队

在 <https://claude.ai/settings/plugins/submit> 提交。信任度最高的位置，且它也喂给 Hermes。它是一个审查队列 —— 和 MCP 渠道一样有"耗时太久"的风险 —— 这正是它排最后的原因：到它归档时，上面的一切都已经在上线了。

该目录里的条目用 `git-subdir`，带固定的 `ref` **和** `sha`，所以身处这个 monorepo 内部不是阻碍。**打一个发布标签并把标签给他们。**

## 第四扇门：treg.to 本身

`GET /.well-known/skills/index.json` + `/.well-known/skills/treg/SKILL.md`（在 `src/treg/api.py` 里）
使这个主机成为 agentskills.io 约定下的一个一等技能来源 —— 没有注册表、没有审查、没有第三方。Hermes 直接读它。因为它走的是和 `/skill.md` 相同的 `_serve_md`，`{BASE}` 会被模板化为**服务**主机，所以一个自托管的注册表宣传的是它自己，而不是 treg.to。

## 在任何地方提交之前

- `uv run --frozen python -m pytest tests/test_plugin.py tests/test_skill_md.py -q`
- `claude plugin validate .` —— 以 Claude Code 自己解析的方式校验市场清单，能抓出 JSON schema 抓不到的形状错误。
- 从一个干净的克隆真正安装它，因为读着正确的标记仍可能坏掉：

  ```bash
  git clone --depth 1 https://github.com/superdesigndev/treg /tmp/treg-check
  claude plugin marketplace add /tmp/treg-check
  claude plugin install treg@treg
  claude plugin details treg@treg     # 然后：uninstall + marketplace remove
  ```

  `details` 必须报告 **Skills (1) treg** 和 **MCP servers (1) treg**，但它会数到一个 Claude Code 后来会拒绝的服务器。`claude mcp list` 才是真正的检查：它必须列出
  `plugin:treg:treg: https://treg.to/mcp/ (HTTP) - ! Needs authentication`。
- `claude plugin tag` 创建 `treg--v{version}` 发布标签，并校验 `plugin.json` 与外层市场条目一致 —— 在把一个标签交给 Anthropic 之前值得跑一下。
- 确认文案仍然说 treg **对比**供应商，由调用方选择。treg 不路由，也不故障转移；落地页曾经为此声明纠过一次，而商店上架更难纠正。`test_the_listing_does_not_promise_routing` 守护这一点。
- 确认一句话定位在三处完全一致（`test_one_product_one_sentence`）。
