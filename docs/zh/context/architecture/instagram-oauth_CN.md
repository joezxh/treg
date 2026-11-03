---
title: Instagram OAuth — 直接 Login 与可选的 Facebook Page 工具
status: built; Meta 配置与实时验证待办
sources:
  - scripts/catalog_ingest.py
  - src/treg/application/call/access.py
  - src/treg/application/call/resolve.py
  - src/treg/application/call/service.py
  - src/treg/catalog/instagram.yaml
  - src/treg/catalog/instagram.extended.yaml
  - src/treg/cli.py
  - src/treg/domain/catalog/store.py
  - src/treg/domain/connections/authorization.py
  - src/treg/domain/connections/oauth_flow.py
  - src/treg/infra/oauth_exchange.py
  - src/treg/mcp.py
  - src/treg/routers/call.py
  - frontend/src/state/connections.js
  - frontend/src/pages/ProviderPage.vue
  - src/treg/alembic/versions/0010_oauth_authorization_method.py
  - tests/test_instagram_oauth_architecture.py
related:
  - architecture/auth-secrets.md
  - architecture/catalog.md
  - architecture/proxy-model.md
  - architecture/mcp-oauth.md
  - interface/api.md
  - interface/cli.md
  - interface/dashboard.md
---

# Instagram OAuth

## 契约

`instagram` 是一个带两个独立 grant 的 catalog 供应商：

- `instagram-login` 使用一个 Instagram 用户令牌与 `graph.instagram.com`。在它的注册表审查 key 待定时，它的连接副本说只有 app-role 账户能完成它。
- `facebook-page` 使用一个 Facebook Page 令牌与 `graph.facebook.com`。所选的 Instagram 专业账户必须链接到那个 Page。

`TREG_OAUTH_REVIEW_PENDING` 控制发布而无需代码编辑。通用注册表规则给出这三个状态：

- `instagram-login,page-messages`：普通 Connect 使用 Page `page-tools`；警告与可选的 Page-message 选择对审查者与 app 角色仍可见。
- `instagram-login`：普通 Connect 使用完整 `page-messages`；它的警告与额外 Page 权限选择消失。
- 空：普通 Connect 回到直接 Instagram `manage`；所有审查警告消失。

grant 有独立的 `Secret` 行、工具名、scopes、令牌、过期、健康与资源状态。一个直接 grant 不满足一个仅 Page 端点。一个 Facebook Pages 连接也是独立的且绝不创建 Instagram grant。

`facebook-page` 方法有两个累积的能力。`page-tools` 包含用于核心 Instagram 动作以及 hashtag、discovery、mention/tag、shopping 与最近搜索工具的已批准 Page 权限。它不请求 `instagram_manage_messages` 或 `pages_messaging`。`page-messages` 添加那些消息权限。方法元数据提供它们的标签、帮助、动作副本与权限卡细节；仪表盘不含 Instagram 特定的分支。缺失 scope 指引选择满足端点的最小能力。

旧 Instagram grant 使用 Facebook Login。迁移 `0010` 把它们标记为 `facebook-page` 而不读取令牌材料。运行时元数据也把一个旧 Instagram 行上的空方法视为 `facebook-page`，因此滚动升级继续工作。共享的调用与重连代码向供应商注册表请求这个遗留值；两个服务都不含 Instagram 分支。

## 已验证端点矩阵（2026-09-01）

图例：

- **D** = 在 `https://graph.instagram.com/v25.0` 上带 Instagram 用户令牌的 Instagram Login。
- **P** = 在 `https://graph.facebook.com/v25.0` 上带所选 Page 令牌的 Facebook Page 授权。
- `IG` = Instagram 专业账户 id。`Page+IG` = 一个链接的 Page 与它的 Instagram 专业账户。
- 对于一个 D+P 行，列出的 `instagram_business_*` scope 是直接 scope。Page profile 把它映射到它的 `instagram_*` 等价物并添加 `pages_read_engagement`。Messaging 也需要 `pages_messaging`。

| 端点 ID | 方法与路径 | Grant | 必需 scope(s) | 资源 | 令牌 |
|---|---|---|---|---|---|
| `instagram.instagram.user.profile` | GET `/{ig_user_id}` | D+P | basic | IG | method-specific |
| `instagram.instagram.user.posts` | GET `/{ig_user_id}/media` | D+P | basic | IG | method-specific |
| `instagram.instagram.post.comments` | GET `/{ig_media_id}/comments` | D+P | basic, manage comments | IG | method-specific |
| `instagram.instagram.account.insights` | GET `/{ig_user_id}/insights` | D+P | basic, manage insights | IG | method-specific |
| `instagram.instagram.media.insights` | GET `/{ig_media_id}/insights` | D+P | basic, manage insights | IG | method-specific |
| `instagram.x.user-messages` | GET D `/{ig_user_id}/conversations`; P `/{page_id}/conversations` 带 `platform=instagram` | D+P | basic, manage messages | IG / Page+IG | method-specific |
| `instagram.instagram.message.send` | POST D `/{ig_user_id}/messages`; P `/{page_id}/messages` | D+P | basic, manage messages | IG / Page+IG | method-specific |
| `instagram.instagram.media.container.create` | POST `/{ig_user_id}/media` | D+P | basic, content publish | IG | method-specific |
| `instagram.instagram.media.container.status` | GET `/{ig_container_id}` | D+P | basic, content publish | IG | method-specific |
| `instagram.instagram.post.publish` | POST `/{ig_user_id}/media_publish` | D+P | basic, content publish | IG | method-specific |
| `instagram.x.comment-delete` | DELETE `/{ig_comment_id}` | D+P | basic, manage comments | IG | method-specific |
| `instagram.x.comment` | GET `/{ig_comment_id}` | D+P | basic, manage comments | IG | method-specific |
| `instagram.x.comment-replies` | GET `/{ig_comment_id}/replies` | D+P | basic, manage comments | IG | method-specific |
| `instagram.x.comment-reply-create` | POST `/{ig_comment_id}/replies` | D+P | basic, manage comments | IG | method-specific |
| `instagram.x.comment-hide` | POST `/{ig_comment_id}` 带布尔 `hide` | D+P | basic, manage comments | IG | method-specific |
| `instagram.x.media` | GET `/{ig_media_id}` | D+P | basic | IG | method-specific |
| `instagram.x.media-children` | GET `/{ig_media_id}/children` | D+P | basic | IG | method-specific |
| `instagram.x.media-comment-create` | POST `/{ig_media_id}/comments` | D+P | basic, manage comments | IG | method-specific |
| `instagram.x.user-content-publishing-limit` | GET `/{ig_user_id}/content_publishing_limit` | D+P | basic, content publish | IG | method-specific |
| `instagram.x.user-live-media` | GET `/{ig_user_id}/live_media` | D+P | basic | IG | method-specific |
| `instagram.x.user-stories` | GET `/{ig_user_id}/stories` | D+P | basic | IG | method-specific |
| `instagram.x.hashtag-search` | GET `/ig_hashtag_search` | P | `instagram_basic`, `pages_read_engagement` | Page+IG | Page |
| `instagram.x.hashtag` | GET `/{ig_hashtag_id}` | P | `instagram_basic`, `pages_read_engagement` | Page+IG | Page |
| `instagram.x.hashtag-recent-media` | GET `/{ig_hashtag_id}/recent_media` | P | `instagram_basic`, `pages_read_engagement` | Page+IG | Page |
| `instagram.x.hashtag-top-media` | GET `/{ig_hashtag_id}/top_media` | P | `instagram_basic`, `pages_read_engagement` | Page+IG | Page |
| `instagram.x.catalog-product-search` | GET `/{ig_user_id}/catalog_product_search` | P | basic, shopping products, Page read | Page+IG | Page |
| `instagram.x.user-mentioned-comment` | GET `/{ig_user_id}/mentioned_comment` | P | basic, Page read | Page+IG | Page |
| `instagram.x.user-mentioned-media` | GET `/{ig_user_id}/mentioned_media` | P | basic, Page read | Page+IG | Page |
| `instagram.x.user-product-appeal` | GET `/{ig_user_id}/product_appeal` | P | basic, shopping products, Page read | Page+IG | Page |
| `instagram.x.user-recently-searched-hashtags` | GET `/{ig_user_id}/recently_searched_hashtags` | P | basic, Page read | Page+IG | Page |
| `instagram.x.user-tags` | GET `/{ig_user_id}/tags` | P | basic, Page read | Page+IG | Page |
| `instagram.x.user-business-discovery` | GET `/{ig_user_id}` 带必需 `fields=business_discovery...` | P | basic, Page read | Page+IG | Page |

已验证结果是 21 个支持两种方法的端点与 11 个仅 Page 端点。这不是早先假设的 23/9 拆分。

每个扩展的 Instagram 端点在 catalog 中声明它的路径、查询与 body 输入。这是仪表盘表单、生成的 CLI 命令、API 示例与 agent 提示使用的契约。评论审核写接受 `hide=true` 与 `hide=false`，因此同一端点隐藏与取消隐藏。

用于审计的官方来源：

- [Instagram API with Instagram Login](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/)
- [Instagram API with Facebook Login](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-facebook-login/)
- [Instagram Login permissions](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/)
- [Content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/)
- [Comment moderation](https://developers.facebook.com/docs/instagram-platform/comment-moderation/)
- [Insights](https://developers.facebook.com/docs/instagram-platform/insights/)
- [Messaging conversations](https://developers.facebook.com/docs/messenger-platform/instagram/features/conversation/)
- [Send messages](https://developers.facebook.com/docs/messenger-platform/instagram/features/send-message/)
- [Hashtag search](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/hashtag-search/)
- [Business discovery](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/business-discovery/)

## 连接与健康流

Instagram Login 把短期令牌交换为一个可刷新的长期令牌。刷新元数据使用 `ig_refresh_token` 与 Instagram 刷新端点。回调然后请求 `/me?fields=user_id,username`。它存储那一个被授权的专业账户作为所选资源并创建直接工具。

如果身份响应没有可用账户，secret 保持可见带 `health=setup_required`。不创建工具。细节告诉用户确认该账户是一个 Business 或 Creator 账户并重新连接。供应商请求在数据库会话关闭后运行。

Page grant 保留现有 Page 与 Business discovery。用户选择链接的 Instagram 账户。Treg 推导并把 Page 令牌存储在加密的 OAuth blob 内。仪表盘的 **Add account** 动作把两个 grant 呈现为一个单选方法选择器。它的推荐方法、条件审查副本与有效能力选择都来自同一个注册表审查状态。两个 key 都待定时，Facebook Page 工具被推荐并打开一个核心或消息选择。Page 消息批准之后，该方法直接用完整 Page grant 继续。直接批准之后，Instagram Login 被推荐并打开通常的读/发/管理能力选择器。现有连接行在重连时保留它们存储的方法与最宽授予能力。

在 catalog 调用之前，解析按端点供应商与授权方法选择一个 grant。它在任何上游调用之前检查令牌过期、scopes 与所选资源。一个缺失的 grant 以稳定的字段返回 HTTP 428：error、provider、endpoint id、method、capability、scopes、message、CLI 命令与仪表盘动作。两个 MCP 界面在该调用结果 body 内不变地返回这个对象。

Catalog 可用性也是授权方法感知的。一个双方法端点当存在任一兼容 grant 时连接；一个仅 Page 端点只有当 `facebook-page` grant 存在时连接。仪表盘从每个端点的 `authorization_methods` 与每个连接的存储 `authorization_method` 推导这个，而非特例化端点 id。它的访问 dry-run 保留所选方法的注册表指引，包括仅 Page 的 `--capability page-tools` 命令与动作标签。一个核心 Page grant 不标记一个消息端点为可调用；它的访问检查返回 `page-messages` 升级命令。

对于一个双方法端点，调用方可以选择 `instagram-login` 或 `facebook-page`。仪表盘显示一个选择器；CLI 使用 `--authorization-method`；MCP 工具使用 `authorization_method` 参数；直接 API 调用使用 `X-Treg-Authorization-Method`。选择也控制显示哪个路径与输入。如果省略，端点的第一个声明方法是确定性默认（共享端点的 Instagram Login）。该控制头部被 treg 消费且从不被转发上游。共享客户端从注册表元数据接受方法 id 与显示标签。`POST /oauth/start` 返回所选方法描述作为 `connect_guidance`，让 CLI 无需供应商特定代码就能解释该 grant。

当多个存储的 grant 匹配一个方法时，catalog 回退选择最新的行。工具-grant 解析一次性加载供应商的 secrets 并从那个集合匹配 bindings，而非为每个 binding 加载一个 secret。

## Meta 配置与实时验证

没有仓库任务改变 Meta 设置。一个人必须做这些步骤：

1. 打开 [Meta App Dashboard](https://developers.facebook.com/apps/) 并选择将拥有 Instagram Login 的应用。
2. 添加或打开 **Instagram > API setup with Instagram login > Business login settings**。
3. 把生产重定向 URI 设置为 `https://treg.to/oauth/callback`。对于本地测试，仅在那个隧道活跃时设置 `https://<your-tunnel-host>/oauth/callback`。
4. 把独立的 Instagram App ID 与 Instagram App Secret 复制到本地 `.env` 作为 `TREG_INSTAGRAM_CLIENT_ID` 与 `TREG_INSTAGRAM_CLIENT_SECRET`。不要把这些值放入聊天或源码控制。
5. 当用户将连接应用所有者不拥有或管理的账户时，为 `instagram_business_basic`、`instagram_business_manage_insights`、`instagram_business_content_publish`、`instagram_business_manage_comments` 与 `instagram_business_manage_messages` 请求 Advanced Access。
6. 把现有的 Meta app 凭据保留在 `TREG_META_CLIENT_ID` 与 `TREG_META_CLIENT_SECRET` 用于 `page-tools`。在 App Review 中确认它的 Page 与 Instagram 权限，包括 `instagram_shopping_tag_products`（如果产品工具保持启用）。
7. 通过直接流验证一个 Business 账户与一个无链接 Page 的 Creator 账户。然后通过 `page-tools` 验证一个链接的 Page 账户。从每个类别运行一个安全读。只在有意的测试内容与收件人时测试发布与消息。

App Review 对于应用所有者不拥有或管理的账户的生产访问是必需的。App-role 账户的开发模式测试不能证明审查已完成。只在 Meta 标记相关访问为已批准后改变 `TREG_OAUTH_REVIEW_PENDING`。
