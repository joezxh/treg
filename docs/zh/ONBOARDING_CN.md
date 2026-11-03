# tools-registry — 上手引导

agent（或人）开始调用共享工具、以及共享自己工具所遵循的引导流程。CLI 是 `https://treg.to` 上 API 的一个瘦客户端；API 才是唯一的大脑。

## 1. 安装 CLI

```bash
curl -fsSL https://treg.to/install.sh | sh   # 安装 `treg`，并将其指向注册表
```

（从源码克隆开始？`uv sync && uv run treg --help`。）

## 2. 登录

三扇门，一种身份（你的邮箱）：

```bash
treg login                                  # GitHub OAuth（打开浏览器）
treg login --email you@example.com          # 邮箱一次性验证码
treg login --token <TOKEN>                  # agents/CI：由团队 owner 发放的按组织 token
```

你的 token 在每次调用时标识你的身份（`X-Treg-Token`）。第一次来？`treg onboard` 会用一次性的演示团队带你走完所有流程。

## 3a. 使用别人已共享的工具（消费者）

```bash
treg tool ls                                 # 有哪些可用
treg call posthog query/events --query limit=5
treg run gh -- pr list                       # 厂商 CLI 也可用
```

你**不持有任何上游密钥** —— 注册表会在服务端注入它。

## 3b. 共享你自己的（创建者）

把 treg 指向一个项目 —— 它会找出 `.env` 里的供应商密钥、技能目录，以及已安装的目录 CLI，并注册你选定的部分：

```bash
treg scan          # 只读预览；不会有任何东西离开本机
treg upload        # 注册（服务端加密）；幂等，--replace 用于更新
```

对于单个技能或棘手的工具（多凭据、OAuth），请看 [`USAGE.md`](../USAGE.md) 中的手动流程 —— `treg skill init` / `skill add`、`treg tool add --bind`、`treg oauth connect`。

## 4. 验证 + 观察

```bash
treg call <tool> <upstream-path>     # 冒烟测试
treg calls                           # 审计：谁在什么时候调用了哪个工具、状态如何
treg health                          # 整个组织的凭据健康度
```

## 注意事项

- 密钥只写；API 永不返回已存的值。
- 一个工具可以引用另一名成员上传的密钥（use-without-hold）。
- 一切都以组织为作用域：`treg org ls` / `treg org use <slug>` 选择当前激活的团队。
