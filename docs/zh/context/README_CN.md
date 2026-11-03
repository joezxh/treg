# tools-registry — 设计片段（design fragments）

<!-- 由 scripts/build-map.py 生成 — 请勿手工编辑；请编辑片段的 frontmatter 代替 -->

与代码库一一对应的小型、聚焦片段。每个片段声明它所覆盖的源文件（frontmatter 中的 `sources:`）。用
`python3 .claude/skills/tools-registry-context/scripts/build-map.py` 重新生成本索引。

## 基础（Foundation）

| 片段 | 状态 | 覆盖 |
|---|---|---|
| [Tools Registry — 章程（它是什么、为什么、代理模型）](foundation/charter.md) | foundational | 2026-06-30-jason-tools-registry.md, README.md |

## 架构（Architecture，代理、鉴权、数据模型）

| 片段 | 状态 | 覆盖 |
|---|---|---|
| [Google Ads 转化追踪 — 采集、outbox、上传](architecture/ads-conversions.md) | shipped | adsconv.py, signup.py, adtrack.js, gtag.js, … |
| [Archive — 带版本的记录与缓存准入](architecture/archive.md) | building | archive.py, hunter.yaml, results.py, 0031_archive_result_admission.py, … |
| [Auth & secrets — 注入器、加密、OAuth 新鲜度、健康检查](architecture/auth-secrets.md) | shipped | injectors.py, ssrf.py, crypto.py, oauth.py, … |
| [Call events — 每次调用一条伪匿名事件，写入 Postgres 之外的 Iceberg 表](architecture/call-events.md) | building | call_events.py, call_events.py, contracts.yaml, test_call_events.py |
| [Endpoint catalog — 用一把已连接密钥"能做什么"，以及该由哪个供应商来做](architecture/catalog.md) | shipped | rankings.py, rankings.py, test_rankings.py, catalog_added.py, … |
| [应用组合与部署角色](architecture/composition.md) | shipped | bootstrap.py, bootstrap_handlers.py, bootstrap_http.py, worker.py, … |
| [数据模型 — 注册表表结构、异步 DB、审计写入器](architecture/data-model.md) | shipped | 0042_pinned_read_scope.py, alembic.ini, env.py, 0001_baseline_current_schema.py, … |
| [Feedback — 问题与建议的私密 intake](architecture/feedback.md) | shipped | feedback_contract.py, __init__.py, reports.py, reviews.py, … |
| [为某项工作找工具 — /catalog/find，按工作召回并做一次裁判请求](architecture/find.md) | building | catalog_find.py, find_recall.py, find_index.py, embed.py, … |
| [The tool hub — 创作者发布、由其他工具组成的工具](architecture/hub.md) | 已构建（第 1–10 阶段，2026-09-09/14；定价灵活性 9.1–9.5 见 `docs/hub-pricing-decisions.md`，上架 + 公开运行日志 10.1–10.5 见 `docs/hub-listing-decisions.md`）；位于 `hub_enabled`（TREG_HUB_ENABLED）之后，在最终合并之前生产环境关闭 | __init__.py, manifest.py, refs.py, graph.py, … |
| [强制执行的导入边界](architecture/import-boundaries.md) | shipped | pyproject.toml, ci.yml, __init__.py, __init__.py, … |
| [Instagram OAuth — 直接 Login 与可选的 Facebook Page 工具](architecture/instagram-oauth.md) | 已构建；Meta 配置与实时验证待办 | catalog_ingest.py, access.py, resolve.py, service.py, … |
| [Local proxy — 拦截程序自身的对外调用（`treg <command>`）](architecture/local-proxy.md) | shipped | localproxy.py, server.js |
| [Local CLI 运行 — 用服务端持有的凭据，以专用用户身份运行供应商 CLI（`treg run`）](architecture/local-run.md) | shipped | localrun.py, egress.py, fsjail.py |
| [MCP — 智能体的前门，以及 treg 作为 OAuth 授权服务器](architecture/mcp-oauth.md) | shipped | auth.py, mcp.py, health.py, mcp_oauth.py, … |
| [Media hosting — 供应商可拉取的引用文件（`treg host`）](architecture/media.md) | shipped | media.py, media.py, models.py, object_store.py, … |
| [Money — 预收余额、账本、Stripe，以及核对它的报表](architecture/money.md) | shipped | policy.py, tavily.yaml, tinyfish.yaml, test_tinyfish.py, … |
| [Multi-tenancy — 组织、成员关系、邀请、每组织作用域](architecture/multi-tenancy.md) | shipped | access.py, 0042_pinned_read_scope.py, test_pinned_read_scope.py, models.py, … |
| [已发布组织的并发请求准入](architecture/org-concurrency.md) | shipped | org_concurrency.py, kv.py, config.py, call.py, … |
| [精确的组织与端点调用配额](architecture/org-endpoint-quota.md) | shipped | org_endpoint_quota.py, service.py, types.py, route.py, … |
| [已发布组织的暂停、速率与并发准入](architecture/org-flow-control.md) | shipped | org_flow_control.py, structured_logging.py, kv.py, config.py, … |
| [进程内组织流量日志](architecture/org-traffic.md) | shipped | org_traffic.py, structured_logging.py, bootstrap.py, call.py, … |
| [Policy extensions — 私有滥用策略可插入的决策点](architecture/policy-extensions.md) | shipped | policy.py, bootstrap.py, signup.py, promotions.py, … |
| [The proxy — 忠实的凭据注入式转发 + 工具解析](architecture/proxy-model.md) | shipped | relay.py, jsontext.py, ssrf.py, api.py, … |
| [Replay — 录制的交换经由某一 checkout 的计费、结果与路由代码重跑](architecture/replay.md) | building | __init__.py, __main__.py, records.py, engine.py, … |
| [Discovery 实验 — 目录搜索背后的相关性裁判，按调用者下一步行为度量；面向智能体提供的"工作优先"答案](architecture/search-experiment.md) | building | catalog_search.py, search_experiment.py, interleave.py, judge.py, … |
| [Shadow provider — 候选供应者与已服务的调用被问同样的问题，事后比较](architecture/shadow.md) | building | shadow.py, shadow.py, 0086_shadow_pairs.py, test_shadow.py |
| [Showcase 排行榜与图片 — 应用、评审、投票、头像](architecture/showcase.md) | shipped | __init__.py, showcase.py, showcase.py, __init__.py, … |
| [Super-admin — 跨租户读取 + 控制](architecture/super-admin.md) | shipped | api.py, admin.py, evidence_retention.py, access.py, … |
| [The table 层 — 一次调用，以行列形式作答（`/table/`）](architecture/table.md) | 已构建，位于 `table_enabled`（TREG_TABLE_ENABLED）之后，默认关闭 | __init__.py, table.py, table.py, call.py, … |
| [Workbench 表格存储](architecture/workbench-storage.md) | foundational | models.py, 0077_workbench_table_metadata.py, teams.py, test_workbench_table_schema.py, … |

## 接口（Interfaces，API · CLI · skill）

| 片段 | 状态 | 覆盖 |
|---|---|---|
| [The API — 唯一的大脑（FastAPI）](interface/api.md) | shipped | key_spend.py, media.py, sitetrack.js, api.py, … |
| [目录浏览分类法 — 开放的放置与命名决策](interface/catalog-review-proposal.md) | backlog | — |
| [The CLI (treg) + skill 脚手架](interface/cli.md) | shipped | cli.py, cli_view.py, home.py, test_released_cli_compat.py, … |
| [Web 仪表盘（由 FastAPI 提供）](interface/dashboard.md) | shipped | App.vue, TeamShowcase.vue, TeamAvatar.vue, UserAvatarDialog.vue, … |
| [Enrich Arena — 付费比较、一键反馈、可见的瀑布流](interface/enrich-arena.md) | shipped | arena.py, arena.py, arena.py, models.py, … |
| [Import — 扫描一个 .env 和/或一个 skills 目录，自动注册为工具 + 套件](interface/env-import.md) | in-progress | providers.py, skills.py |
| [Landing sandbox 后端 - 已关闭](interface/landing-sandbox.md) | closed | sandbox.py, sandbox_identity.py, sandbox.py, __init__.py, … |
| [Onboarding — 首次运行的演示团队（dashboard + CLI）](interface/onboarding.md) | shipped | auth.py, __init__.py, demo.py, first_run.py, … |
| [Search surfaces — robots、sitemap、可爬取目录，以及社交卡片](interface/seo.md) | shipped | api.py, web.py, agent_pages.py, robots.txt, … |
| [Shell 模式（treg shell）— 透明的 CLI 拦截](interface/shell.md) | shipped | shell.py, cli.py |
| [ChatGPT 插件提交的测试用例](interface/skill-openai-test-cases.md) | reference | — |
| [ChatGPT 插件提交的工具理由说明](interface/skill-openai-tool-justifications.md) | reference | — |
| [可交付的 tools-registry skill（3 种人设）](interface/skill.md) | shipped | skill.md, integrate.md, SKILL.md, SKILL.md, … |
| [Web Arena — 私有比较与实时供应商观察](interface/web-arena.md) | gated | web_arena.py, web_arena_scores.py, web_arena.py, web_arena_quality.py, … |

## Ops（部署、扩展）

| 片段 | 状态 | 覆盖 |
|---|---|---|
| [Provider capacity — 了解 treg 自有供应商账户还剩多少](ops/capacity.md) | shipped | __init__.py, capacity_notice.py, test_capacity_notice.py, collectors.py, … |
| [运行与部署服务端](ops/deploy.md) | shipped | pyproject.toml, hatch_build.py, build-dashboard.sh, build-web.sh, … |

## Reference

| 片段 | 状态 | 覆盖 |
|---|---|---|
| [术语表（Glossary）](reference/glossary.md) | reference | 2026-06-30-jason-tools-registry.md |

## guides

| 片段 | 状态 | 覆盖 |
|---|---|---|
| [扩展一个目录分类 — 添加供应商的 playbook](guides/expanding-a-category.md) | guide | oauth_providers.py, authorization.py, oauth_flow.py, oauth_exchange.py, … |
