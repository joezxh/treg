---
title: 术语表（Glossary）
status: reference
sources:
  - external:meetings/2026-06-30-jason-tools-registry.md
related:
  - foundation/charter.md
  - architecture/data-model.md
---

# 术语表（Glossary）

- **工具（Tool）** — 一个已注册、可调用能力 = 一个上游 `base_url` + 一组凭据**绑定（binding）**。按名称或按主机（URL 透传）解析。
- **绑定（Binding）** — 工具上的一次凭据注入：`{secret_id, injector, location, name, format, secret_field, token_encode}`。工具会对每一次调用应用其全部绑定。
- **密钥（Secret）** — 一个被存储的凭据（种类 `env` | `secret_file` | `oauth` | `cli_auth`），静态存储时使用 Fernet 加密，绝不返回给客户端。
- **注入器（Injector）** — 按绑定规则把密钥放入请求（请求头或查询参数）的代码；字符串形态（`env`、`cli_auth`）与 JSON 块形态（`secret_file`、`oauth`）不同。
- **套件（Bundle / skill）** — 一个具名分组 = 配方（SKILL.md）+ 其密钥 + 其工具；通过 `/skills` 原子式注册。
- **代理 / 转发（Proxy / relay）** — `/call` 端点，转发消费者真实的向上游请求并在服务端注入鉴权，因此消费者永远不持有密钥。
- **URL 透传（URL-passthrough）** — 原生面向智能体的调用形式：用 `…/call/` 作为真实上游 URL 的前缀，而不是命名工具 + 路径。
- **无预留使用（Use-without-hold）** — 调用/构建一个密钥已存于注册表的工具，本地不持有任何密钥。
- **消费者 / 创建者 / 管理员（Consumer / creator / admin）** — 可交付 skill 的三种角色：谁调用工具 · 谁注册工具 · 谁管理与监控。
- **自动刷新 vs 手动（OAuth）** — 一个可刷新的令牌块（含 refresh_token + 客户端凭据）由 treg 保持其新鲜度；一个裸上传的令牌按原样注入，过期时由使用者重新上传。
