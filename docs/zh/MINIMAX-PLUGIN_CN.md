# MiniMax 插件，以及如何提交它

treg 的第五个橱窗：**MiniMax Plugin Marketplace**，同时服务于 **MiniMax Code**（桌面端）和 **MiniMax Agent**（云端）。和 Claude Code 与 Cursor 插件一样，它是**纯技能**的，而且原因比"方便"更硬：MiniMax 拒绝任何持有凭据的包，而 treg 的 MCP 是按用户做 bearer 认证的。一个经过认证的 MCP 必须走他们的 **App/Connector** 程序（OAuth MCP 服务器、PKCE、MiniMax 注册的客户端）—— 见下方"以后：一个 App"。

规则来源：MiniMax 的 *Plugin Development and Submission Guide*（飞书 wiki
`QlTLwbAGNiACwLkWI85cFxHzn4L`，最后更新 2026-08-17）。那是一个飞书登录后的 JS 渲染页面；要紧的规则被编码在 `scripts/minimax_plugin.py` 里。

## 什么东西在哪

```
plugins/minimax/
├── .minimax-plugin/plugin.json   manifest（schemaVersion 1）
├── icon.png                      512×512，▚ 标记 —— 与 plugin/assets/icon.png 同一文件
└── skills/treg/SKILL.md          GENERATED —— 永远不要手工编辑
scripts/minimax_plugin.py         validator（--check）与 ZIP 构建器（--zip OUT）
```

`plugins/minimax/` 是**插件根目录**（与 Cursor 根目录 `plugins/treg/` 同级；每个商店都需要自己的根目录，因为清单和生成的引导程序各不相同）：`.minimax-plugin/plugin.json` 直接位于其内，这正是 MiniMax 对 ZIP 根或 GitHub 子目录的要求。manifest 的 `name` 是 `treg`；该技能在运行时以 `treg:treg` 暴露。

**永远不要编辑 `plugins/minimax/skills/treg/SKILL.md`。** 改 `src/treg/web/skill.md` 然后重新生成：

```bash
uv run python scripts/build_plugin.py            # 重新生成所有插件
uv run python scripts/build_plugin.py --check    # 任何一个过期就失败（也是一项测试）
python3 scripts/minimax_plugin.py --check  # MiniMax 包规则（也是一项测试）
```

### 没有引导程序

该技能就是那份服务页面（原样）。它的第一节已经覆盖了既没有 treg MCP 工具也没有 CLI 的 agent，里面没有任何东西把 agent 送到 `treg mcp install`，而后者没有 MiniMax 目标。

### 他们的校验器强制了什么（以及我们预先检查了什么）

- 根目录下的 `.minimax-plugin/plugin.json` 在 ZIP 里**没有外层包装目录**。
- `name`：小写、以字母开头、`[a-z0-9._-]` 的 ≤80 字符。`version`：SemVer，**只要包内容改变就**必须 bump（仅 region/target 的改变可以保留）。我们的跟随 `pyproject.toml` —— `test_plugin_version_tracks_the_package` 固定它。
- `category` 来自固定列表（Office、Studio、Design & Sites、Code、Business、Sales、Productivity、Science & Healthcare、Education、Other）。我们用 **Productivity**。
- `exampleQueries`：0–3，非空，≤4,096 字符，*生产*内容。
- `apps` / `mcpServers` / `skills`：相对路径；**未使用的保持为空数组**。
- `icon`：相对路径，小写的 `.png/.jpg/.jpeg/.webp`，正方形。
- 技能：`skills/<name>/SKILL.md`，YAML frontmatter 的 `name` == 目录名且 `description` 非空；正文必须是可执行的指令，而不是营销。
- 路径仅 ASCII，`/` 分隔符。无符号链接、硬链接、LFS 指针、子模块、安装脚本、原生二进制文件、可执行位。无 BOM 的 UTF-8。JSON = 对象，无重复键。
- 限制：ZIP ≤64 MiB，≤2,048 条目，≤1,024 文件，≤16 MiB 每文件，路径 ≤512 B / 段 ≤128 B / 深度 ≤16。
- **任何地方都不得有 token、key、secret 或个人数据。**

该清单不带 `license` 键 —— 他们的 schema 没有定义，未知键是校验器风险。许可改在这里说明：`SKILL.md` 是关于一个托管服务的散文，按仓库的 Apache-2.0 发布（见 `LICENSE`）。

## 提交操作手册

接受两个来源，走同一条流水线。**优先用 GitHub** —— 没有需要管理的产物，更新就是新的 `Ref`。

**提交**（指南里链接的表单："Open the Plugin submission form"；需要飞书账号 —— 用一个团队保留的，之后查询状态必须用*同一个*账号）：

| 字段 | 值 |
|---|---|
| Action | Submit a new Plugin |
| Region | **US**（以及 CN，如果想要 —— 独立维度；treg.to 从 CN 可达，但计费用的是 Stripe） |
| Delivery target | **Desktop (MiniMax Code) + Cloud (MiniMax Agent)** —— 该技能是 CLI 驱动的，所以云端只有 Agent 沙箱能跑 `install.sh` 时才有用；两个都选，他们可以禁用其一 |
| Source | GitHub |
| Repo | `https://github.com/superdesigndev/treg` |
| Ref | `main`（或发布标签，如 `v0.12.1`） |
| Plugin subdirectory | `plugins/minimax` |
| Email | jason@superdesign.dev |

ZIP 备选 —— 确定性构建，无外层包装目录：

```bash
python3 scripts/minimax_plugin.py --zip treg-minimax-$(python3 -c 'import tomllib;print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])').zip
```

**提交后：**保存 `submission_id`。流水线：源冻结 → 脚本校验（失败以飞书消息返回） → 向 CN/US 市场 `main` 的 Release MR → 对 MR diff、Markdown 报告、图标、CI 的人工评审 → owner 合并 → 流水线打包 → 状态由飞书消息显示为 "Publishing" / "Published" / "Publishing failed"。状态查询需要提交用的飞书账号 + `submission_id` + 邮箱。

**更新：**`name` 保持 `treg`，bump `version`（发布 bump 会做这个），提供维护证明（GitHub 仓库就是证明），用新 Ref 重新提交。没有变更摘要 —— 他们 diff 这个 MR。

## 已知的评审风险

1. **技能里的 `curl … | sh`。** 包里没有安装脚本，但技能*告诉 agent 去跑一个*。ClawHub 的 LLM 评审标记了同一行（`SQP-2`，见 `docs/CLAUDE-PLUGIN.md`）。如果评审反对，回退是 `pip install treg` / `uv tool install treg` —— CLI 在 PyPI 上 —— 以及 `MINIMAX_BOOTSTRAP` 里一行替换。
2. **云目标。** 在 MiniMax Agent 上，技能只有在沙箱有一个带网络出口的 shell 并能为 `treg login` 打开浏览器时才有效（否则就指向他们用 device-code 登录）。如果云端没通过他们的验证，重新提交仅桌面端 —— 那是目录元数据变更，不需要 bump 版本。
3. **描述 vs 实现。** 他们的规则：说它解决什么问题，而不是怎么解决。manifest 的 description 只有能力；保持这样。

## 以后：一个 App

要把那五个 MCP 工具原生带进 MiniMax，treg 要进入他们的 **App/Connector** 轨道：在构建*之前*联系 MiniMax，提供测试 + 生产 Streamable-HTTP MCP 端点、带 discovery 元数据的 OAuth issuer、authorization/token/registration/revocation 端点、scopes、DCR/PKCE（S256）支持、刷新 token、callback 允许名单需求、一个测试账号、速率限制与错误码。然后 MiniMax 分配一个 `provider`，插件获得 `treg.app.json`（`{"schemaVersion":1,"provider":"treg"}`）。treg 的 MCP 目前用静态 bearer token 认证，他们的指南说要在开发*之前*和他们提 —— 所以这是一个产品决策（在 `/mcp/` 前放一个 OAuth AS），而不是打包决策。
