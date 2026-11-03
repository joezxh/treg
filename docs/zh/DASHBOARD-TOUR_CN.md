# tools-registry — 控制台导览

Web UI 里你能做的每一件事，每一步都配截图。交互式版本（Ledger 风格，上一页/下一页，主题切换）托管在 `https://treg.to/dashboard-tour/`（Help → Dashboard tour）；CLI 走查见
[`docs/TUTORIAL.md`](TUTORIAL.md) / `https://treg.to/tutorial`。

截图由 `docs/dash-tour/capture.py`（Playwright）生成 —— UI 改动后重新运行它。

---

## 登录

### 1 · 三种入口
登录界面提供三扇独立的门 —— 选**一扇**：**用 GitHub 继续**（真实 OAuth）、**给我发登录验证码**（适用于任何邮箱），或折叠的**粘贴组织 token**（agent 与 CLI）。

![](../src/treg/web/tour/img/01-signin.webp)

> **注意：**本导览使用邮箱验证码这扇门。尚未接入邮件服务器，所以**开发模式下验证码直接显示在页面上**而不是发到邮箱。

### 2 · 邮箱验证码
输入邮箱并点击**给我发登录验证码** —— 页面会显示 `dev code 619565` 以及填写它的输入框。输入 6 位数字并**登录**。首次登录同时会注册你（以及一个个人组织）。

![](../src/treg/web/tour/img/02-email-code.webp)

### 3 · 你的控制台
你进入的是**当前激活的组织**。全新账号有一个个人组织，没有工具。页头有组织切换器、主题切换、头像和退出登录；左侧导航有 工具、组织、活动、教程。

![](../src/treg/web/tour/img/03-dashboard-empty.webp)

---

## 创建团队

### 4 · 创建团队
点击 **+ New team** 并命名 —— 你成为它的 **owner**，它变为激活状态。团队就是你共享工具的地方。

![](../src/treg/web/tour/img/04-create-team.webp)

> **注意：**个人组织在登录时自动创建；团队则总是显式创建。

### 5 · 你是 owner
在 **Organizations** 页面，你的激活团队会有一个 **Manage** 面板：成员、邀请，以及一个危险区。

![](../src/treg/web/tour/img/05-manage-panel.webp)

---

## 邀请成员

### 6 · 邀请队友
输入邮箱，选择角色（viewer / member / admin），点击 **Invite**。treg 会铸造一个**一次性邀请码**内联显示；他们也可以无码接受。**Pending invites**（待接受邀请）下方列出了未完成的邀请（含 Revoke 撤销）。

![](../src/treg/web/tour/img/06-invite.webp)

### 7 · 通过横幅接受
被邀请者登录时，邀请会显示为一个**横幅** —— 点一下 **Accept** 就加入了。无需复制验证码。

![](../src/treg/web/tour/img/08-invite-banner.webp)

> **注意：**邀请绑定到邮箱，所以证明该邮箱（任何入口）即可 —— 验证码只是带外的一个快捷方式。

### 8 · ……或用邀请码加入
拿到了带外传来的验证码？打开 **⤷ Join by code** 并粘贴（必须与你的邮箱匹配）。

![](../src/treg/web/tour/img/17-join-by-code.webp)

---

## 注册资源

### 9 · 添加密钥
**member+** 可以注册。打开 **⚿ Secrets** 并添加一个凭据（名称、值、类型）。值在服务端加密，此后不再显示。

![](../src/treg/web/tour/img/09-secrets.webp)

### 10 · 注册工具
**+ Add tool**：一个工具就是一个上游 **base URL** + 一个 **binding** —— 即密钥、它去哪里
（header/query）、字段名，以及像 `Bearer {secret}` 这样的格式。

![](../src/treg/web/tour/img/10-add-tool.webp)

> **注意：**`{secret}` 在调用时被替换为真实凭据 —— 调用方从不持有它。

### 11 · 多凭据工具
点击 **+ binding** 增加一行 —— 每次调用都会应用每一条 binding（例如一个 OAuth bearer *和*
一个 developer-token 头）。

![](../src/treg/web/tour/img/11-multi-binding.webp)

### 12 · 编辑工具
**✎** 按钮会以预填内容（base URL + bindings）重新打开构建器 → 保存时执行 PATCH。名称保持不变；删除用 **✕**（内联确认）。仍被工具绑定的密钥受保护，无法删除。

![](../src/treg/web/tour/img/12-edit-tool.webp)

### 13 · 注册技能（套件）
一个 **skill** = 一份配方 + 它的密钥 + 它的工具，原子化注册。**+ Skill** → 粘贴 payload
（密钥值内联；CLI 的 `treg.json` 改为从文件加载）。binding 通过 `local_name` 引用密钥；JSON 会先经过校验。

![](../src/treg/web/tour/img/13-skill.webp)

### 14 · 你的工具
已注册的工具以卡片呈现 —— 主机、注入器、拥有者、健康徽章。每个卡片都可：复制片段、试用、编辑或删除。

![](../src/treg/web/tour/img/14-tools-list.webp)

---

## 使用工具

### 15 · 试用 —— 密钥被注入
**Try it** → 输入上游路径 → Send。调用经过代理运行，凭据在服务端注入；响应里显示 `authorization: Bearer …` 尽管你从未发送过密钥。

![](../src/treg/web/tour/img/15-try-it.webp)

> **注意：**这就是整个产品 —— 通过 treg 调用真实 API，密钥在服务端被加上。即使是 **viewer** 也能这么做。

### 16 · 复制片段
**Copy for…** 为 Claude Code、CLI、Python、Node 或 cURL 提供现成片段 —— 指向代理并带上你的 token，没有内联任何密钥。

![](../src/treg/web/tour/img/16-copy.webp)

---

## 角色

### 17 · viewer 角色
以 **viewer** 身份登录时，你能看到工具并可以**复制** / **试用** —— 但注册控件（Secrets、
+ Skill、+ Add tool）和 Manage 面板都消失了。可以免改凭据地使用。

![](../src/treg/web/tour/img/18-viewer-tools.webp)

> **注意：**角色层级为 owner > admin > member > viewer。UI 会隐藏你角色无权做的事；服务端也会强制执行。

### 18 · 管理团队
作为 owner，Manage 面板列出所有人：通过下拉框改角色（仅 owner 可）、**移除** 成员（admin+），以及一个**危险区**，含 Leave（最后 owner 保护）和 Delete（输入确认）。

![](../src/treg/web/tour/img/20-danger-zone.webp)

---

## 超级管理员

### 19 · 平台管控
超级管理员会获得一个跨租户的 **Admin** 导航：平台统计、每个组织（暂停 / 删除）、以及每个用户（授予/撤销超级管理员、暂停、删除）。你自己的那一行受到防锁死保护。

![](../src/treg/web/tour/img/22-admin-users.webp)

> **注意：**Admin 导航只向超级管理员显示。

---

## 收尾

### 20 · 活动 —— 审计日志
**Activity** 列出组织内每一次代理调用 —— 谁、什么、何时、状态。即使有人用的是队友的密钥，账本也会记录真实的调用方。

![](../src/treg/web/tour/img/23-activity.webp)

### 21 · 应用内教程
在 **Help → Tutorial** 下，控制台也内置了完整的交互式 CLI 走查 —— 终端与浏览器记录在一处。

![](../src/treg/web/tour/img/24-help-tutorial.webp)

> 这就是整个 UI：登录 → 建团队 → 邀请 → 注册 → 调用 → 管理 → 拆除。🏁
