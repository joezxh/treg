---
title: Local CLI runs — 用服务端持有的凭据，以专用用户身份运行供应商 CLI（`treg run`）
status: shipped
sources:
  - src/treg/localrun.py
  - src/treg/egress.py
  - src/treg/fsjail.py
related:
  - interface/api.md
  - interface/cli.md
  - interface/env-import.md
  - interface/shell.md
  - architecture/auth-secrets.md
  - architecture/data-model.md
---

# Local CLI runs（`treg run --local`，本地 CLI 运行）

一个成员在他们自己的机器上运行一个供应商 CLI（`stripe`、`gh`、`flyctl`、`gcloud`……）而凭据仍由 treg 保管。安全目标：**同一用户的其他程序在 CLI 运行时不得读取该凭据**。

> 服务端的 CLI 执行（`--server`）已被全局禁用：`POST /run` 返回 503。本片段覆盖 **`--local`**（默认）层。

## 为什么是专用用户（两个死胡同，简述）

两个更便宜的想法在真实 Linux 上测试过并被拒绝：
- **`PR_SET_DUMPABLE=0` 在 exec 之前** — 不起作用：`execve` 重置该标志，因此被 exec 的 CLI 再次可读。
- **无 root 的 bubblewrap** — 不起作用：你拥有你创建的用户命名空间，因此你仍能读入它（它映射到你相同的 uid）。

只有在一个**真正不同的用户 id** 下运行 CLI 才能对成员隐藏它的环境与时序（已证明：一个不同 uid 进程的 `/proc/<pid>/environ` 成员不可读；只有 root 可读）。因此 `treg run` 以一个专用的 **`treg-run`** 系统用户运行 CLI —— MongoDB 模式。

## 流程

1. 成员的 `treg run <tool> -- <args>`（瘦客户端）通过 `sudo -u treg-run <runner>` 移交给 `treg-run` 用户，把成员**自己**的 treg 令牌通过环境（`TREG_RUN_TOKEN/BASE/ORG`，由安装时的 sudoers 规则保留）传递。`sudo` 连接终端，因此输入、输出、信号与退出码自然流动。
2. **runner**（作为 `treg-run` 运行，`cmd_run_helper` → 隐藏的 `__run-helper`）用成员的令牌调用 `POST /tools/{name}/grant`，接收凭据，用它运行 CLI，并报告结果。**供应商凭据只存在于 `treg-run` 下** —— 成员从不持有它。安装（`treg setup-local-run`，一次，作为 admin）创建用户、安装 runner，并添加一个窄 sudoers 规则，允许成员**仅**以 `treg-run` 运行那个 runner（绝不是一个 shell）。
3. 没有该安装时，`treg run` 回退到以成员身份运行，**尽力而为**，带一个明确警告：强隔离未激活。Windows 尚未覆盖。

**隔离现在在 macOS 上也工作，不只 Linux。** `cmd_setup_local_run` + `_create_run_user` 在 Linux 上通过 `useradd`、在 macOS 上通过 **`dscl`** 创建 `treg-run` 用户（一个隐藏的服务账户，带来自 `_pick_macos_service_uid` 的空闲系统 uid），且 `_run_local` 在**两者**上通过 `sudo -u treg-run` 移交。一个不同的 uid 正是隐藏凭据的东西：一个成员不能读另一个 uid 的 `/proc/<pid>/environ`（Linux）也不能读它的任务端口（macOS 上 `task_for_pid` 跨 uid 被拒绝，即使对非授权进程上的 root）。一个安装时检查在该成员自身 `0700` 家目录内警告如果 `treg` 自身居住其中 —— `treg-run` 无法遍历进入去 exec 它，因此 treg 必须安装在**系统可访问路径**（隔离对抗它自己的启动器）。

权衡（一个真实边界固有的）：CLI 以 `treg-run` 运行，因此它不能读成员的**私有**（仅所有者）文件或写成员拥有的文件；它仍能读世界/组可读文件。需要成员自身私有文件或 `localhost` 的命令不在受保护模式范围内。

## 服务端 — grant（`localrun.py`）

`localrun.py` 把 `sqlalchemy`、`sqlmodel`、`.crypto`、`.oauth` 与 `.models` 排除在其顶层导入之外（仅 `TYPE_CHECKING`，在 `render_grant` 内惰性加载），因为这些是仅服务端依赖且该模块必须可被轻量 CLI 安装导入（在 `pyproject.toml` 中的"Lightweight CLI modules"导入-linter 契约）。`render_grant(tool, profile, db, http)` 返回一个交付无关（delivery-agnostic）的列表：`{"items": [{via:"env", name, value} | {via:"argv", argv:[…]}], "ttl_seconds"}`。runner 在 `treg-run` 下把每个项应用到 CLI（环境变量或命令行标志）。一个 **oauth** secret 先被刷新（`oauth.ensure_fresh`）且只释放短寿命的**叶子**：注入项的 `secret_field` 必须在**允许列表**（`_OAUTH_RELEASABLE_FIELDS` = `access_token`/`token`）上，因此一个 grant 绝不能交出 `refresh_token` 或 `client_secret` —— 可重新签发的身份留在服务端（一个在 treg 第一次刷新前携带 `token`、之后携带 `access_token` 的 Google 式 blob 通过回退到兄弟键来处理）。值被 `.strip()`。

**一个 grant 可释放哪个 secret（`render_grant` 允许列表）。** 一个 grant 只释放属于该工具的 secret：它的某个 HTTP binding 的 `secret_id`、该工具自身 bundle 中的 secret（`Secret.bundle_id == tool.bundle_id`），或该工具所有者拥有的 secret（`secret.owner == tool.owner`）——总是同 org。没有这个，一个成员可以把一个注入项指向**另一个**用户的 secret id 并读取它的值（否则值绝不返回）。

**针对共享 key 的 runner 证明门。** `/grant` 端点通过 `X-Treg-Run-Proof` 头部区分来自隔离 runner 的调用与来自直接成员调用的区别（该值只有 treg-run 能读，来自 `/etc/treg-run/proof`，由 `setup-local-run --run-proof` 安装并导出为 `TREG_RUN_PROOF`）。一个成员总是可以运行一个 key 他们**自己拥有**的工具；一个**共享** key（他们不拥有的）只有在有效证明存在时才释放 —— 因此一个直接的成员 `/grant` 调用不能提取队友的凭据，但同一 key 通过隔离 runner 运行良好。没有安装证明时，只有自有 key 工具本地运行。`effective_profile` 把创建者的 `tool.cli` 合并在 catalog profile 之上（catalog 绝不启用 —— 只有 `tool.cli.enabled` 启用；拒绝列表取并集除非 `deny_defaults:false`；返回的列表被复制以便请求不能变异模块级 CATALOG）。`check_deny` 在服务端拒绝一个匹配的 argv，在那里 secret 居住。`validate_cli_profile` 在写时拒绝一个坏 profile —— 包括危险的 env 名（`_is_dangerous_env`：`LD_*`、`PATH`、`NODE_OPTIONS`……）、一个非裸 `bin`（`_BIN_RE`）、一个无 `{secret}` 的 `format`、不可编译的模式、超大列表，以及自动导入元数据（`auth_mechanism` 必须是 `AUTH_MECHANISMS` = `env|argv|config_file|device` 之一；`detect.config_paths` 一个非空字符串列表；`beta` 一个 bool）。`_resolve_secret_id` 对一个无显式映射的歧义多凭据工具返回 None（因此 grant 大声失败，绝不注入错误的 key）。

**`auth_mechanism` 描述凭据注入。** `env`/`argv` 注入一个值；`config_file` 读取 CLI 自身的 `~/.config`，且 `device` 使用它本地的授权流。`server_runnable`（`_tool_view`）在服务端执行被禁用时总为 false。认证机制也驱动 `treg upload clis` 路由（见 [env-import](../interface/env-import.md)）。

## 本地沙箱（围绕运行的纵深防御）

隔离的 uid 对成员隐藏凭据。再三层阻止它从 CLI *泄漏出去*：

**输出修订（共享 key 运行）。** 当调用方**不**拥有被注入的 key 时，grant 端点在响应上设置 `redact_output`（它复用同一个 `needs_proof` 决策）。客户端 `_StreamRedactor`（在 `cli.py` 中，由 `_run_helper` 驱动）然后在 CLI 的 stdout/stderr 到达终端之前把注入值擦除 —— 边界安全（它在读取间保留 `len(secret)-1` 字节以便一个跨块分割的值仍被捕获）。一个自有 key 运行无需擦除（你可以看到你自己的 key）并保持一个原始、无缓冲的 TTY。

**针对泄漏子命令的拒绝规则。** Catalog CLI 携带 `deny` 模式（在 `providers.CATALOG` 中，由 grant 时的 `check_deny` 强制，那里 secret 居住）拒绝会打印被注入 key 或作为 `treg-run` 运行成员代码的特性：`gh extension`/`alias`/`auth token`/`--show-token`、`flyctl|turso auth token`、`doppler|infisical run`、`doppler secrets download`、`infisical export`。一个创建者可以通过 `deny_defaults: false` 放宽它自己的列表。

**空注入 grant。** 一个自认证的本地层 CLI（自动导入：`gh`、`gcloud`、`vercel` —— 凭据住在 CLI 自身的配置中）注入**无物**。`render_grant` 为它返回 `{items: [], ttl_seconds: None}`（无 `ValueError`），因此 grant 有效且只返回 bin + 审计。自动导入在工具上存储一个显式的 `inject: []` 以便 `effective_profile` 的 catalog 合并不能重新添加 catalog 的注入 —— 这修复了一个 bug，其中 `gh` 的 catalog `GH_TOKEN` 注入在 grant 时泄漏回来且无法解析。

## 出口允许列表 — 沙箱的网络一半

隔离的 uid + 修订仍留一个通道：一个运行成员代码的 CLI 特性（一个插件、`doppler run`）继承了 key 且可以把它 `curl` 给攻击者 —— 一个既非修订（它在网络上，而非 stdout）也非拒绝（未知特性）完全阻止的泄漏。`src/treg/egress.py` 通过把 `treg-run` uid 的**出站网络**限制到一个固定的允许列表来关闭它。纯构建器：`collect_hosts(registry, catalog)`（注册表 —— 因此 runner 能到达 `/grant` —— 加上每个 catalog `base_url` 主机）、`resolve_hosts`（→ 当前 IPv4/IPv6）、`pf_ruleset`（macOS `pf` 每用户 `user treg-run` 规则 —— 已验证：macOS pf 支持 `user` 关键字 + IP 列表，因此来自该 uid 的恶意 `curl evil.com` 在包级别被丢弃而其他用户不受影响）、`nft_ruleset`（Linux nftables owner-match 在 `skuid`）。`_install_egress`（在 `cli.py` 中）现在解析 + 加载它们并持久化：macOS 通过一个 `LaunchDaemon`（`dev.treg.egress`）重新运行一个 root 拥有的加载器（`/usr/local/bin/treg-egress-load`，在启动时重新加载 Apple 的规则集 + `/etc/treg-run/egress.pf`）；Linux 写入 `/etc/treg-run/egress.nft`。安装标志：`--no-egress`（退出）、`--registry`（要允许的主机；否则成员配置的基础 URL）、`--refresh-egress`（见下）。这是选项 1 —— 一个**静态**允许列表在设置时设置一次；一个每运行动态规则（选项 2）因复杂性被拒绝。

### 出口允许列表 — 刷新 catalog IP（IP 轮换）

静态允许列表钉死**在安装时**解析的 IP。供应商与 CDN IP 漂移，因此一个 catalog 主机可以轮换到一个不在列表上的新 IP —— 然后一个合法调用被丢弃（或一个陈旧 IP 残留，无害）。补救是**重新解析**：`sudo treg setup-local-run --refresh-egress` 重新运行 `collect_hosts` → `resolve_hosts` → `_install_egress` 而不触碰用户/runner/sudoers。运维上这想要一个周期性刷新（cron / launchd 定时器）。**开放设计问题：** catalog 是否应携带每个供应商已知的 IP 范围（稳定，无每机器 DNS），或 treg 应发布一个自动刷新定时器。这种搅动是选项 1（静态 IP）固有的；那是针对选项 2 的每运行规则接受的权衡。

### 文件系统 jail（`treg run --fs-jail`，可选）

最后的通道：即使有 uid 隔离 + 出口，一个运行成员代码的 CLI 特性仍可能把 key **写**到一个成员随后读取的文件。`--fs-jail` 把运行的写限制到一个私有的每运行暂存区（0700，treg-run 拥有，作为 `HOME`/`TMPDIR` 指向），运行后移除。`src/treg/fsjail.py`：`macos_profile` 构建一个 seatbelt 配置文件（`allow default`，然后 `deny file-write*` 除了暂存子路径 + `/dev/`）；`wrap_macos` 前缀 `sandbox-exec -f <profile>`。`_run_helper` 读取 `TREG_RUN_FSJAIL`（由 `_run_local` 通过 sudoers `env_keep` 转发）并在 macOS 上应用它。可选加入因为它也阻塞一个 CLI 在成员想要的地方写合法输出文件。已在 macOS 上实时验证：jail 下的 `touch /tmp/x` → "Operation not permitted"；没有它 → 文件被创建。Linux（Landlock / mount ns）是一个后续 —— 构建器存在，接线不存在。

### 每成员门（访问控制特性）

在渲染一个 grant 之前，`grant_local_run` 也强制每成员 ACL：`_require_tool_access`（成员的 `tool_access` 必须为 NULL 或命名该工具）与 `_require_local_run`（成员的 `local_run_enabled` 必须为 true，否则"在服务器上运行"）。两者都门控 **LOCAL** 层；工具 ACL 也门控代理 `call` + 服务器 `run`。所有者豁免。见 [multi-tenancy](multi-tenancy.md)。

## 信任姿态

凭据住在 `treg-run` 下，成员 uid 不可读（只有 root 能读任何进程）。grant 是仅成员+（一个查看者可能通过代理调用 —— 那不泄漏任何东西 —— 但不能提取一个值），每个工具所有者选择加入（`cli.enabled`），完全审计（grant/deny/report，argv 修订掉 key 形令牌），且服务端拒绝检查。端点 + 客户端住在 [api](../interface/api.md) 与 [cli](../interface/cli.md)；catalog profile 在 [env-import](../interface/env-import.md)。
