# DeepSeek Harness 套件

[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（`dsh`）是一个建立在"一切皆插件"之上的编码 agent。它是同一个技能的第四个橱窗，也是唯一一个能在一次零配置安装里同时发出连接器**和** CLI 路径的橱窗。

## 安装

```bash
dsh plugin --profile <name> add github:superdesigndev/treg
dsh --profile <name>
```

## 为什么没有清单

dsh 不读取 `plugin.json`。它安装一个 **`package.json` 声明了 `dsh.bundle`** 的 npm 包，指向一层 `cordis.patch.yml` 配置，并把那个 bundle 追加到该 profile 的 `dsh.profile.bundles` 列表。各层按列表顺序组合，所以用户可以用自己的 profile patch 覆盖我们随包发出的任何一行，而无需动这个包
（[publish.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md)）。

```
package.json                  bundle 清单 —— `dsh.bundle.patch`
dsh/cordis.patch.yml          该层：技能行 + MCP 行
dsh/index.js                  一个覆盖下面这棵树的 ctx.skills provider
dsh/skills/treg/SKILL.md      GENERATED —— 永远不要手工编辑
```

## MCP 行在没有 token 之前是禁用的

Claude Code 与 Cursor 插件把 treg 的 MCP 服务器声明为仅 URL，并让宿主运行 OAuth，所以它等待登录。`@deepseek-ai/dsh-mcp-client` 用 `requestInit.headers` 且没有 `authProvider` 构建它的 Streamable HTTP 传输，所以它即便其 MCP SDK 能跑 OAuth 也不跑（已通过 `0.2.1-rc.4` 与 master 检查；npm 上 `latest` 仍指向 `0.0.1-rc.1`）。所以一个在还没有 token 时就注册的行的后果是五个永远在线的工具，每次调用都 401。一个 dsh 行带有一个在启动时求值的 `disabled` 表达式：

```yaml
- id: treg-mcp
  name: '@deepseek-ai/dsh-mcp-client'
  disabled: !!js !process.env.TREG_TOKEN
```

所以一个环境里带有 `TREG_TOKEN` 的用户在启动时就得到 `mcp__treg__catalog_search` 及同类工具，而其他所有人得到一个干净的安装有且一个技能带着他们走 `treg login`。该行在**启动时**求值，所以之后才导出的 token 需要一次 `dsh` 重启 —— 引导程序就是这么说的，因为一个等着本会话不会出现工具的人正是失败模式。

`treg mcp install` 刻意*不*在这条路径里：它写 Claude Code、Cursor 和 opencode 的配置（`mcp_install.py`），而 dsh profile 都不是这些。`treg mcp install` 在检测到 `~/.dsh` 时会打印那条指令，而 dsh 引导程序会避开它。

## `dsh/index.js` 上的两个约束

**没有构建步骤。** `dsh plugin add github:...` 取的是源码，不是构建产物。一个 TypeScript 包会需要一个 `prepare` 脚本，而 pnpm ≥10 在用户往 profile 的 `pnpm-workspace.yaml` 加了 `allowBuilds` 条目之前，拒绝从 git 依赖运行它 —— 也就是说，文档化的安装命令对每个人首次运行都会失败。纯手工写的 ESM 绕开了它。

**没有 `@deepseek-ai/*` 依赖。** 显而易见的实现是用 `customSkillDirs` 挂载内置的
`@deepseek-ai/dsh-skill-filesystem`，但一个树外的 bundle 依赖一个内置包会安装第二份，从而与宿主的那份漂移。provider 的 `list`/`get` 契约是稳定的接缝，所以 `index.js` 直接实现它 —— 正是 `dsh-skill-badge` 用于其自带技能的那种形态。`tests/test_plugin.py` 把这两个约束都固定下来。

技能的 `description` 在运行时从 `SKILL.md` 解析出来，而不是在 JS 里重述，所以没有第二份会腐坏。

## 发现

插件通过 [`dsh-plugin`](https://github.com/topics/dsh-plugin) 这个 GitHub topic 被发现，那正是生态目录（awesome-dsh-plugin、dsh.tools）同步的来源。topic 设置在本仓库上；向那些目录提一个上架 PR 是人工的那一半。
