---
title: Policy extensions — 私有滥用策略可插入的决策点
status: shipped
sources:
  - src/treg/policy.py
  - src/treg/bootstrap.py
  - src/treg/application/signup.py
  - src/treg/domain/identity/promotions.py
  - tests/test_policy.py
---

# Policy extensions（策略扩展）

## 为什么

treg 中的每一条防御机制都是公开的，且自托管者需要全部：限流器、邮件域名黑名单、Turnstile、每收件箱一积分的声明。但那些机制被调校所依据的数值是另一回事。一个公开的阈值是一个靶子：一个农场脚本可以把自己精确地控制在它之下。因此一个托管部署可能把它自己的滥用策略（阈值、名单、评分）保存在本仓库之外，并通过一组固定的决策点插入进来。

**treg.to 就是这么做的。** 它安装了一个带有自己滥用规则的私有扩展。该扩展只看到决策点交给它的东西，且只能以该点的结果作答，因此它只能限制、绝不能更多：它不能授予 treg 会拒绝的任何东西、不能动钱、也不能改变一个公开限制。自托管部署在没有它的情况下运行，并在每一点得到 treg 的默认，也就是这些文档别处所描述的那种行为。

## 契约（`src/treg/policy.py`）

`treg.policy` 是一个扩展可以 import 的唯一 treg 模块。它由
`POLICY_API_VERSION` 版本化；一个不兼容的变更会提升它。

- **加载。** 一个扩展是 `treg.extensions` 入口点组下的一个对象，带整数 `api_version` 与 `install(app, registry)`。`create_app` 把每个已安装的扩展最后加载进一个全新的 `PolicyRegistry`，并把它们的名字记录在 `app.state.extensions` 上。版本不匹配或 `install` 失败都会拒绝启动。`TREG_REQUIRED_EXTENSIONS`（逗号分隔的入口点名）在命名扩展未安装时也会拒绝启动，因此一个坏掉的构建绝不会在没有其运营者所依赖的策略的情况下提供服务。为空（默认）时不要求任何东西。
- **每点一个处理器。** 为某点注册第二个处理器是一个错误。
- **treg 拥有失败处理，且失败回退到默认值。** 当一个处理器慢、抛出异常或返回该点结果之外的值时，treg 使用该点的公开默认。一次扩展失败几乎总是运营者自己的 bug 或配置错误，而非调用方能诱发，因此它除了"没有该扩展的 treg 会做的事"之外，不应让用户付出代价。它被改为报告：一行日志 `event=policy_failed point=<point> error=<exception type> outcome=<default>` 以及一个用于告警的 `PolicyFailed` 故障事件（组件 `policy`），两者都只带异常类型、绝不带消息（消息可能命名一条私有规则）。一个想在自己状态缺失时严格的扩展自己决定这一点并正常作答。
- **处理器不得阻塞。** 预算在它的下一次 `await` 取消一个处理器；一个阻塞事件循环的处理器不会被打断。
- **每进程一个注册表。** `policy.registry` 持有最近一次 `load_extensions` 的处理器；构建了多个 app 的测试自己恢复它。
- **拒绝不揭示规则。** treg 只记录并展示该点的公开结果。是哪条规则触发的，留在扩展内。

## 决策点

| 点 | 调用位置 | 结果 | 预算 | 超时/错误/坏结果时 |
| --------------- | -------------------------------------------------------- | ----------------- | ------ | -------------------------------- |
| `signup_credit` | `signup._grant_signup_promo`，在 `claim_signup_promo` 之前 | `grant`、`defer` | 300 ms | `grant`，被报告 |

### `signup_credit`

每次团队创建时询问一次，且在首次验证一个已拥有团队的用户（针对最老的此类团队，`signup.grant_signup_promo_on_proof`）的登录时询问一次，仅针对一个现在就能声明的人
（`promotions.signup_promo_email`：已验证、仍有资格、未被暂停、非 demo），且只有当授予额度大于零时。上下文是该用户与团队的 ID、登录邮箱及其规范收件箱（`promo_inbox`）。资格读取的事务在决策之前提交，因此没有任何数据库连接等待该扩展。

`defer` 不写任何东西：没有声明行、没有账本条目，且 `signup_promo_available` 保持为真。该团队（或登录）照常继续。当同一用户创建他们的下一个团队时该点再次被询问，因此一个后来的 `grant` 是释放路径，且不需要新的账本条目类型。首次验证发生一次，因此那里的延迟（deferral）绝不会被后来的登录再次询问。treg 记录 `event=signup_credit_deferred org=<id> user=<id>`。授予之后用户不再有资格且再也不会被询问。

一次失败会授予，正如没有扩展的 treg 会做的那样。其他的 signup-credit 防御（每收件箱一积分、真人检查、域名黑名单）持续适用，因此一个坏掉的扩展会把部署退回它的公开基线，而非扣留每个新用户的积分直到有人注意到。

一个认为自己的注册积分被错误扣留的用户联系该部署的支持；一个运营者可以通过普通的管理员授予来发放积分。
