# brand-mentions（品牌提及）

本周在 Reddit 与 X 上谁在谈论某个品牌，且不含噪音。两个网络的搜索都很宽松（搜索 `linear.app` 会返回 r/LinearTVSupporters；X 会把链接卡片也算进来），所以脚本只在帖子自身文本包含该关键词时才保留，去重后按最新优先排序。`dropped_as_noise` 说明它丢弃了多少内容。

每条提及包含 `source`、`url`、`author`、`where`（subreddit 或 x）、`created_at`、`text`（前 600 字符）以及 `engagement`。X 搜索经由 treg 的路由器，因此由最便宜的 X 供应商来应答。

脚本内计价：`ctx.charge(mentions.length * 0.002, "per mention")`，叠加在供应商费用之上（每次运行约 $0.003），上限为 `max_price_usd` $0.10（50 条提及，即 `limit` 所允许的最大值）。一次什么都没找到的运行只付供应商费用。
