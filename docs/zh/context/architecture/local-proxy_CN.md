---
title: Local proxy — 拦截程序自身的对外调用（`treg <command>`）
status: shipped
sources:
  - src/treg/localproxy.py
  - examples/proxy-demo/server.js
related:
  - architecture/proxy-model.md
  - interface/shell.md
  - interface/cli.md
  - architecture/local-run.md
---

# The local proxy（本地代理）

每个进入 treg 的其他方式都要求调用方**知道 treg**——`treg call`、`treg run`、`/call/` URL。一个程序一旦用自己的请求写到 `api.stripe.com`，treg 对它就是不可见的，且它没有 key。本地代理关闭这个缺口：在出去的路上拦截该调用，让**服务器**添加凭据。

**不是 `infra/upstream/relay.py`。** 那是 SERVER 转发（`relay()`），注入的那个东西。这是喂它的本地捕获器——一次调用的两端。该模块以 `localrun.py` 命名，它在"在成员机器上运行的代码"中的邻居。计划 + 构建日志：`docs/LOCAL-PROXY-PLAN.md`。

## 一图概览

```
  一个从未听说过 treg 的程序
        │  HTTPS_PROXY=http://treg:<session-token>@127.0.0.1:<port>
        ▼
  本地代理  (src/treg/localproxy.py — 本片段)
        │
        ├─ 主机 NOT 注册  ──► 盲隧道。字节复制，从不解密，
        │                           从不为此签署证书。
        │
        └─ 主机 IS 注册   ──► 用我们签署的叶子终止 TLS
                                    读取明文请求
                                    重新寻址，保持 method/path/query/body
                                          │
                                          ▼
                       treg 服务器   POST /call/https://api.stripe.com/v1/charges
                                     + X-Treg-Token / X-Treg-Org / X-Treg-Client
                                          │  relay() 注入凭据  ← proxy-model.md
                                          ▼
                                     api.stripe.com
                                          │
        ◄─────────────── 响应流回，不变 ──────────────────┘
```

代理携带成员的**treg 令牌**且别无其他。供应商 key 从不到达机器。

因为该调用落在普通的 `/call/` 路径上，一切已构建的东西都适用而无需第二个副本：每成员工具列表、项目范围、拒绝规则、每日上限、审计记录、OAuth 刷新。这就是为什么这个模块很小且不存在第二个策略引擎——见 [proxy-model](proxy-model.md)。

## 我们从 oneCLI 拿了什么，又拒绝了什么

他们的设计有可分离的两半。我们保留捕获机制（`HTTPS_PROXY` + 自有 CA）并抛弃注入一半：他们的网关持有 `SECRET_ENCRYPTION_KEY` 并**在笔记本上**解密 secret（`crypto.rs`、`connect.rs`）。那正是 treg 要防止的情况。一个未来的"在 `treg run` 下本地注入"模式刻意超出范围——稍后决定它不花费任何东西，现在把它搞错要付出产品的承诺。

## 三个前门，一个引擎

| 门 | 变更范围 | 用它当 |
|---|---|---|
| **`treg <command>`**（`cmd_with`） | 那个进程及其子进程 | 正常情况 —— `treg claude`、`treg node app.js` |
| **`treg shell start --proxy`** | 一个子 shell | 你想要一个团队 CLI *与* 原始调用都工作的会话 |
| **`treg serve`** | 任何用 `eval "$(treg serve env)"` 选择加入的终端 | 你想要它跨终端运行 |

**`treg <command>` 是头条。** treg 是它启动的东西的 PARENT，因此环境只到达那个进程：`treg claude` 使用团队访问，纯 `claude` 不受影响且使用成员自己的 key。不写入任何配置文件，因此没有要撤销的东西。`main()` 当第一个词（在 `with` 自己的标志之后）**不是**一个 treg 子命令**且**在 `PATH` 上**存在**时，通过 `_looks_like_a_program()` 落入它。两个条件都重要：没有第一个，一个杂散的 `call` 二进制会遮蔽 `treg call`；没有第二个，`treg toool ls` 会变成一次 exec 尝试而非普通的 argparse 错误。它附加到一个运行的 `serve` 守护进程并让它保持运行，或在**端口 0** 启动一个私有代理——操作系统选择，因此并行会话从不冲突——并在一个 `finally` 中停止它。子进程通过 `shell._run_subshell` 运行，它忽略 SIGINT/SIGQUIT 以便一个交互式 agent 拥有终端，且子进程的退出码变成 treg 的。

**刻意删除：全局 hook。** 一个写入 `BASH_ENV` 到 `~/.claude/settings.json` 的 `treg serve hook`（如 oneCLI 的 Claude 插件所做的）被构建并在同一天移除。它永久捕获那台机器上该 agent 的每个会话，无论成员那天是否想要 treg，且不留下容易改用个人 key 的方式。每启动给出相同的"从不需要 eval"结果而没有那种触及面。**不要重新添加它。**

## 组件图

| 符号 | 工作 |
|---|---|
| `handle_client` | 一个连接：读头、鉴权，然后拦截 / 隧道 / 转发 |
| `authorized` | `Proxy-Authorization: Basic treg:<token>`、`compare_digest` |
| `_blind_tunnel` | 针对未注册主机的 CONNECT —— 复制字节，不解密 |
| `_intercept` | 针对已注册主机的 CONNECT —— TLS 终止，然后把每个请求转发到 treg |
| `_forward_plain` | 绝对形式的 `http://`（我们也设置了 `HTTP_PROXY`，因此 http 调用方绝不能中断） |
| `_treg_url` | `https://host/path` → `{base}/call/https://host/path`（URL 透传形状） |
| `_forward_headers` | 丢弃传输 + 调用方 `x-treg-*`；添加我们的 token/org/client |
| `_send_to_treg` | 出站请求，含边缘 WAF base64 重试 |
| `_write_response` / `_body_chunks` | 把答案流回，重新派生帧 |
| `_explain_treg_error` / `treg_error_message` | 把 treg 自己的拒绝变成一个指令 |
| `CertAuthority` / `ensure_ca` / `build_bundle` | 机器的 CA、它的叶子、信任包 |
| `proxy_env` | 把进程指向我们并让它信任我们的变量 |
| `fetch_hosts` / `refresh_hosts_forever` | 允许列表，来自 `GET /tools` |
| `serve` / `start` / `ProxyHandle` | 在这个循环 / 在一个线程中绑定；`.env()`、`.stop()` |
| `write_state` / `running` / `pid_alive` | `treg serve` 守护进程的 `proxy.json` |
| `treg_client` | 代理自己的 httpx 客户端 —— **`trust_env=False`** |

## 请求生命周期，按顺序

1. `handle_client` 用 `readuntil(b"\r\n\r\n")` 读头，上限 `_HEAD_LIMIT`（64 KiB → `431`）。
2. `authorized()` 检查会话令牌。无/错误令牌 → `407`，且消息绝不打印令牌本身。
3. `CONNECT` → `split_hostport`。`_is_self` 拒绝我们自己的地址（一个每次尝试会吃掉一个连接的循环）。
4. `cfg.intercepts(host)` 决定。它要求主机被允许列表**且**一个 CA **且**一个 treg 令牌：终止 TLS 然后没有完成调用的方式比不拦截更糟，因为调用方因它看不到的原因而中断。
5. 拦截：`200 Connection established`，然后 `StreamWriter.start_tls(ca.context_for(host))`。
6. 该连接上的每个请求（keep-alive 被遵守）：解析头、读 body（`_request_body` —— chunked 解码，≤1 MiB 缓冲以便可能做 WAF 重试，更大的流式传输）、构建 treg URL 与头部、`_send_to_treg`，然后如果答案携带 `X-Treg-Error` 则 `_explain_treg_error`，否则 `_write_response`。
7. 响应帧是**重新派生的，而非复制的**：当 treg 给了一个时 `Content-Length`，当没给时 chunked，因为我们的跳必须自洽即使进入 treg 的跳以不同方式成帧。`Accept-Encoding` 在调用方什么都没要求时归一化为 `identity` —— 与 `relay()` 应用的相同规则 —— 否则 httpx 会自己请求 gzip 并把调用方从未要求的压缩字节交给它。

## 证书（`CertAuthority`、`ensure_ca`、`build_bundle`）

**每机器**首次使用时生成：ECDSA P-256、2 年、自签名、`BasicConstraints(ca=True)`。私钥文件在**任何字节进入之前**以 0600 创建 —— 先写后改权限会留下一个私钥世界可读的窗口。当文件不可读或在最后 30 天内时它重新生成（`_RENEW_WITHIN_DAYS`），因此过期绝不会作为无法解释的 TLS 错误在会话中途浮现；`--renew-ca` 强制它。

`build_bundle` 写入**系统根加我们的**（与 httpx 一起发布的 `certifi`，回退到 OpenSSL 的配置化文件）。追加是重点：`SSL_CERT_FILE` 替换信任列表，因此只持有我们 CA 的包会让调用方无法验证真实的互联网。

叶子按需用一把复用的 key 签署并每主机缓存为一个 `ssl.SSLContext`。Python 的 `load_cert_chain` 只从文件读取，因此一个叶子被写入一个 0600 临时文件，加载后即刻删除。

**系统信任存储绝不被触碰。** 信任由环境变量限定范围，因此只有启动的进程树信任我们 —— 不是浏览器，不是操作系统。oneCLI 做同样的事；他们仓库中任何地方都没有 `add-trusted-cert`。

## 环境（`proxy_env`）

`HTTPS_PROXY`/`HTTP_PROXY` 在**两种字母大小写**（`curl` 读小写）、覆盖环回与注册表主机的 `NO_PROXY`、在 `NODE_EXTRA_CA_CERTS` / `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` / `CURL_CA_BUNDLE` / `GIT_SSL_CAINFO` / `DENO_CERT` / `AWS_CA_BUNDLE` 下的包，以及 `NODE_USE_ENV_PROXY=1`。

**Node 注意事项 —— 测量的，而非假设的。** Node 的内置 `fetch` 完全忽略代理变量，直到 **Node 24**，那里 `NODE_USE_ENV_PROXY` 开启它；该标志在那之前不存在（在 23.11 上 `node --use-env-proxy` 是一个"bad option"，在开发机上测试过）。因此在 Node 23 或更早，一个普通的 `fetch()` 径直绕过代理，调用无凭据地出去 —— 那看起来正好像功能坏了。任何自己读环境的东西在任何版本都被捕获：curl、git、python-requests/httpx、axios、got、undici 的 `ProxyAgent`、Deno。

## 允许列表（`fetch_hosts`、`refresh_hosts_forever`）

主机来自 `GET /tools`，它已过滤到**该成员**可以使用的 —— 因此允许列表免费继承了每成员工具列表与项目范围，且一个他们不能用的主机甚至从不解密。两个失败模式被刻意处理：一次失败的获取返回一个空集（无答案绝不能意味着"拦截一切"），且刷新器绝不在工作的列表上应用空集答案，那会静默停止注入而调用继续出去。两个前门都从他们已获取的 tool 列表为它播种，因此打开代理不花费额外请求。

## 调用方可行动的错（`treg_error_message`、`_explain_treg_error`）

来自 treg 的一个原始 404 读作"供应商没有这样的端点"，且一个 agent "修复"它通过重写一个完美的 URL。因此 treg 自己的拒绝被替换为一个命名 treg 与下一步动作（注册工具 / 问一个管理员 / `treg login` / 上限已用完）的消息。

这只针对 `X-Treg-Error` 触发，即 `api.py` 的 `_mark_treg_own_errors` 放在 treg 自己 `/call/` 拒绝上的头部 —— 否则一个真实的供应商 404 也会被重写。针对不发送它的更旧的注册表，回复原样通过。treg 不可达回答 `502` 命名 treg 并说供应商调用**没有**被做，因此调用方不责怪一个健康的供应商并永远重试。

## 安全不变式 —— 每个附带会出错的东西

| # | 不变式 | 它防止的 |
|---|---|---|
| 1 | 每机器 CA 私钥、0600、从不运送 | 一个共享 CA 会让任何持有者冒充任何站点给每个用户 |
| 2 | 绝不触碰系统信任存储 | 拦截会触及浏览器与整个 OS，而非仅启动的东西 |
| 3 | 仅允许列表 | 读取调用方自己的 `api.anthropic.com` / `api.openai.com` 流量 |
| 4 | 绑定 `127.0.0.1`（`LISTEN_HOST`） | 网络上任何人花费成员的配额 |
| 5 | 随机会话令牌（`mint_token`）+ `_CALLER_MUST_NOT_SET` | 另一个本地进程，或调用方自己的头部，以他人身份说话 |
| 6 | `treg_client` 上的 `trust_env=False` | httpx 从它自己的环境读 `HTTPS_PROXY` —— 第一次调用会循环回我们 |
| 7 | 只记录主机与状态（`_log`） | 日志文件中的 body、头部或令牌 |

## 守护进程的状态（`treg serve` 仅）

一个服务必须能被其他终端找到，因此 `write_state` 在模式 **0600** 把端口、pid、令牌、注册表与捕获的主机记录在 `~/.treg/proxy/proxy.json`，在任何字节进入之前创建。那个文件是 `serve` 相对于其他两个门的全部额外风险：它持有会话的代理令牌 —— 绝不供应商 key —— 但它在磁盘上。`running()` 把一个 pid 已消失的状态文件当作*未运行*并删除它，否则 `status` 会永远坚持且 `start` 会拒绝替换一个死守护进程。`pid_alive` 在调用 `os.kill` **之前**拒绝一个非正的 pid，因为 `os.kill(0, …)` 信号调用者的整个进程组 —— 一个被截断的 pid 会读作存活且 `stop` 会信号终端。

分离的子进程作为 `sys.executable -c "from treg.cli import main; main()" serve start --foreground` 启动，绝不在 `PATH` 上的 `treg`：一个落后一个版本的 Homebrew 副本会被启动且根本不会有该命令。输出去到 `~/.treg/proxy/serve.log`，且父进程在子进程未出现时打印该日志的最后一行，而非告诉用户去读一个文件。

## 打包

证书生成需要 `cryptography`，它是编译的，因此它位于一个 **`[proxy]` extra** 而非基础安装 —— `pip install tools-registry` 必须保持轻量 CLI（`httpx` + `questionary`）。`_require_cryptography` 以确切的安装行抛出 `ProxyDependencyError`。`[server]` 已包含它，因此自托管者免费得到它。

## 测试实际证明了什么

`tests/test_localproxy.py`（单元 + 集成，无网络）与 `tests/test_shell.py` 的代理部分（前门）。值得知道的：对我们签署的叶子**且**它被一个只信任系统根的客户端拒绝的真实 TLS 握手（不变式 2）；从不为隧道主机生成叶子（不变式 3）；调用方不能伪造 `x-treg-*`；`trust_env` 关闭；供应商自己的错误从不重写；以及端到端 `test_the_agent_calls_the_vendor_and_treg_injects_the_key`，它通过一个**真实** FastAPI app 的代理驱动一个普通 `httpx.Client`。

## 已知限制 —— 大声说出来

证书**固定（pinning）**：一个只接受自己证书的客户端拒绝我们的。它单独失败，且会需要一个每主机绝不拦截列表（未构建）。**远程 MCP 服务器**不被覆盖 —— 一个托管的从一个别人的机器调用；一个本地 stdio 的继承环境并被捕获。不是 HTTPS，不被覆盖：SSH 与数据库线协议；WebSocket 被隧道，不被拦截。每个被拦截的调用给 treg 加一个来回跳，**且如果 treg 宕机则失败** —— key 永不落地的代价。大上传流经我们。某些供应商 CLI 仍需要 `treg run`：`gh` 在它做任何网络调用之前就拒绝，因此没有东西可拦截。
