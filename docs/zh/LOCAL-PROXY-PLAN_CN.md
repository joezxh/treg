# 本地代理 —— 在不让 agent 知情的情况下截获它的调用（`treg serve`）

**状态：**已发布（P0–P5 + `treg serve`，分支 `feat/local-proxy`，2026-07-30）·**依赖：**一项小的服务端新增、`X-Treg-Error` 标记 · **v1 范围：**本地捕获，在服务端注入。

## 它解决的问题

treg 今天只有当 agent 被告知用它时才工作 —— `treg call …`，或者 `/call/` URL。一旦一个 agent 自己写了脚本直接调 `api.stripe.com`，treg 就不可见了，脚本也没有 key。

一个本地代理补上这个缺口：agent 发起一个普通调用，我们在出站路上截获它，然后由**服务端**加上凭据。agent 这边不需要任何改变。

## 我们从 oneCLI 拿走什么，又没拿什么

他们的设计是两半可分离的。我们要的是其中一半。

| 一半 | oneCLI | treg |
|---|---|---|
| 捕获请求 | `HTTPS_PROXY` + 它自己的证书颁发机构 | **相同** |
| 应用凭据 | 在本地，在用户机器上解密真实密钥 | **在服务端** —— 密钥永不到达 |

他们的网关持有 `SECRET_ENCRYPTION_KEY` 并在笔记本上解密 secret（`crypto.rs`、`connect.rs`）。那正是 treg 存在要避免的情形，所以我们保留捕获机制，扔掉注入那一半。

**v1 只是服务端注入。** 一个未来的"在 `treg-run` 下本地注入"模式是可能的 —— 授权路径、run-proof 门和自有-vs-共享规则已经存在 —— 但它刻意不在范围内。以后决定它零成本；现在搞错则赔上产品的核心承诺。

## 工作原理

```
agent → api.stripe.com/v1/charges
   ↓  HTTPS_PROXY=127.0.0.1:<port>
本地代理   — 这个 host 是一个已注册工具吗？
   ├─ 否  → 盲隧道，字节不动，我们看不到内部
   └─ 是 → 用我们签的叶子证书终止 TLS，读请求，重新寻址
              ↓
        treg 服务端  POST /call/https://api.stripe.com/v1/charges   (X-Treg-Token)
              ↓  服务端注入凭据 —— 既有的 relay
        Stripe → 响应一路流回到 agent
```

代理携带成员的 **treg token**，别的什么都没有。没有任何供应商 key 到达机器。

因为调用落在普通的 `/call/` 路径上，所有已经建好的东西都原样适用：每成员的工具有 ACL、项目作用域、deny 规则、每日上限、审计记录、OAuth 自动刷新。没有第二个策略引擎要写 —— 这正是 oneCLI 需要 24k 行 Rust 而我们不需要的原因。

## 硬性约束：CLI 必须保持轻量

`pip install tools-registry` 是**仅 CLI**（`httpx` + `questionary`）。证书生成需要 `cryptography`，它是一个编译型依赖，今天活在 `[server]` extra 里。它绝不能进入基础安装。

**决策：第三份 extra，`[proxy]` → 仅 `cryptography`。** 代理本身用标准库的 `asyncio` + `ssl` 和 `httpx`（已是基础）。没有该 extra 时，代理抛出 `ProxyDependencyError` 并附精确的安装有误。 `[server]` 已经包含 `cryptography`，所以自托管者免费得到它。**已发布** —— 见 `pyproject.toml` 的 `[project.optional-dependencies].proxy`。

## 组件

| 部件 | 在哪 | 备注 |
|---|---|---|
| 代理服务器 | `src/treg/localproxy.py`（新） | 命名参照 `localrun.py`；**不是** `proxy.py`，那是服务端 relay |
| CA + 叶子证书 | 同一模块 | ECDSA P-256，叶子按 host 在内存里缓存 |
| CLI 标志 | `cli.py` 里的 `cmd_shell_start` | `treg shell start --proxy [--proxy-port] [--renew-ca]` |
| 守护进程 | `cli.py` 里的 `cmd_serve_*` | `treg serve start\|stop\|status\|env` —— `eval "$(treg serve env)"` |
| Shell 接线 | `shell.py` | `start_session(extra_env=…, on_close=…)` 发布环境，停止代理 |
| 状态 | `~/.treg/proxy/` | `ca-key.pem` 0600 · `ca-cert.pem` 0644 · `ca-bundle.pem` 0644 · `proxy.json` 0600（**仅守护进程** —— 端口 + 代理 token，以便另一个终端能找到它；`--proxy` 不写其中任何东西） · `serve.log`。设了 `TREG_CONFIG` 时跟随它 |

### 我们设置的环境

```
HTTPS_PROXY / HTTP_PROXY = http://treg:<local-token>@127.0.0.1:<port>
NODE_USE_ENV_PROXY       = 1      # Node 的内建 fetch 没有这个会忽略 HTTPS_PROXY
NODE_EXTRA_CA_CERTS      = ~/.treg/proxy/ca-bundle.pem
SSL_CERT_FILE            = "
REQUESTS_CA_BUNDLE       = "
CURL_CA_BUNDLE           = "
GIT_SSL_CAINFO           = "
DENO_CERT                = "
AWS_CA_BUNDLE            = "
NO_PROXY                 = localhost,127.0.0.1,<treg host>
```

`NODE_USE_ENV_PROXY` 是那个否则会搭上一天调试的东西：自 Node 18 起，内建 `fetch` 静默忽略代理环境变量直接出站。oneCLI 在他们的集成文档里也带着同一个标志。

该 bundle 是**系统 CA + 我们的**，所以 agent 仍然信任真实的互联网。永不替换系统根；追加到它们之上。

## 不可商议项

1. **CA 私钥按机器生成。** 永不发布、永不共享、永不提交。一个分发给所有用户的单一 CA 会让任何人冒充任何站点给每个用户。
2. **v1 永不碰系统信任库。** 环境变量作用域意味着只有 agent 的进程树信任我们 —— 不是浏览器，不是 OS。oneCLI 也一样；他们的仓库里没有任何 `add-trusted-cert`。
3. **仅允许名单。** 只在一个 host 是已注册工具时才拦截它。其他一切都是我们读不到的盲隧道。这也正是阻止我们弄坏（并读取）agent 自己到 `api.anthropic.com` / `api.openai.com` 调用的东西。
4. **只绑定 `127.0.0.1`** —— 绝不 `0.0.0.0`。
5. **代理认证。** 每个会话铸造的一个随机 token，携带在代理 URL 里，以便另一个本地进程无法悄悄通过我们花掉成员的配额。
6. **代理自己的 httpx 客户端上 `trust_env=False`。** 否则它会从自己的环境读 `HTTPS_PROXY` 然后和自己说话 —— 在第一个请求上就死循环。
7. **永不记录 body、header 或 token。** 只记 host 和状态。

## 阶段 —— 每个独立可测

**P0 · 骨架（无拦截）。—— 完成。** 监听、认证、双向盲隧道所有东西。*证明：*`curl -x http://treg:<token>@127.0.0.1:PORT https://example.com` 和没有代理时完全一样（已验证：200，`ssl_verify_result=0`）；没有 token 则是 407。

**P1 · 证书。—— 完成。** 生成 + 持久化 CA、构建 bundle、签名并缓存叶子证书（`ensure_ca`、`build_bundle`、`CertAuthority.leaf_pem` / `context_for`），外加 `proxy_env()`，即 P4 将发布的精确环境。*证明：*单元测试签名一个叶子并与它完成一次真实 TLS 握手；`curl --cacert ca-bundle.pem` 接受它，而仅用系统根的 curl 拒绝它。

**P2 · 拦截并转发。—— 完成。** 对允许名单里的 host：终止 TLS（`_intercept`）、读请求、重新寻址到 `{base}/call/https://{host}{path}`（`_treg_url`）、把调用方的传输和 `x-treg-*` 头换成我们自己的（`_forward_headers`）、并把答案流回（`_write_response`）。keep-alive 被遵守，所以几次调用共享一次握手。*证明：*`test_the_agent_calls_the_vendor_and_treg_injects_the_key` 跑一个普通的 `httpx.Client` —— 没有 treg 感知、没有 key —— 通过代理针对**真实**的 FastAPI 应用；凭据到达上游是因为服务端注入了它。

**P3 · 允许名单 + 错误。—— 完成。** 启动时从 `GET /tools` 拉取 host，定时刷新 —— `ProxyConfig.hosts` 是接缝，目前由调用方填充。把 treg 的失败映射成可读的东西：`_resolve_call` 的 404 意味着"这个 host 或 path 没注册工具"；403 意味着"你无权访问"。（treg 不可达的情况已经处理 —— 一个 502，点名 treg 并说供应商调用**没有**发出，所以 agent 不会怪一个健康的供应商去重试。）

**P4 · 接线 UX。—— 完成。** `treg shell start` 铸造一个 token、启动代理、并把 `handle.env(treg_host)` 合并进子 shell 环境（`start_session` 已经构建那个字典），在拆除时停止它。横幅说明哪些 host 被捕获。没有独立命令 —— 决策 1。

**P5 · 文档。—— 完成。** `docs/context/architecture/local-proxy.md` 片段（新子系统，所以需要一份），外加 `/llms.txt` 和仪表盘的 agent 指令。

## 测试

- **单元，无网络：** CA + 叶子生成、允许名单匹配、URL 重写、header 过滤、`NO_PROXY` 解析。
- **集成：** 针对既有的 ASGI 测试应用跑代理；用配置成使用该代理并信任 bundle 的 `httpx` 驱动它。断言落在 `/call/` 上的请求是逐字节忠实的。
- **循环守卫：** 一个显式测试代理自己的客户端忽略 `HTTPS_PROXY`。
- **盲隧道：** 断言一个未注册的 host 永不解密（不为它生成叶子）。

## 已知限制 —— 在文档里大声说出来

- **证书固定。** 一个只接受自己精确证书的工具有会拒绝。需要一个每 host 的"永不拦截"列表。
- **远程 MCP 服务器不被覆盖。** 一个本地（stdio）MCP 服务器继承我们的环境并被捕获；一个被托管的则在别人的机器上发起它的调用。
- **非 HTTPS，不覆盖：** SSH、数据库线协议。WebSocket 应该被隧道化，而非拦截 —— relay 是请求/响应。
- **延迟 + 一个硬依赖。** 每个被拦截的调用都到 treg 再回来；如果 treg 宕机那些调用就失败。这是 key 永不落地的代价。
- **大上传流经我们。** 注意 Render 上的请求超时。
- **有些供应商 CLI 仍需要 `treg run`。** `gh` 在它做任何网络调用之前就拒绝，所以没什么可拦截。代理扩大了覆盖面；它不取代 `treg run`。

## 刻意不在 v1 里

在 `treg-run` 下的本地注入 · 系统信任库安装 · Windows · WebSocket 拦截 · 每 agent 代理 token（每会话一个就够） · 路由之外的请求/响应检视。

## 决策（2026-07-30 与 Unclecode 敲定）

1. **命令形态 —— 先 `treg shell start --proxy`，之后加 `treg serve`。** 原决策是仅 shell，因为代理那时随一个会话启动并消亡，它的 token 永远不必写到磁盘。实测 live 之后，Unclecode 也要了守护进程，所以两者都发布了：`--proxy` 给子 shell，`treg serve start|stop|status|env` 给一个后台服务，其他终端用 `eval "$(treg serve env)"` 指向它。守护进程的代价正是第一个决策想避免的东西 —— 一个 `proxy.json`（0600）装着端口和代理 token —— 而那在 USAGE 里说清楚了，以便选择是知情的。`_start_proxy_handle` 是单一共享代码路径。
2. **CA 有效期 —— 2 年**，在其最后 30 天内自动重生成（`_RENEW_WITHIN_DAYS`），外加一个显式 renew。不是 oneCLI 的 10 年：一个 key 在笔记本上躺十年，对能冒充任何站点的东西来说太久了。
3. **默认端口 —— 18791**，紧挨开发服务器的 18790。
4. **`[proxy]` extra —— 是**，仅 `cryptography`。把它折进基础被拒绝：它是编译型的，而 `pip install tools-registry` 必须保持轻量 CLI。

## 构建日志

- **P0 + P1 发布**（2026-07-30）—— `src/treg/localproxy.py`、`tests/test_localproxy.py`（34 个测试）。用真实 `curl` 验证：`https://example.com` 和 `https://api.github.com` 隧道穿过时证书验证完好无损；一个由 CA 签名的叶子在被指向 `ca-bundle.pem` 时被 curl/OpenSSL 接受，而**仅**用系统根时被拒绝 —— 这正是不可商议项 #2 成立的证明。
- `_is_self` 循环守卫和纯 `http://` 转发路径（在上游看到之前剥掉 `Proxy-Authorization`）是在 P0 草图之外加的 —— `HTTP_PROXY` 与 `HTTPS_PROXY` 一起设置，所以一个 http 调用方不能简单地坏掉。
- **P2 发布**（2026-07-30）—— 又 21 个测试，文件里共 55 个。草图之外：
  - **边缘 WAF 重试。** Render 的边缘对一个看起来像注入的 body 返回 403。CLI 的 `_RegistryClient` 已经把这样一个 body 在 `X-Treg-Body-Encoding` 下重新以 base64 发送；一个被拦截的调用必须做同样的事，否则一个合法的 SQL 查询会静默失败。最多 1 MiB 的 body 被缓冲，以便重试至少可能；更大的流式传输且无法重试。
  - **`_CALLER_MUST_NOT_SET`。** 一个设了自己 `X-Treg-Token` 的 agent 绝不能通过我们的代理花掉另一个成员的配额。调用方的 `x-treg-*` 头被丢弃；只有代理的身份到达 treg。
  - **`intercepts()` 在无凭据时拒绝。** 没有 CA 或没有 treg token 时，我们会终止 TLS 然后没路完成调用 —— 比不拦截还糟，因为 agent 自己的请求为一个它看不到的原因坏了。
  - **`_body_chunks`。** `aiter_raw()` 在一个传输已经加载的响应上抛出 `StreamConsumed`，那会静默丢掉 body。两种形态都处理了。
  - **分帧是重新推导的，不是拷贝的** —— treg 给了 `Content-Length` 时用它，没给时用 chunked —— 因为我们的这一跳必须自洽，即便跳进 treg 时是以不同方式分帧的。
- **`treg serve` 发布**（2026-07-30，live 测试之后）—— `cmd_serve_start/_stop/_status/_env` + `localproxy.py` 里的状态辅助（`write_state`、`read_state`、`running`、`pid_alive`）。测试产生的两个发现，都是真的：
  - `pid_alive(0)` 返回 **True**，因为 `os.kill(0, …)` 给调用方的整个进程组发信号。状态文件里一个被截断的 pid 会被读成"运行中"，而 `treg serve stop` 会信号到用户的终端。非正的 pid 现在在调用前被拒绝。
  - 父进程只说"看日志"当分离的 child 死了。它现在打印 child 的最后一行日志 —— 端口冲突的情况因此读起来像一句话而不是寻宝游戏。
- live 端到端验证：`serve start` → `eval "$(treg serve env)"` → 对一个被捕获 host 的普通 `curl` 到达供应商时带着服务端注入的 `Authorization: Bearer …`，未被捕获的 host 直接出站，`--unset` 清掉 shell，第二次 `start` 被拒绝，`stop` 移除状态文件，一个带着死 pid 的陈旧文件在下一次调用时被清理。
- **Agent hook 发布**（2026-07-30）—— `treg serve hook [--install] [--agent]`。Unclecode 问 oneCLI 如何避开 eval；读他们的代码，它没避：`onecli run` 是父进程，容器拿到 `-e HTTPS_PROXY=…`，他们的 Claude 插件设 **`BASH_ENV`** 为一个生成的 `env.sh`（`plugins/claude/hooks/session-start.mjs:236`）。我们现在做第三种，复用 `agents.py` 的 harness 注册表。用一个裸 `BASH_ENV=… bash -c 'curl …'` 证明：代理运行时带着凭据，在 `serve stop` 之后是明文。
- **该 hook 当天被 `treg <command>` 取代。** Unclecode 拒绝了全局安装器，他是对的：把 `BASH_ENV` 写进 `~/.claude/settings.json` 会捕获该 agent 在这台机器上的每个会话，永远，无论你那天想不想要 treg —— 而且没有简便方式用你自己的个人 key 代替。启动器（`cmd_with`）给出同样的"永无 eval"结果，却没有任何波及面：treg 是它运行的那个命令的父进程。`treg claude` 用团队访问；普通的 `claude` 不受影响。没有任何东西被写进任何配置文件。`treg serve hook`、`env.sh` 和那三个配置安装器被删除 —— 不要重新加回它们。
- **下一步，已请求但未构建：** `treg claude` 也可以把团队的技能预加载进会话，而不是 agent 去下载安装它们。
- **已测量，且它纠正了计划：** `NODE_USE_ENV_PROXY` 只在 **Node 24** 起存在。在开发机（Node 23.11）上 `node --use-env-proxy` 是"坏选项"，而一个裸 `fetch()` 通过代理到达时没带凭据。设该变量对 Node 24+ 仍是对的，但计划里关于它的那行读起来像"Node 现在可用"，而这只在 24 上为真。已记录在片段、USAGE 和 /llms.txt 里。
- **`examples/proxy-demo/`** —— 一个零依赖的 Node 应用，带一个小 Web UI：点一个按钮，它调用 `api.openai.com`（已注册）或 `example.com`（未注册）。`node server.js` 得到 401；`treg node server.js` 得到真实答案，同样的代码。它手工说 CONNECT，因为上面那个 Node 注意事项，它的 README 说明了为什么真实应用不需要这么做。
