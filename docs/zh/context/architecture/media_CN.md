---
title: Media hosting - 供应商可拉取的引用文件（`treg host`）
status: shipped
sources:
  - src/treg/application/media.py
  - src/treg/routers/media.py
  - src/treg/models.py
  - src/treg/infra/object_store.py
  - src/treg/alembic/versions/0037_media_hosting.py
  - src/treg/alembic/versions/0092_media_object_key.py
  - tests/test_media.py
related:
  - architecture/archive.md
  - architecture/proxy-model.md
  - interface/cli.md
  - interface/api.md
---

# Media hosting（媒体托管）

AIGC 端点（reAPI、PiAPI、OpenRouter 视频）把参考图、语音片段和视频当作公开 URL，由供应商的下载器抓取。笔记本上的智能体没有托管主机，而每一个试过的粘贴型托管，都至少在某个供应商的预检探测上失败过一次：catbox 从 reAPI 基于 fal 的探测不可达、tmpfiles 在下载链接上返回 HTML、uguu 超时。为了落地一个 18 秒的 Seedance 任务，五次提交才成功，这就是 2026-09-14 的代价。`treg host <file>` 消除了这一类问题。

## 形态（Shape）

- `POST /media`（member+，原始 body，`Content-Type` 命名媒体类型）把字节（见下文）连同 `media` 表中的一行元数据一起存储，并回答
  `{url, token, content_type, size, expires_at}`。URL 是 `<public_url>/m/<token>`。
- `GET /m/{token}` 刻意不做鉴权：供应商的下载器不持有 treg 令牌。令牌是 192 位随机比特，且行内不记录任何有关 org 的信息，因此 URL 是唯一的能力。以内联方式用存储的类型提供，带 `Cache-Control: public, max-age=3600` 与
  `X-Robots-Tag: noindex`。不存在列表端点。
- 边界全部位于 `application/media.py`：每文件 30 MB（供应商自有的参考上限）、每 org 滚动 24 小时 300 MB、7 天 TTL（reAPI 的输出 URL 寿命大约这么长），且只接受
  `image/*`、`audio/*`、`video/*`，拒绝 SVG（一种携带脚本的图像类型）。Sandbox 组织被拒绝。路由在 `Content-Length` 上拒绝，并在中途到达上限时再次于流中拒绝，因此超大的 body 永远不会完整进入 worker 的 RAM。
- 过期是在每次上传时内联清理，而非由 cron 完成：每次上传在它自己的事务中跑一批有界的清理
  （`SWEEP_BATCH`，最旧的优先，`SKIP LOCKED`）；每次上传增加一行，因此清理能跟上。被清理触及之前，已过期的行在读取时也会 404。
- 每日配额在并发下是精确的：新行被插入，团队 24 小时的总和（包含它）在一个事务中被读取，按团队由 Postgres 咨询锁串行化（SQLite 串行化该插入的写锁），超过配额的写入会回滚。
- 不计量。托管是一种像轮询一样的礼遇，因此 money 的五项记账保持不变，调用运行时永不触碰此表。

## 字节存放何处

`media_body_write` 决定一个新上传的字节去哪；读取跟每行走，而非跟设置走。

- `db`（默认值，也是没有对象存储的自托管注册表所保留的）：字节是行的 `body`。一行正确地服务于一个 30 MB 的引用，且不需要桶。
- `r2`：字节进入归档的私有桶（`archive_object_store_*`，与归档 body 相同的 R2 客户端，`infra.object_store.build_r2`），作为一个命名对象
  `hosted-media/v1/<64 位随机十六进制>`；行保留元数据和 `object_key`，而 `body` 为 NULL。密钥与 URL 的令牌分开抽取，且不命名任何团队或文件。当该桶未配置时，启动会拒绝 `r2`。`media_r2_timeout_s` 限制整个一次传输。

媒体表中数据库里的 body 是活跃的、短寿命的、大体积的字节：每次上传和每次过期都在数据库里写入并释放整个文件，而这正是迁到桶要停止的事。`GET /m/{token}` 读取行、关闭会话，然后以行的大小作为 `Content-Length` 流式传输对象（`open_named`）；一个大小与行不符的对象回答 503，缺失的对象回答 404，不可达的桶回答 503 并带 `Retry-After`。带 `body` 的行在任一种模式下都从它自身提供，因此切到 `r2` 无需回填（数据库行靠 TTL 离开），切回则在桶保持配置期间继续提供对象。

`r2` 下的上传顺序：清理的事务；然后配额事务，它插入带 `object_key` 且无 `body` 的行；然后在没有会话打开的情况下做对象 PUT。令牌仅在 PUT 之后返回，因此之间没有任何 URL 到达该行；一次失败的 PUT 会删除该行。读取或写入桶期间不持有任何数据库连接（AGENTS.md 规则 3）；
`tests/test_media.py` 在 SDK 接缝处检查它。

被清理行的对象在请求路径之外删除，由每进程一个的后台删除器负责，受队列长度（`DELETE_QUEUE_MAX`）与每次运行时间（`DELETE_RUN_S`）限制。在 `db` 模式下上传路径永不触碰桶：被清理行的对象不会在那里被删除。因此出现没有任何行命名的对象是预期内的：溢出或一次失败的删除、一次超出预算的运行、处于 `db` 模式的清理、一次被取消的上传，以及团队删除（它移除一个团队的行而不触碰桶）。这样的对象是不可达的，因为没有行就没有 URL 服务于它。**桶上针对 `hosted-media/` 的生命周期规则才是保证删除的东西**：给桶设一条在 TTL 之后若干天删除那些对象的规则；删除器只是让它们更早消失。

一旦一个部署切换过去，表的磁盘空间只有在数据库行已过期且表已被重写（repack 或 `VACUUM FULL`）之后才回来；普通 vacuum 让空间可复用但不归还它。

## 未构建（Not built）

- treg 侧对智能体传给供应商的 URL 做预检抓取。那会建模供应商的探测，而不可协商的约束 4 禁止这一点，且它看不到只适用于供应商下载器的主机封禁（catbox 给我们返回 200 而 fal 什么都没拿到）。
- 一个 MCP `host` 工具。需要它的 MCP 客户端可以直接 `POST /media`；当某个智能体要求它时再加该工具，并像其他工具一样把它钉在 MCP 工具集测试中。
