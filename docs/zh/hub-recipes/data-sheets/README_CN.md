# sheet-rows（表格行）

把一个公开的 Google Sheet 的行作为一个工具提供。给出该 sheet 的 id（从 URL 取得）以及（如需）标签页的 `gid`。可用 `column` + `equals` 过滤，或用 `search` 搜索每个单元格；`limit` 最大 100。该 sheet 必须被共享为"任何拿到链接的人"（anyone with the link）；本版本不支持私有 sheet。

发布前：`treg tool add sheets --base-url https://docs.google.com`（无密钥），然后在 `uses` 中列出 `sheets`。
