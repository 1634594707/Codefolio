# Changelog

## [v1.3.2] - 2026-04-18

### Added

- GitScore dimension explanations in the backend payload and AI analysis view, including evidence, next steps, low-data handling, and strongest/weakest dimension cues
- Structured repository analysis fields for strengths, risks, resume-ready bullets, next steps, showcase fit, confidence, and evidence-backed engineering signals
- Focused frontend regression coverage for repository analysis URL persistence and export PDF reuse flows

### Changed

- Repository analysis prompts now incorporate README headings plus engineering-signal detection for tests, CI, docs, examples, container files, frontend/backend structure, and API/demo cues
- Repository and overview analysis panels now render richer sections instead of a short templated summary, making the output easier to review and adapt for resumes or portfolios
- Export PDF generation now reuses already available Markdown artifacts when possible and prefers richer resume bullets over generic highlights for selected projects
- Benchmark suggestions and GitScore explanations are now more actionable in both the API shape and frontend presentation
- Repository analysis cache versioning was bumped to refresh older, shallow analysis snapshots
## [v1.3.1] - 2026-04-17

### Added

- UI guidelines regression coverage for page-level accessibility and HTML correctness checks
- Preservation tests covering compare input submission, repository card click separation, overview history navigation, and loading-copy stability

### Changed

- Replaced loading and async copy ASCII ellipses with Unicode ellipses across Compare, CompareRepos, Repositories, Export, AIAnalysis, and Overview
- Added missing `type`, `width` / `height`, `aria-label`, `aria-live`, `role="alert"`, and chart accessibility attributes across affected frontend pages
- Restructured repository cards to avoid nested interactive elements and converted overview history row activation to semantic buttons
- Updated affected unit and property tests to align with the new UI guidelines and stabilized property-based workspace/app-context test fixtures

## [v1.3.0] - 2026-04-15

### Added

- OAuth-based GitHub sign-in, token-aware repository fetching, and re-auth prompts for expired sessions
- Server-sent event generation progress, workspace import/export, and repository analysis LRU caching
- Error boundary and offline banner UX safeguards across the frontend
- Property-based regression coverage for request deduplication, XSS sanitization, workspace snapshots, cache bounds, history parsing, GitScore invariants, and social card theming

### Changed

- GitScore weighting now includes issue participation, quality density, and higher documentation ceiling
- Export flow now sanitizes rendered resume HTML and delegates PDF generation to the backend POST export endpoint
- Social card rendering now honors light and dark theme selection end to end
- Shared frontend config, i18n wiring, history utilities, and responsive topbar behavior were consolidated for consistency

## [v1.2.0] - 2026-04-14

### Added

- Frontend workspace isolation with persisted `workspaceId`, automatic `X-Codefolio-Workspace` request header, and startup registration via `POST /api/workspaces/ensure`
- Workspace-aware benchmark persistence so the latest repository comparison result can be reused on the export page without rebuilding query params
- Docker support for the full stack with `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `.dockerignore`, and root `docker-compose.yml`

### Changed

- Backend snapshot storage now supports `tenant_scope` and records active workspaces in a dedicated `workspaces` table
- AI analysis, repository benchmark analysis, Redis cache keys, and snapshot invalidation now respect workspace scope instead of sharing one global artifact set
- Repository comparison flow now fills empty benchmark slots more naturally and stores successful results into the current workspace context

## [v1.1.0] - 2026-04-14

### 新增功能

**后端**
- `benchmark_recommendation_service.py`：基于 GitHub Search API 的标杆仓库推荐引擎，按语言、话题、规模分类筛选并排序
- `rate_limiter.py`：滑动窗口 per-IP 速率限制器，防止 benchmark 接口被滥用
- `token_redaction.py`：GitHub Token 脱敏工具，确保 token 不出现在日志或错误响应中
- `i18n/en.json` / `i18n/zh.json`：benchmark 维度标签、行动项、假设卡片的中英文翻译文件
- `database.py`：SQLite 数据库辅助模块
- `GET /api/repos/suggest-benchmarks`：推荐相似标杆仓库接口
- `DELETE /api/repos/cache/{owner}/{repo}`：手动清除仓库缓存接口

**前端**
- `BenchmarkMatrix.tsx`：响应式特征对比表格，支持键盘导航、颜色编码（missing/weak/medium/strong）、行展开查看原始信号
- `ActionList.tsx`：可排序（优先级/投入/影响）、可筛选（维度）的行动项列表，支持快速收益高亮、时间线分组、localStorage 持久化
- `HypothesisCards.tsx`：可折叠的成功假设卡片，支持按可迁移性和类别筛选
- `benchmarkExport.ts`：将 BenchmarkReport 导出为 Markdown（中英文），含特征矩阵表格、行动项编号列表、假设章节
- `formatCacheAge.ts`：缓存时间格式化与 7 天过期检测

### 测试覆盖

**后端 — 基于属性的测试（Hypothesis，每项 100+ 次迭代）**

| 测试文件 | 覆盖属性 |
|---|---|
| `test_repository_profile_service.py` | P2 名称规范化、P3 缓存往返一致性 |
| `test_dimension_analyzer.py` | P5 维度完整性、P6 单元格结构、边界用例 |
| `test_bucket_service.py` | P16 分桶逻辑、P10 桶描述存在性 |
| `test_action_generator.py` | P8 行动项结构与排序、P9 快速收益识别 |
| `test_benchmark_infrastructure.py` | P7 无 LLM 分析、P11 多仓库矩阵结构、P13 部分失败处理 |
| `test_narrative_generation.py` | P14 假设证据要求、P15 置信度赋值、P18 单次 LLM 调用、P19 README 截断、P30 LLM 调用次数上限 |
| `test_api_endpoints.py` | P22 错误响应格式、P12 benchmark 数量上限、集成测试 |
| `test_language_handling.py` | P28 语言参数处理 |
| `test_caching_properties.py` | P25 缓存键格式、P26 差异化 TTL、P27 缓存失效、P29 缓存性能、P31 跨请求复用 |
| `test_security_properties.py` | P34 公开仓库访问、P35 Token 安全、P36 速率限制 |
| `test_recommendation_service.py` | P20 推荐数量边界、P21 推荐相似性过滤 |

**前端 — 单元测试（Vitest + @testing-library/react）**

| 测试文件 | 覆盖内容 |
|---|---|
| `CompareRepos.test.tsx` | 输入校验、添加/删除 benchmark、加载/错误状态 |
| `BenchmarkMatrix.test.tsx` | 渲染、颜色编码、键盘导航 |
| `ActionList.test.tsx` | 排序、筛选、快速收益高亮、分组折叠 |
| `HypothesisCards.test.tsx` | 默认折叠、展开/折叠、可迁移性筛选 |
| `SuggestionUI.test.tsx` | 推荐按钮、面板展示、添加推荐、空/错误状态 |
| `Export.test.tsx` | Markdown 生成（含/不含 benchmark 章节）、导出页面渲染 |

**前端 — 属性测试（fast-check，100+ 次迭代）**

| 测试文件 | 覆盖属性 |
|---|---|
| `urlParams.test.ts` | P23 URL 参数隔离（mine/b 与 users 互不干扰） |
| `staleness.test.ts` | P33 过期警告显示（7 天阈值） |
| `benchmarkExport.test.ts` | P24 Markdown 导出完整性 |

### Bug 修复

- `dimension_analyzer.py`：修复 `analyze_compliance` 将 `None` 的 `license_type` 直接写入 `raw_features`，违反 Req 4.10（未检测到的特征应标记为 `"not detected"` 而非 `None`）
- `benchmark_analysis_service.py`：补全缺失的 `_build_bucket`、`_invert_scores` 辅助方法

---

## [v1.0.0] - 2026-04-13

- 初始发布：仓库 benchmark API、分析服务、CompareRepos UI
