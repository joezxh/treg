# engineering-team-size（工程团队规模）

根据公司域名估算其雇佣的工程师数量。移植自一个公开的、按成本排序的阶梯：先做身份的公司增广，再用最便宜的、能应答的供应商。

1. `pdl.companies.enrich` 把域名解析为一个规范化的 LinkedIn 公司 URL 与名称：这是下一层级的连接键，因为仅凭域名经常会匹配到错误的实体。该响应会被复用于 R&D 类别的回退，因此配方只对这一层调用一次。
2. `crustdata.companies.enrich`，带 `fields: ["headcount"]`，先按 URL、再按域名：`headcount.by_role_absolute.Engineering`、公司总数，以及工程职能的同比（YoY）增长。
3. 仅当第 2 层无结果时使用的第一次增广响应：`employee_count_by_class.research_and_development`。该类别字段只存在于携带它的 PDL 套餐上；在没有它的密钥上这一层无应答，运行会报告 `no_estimate`。

`method` 选择阶梯：`cost_optimized`（默认）、`crust_only`、`pdl_only`，或 `validate`（运行每一层并报告分歧）。一个为零的计数绝不会被当作"没有工程师"来信任。`confidence`（置信度）为 `strong`（两层在 25% 内一致）、`medium`（只有一个答案）、`low`（触发了审查原因：密度超过 60% 或 100% 的员工数、供应商分歧、无规范 URL）、`none`（无估算）。`review_reasons` 与 `provider_attempts` 说明了原因。

计价 `per_call`：每次成功运行向创作者支付 $0.15，叠加在供应商费用之上（CrustData 每次匹配约 $0.60；PDL 公司增广每次运行 $0.10 一次）。
