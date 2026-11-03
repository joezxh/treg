# hn-mentions（HN 提及）

来自 Algolia 公开 HN 搜索、提及某个词的 Hacker News 故事与评论。用于发布追踪、竞品观察，或寻找可回答的帖子。`sort: new` 按最新优先列出；`top` 按得分排序。`min_points` 丢弃冷清的故事。每条命中携带 HN 链接、评论对应的故事链接、得分、评论数以及文本的前 500 字符。

宿主是创作者自己的工具，注册一次、无需密钥：

    treg tool add hn --base-url https://hn.algolia.com

调用者永远不需要该工具；运行以创作者的身份发起请求。无供应商费用；每次调用 $0.002。
