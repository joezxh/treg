---
title: Showcase 排行榜与图片 - 应用、评审、投票、头像
status: shipped
sources:
  - src/treg/domain/showcase/__init__.py
  - src/treg/application/showcase.py
  - src/treg/routers/showcase.py
  - src/treg/domain/images/__init__.py
  - src/treg/application/images.py
  - src/treg/routers/images.py
  - src/treg/infra/imaging.py
  - src/treg/infra/media_store.py
  - src/treg/alembic/versions/0076_showcase_and_avatars.py
  - src/treg/web/showcase.html
  - tests/test_showcase_leaderboard.py
  - tests/test_images.py
related:
  - interface/seo.md
  - architecture/media.md
---

# Showcase 排行榜与图片

`/showcase` 有两部分。"应用"是写在页面本身的一篇编辑式画廊（见 [seo](../interface/seo.md)）。它下面的排行榜是数据库驱动的：团队申请、员工评审、人们点赞，而被批准的应用展示其制作者同意的活跃度徽章。

## 申请与评审

一个团队的 owner 或 admin 在 /showcase 或仪表盘的 Teams 页面申请：名称、链接、标语、描述、类别、制作者、X 账号、发布帖、一个图标和最多四张截图，以及哪些指标可被展示。一个团队最多列出五个应用（被拒绝的不计数）。提案存储在 `ShowcaseApp.pending`；在员工批准之前没有任何东西是公开的。四个展示标志（`SHOW_FLAGS`：调用层级、连胜、供应商、类别）不属于被评审的提案：它们位于条目上，一次保存会立即应用它们（一个"共享"事件），因此一个团队无需等待就能关闭其中任何一个；员工在为一个团队列出一个应用时设置它们。对一个已上线应用的编辑是一个新提案，且上线版本一直保留直到被批准；一个被拒绝的应用可以被编辑并自行重新提交。团队的 owner 或 admin 也可以立即把一个已上线的应用从 showcase 移走（"removed"，状态 `hidden`）；只有员工能再次展示它。员工在私有管理后台评审，它调用员工 API（`/admin/showcase/*`，`require_superadmin`）：批准、带理由拒绝（制作者能看到）、隐藏或再次显示、更正文本、上传图片、为一个团队列出一个应用。队列带有 `pending_since`，即被等待的提案被发送的时间，因此管理员可以在其暂存图片过期之前警告。每个变更都向下一个版本追加一个 `ShowcaseAppEvent`；操作携带一个期望的版本，过时的版本会被拒绝。

## 一个应用的活跃度来自哪里

`ShowcaseApp.usage_source` 是 `team`（该团队做的每次调用；默认值，也是员工列出应用时的起点）或 `keys`（仅用 `ShowcaseAppKey` 中的 API key 做的调用）。团队的 owner 或 admin 选择它（`PUT /showcase/apps/{id}/usage`，key 来自 `GET /showcase/teams/{id}/keys`，仅名称与前缀）。它立即应用且不被评审：它不改变任何公开文本、链接或图片，且只能计数该团队自己的调用；该变更是历史中的一个 `usage` 事件。一个 key 最多属于一个应用；它必须是该团队的且未被撤销。一个轮换的 key（`ApiKey.replacement_key_id`）通过它的替换 key 继续计数，该替换 key 随后被同一个应用接手。员工能看到来源与 key 名称但不能改变它们。一个团队的两个应用若都计数整个团队，会显示相同的数字；该团队通过关联 key 来修正。用无 key 做的调用（仪表盘、某些 MCP 连接）只对全团队应用计数。

| 表 | 持有 | 唯一写方 |
|---|---|---|
| `showcaseapp` | 一个条目：状态、上线字段、同意标志、用量来源、待定提案 | `application/showcase.py` |
| `showcaseappevent` | 仅追加的历史 | `application/showcase.py` |
| `showcaseappkey` | 一个应用活跃度来源的 API key，每 key 一个应用 | `set_usage` |
| `showcaseweek` | 每个来源（一个团队，或一个 key）每个 UTC 周一行 | `refresh_activity`（`treg-worker showcase activity`） |
| `showcasecursor` | 已计入某来源各周的最后 call id | `refresh_activity` |
| `showcasevote` | 每人对每应用一次点赞（行即投票） | `vote` |

团队删除会随团队移除所有这些（连同该团队的每一行），如同它对该团队每一行所做的那样；key 关联在团队的 key 之前被移除。

## 每周行，增量计数

月度数字无法从单一的"最后状态"加上新天数来更新：离开窗口的那一周必须被减去，且不同的供应商计数不能相加。worker 为每个来源每周存一行，这些行是可加的：排行榜求和一个应用的来源（它的 key 及其替换、或它的团队），然后最近四个完整周（仍在运行的周从不计数），对它们的供应商列表取并集，并从最后一个完整周往回走活跃日位以得到连胜。行保留十三周，因此连胜可以超出窗口。被拒绝的调用从未到达供应商，不被计数。行属于来源而非应用，因此切换一个应用的来源只改变它读取哪些行；一个没有已批准应用使用的来源会失去它的行与游标，而一个新使用的来源在下一次运行时从窗口开始计数。

worker 一次计数一点点。每个来源有一个游标，即它已计数的最后一个 `callrecord.id`；一次运行只读该来源在那之后的调用，针对团队走 `(org_id, id)` 索引、针对 key 走 `(org_id, api_key_id, id)` 索引，以几千行为一批，每批是一个短事务，把它们加到它们的周行并移动游标（游标行在被锁之前若缺失则插入，因此两次运行绝不会都创建它）。因此重叠的运行绝不会把一次调用计数两次。比几分钟新的调用等待下一次运行，因此一个仍在被提交的更低 id 不会被跳过。来源轮流每批一次直到运行上限，因此一个繁忙的来源绝不会拖住其他来源；一个繁忙来源的前四周在几次运行中计完。团队的整周查询不是一个选项：一个繁忙团队的周可能是一个非常大的行数，每行从表中读取，因为 `(org_id, created_at)` 索引不持有供应商或工具。点赞是实时的。

## 什么离开服务器

`domain.showcase.public_entry` 是活跃度离开的唯一形态：点赞计数、徽章，以及按每个同意标志，一个调用层级（`100+` 到 `100k+`）、带增长四舍五入到十个百分点的 Rising、连胜天数、供应商计数、顶级类别。看板只排名那些制作者同意该看板指标的应用。`GET /showcase/leaderboard` 在每次查看时检查（`no-cache` 带一个 ETag；未变的看板回答 304），因此一次批准或一个点赞立即显示。没有踩；第二次点击收回一个点赞。点赞需要浏览器会话、一个已验证的人（无智能体、demo 或暂停身份）、相同的源站，以及一个速率限制。应用链接携带 `rel="noopener ugc"`：制作者写这些条目，且 referrer 保留以便他们能看到来自 treg 的访问。所有 showcase 路由，如同页面，在自托管注册表上 404。

## 图片

一条流水线服务每种类型（`domain.images.KINDS`）：用户与团队头像（256 像素正方形 WebP）、showcase 图标（从至少 96 像素来的 512 像素正方形 PNG，因此 logo 在给得大时保持锐利）与截图（WebP，最长边 1280 以及一份 640 副本，保持形状：手机截图保持高；没有任何东西被裁剪或拉伸，且只有正方形被放大以填满它的边）。一次上传在流式传输期间受大小限制，它的前导字节必须是 PNG、JPEG 或 WebP，它在一个像素上限下被解码，并在一个 worker 线程中从它的像素重绘，文件以重绘后主图的 SHA-256 命名，位于 `img/<kind>/`。一切落在私有 STAGING 桶；"发布"把它复制到 PUBLIC 桶（通过 treg 读写：SDK 不能跨桶复制）。头像在设置时发布（staging 只是它们等待到人保存的地方）；showcase 图片在批准后、在行指向它们之前发布，且一个暂存图片已过期的批准会失败并提示"重新上传"。一张被替换的图片一旦没有任何行命名它，就从公共桶删除。`treg-worker media sweep` 通过同一检查删除每个公共图片再也没有行命名它：一个被删除团队或个人留下的，或一个竞态变更遗漏的文件；它跳过比一天新的文件，因为批准在行被保存之前发布。同名文件是一个文件，因此两个团队使用的一张图片在任一方命名它时都保留。

公共桶可能与其他用途共享（页面视频在 `site/` 下）：treg 只在 `img/` 下读取、写入和删除，且桶必须不带任何不限于它自己前缀的生命周期规则。Staging 是 treg 独有的，带一条在约 30 天后让每个对象过期的生命周期规则（被放弃的上传与长久等待的提案都一样）。

URL 从 `TREG_MEDIA_BASE_URL`（一个媒体域名）构建，或当它为空时 treg 自己的 `/media-files/`；数据库只存储 key，因此移动到一个域名不改变任何数据。没有媒体设置时该功能关闭：上传回答 503 且页面显示首字母；一个既不是 https 也不是 localhost 的端点也会让它关闭（被记录），绝不破坏登录。上传与头像变更拒绝跨站 Origin，如同每个 cookie 鉴证的变更。存储 I/O 期间不持有任何数据库连接；每个步骤打开它自己的短会话。
