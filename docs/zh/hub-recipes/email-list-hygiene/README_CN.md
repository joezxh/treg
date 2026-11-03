# email-list-hygiene（邮件列表清洗）

在付费使用验证器或发送工具之前，对潜在客户列表做一次免费初筛。每个地址得到一个判定：

| 判定 | 含义 |
|---|---|
| `ok` | 一个值得验证的工作地址 |
| `personal` | gmail.com、outlook.com、icloud.com 及约 100 个其他消费级供应商 |
| `disposable` | 一次性收件箱（CC0 disposable-email-domains 黑名单，约 9,000 个域名） |
| `role` | info@、sales@、support@ 及其他共享收件箱 |
| `duplicate` | 已在列表中更靠前的位置出现过 |
| `invalid` | 不是一个电子邮件地址 |

`to_verify` 是要继续发送下去的列表（用 `allow_personal: true` 可加入 personal 收件箱）；`summary` 统计每种判定。每次调用最多 2,000 个地址。不调用任何工具，也不产生供应商费用：域名列表随工具以 `data.csv` 形式内置。每次调用 $0.002。

要刷新 disposable 列表，从 github.com/disposable-email-domains/disposable-email-domains 重新构建 `data.csv` 并再次发布。
