# Codefolio：对比模式扩展 — 仓库增长与「为什么火」设计

> 版本：0.4  
> 状态：草案（供评审与拆任务）  
> 关联：现有「用户对比」见 `frontend/src/pages/Compare.tsx`；总架构见 `.kiro/specs/codefolio/design.md`

**执行摘要**

- **要做什么**：在「用户对比」之外增加「仓库对标」，用可解释特征、差距矩阵与行动项回答「为什么表现更好 / 我该怎么改」，并严守「相关≠因果」。
- **与当前代码的差距**：后端尚无 `repos/profile`、`benchmark` 等端点；仓库深度信号已通过用户画像拉取与 `POST /api/repository/analyze` 部分具备，可复用字段与 Redis 缓存键策略。
- **实现时优先注意**：避免复制「对比页对每个用户打满 `/api/generate`」的成本结构；标杆分析应尽量 **规则 + 可选单次 LLM**，并对 GitHub 元数据做强缓存。

---

## 1. 背景与问题

### 1.0 与当前代码库的对照（实现审计）

| 设计概念 | 文档中的设想 | 仓库中 **已有** | 缺口 / 备注 |
|----------|----------------|-----------------|-------------|
| 用户对比 | Tab「用户对比」 | `/compare`，查询串 `?users=u1,u2,u3`；状态 `compareList` 持久化在 `localStorage`（`codefolio-compare-list`） | 与设计草案中的 `/compare/repos?...` **尚未**并存；后续新增 Tab 时保持 **参数名分离**（见 §6.1） |
| 对比数据加载 | 复用 token / 缓存 | 优先读 `getGenerateCache`，未命中则 `POST /api/generate` | **成本敏感**：每次对比会触发完整档案生成（含多项 AI），与「仅要比分与图表」的轻量需求不匹配；未来可考虑 `GET /api/profile/summary` 类只读端点或「跳过 AI」开关（开放问题可收束） |
| 仓库元数据 | Repository Profile | `GitHubService` 拉取的用户 `repositories[]`（含 stars、topics、`has_readme`、`has_license`、`file_tree` 等） | 缺 **跨仓** 对齐、**分桶**、**标杆推荐**；无持久化「画像快照」表（仅 Redis 缓存用户与单仓分析） |
| 单仓 AI 解读 | 假设卡片证据链 | `POST /api/repository/analyze` → `AIService.generate_repository_analysis`；缓存键 `ai:{username}:repo-analysis:v2:{repo}:{lang}`（见 `backend/cache_keys.py`） | 输出形态与本文 **Success Hypothesis Card** 未对齐；可演进为同一 schema 的「单仓深度」子集 |
| 导出 / 叙事 | 对标报告进导出流 | `Export.tsx`、简历 Markdown、PDF | 需定义 **对标报告 Markdown 片段** 的插入位置与 i18n |
| 数据库 | PG / SQLite 存画像与报告 | 当前 **无** 独立 OLTP；Redis 用于 GitHub + AI 缓存 | 与 §8 一致：MVP 可继续 Redis-only，报告落库为 Phase 2+ 可选 |

### 1.1 现状

- **对比模式**当前以 **GitHub 用户** 为主：多用户 GitScore、雷达维度、语言分布、优势摘要等。
- **简历/导出**流程已强调 README、License、结构等「可写进简历」的信号。
- 用户期望在同一产品心智下回答三类问题：
  1. **别人的某个项目为什么能火**（或可观测地「表现更好」）？
  2. **我的项目接下来怎么更新**才更可能获得关注与采用？
  3. **我缺哪些方向**（定位、运营、工程、社区、传播）？

### 1.2 核心矛盾

- 「火」**不是单一标量**：受作者影响力、时机、赛道、运气影响；产品应避免「保证爆款」表述。
- 公开数据**无法还原因果**，只能做：**同类可比下的特征差异 + 可验证假设 + 可执行建议**。
- 需与现有 **Codefolio** 定位一致：**帮助开发者理解差距、行动清单、写进简历的叙事**，而非替代增长黑客工具全家桶。

### 1.3 设计原则

1. **可解释**：每条结论尽量带「数据证据」或「可勾选检查项」。
2. **同类可比**：标杆默认按语言 / topic / 仓库体量分桶，避免拿内核项目和个人脚本比 star。
3. **可行动**：输出优先是可执行任务（README 补图、发版节奏），其次才是战略叙事。
4. **诚实边界**：显著标注「相关非因果」「不可观测因素」。
5. **渐进交付**：先两仓静态对标，再推荐标杆、再时间序列与社区信号。

### 1.4 高频用户视角：体验与工程上的改进方向

以下从 **真实使用路径**（搜索用户 → 仓库页选项目 → AI 分析 → 导出 / 对比）反推，供与分期 Roadmap 对齐；**不等同于**本迭代必须全做。

**产品与信息架构**

1. **对比与工作区的连贯性**：侧栏「对比」未带 `?user=`，与 Repositories / Export 的「当前用户」上下文分离，对老用户是合理（跨人对比），但对「拿当前用户快速拉两人」略多一步。建议在仓库对标落地时：**一键带入** `currentUser` 的默认「我的仓」候选（与 §6.1 入口一致）。
2. **历史与可复现**：`Overview` 历史、`generate` 缓存与 `compareList` 三套记忆互不统一。对标报告若需「一周后打开同一份结论」，依赖 **URL 参数 + 服务端报告 id** 比仅靠本地 state 更可靠。
3. **期望管理文案**：对比页 AI「Roast」偏娱乐；仓库对标侧应默认 **专业/教练口吻**，并在 UI 上与用户对比区分，避免同一产品两种人格混读。

**性能与成本**

4. **对比页 API 形态**：三人对比最坏情况 = 三次完整 `generate`（三次全套 AI）。建议在规格层记下：**轻量对比**（仅 GitHub 聚合 + 规则 GitScore）与 **完整对比**（含 AI）分流，仓库对标 **禁止**默认走「每仓全套 profile AI」。
5. **GitHub 配额**：标杆推荐若打搜索 API，需与现有 `GitHubService` 的缓存 TTL（`GITHUB_CACHE_TTL`）统一，并在 UI 上展示「数据刷新时间」。

**仓库对标专属**

6. **复用单仓分析**：Phase 1 可规定：对用户已跑过 `repository/analyze` 的仓，**直接复用缓存**生成证据条目，减少重复 LLM。
7. **空状态与失败**：与 Compare 类似，需 **部分成功**（例如 2 个标杆里 1 个 404）时的行级错误与重试，而非整页失败。
8. **无障碍与表格**：§9.2 已列；补充：差距矩阵列数随标杆数增加时，**移动端**需卡片化布局或横向滚动策略（与现有 `compare-*` 响应式模式对齐）。

---

## 2. 目标用户与场景

### 2.1 用户画像

| 画像 | 动机 | 典型行为 |
|------|------|----------|
| 独立开发者 | 希望某个 side project 被看见 | 补 README、选 topic、发 demo |
| 求职者 | 需要「代表项目」有说服力 | 对齐热门同类项目的完成度 |
| 技术负责人 | 评估开源策略 | License、贡献指南、发布节奏 |
| 学生 / 转岗 | 不知道「好项目长什么样」 | 用标杆库学习结构与叙事 |

### 2.2 关键场景（用户故事）

- 作为用户，我选择 **我的仓库 A** 和 **标杆仓库 B**，希望看到 **差距列表** 和 **按优先级排序的改进清单**。
- 作为用户，我只选 **我的仓库**，希望系统 **在同 topic / 同语言下推荐 2～3 个标杆** 并说明推荐理由。
- 作为用户，我在 **对比页** 同时保留 **多人对比** 与 **仓库对标** 两种 Tab，数据可复用（同一 GitHub token 与缓存策略）。

---

## 3. 「火」的操作化定义

### 3.1 多指标合成（建议）

将「表现好」拆为若干 **可计算维度**，再在同类分桶内算 **分位数** 或 **z-score**：

| 维度 | 含义 | 数据来源（示例） |
|------|------|------------------|
| 注意力 | Star、Star 增速（需时间窗口） | REST/GraphQL 历史若可缓存 |
| 协作 | Fork、PR、贡献者数 | API |
| 活跃度 | 最近 commit、issue 更新 | API |
| 可信度 | README、License、CI、Release | 已有/扩展 |
| 发现性 | Topics 数量与相关性、描述关键词 | API |
| 粘性 | Issue 讨论深度、重复贡献者占比 | API（进阶） |

**默认展示**：不合成单一「火爆指数」，而是 **雷达或多柱对比 + 文字解释**，避免一个数字误导。

### 3.2 同类可比（分桶策略）

- **主桶**：`primary_language` + 至少一个 **重叠 topic**（若无 topic，退化为语言 + 规模档）。
- **规模档**：按 star 数量级或代码量分档（例如 `<100` / `100-1k` / `1k+`），避免体量悬殊。
- **时间窗**：新仓库（`<6 个月`）与老仓库分开解读增速。

### 3.3 与「简历价值」的衔接

- 对求职者：**「完成度信号」**（README、测试、文档、License）权重大于绝对 star。
- 对增长向用户：**增速 + 传播结构**（是否易被引用、是否模板化）权重略升。

---

## 4. 「为什么能火」分析框架

### 4.1 成功假设卡片（Success Hypothesis Card）

对每个标杆库生成 **结构化卡片**（便于 UI 与 JSON schema）：

```text
- hypothesis_id
- title（一句话假设）
- category（见下节分类）
- evidence[]（每条：type=readme_section|metric|file|topic, detail）
- transferability（high|medium|low）对「我的仓库」类型是否适用
- caveats[]（不可复制因素：个人 IP、时代红利等）
- confidence（rule_based|llm_summarized）
```

### 4.2 分析维度分类（固定 taxonomy，利于对比表）

1. **定位与叙事**：一句话价值、目标用户、与替代方案差异、README 首屏信息密度  
2. **第一印象**：截图/GIF、徽章、目录结构、多语言 README  
3. **上手与演示**：Quickstart 步数、docker / 一键脚本、example 目录、在线 demo 链接  
4. **工程可信度**：测试、CI、类型检查、安全政策、依赖透明度  
5. **发布与维护**：SemVer、CHANGELOG、Release 频率、deprecation 说明  
6. **社区与协作**：CONTRIBUTING、Code of Conduct、issue 模板、good first issue、回应节奏  
7. **发现与增长**：Topics、SEO 友好描述、是否易被其他仓库依赖、CLI/库/应用形态差异  
8. **合规与采用**：License 清晰度、商业友好度、专利/商标说明（进阶）

### 4.3 规则层 + LLM 层分工

- **规则层**：从 GitHub 元数据与静态文件抽取 **布尔/数值特征**（是否有 `.github/workflows`、README 字数、是否有 `## Installation` 等）。
- **LLM 层**：在特征与摘录片段上生成 **假设归纳、叙事建议、中文/英文润色**；**禁止**编造未出现的指标（通过 schema 校验与引用 evidence id）。

### 4.4 反幻觉与质检

- 输出中每条叙事建议应 **引用至少一条 evidence**（或标记为「推测」）。
- 对缺失数据：**明确写「未检测到」**，不推断为「没有」。
- 可选：**二次 LLM 自检**（短 prompt：「删除无法从证据推出的句子」）。

---

## 5. 「我该怎么更新」：差距 → 路线图

### 5.1 特征差分矩阵

行：**分析维度**；列：**我的仓库 | 标杆 A | 标杆 B**；单元格：**等级**（缺失 / 弱 / 中 / 强）或 **原始特征**。

### 5.2 行动项（Action Item）结构

```text
- action_id
- dimension
- title
- rationale（对应哪条差距）
- effort（S|M|L）与 impact（1-5）
- priority_score（可简单 = impact / effort）
- checklist[]（可勾选的子步骤）
- suggested_deadline（可选：7 天 / 30 天）
```

### 5.3 路线图视图

- **Quick wins（7 天）**：低成本高感知（README 动图、topic、License badge）。  
- **Foundation（30 天）**：CI、基础测试、首个语义化版本 Release。  
- **Growth（90 天）**：插件化、文档站、社区模板、被其他项目引用路径。

### 5.4 「缺什么方向」：战略包（Strategy Pack）

在行动清单之上，生成 **3～5 条互斥或组合策略**，每条包含：

- **适用条件**（例如：库形态为 CLI、无 UI）  
- **目标信号**（例如：fork 数、被依赖数、issue 质量）  
- **不要做清单**（避免与定位冲突的动作）

示例策略包名称（仅示意）：

- **演示优先型**：一切为「10 秒看懂 + 30 秒跑通」服务。  
- **生态嵌入型**：优先被其他仓库引用、提供稳定 API 与 semver。  
- **社区飞轮型**：降低 first contribution 成本、明确 roadmap。  
- **可信企业型**：License、安全、支持渠道、长期维护承诺。  
- **垂直深度型**：单点痛点打穿 + 极致文档与案例。

---

## 6. 产品与信息架构

### 6.1 入口建议

| 入口 | 说明 |
|------|------|
| 对比页 Tab | 「用户对比」|「仓库对标」切换；**现状**路由为 `/compare?users=`（仅用户对比），新增仓库模式时采用 **独立 query**（如 §9.1 的 `mine` / `b`），避免与 `users` 语义冲突 |
| 仓库详情/列表 | 从 `Repositories.tsx` 卡片「对标热门同类」一键带入 `owner/repo`（可与「分析到简历」并存为次要操作） |
| 概览候选区 | `Overview.tsx`「最佳候选」旁「找同类标杆」——与现有 `candidateAction` 跳转 Repositories 形成漏斗 |

### 6.2 仓库对标页（线框级）

1. **选择区**：我的仓库（必选）+ 标杆 1～3（可选；空则「推荐标杆」）。  
2. **总览**：同类桶说明、体量与年龄对比一句话。  
3. **假设卡片墙**：按 taxonomy 分组折叠。  
4. **差距矩阵**：可导出 Markdown（与导出页能力协同）。  
5. **行动清单**：可排序、可勾选、可同步到本地 TODO（未来：导出到 Notion/Issue，非 MVP）。  
6. **免责声明**：固定页脚组件。

### 6.3 与现有 Compare 的关系

- **用户对比**：保留现有雷达、GitScore、语言分布。  
- **仓库对标**：新数据模型与 API；前端可复用卡片、图表、配色与 i18n 模式。  
- **深层联动（后期）**：同一用户下「你最弱的维度」与「你仓库最弱的完成度」交叉推荐（需小心信息过载）。

---

## 7. 数据与 API 草案

### 7.1 仓库画像（Repository Profile）缓存

建议后端持久化或 Redis 缓存 **按 `owner/repo` + commit SHA 或时间戳** 的 JSON：

- 基础字段：stars、forks、topics、language、pushed_at、created_at、license、description  
- 结构信号：默认分支、是否有 wiki、releases 列表摘要  
- 文件层：README 是否存在、章节标题列表、是否有 `docs/`、`examples/`、workflow 文件数  
- 可选：最近 N 条 commit message 主题（脱敏统计）

### 7.2 建议端点（命名示意）

- `POST /api/repos/profile`：拉取或返回缓存画像。  
- `POST /api/repos/benchmark`：请求体 `{ mine, benchmarks[], language_hint?, topics_hint? }` → 返回差分矩阵 + 假设卡片 + 行动项。  
- `GET /api/repos/suggest-benchmarks?owner=&repo=&limit=`：推荐标杆列表 + 理由代码（便于前端展示图标）。

### 7.3 速率与成本

- GitHub API：批量对比需 **聚合请求** 与 **强缓存**（TTL 按数据类型分级：元数据短、README 中、star 历史长）。  
- LLM：对 **差分结果 + 截断 README** 调用一次或分块总结；大仓库 README 需 **分段摘要再合并**。

### 7.4 与现有后端能力的衔接（减少重复造轮子）

- **`POST /api/repository/analyze`**：请求体已有 `username` + `repo_name` + `language`；响应中的 `repository`（topics、file_tree、`has_readme` 等）与 `analysis` 可直接映射为 §4.1 的 `evidence[]` 与规则层特征。新增 benchmark 端点时优先 **组合调用** 已有 `GitHubService.fetch_user_data` 或抽一层 `fetch_repo_full_name(owner, repo)`，避免第三条数据抓取路径分叉。
- **Redis**：`repository_analysis_cache_key` / `DELETE /api/cache/{username}` 已覆盖仓级分析缓存；若增加「对标报告」缓存，键建议带 `prompt_hash` 或 `feature_hash`，并在文档 `.env.example` 中补充 TTL 说明（与 `AI_CACHE_TTL` 区分）。
- **错误模型**：沿用 `map_exception_to_http` 的 `{ code, message, details }`，前端可用与 `App.tsx` 中 `errorByCode` 相同模式扩展 `repository_not_found`、`benchmark_*` 等 code。

---

## 8. 数据库与存储选型

本功能涉及 **仓库画像缓存**、**可选的 Star 时序**、**对标任务记录**、**LLM 结果缓存** 等，需要区分 **事务型主库**、**热缓存** 与 **分析/时序** 负载，避免「一个数据库打天下」导致成本或模型扭曲。

### 8.1 按场景拆存储职责

| 场景 | 访问模式 | 一致性要求 | 典型数据 |
|------|----------|------------|----------|
| 仓库画像快照 | 读多写少，按 `owner/repo` 键查 | 最终一致即可 | JSON 特征、README 摘要、抓取时间 |
| API 限流与会话 | 极高 QPS、可丢 | 弱 | 计数器、短期 token |
| Star / 指标历史 | 追加写、按时间范围查 | 最终一致 | `(repo_id, observed_at, stars)` |
| 对标报告 | 写入一次、多次读取 | 强一致（用户维度） | 报告 JSON、版本号、用户关联（若登录） |
| 全文 / 相似仓库检索 | 读多、复杂查询 | 可异步重建 | topic、description 索引（可用 PG 或专用引擎） |

**原则**：热路径用 **内存或 Redis**；需要关联查询与长期保留的用 **关系型主库**；超大规模时序再考虑 **专用时序库或列存**（Phase 3+）。

### 8.2 主库（OLTP）选项对比

| 选项 | 适用阶段 | 优点 | 缺点 / 风险 |
|------|----------|------|-------------|
| **PostgreSQL** | 默认推荐（与总架构一致） | JSONB 存画像灵活、索引强、生态成熟（全文 `tsvector`、可选 Timescale 扩展）、托管多（RDS、Neon、Supabase） | 自托管需备份与升级策略 |
| **SQLite** | 单机 / 边缘 / 极简 MVP | 零运维、嵌入式、适合 demo 与侧车 | 高并发写入与多副本需额外方案；不适合多实例无共享盘横向扩展 |
| **MySQL / MariaDB** | 团队已有 MySQL 栈时 | 成熟、托管便宜 | JSON 与复杂分析相对 PG 略弱；本设计未强依赖 |
| **MongoDB** | 纯文档、schema 极不稳定时 | 嵌套文档自然 | 多文档事务与报表 JOIN 成本；与本项目「报表 + 用户」模型重叠度一般 |

**建议默认**：**PostgreSQL** 作为主库（与 `.kiro/specs/codefolio/design.md` 中 PostgreSQL 选型对齐）；若部署目标仅为 **单进程演示**，可 **SQLite 起步**，迁移路径用抽象 Repository 层 + Alembic/Flyway 类迁移。

### 8.3 缓存层选项对比

| 选项 | 适用 | 说明 |
|------|------|------|
| **Redis** | 生产推荐 | TTL 控制 GitHub 与 LLM 缓存、分布式限流；数据结构丰富 |
| **KeyDB / Valkey** | Redis 协议兼容 | 开源协议或成本考量时的替代 |
| **进程内 LRU** | Phase 1 无 Redis 时 | 实现快，多实例不一致；仅适合单机 |

**建议**：有 **多实例 API** 时上 **Redis**；单机 MVP 可 **内存 dict + TTL**，文档中写明后续替换点。

### 8.4 时序与分析（可选，Phase 3+）

| 选项 | 何时考虑 |
|------|----------|
| **PostgreSQL + 分区表 / TimescaleDB** | Star 采样点千万级以下、希望与主库同栈运维 |
| **ClickHouse / BigQuery** | 全站分析、大量历史 star 快照、BI 查询 |
| **仅对象存储 + 批处理** | 成本极低、实时性要求低（日更曲线） |

MVP **不必**上独立时序库；先 **PG 一张窄表** `(repo_full_name, captured_at, stars, forks)` + 索引 `(repo_full_name, captured_at DESC)` 即可。

### 8.5 推荐组合（按团队体量）

1. **MVP / 个人部署**  
   - 主库：**SQLite** 或 **PostgreSQL**（Docker 一键）  
   - 缓存：进程内 TTL  
   - 对象存储：可选（存大 README 原文快照时）

2. **小团队生产（推荐）**  
   - 主库：**PostgreSQL**（Neon / RDS / 自建）  
   - 缓存：**Redis**  
   - 文件：S3 兼容桶（若存卡片/导出）

3. **增长与分析后期**  
   - 保留 **PostgreSQL** 为权威源  
   - Star 历史超阈值再 **分区** 或 **异步导出到列存** 做报表

### 8.6 与本功能相关的逻辑表（示意）

非最终 schema，仅表达实体关系，便于选库后落地：

- `repository_snapshot`：`full_name`、`fetched_at`、`payload_json`（JSONB）、`content_hash`  
- `repo_metrics_timeseries`：`full_name`、`observed_at`、`stars`、`forks`（可选）  
- `benchmark_report`：`id`、`mine_repo`、`benchmark_repos[]`、`report_json`、`locale`、`created_at`  
- `llm_cache`：`prompt_hash`、`model`、`response_json`、`expires_at`（或仅用 Redis，不落库）

PostgreSQL 下 `payload_json`、`report_json` 用 **JSONB** + **GIN**（按 topic、language 查询时）较合适。

### 8.7 选型决策检查清单

- [ ] 是否 **多实例** 部署 API？是 → 缓存用 **Redis**，避免内存缓存不一致。  
- [ ] 是否需要 **登录用户** 保存历史对标？是 → 主库必选 **可事务** 的 RDBMS。  
- [ ] Phase 3 是否承诺 **Star 曲线**？是 → 提前在 PG 设计 **分区或保留策略**（如保留 90 天细粒度 + 周聚合）。  
- [ ] 是否已有 **托管偏好**（Supabase、PlanetScale、RDS）？在以上默认上 **优先对齐现有供应商** 以降低运维面。  
- [ ] **合规**：数据驻留区域（EU/国内）是否限制云厂商？反向约束托管 PG/Redis 区域。

---

## 9. 前端与交互细节

### 9.1 状态与 URL

- Query 示例：`/compare/repos?mine=user/repo&b=org/repo1,org/repo2`  
- 与现有 `compare?users=` **参数名区分**，避免路由歧义。  
- 路由与组件拆分草图见 **§16**；后端契约见 **§15**。

### 9.2 无障碍与可读性

- 差分表支持 **键盘导航**、**高对比**模式下的边框加强。  
- 假设卡片 **默认折叠**「证据详情」，避免首屏过长。

### 9.3 国际化

- taxonomy 维度名、策略包名：**中/英 key** 与现有 `labels` 模式一致。  
- LLM 输出语言与 **内容语言设置** 对齐（与 `contentLanguage` 一致）。

---

## 10. 分阶段交付（Roadmap）

### Phase 0 — 设计冻结

- 确定 taxonomy、Action schema、免责声明文案。  
- 确定「同类桶」最低可行规则（避免过度工程）。

### Phase 1 — MVP

- 两仓静态对标：特征表 + 10～15 条规则驱动行动建议 + **单次** LLM（仅润色与假设归纳，输入为规则差分 + README 截断，**禁止**每仓重复全量 profile AI）。  
- 仅支持手动输入两个 `owner/repo`。  
- **工程验收**：新端点复用 §7.4；README / 元数据命中 Redis 缓存；P95 延迟与 LLM 调用次数可观测（日志或简单 metric）。

### Phase 2 — 产品化

- 标杆推荐（同 topic + 规模档）。  
- 从 Repositories / Overview 一键带入（见 §6.1）。  
- 导出：`Export.tsx` 增加可选区块「仓库对标摘要」或独立「复制对标报告」按钮（与简历主体解耦，避免拖慢 PDF 首版）。

### Phase 3 — 增强

- Star **增速曲线**（需历史数据存储策略）。  
- **依赖反向引用**（被哪些仓库 dependabot 式引用，若 API 允许）。  
- **社区健康**（贡献者曲线、bus factor 粗指标）。

### Phase 4 — 实验性

- 允许粘贴 **Hacker News / Reddit 帖子链接** 作为「传播上下文」（抓取标题与评论主题，辅助解释「外因」）。  
- 与个人 **开发者对比** 联动：「你的账号增长策略 vs 仓库完成度」一页摘要。

---

## 11. 指标与实验

### 11.1 产品指标

- 仓库对标页 **完成率**（选满并生成报告的比例）。  
- **复制/导出**次数。  
- **返回率**（7 天内再次打开同一仓库对标）。

### 11.2 质量指标

- 用户反馈：**「建议不接地气」** 比例（内嵌 thumbs）。  
- **证据覆盖率**：每条 LLM 结论绑定 evidence 的比例（后台日志）。

### 11.3 A/B 想法

- 行动清单 **按 impact/effort 排序** vs **按维度分组**。  
- 是否默认展示 **策略包**（部分用户可能只要 checklist）。

---

## 12. 风险、合规与伦理

- **幻觉风险**：严格 schema + 证据引用；缺失数据显式标注。  
- **竞品与抄袭**：建议强调「学习结构与完成度」，禁止鼓励抄袭代码与文案。  
- **隐私**：仅公开仓库；若未来支持私有仓需 OAuth 与范围说明。  
- **GitHub ToS**：遵守 API 使用条款与缓存政策。  
- **期望管理**：文案避免「必火」「爆款公式」等表述。

---

## 13. 开放问题（待决策）

1. 标杆推荐是否 **排除** 组织官方超大仓（kubernetes 等）默认不出现在 side project 桶？  
2. Star **历史**是否值得单独建表，还是用第三方数据集快照？  
3. **中文社区**（掘金、小红书）传播是否纳入 Phase 4，还是保持 GitHub 内闭环？  
4. 是否对 **许可证不兼容** 的「借鉴」给出警告（例如 GPL vs 闭源产品）？  
5. 行动清单是否需要 **与 GitHub Issue 创建** 集成（OAuth 范围与复杂度）。  
6. **用户对比**是否引入「无 AI / 仅数据」模式以降低 `generate` 成本，并与仓库对标共享同一套轻量画像？  
7. 仓库对标路由采用 **`/compare` 下 Tab** 还是 **`/compare/repos` 子路径**（利于分享链接与代码分割）？

---

## 14. 附录：与现有代码的映射（实现时查阅）

| 概念 | 可能落点 |
|------|----------|
| 用户对比 UI | `frontend/src/pages/Compare.tsx` |
| 对比列表状态 | `frontend/src/context/AppContext.tsx`（`compareList`、`addToCompare`，键名 `codefolio-compare-list`） |
| 从总览加入对比 | `frontend/src/pages/Overview.tsx`（跳转 `/compare?users=...`） |
| 仓库列表与卡片 | `frontend/src/pages/Repositories.tsx` |
| 单仓 AI 与简历条目 | `frontend/src/utils/resumeProjects.ts`、`POST /api/repository/analyze` |
| 导出与 Markdown | `frontend/src/pages/Export.tsx` |
| 后端入口与错误包装 | `backend/main.py`（`map_exception_to_http`、`sanitize_username`） |
| GitHub 数据抓取 | `backend/services/github_service.py` |
| 评分维度 | `backend/services/score_engine.py`（与用户侧 GitScore 雷达一致） |
| AI 调用 | `backend/services/ai_service.py`（仓级：`generate_repository_analysis`） |
| Redis 键与清理 | `backend/cache_keys.py`、`DELETE /api/cache/{username}` |
| 前端类型 | `frontend/src/types/generate.ts`（`GenerateResponse.user.repositories` 字段可对齐画像） |
| 仓库对标 API / 路由草案 | 本文 **§15**、**§16** |
| 总设计 | `.kiro/specs/codefolio/design.md` |

---

## 15. 附录：后端接口草稿（MVP → Phase 2）

以下为 **草案**，实现时可拆到 `backend/routers/repos_benchmark.py` 并在 `main.py` 挂载 `app.include_router(...)`；错误体与现有接口一致：`{ "code": string, "message": string, "details"?: any }`。

### 15.1 约定

- **`full_name`**：`owner/repo`，大小写不敏感；服务端规范化为 GitHub 返回形式。
- **`language`**：`en` | `zh`，与 `GenerateRequestModel` 对齐。
- **缓存**：画像类响应带 `fetched_at`（ISO8601）；Redis 键建议 `repo:profile:v1:{owner_lower}/{repo_lower}`，TTL 分级见 §7.3。

### 15.2 `POST /api/repos/profile`

拉取或返回缓存的 **单仓画像**（规则层输入，不必调用 LLM）。

**Request**

```json
{
  "full_name": "facebook/react",
  "language": "zh"
}
```

**Response（200）** — 字段与现有 `repository/analyze` 中 `repository` 块 **对齐并扩展**，便于前端共用类型：

| 字段 | 类型 | 说明 |
|------|------|------|
| `full_name` | string | 规范 owner/repo |
| `description` | string? | |
| `stars` / `forks` | number | |
| `language` | string? | GitHub 主语言 |
| `topics` | string[] | |
| `license` | string? | SPDX 或 name |
| `default_branch` | string? | |
| `created_at` / `pushed_at` | string? | ISO8601 |
| `has_readme` | bool | |
| `readme_sections` | string[] | 一级 `##` 标题列表（可选） |
| `has_license_file` | bool | 与现 `has_license` 同义时可映射 |
| `workflow_file_count` | number | `.github/workflows` 下文件数 |
| `has_contributing` | bool | |
| `has_code_of_conduct` | bool | |
| `has_security_policy` | bool | |
| `release_count_1y` | number? | 近一年 release 数（可选，Phase 2） |
| `fetched_at` | string | 本次画像生成时间 |

**Errors**

| HTTP | code | 场景 |
|------|------|------|
| 400 | `invalid_repo` | 非法 full_name |
| 404 | `repository_not_found` | 仓库不存在或不可见 |
| 429 | `rate_limit_exceeded` | GitHub 限流 |

### 15.3 `POST /api/repos/benchmark`（MVP 核心）

两仓或多仓 **静态差分** + 规则行动项；**可选**单次 LLM 润色（`include_narrative: true`）。

**Request**

```json
{
  "mine": "octocat/Hello-World",
  "benchmarks": ["vercel/next.js"],
  "language": "zh",
  "options": {
    "include_narrative": true,
    "max_readme_chars_per_repo": 12000
  }
}
```

约束：`benchmarks` 长度建议 Phase 1 为 `1`，Phase 2 为 `1～3`。

**Response（200）**

```json
{
  "bucket": {
    "label": "TypeScript · shared topic: react",
    "warning": "体量差异较大，结论仅供参考。"
  },
  "profiles": {},
  "feature_matrix": {
    "rows": [
      {
        "dimension_id": "first_impression",
        "label_key": "benchmark.dimension.first_impression",
        "cells": [
          { "repo": "octocat/Hello-World", "level": "weak", "raw": { "has_screenshot": false } },
          { "repo": "vercel/next.js", "level": "strong", "raw": { "has_screenshot": true } }
        ]
      }
    ]
  },
  "hypotheses": [
    {
      "hypothesis_id": "h1",
      "title": "首屏信息密度更高",
      "category": "positioning",
      "evidence": [
        { "type": "metric", "detail": "readme_h2_count: 12 vs 3", "repo": "vercel/next.js" }
      ],
      "transferability": "high",
      "caveats": ["作者影响力未纳入"],
      "confidence": "rule_based"
    }
  ],
  "actions": [
    {
      "action_id": "a1",
      "dimension": "first_impression",
      "title": "补充 README 首屏截图或 GIF",
      "rationale": "benchmark 在 first_impression 为 strong",
      "effort": "S",
      "impact": 4,
      "priority_score": 4.0,
      "checklist": ["截取核心流程 1 张", "压缩到 < 500KB"],
      "suggested_deadline": "7d"
    }
  ],
  "narrative": {
    "summary": "（可选，LLM）",
    "disclaimer": "相关非因果；数据来自公开仓库快照。"
  },
  "generated_at": "2026-04-12T12:00:00Z",
  "llm_calls": 0
}
```

说明：`profiles` 可为各仓 `POST /api/repos/profile` 同结构的字典，或仅 `full_name` 列表由前端自行再拉（MVP 可内联完整 profiles 减少往返）。

**Errors**

| HTTP | code | 场景 |
|------|------|------|
| 400 | `invalid_repo` / `too_many_benchmarks` | |
| 404 | `repository_not_found` | 任一仓库解析失败 |
| 503 | `upstream_timeout` | GitHub 超时 |

### 15.4 `GET /api/repos/suggest-benchmarks`（Phase 2）

**Query**：`mine=owner/repo`（必填）、`limit=3`（默认 3）、`language=zh`（可选，影响理由文案语言若走 LLM）。

**Response（200）**

```json
{
  "suggestions": [
    {
      "full_name": "org/similar-project",
      "reason_code": "overlap_topic_language",
      "reason_params": { "topics": ["cli", "typescript"] },
      "stars": 4200
    }
  ],
  "fetched_at": "2026-04-12T12:00:00Z"
}
```

`reason_code` 供前端做图标/文案映射，避免长句硬编码。

### 15.5 与现有端点关系

| 新端点 | 与现有逻辑 |
|--------|------------|
| `POST /api/repos/profile` | 可内部复用 `GitHubService` 拉取；结构兼容 `POST /api/repository/analyze` 的 `repository` 字段 |
| `POST /api/repos/benchmark` | 规则层纯本地；`include_narrative` 时调用 `AIService` **一次**，输入为 `feature_matrix` + README 截断 |
| `GET /api/repos/suggest-benchmarks` | 依赖 Search API 或预计算索引；注意配额 |

---

## 16. 附录：前端路由与页面草图

### 16.1 路由方案（推荐）

采用 **子路径** 与现网用户对比分离，分享链接清晰，且与 `?users=` 无歧义：

| 路径 | 说明 |
|------|------|
| `/compare` | **对比首页**：简单说明 + 两个入口按钮（或 Tab）跳转下列子路径 |
| `/compare/users` | **用户对比**（由现有 `Compare.tsx` 迁入或 `Navigate` 自 `/compare?users=` 兼容） |
| `/compare/repos` | **仓库对标**（新页面） |

**兼容策略（可选）**：保留 `/compare?users=a,b` 重定向到 `/compare/users?users=a,b`，避免破坏旧书签。

### 16.2 仓库对标 URL Query（草案）

与 §9.1 一致，**不与** `users` 混用：

```
/compare/repos?mine=octocat/Hello-World&b=vercel/next.js,tiangolo/fastapi
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `mine` | MVP 必填 | 我的仓库 `owner/repo` |
| `b` | 可选 | 标杆，逗号分隔，1～3 个；空则页面内展示「推荐标杆」占位或调用 `suggest-benchmarks` |

规范：`mine` / `b` 中 segment 需 URL 编码；解析可用现有 `splitGitHubUsernameInputs` 的变体（支持 `owner/repo`）。

### 16.3 组件与文件落点（草图）

```
frontend/src/pages/
  CompareHub.tsx          # 可选：/compare 着陆，Tab 链到 users / repos
  Compare.tsx             # 建议改为仅用户对比，或改名为 CompareUsers.tsx
  CompareRepos.tsx        # 新：仓库对标主页面
```

`App.tsx` 中 `Routes` 增量示例（概念草图）：

```tsx
<Route path="/compare" element={<CompareHub language={language} />} />
<Route path="/compare/users" element={<Compare language={language} />} />
<Route path="/compare/repos" element={<CompareRepos language={language} />} />
```

若 **不做 Hub**：可直接 `<Route path="/compare" element={<Compare .../>} />` 并在 `Compare` 内用 **Tab** 切换「用户 | 仓库」，此时 URL 可为 `/compare?tab=repos&mine=...`；代价是 **`users` 与 `mine` 同在** 时需约定互斥规则。§13 开放问题 7 选定后实现二选一即可。

### 16.4 导航入口（与 §6.1 对齐）

| 来源 | 行为 |
|------|------|
| 侧栏「对比」 | 指向 `/compare` 或默认 `/compare/users`（保持老用户习惯） |
| `Repositories.tsx` 卡片 | 「对标同类」→ `navigate(/compare/repos?mine=${user}/${repo})` |
| `Overview.tsx` 候选区 | 「找同类标杆」→ `/compare/repos?mine=...`（`mine` 从当前 workspace 用户与默认候选 repo 推导，若无则只打开页面提示先选仓） |

### 16.5 状态与缓存（前端）

- **不必**把标杆列表塞进 `AppContext`（除非要做跨页「待对标队列」）；优先 **URL 为单一事实来源**，刷新可复现。
- 报告正文可在会话内 `useState`；「复制 Markdown」从响应中的 `feature_matrix` + `actions` 拼字符串，与 `Export` 的衔接 Phase 2 再做。

### 16.6 侧栏 `getNavLink` 注意点

现网 `/compare` **不带** `?user=`。新增子路径后，仍建议 **对比相关链接不加 user**，避免与多用户 / 多仓库语义冲突；仓库对标所需 `mine` 仅走 `/compare/repos?mine=...`。

---

## 17. 修订记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-04-12 | 0.1 | 初稿：目标、指标、框架、API 草案、分期与风险 |
| 2026-04-12 | 0.2 | 新增 §8 数据库与存储选型（职责拆分、主库/缓存/时序对比、推荐组合、示意表、决策清单）；章节编号顺延 |
| 2026-04-12 | 0.3 | 新增执行摘要、§1.0 实现审计表、§1.4 用户视角改进清单、§7.4 与现有 API/缓存衔接；校准 §6.1 与现网 `/compare?users=`；收紧 Phase 1 工程验收与 LLM 边界；§13/§14 增补开放问题与代码映射 |
| 2026-04-12 | 0.4 | 新增 §15 后端接口草稿（profile / benchmark / suggest）、§16 前端路由与组件草图 |
