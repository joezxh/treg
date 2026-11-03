# 企业 SSO 配置

本集成用 WorkOS 为客户做 SAML 或 OIDC 连接。treg 仍负责账号、团队角色、浏览器会话与 API key。团队 owner 购买一份按月 Stripe 订阅，并从 **Team → SSO** 打开 WorkOS 配置。该链接在点击时生成，五分钟后过期。owner 可以通过 WorkOS 按邮箱邀请一位 IT 管理员，或直接打开这个短时效配置链接。owner 可以从 **Team → SSO** 复制员工登录链接；在任意 treg 登录对话框里，员工可以选择 **Company SSO**，输入其公司邮箱，并选择 **Continue with SSO**。邮箱验证码仍是默认登录方式。该查找会把他们路由到已验证的公司连接。它不会认证他们或让他们加入。他们首次成功登录会以 member 身份加入既有团队。owner 可以在 **Members** 里改角色。团队展示名可能重复；链接名是员工登录 URL 里唯一的 slug（例如，第二个名为 `Test` 的团队会得到 `test-2`）。当邮箱发现无匹配或匹配到多个团队时，员工可以使用 owner 的确切链接。当匹配到多个团队时，对话框会列出它们的名称与唯一链接名，以便员工选择。邮箱只是一个路由提示，而非访问凭证。既有已验证的 treg 用户必须先正常登录一次，再关联其公司身份；treg 会在同一浏览器里恢复那个待处理的 SSO 尝试。

## 配置部署

1. 在运行新代码前，应用 Alembic 迁移直到 `0085`。
2. 在 WorkOS 环境里创建一个 API key 并找到 client ID。在服务器上设置 `TREG_WORKOS_API_KEY` 和 `TREG_WORKOS_CLIENT_ID`。为 state 与浏览器 cookie 设置一个稳定的 `TREG_SECRET_KEY` 和 `TREG_SESSION_SECRET`。
3. 把 `<TREG_PUBLIC_URL>/auth/sso/callback` 加为允许的 WorkOS 重定向 URI。传给 WorkOS 的 URL 来自 `TREG_PUBLIC_URL`，所以必须完全匹配。
4. 对于 Directory Sync，把 `<TREG_PUBLIC_URL>/auth/sso/workos/webhook` 注册为 WorkOS webhook。订阅它到 `dsync.activated`、`dsync.deleted`，以及 `dsync.user.created`、`dsync.user.updated`、`dsync.user.deleted`。把它的签名密钥设为 `TREG_WORKOS_WEBHOOK_SECRET`。没有该密钥，端点返回 404。定期运行 `treg-worker enterprise reconcile` 修复错过的 webhook 投递。订阅结束后还要定期运行 `treg-worker enterprise cleanup`。它会移除 WorkOS SSO 连接与目录；监控其非零退出状态并重试失败项。它在改动访问权限前会读取完整的 WorkOS 名册；监控失败。
5. 配置 Stripe 既有的 `TREG_STRIPE_SECRET_KEY` 与 `TREG_STRIPE_WEBHOOK_SECRET`。在和密钥相同的测试或正式账号里，为每个提供的方案创建一个可复用的 USD 按月 Stripe Product/Price。设置 bundle 的 `TREG_ENTERPRISE_SSO_BUNDLE_PRICE_ID`，以及（仅当提供 SSO-only 时）`TREG_ENTERPRISE_SSO_ONLY_PRICE_ID`。未设置的 Price 会隐藏那个方案。treg 读取 Price 来显示其金额，并在打开 Checkout 前拒绝一个未激活、非固定金额、非 USD 或非按月的 Price。如果配置的 Price 在 owner 打开页面后发生了变化，Checkout 会要求他们刷新。可选的 `TREG_ENTERPRISE_SSO_BUNDLE_MIN_PRICE_USD` 与 `TREG_ENTERPRISE_SSO_ONLY_MIN_PRICE_USD` 会拒绝低于各方案部署特定下限的 Stripe Price；两者默认都为零。当 Stripe 的 Price API 暂时不可用时，既有订阅者仍可管理 SSO。价格变更需要新的 Price ID；既有订阅会保留其旧 Price，直到被显式迁移。把 `checkout.session.completed`、`customer.subscription.created`、`customer.subscription.updated` 和 `customer.subscription.deleted` 发送到既有的 `/billing/stripe/webhook` 端点。同一个 Stripe 账号既能处理工具余额充值，也能处理 SSO 订阅；订阅事件不会改变预付费余额。
6. 对于 IdP 应用磁贴，把 WorkOS 应用的登录端点设为 `<TREG_PUBLIC_URL>/auth/sso/idp/start`。WorkOS 提供连接提示，treg 开始其正常的、带 state 校验的 SSO 重定向。用客户的 IdP 测试这个磁贴。

WorkOS staging 与 Stripe 测试模式可以一起用。把 staging 密钥和测试密钥放在同一个测试部署里；生产凭据需要自己配置的重定向与 webhook。内置的 WorkOS Test Identity Provider 只接受在其 WorkOS 组织上验证过的域名的 profile。另一个邮箱域名的 profile 会在 treg 收到验证码前被拒绝；treg 会把员工送回其登录对话框并附说明。

## Owner 与员工流程

团队 owner 在 Stripe 配置的按月金额下选择 **SSO** 或 **SSO + Directory Sync**。默认的 `TREG_ENTERPRISE_SSO_BUNDLE_ONLY=true` 只显示 bundle；设为 `false` 则提供两者。每次 Checkout 使用配置好的可复用 Stripe Price，而不是为每个团队新建 Product 和 Price。在 Stripe 报告一个激活的订阅后，owner 依照 **Team → SSO** 里已勾选的配置卡片操作。**Set up company SSO** 打开 WorkOS；对于 bundle，**Set up Directory Sync** 打开目录配置。owner 应在点击 **Require SSO** 之前先完成一次真实的测试登录。该控件只有在一次成功的 WorkOS 登录之后才可用。

owner 可以输入一位 IT 管理员的邮箱，让 WorkOS 发送配置说明；收件人不需要 treg owner 账号。Admin Portal 按钮仍保留给自行配置的 owner。SSO 标签页对团队 owner 始终可用。其他成员只有在付费 SSO 连接就绪后才能看到它；该标签页让他们复制员工登录链接，而不是再用他们已登录的浏览器走一遍 SSO。Team 标题处也提供该链接，无需打开 SSO 设置。非 owner 不会拉取 Stripe 方案价格。

一个通过其团队 WorkOS 组织登录的员工会获得一个 `member` 角色的团队成员关系。即便是用同一个公司邮箱，一次普通的邮箱或社交登录也不满足该团队的 SSO 强制要求。既有的团队角色永不被 IdP 组覆盖。SSO 只有在邮件匹配一个已验证的 WorkOS 组织域时才创建新账号。一个既有 treg 账号必须在同一浏览器里用其常用方式登录，再完成一次公司 SSO 登录以关联 IdP 身份。仅一个 SSO 断言无法认领那个全局账号。在把一个 WorkOS 域标记为已验证之前先验证域名所有权；控制台可以无需 DNS 挑战就把一个手动添加的域标记为已验证。保持 WorkOS 的组织外 profile 选项关闭。owner 保留其普通登录作为恢复路径。团队 API key 仍是独立的凭据；Directory Sync 停用会移除受影响的成员关系并撤销其 key。在 SSO-only 方案下，从 IdP 里移除某人会停止其未来的 SSO 登录，但 treg 无法承诺立即撤销一个既有团队会话或 key。用 Directory Sync 来做这件事。一个 SSO 浏览器会话及其铸造的任何 CLI 或 MCP OAuth 凭据都仅限于该公司团队，即便那个人还属于其他 treg 团队。CLI 与 OAuth 同意省略需要不同登录方式的团队；审批、token 交换、刷新与使用都检查同一条规则。一个通过普通登录建立的既有 OAuth 授权，在该团队开始要求 SSO 后停止对其生效。当 owner 要求 SSO 时，更早的非 owner bearer key（含 Default 与 agent key）停止授权该团队。员工可以用公司 SSO 登录并签发新的 CLI 或附加 key。owner 可以签发新的 agent key。这些新凭据在其 key 或成员关系被撤销前一直有效；Directory Sync 移除会同时撤销两者。用普通登录访问其他团队。如果一位管理员在 treg 里移除了一个 SSO 成员，即便目录仍把他们列为活跃，那个人也保持被屏蔽。owner 可以从 SSO 标签页再次允许 SSO。目录停用与后来的重新激活是自动的，除非团队管理员显式移除了那个人。手动屏蔽在订阅取消和后来 WorkOS 连接替换之后仍然保留。

owner 可以从 SSO 标签页安排在当前计费周期结束时取消订阅。当 Stripe 重试 `past_due` 付款时，SSO 与 Directory Sync 保持活跃。订阅结束时，treg 解除强制要求，以便既有成员可以使用普通登录。SSO 创建的成员关系及其团队 key 被撤销；预先存在的成员保留其成员关系。然后清理 worker 会验证 WorkOS 组织属于该团队，并删除其所有目录与 SSO 连接，包括首次登录前创建的那些。失败的清理会被重试；新的订阅会等待清理完成。WorkOS 配置被永久移除，所以回归的客户可能需要其 IT 管理员重新配置。一个活跃订阅必须先结束，该团队才能被删除。如果一个已取消的团队仍有待清理的 WorkOS 配置，团队删除也会等待，以免资源变成孤儿。

## 证据与个人信息

公司登录与失败、配置动作、角色变更、强制要求变更，以及 Directory Sync 访问移除都会写入一条持久的、以团队为作用域的审计行。访问变更及其审计行一起提交；配置请求在 WorkOS 响应后记录。行包含事件、内部用户 ID、相关时的角色转换，以及时间，而不含邮箱地址、profile 载荷或 WorkOS 密钥。团队删除会移除这些行。在约定的保留期（默认 400 天）后安排 `treg-worker enterprise purge-audit`；最终期限与 SOC 2 审计员和隐私顾问共同确定。为配置审批、IT 验证、定期访问审查、同步失败监控和事件响应保留单独的证据。这些运维控制以及 WorkOS/Stripe 处理条款是 SOC 2 与 GDPR 所必需的；仅有代码和测试不足以确立合规。取消后，旧的 WorkOS 身份与目录行会被删除。一个被手动移除的员工只留下团队 ID、treg 用户 ID 和屏蔽时间，以便新的连接无法重新接纳他们。owner 可以移除该屏蔽；团队删除与全局用户擦除会移除它。这是个人信息，所以隐私请求必须连同账号、目录名册、WorkOS 数据与审计记录一起审查它。一个活跃的公司目录可以把一个已删除的名册条目同步回来；请与客户身份管理员协调个人擦除。

## 生产前验证

仓库测试模拟文档化的 WorkOS profile 与目录事件载荷，并验证错误组织拒绝、已验证域与账号关联检查、CLI 与 OAuth 作用域、普通会话拒绝、webhook 签名，以及去配给（deprovisioning）。生产前，请通过一个已验证公司域的 WorkOS 组织与一份 Stripe 测试订阅做一次 staging 登录，确认 webhook 投递与取消，并测试停用一名目录用户。被模拟的测试无法证明外部控制台配置或供应商特定的 SAML/OIDC 握手。
