# 实施计划：GitScorer UX 优化

## 概述

本计划将 18 项需求（P0→P3）分解为可逐步执行的编码任务，按优先级排列：P0 核心体验修复 → P1 功能补全 → P2 功能增强 → P3 架构改善。每个任务均可独立执行，并在完成后与已有代码集成。

---

## 任务列表

### P0：核心用户体验修复

- [x] 1. 创建共享配置文件（前置依赖）
  - 在 `frontend/src/config/api.ts` 中定义 `API_BASE_URL` 常量，读取 `VITE_API_BASE_URL` 环境变量，回退到 `http://localhost:8000`
  - 在 `frontend/src/config/constants.ts` 中定义 `RESUME_PROJECTS_MAX_PER_USER = 6`
  - 这两个文件是后续多个任务的前置依赖，需优先创建
  - _需求：13.1、13.3、9.1、9.4_

- [x] 2. 实现请求级去重（AppContext 扩展）
  - [x] 2.1 在 `AppContext.tsx` 中新增 `pendingRequests` Map（类型 `Map<string, Promise<GenerateResponse>>`），key 格式为 `"{username}:{lang}"`
    - 在 `AppContextType` 接口中新增 `generateWithDedup` 和 `getPendingRequest` 方法签名
    - _需求：1.1、1.2、1.5_
  - [x] 2.2 实现 `generateWithDedup(username, lang)` 方法
    - 检查 `pendingRequests` 中是否已有相同 key 的 Promise；若有，直接返回该 Promise
    - 若无，创建新的 HTTP 请求 Promise，存入 `pendingRequests`，请求完成后写入 `generateCacheEntries` 并删除 pending 记录
    - 请求失败时清除对应 pending 记录，以便下次重试
    - _需求：1.1、1.2、1.3、1.4_
  - [x] 2.3 实现 `getPendingRequest(username, lang)` 方法
    - 返回当前进行中的 Promise 或 `null`
    - _需求：1.5_
  - [x]* 2.4 为请求去重逻辑编写属性测试
    - **属性 1：请求去重一致性**——并发调用 `generateWithDedup` 时，HTTP 请求数恰好为 1，所有调用方收到相同数据
    - **属性 2：请求失败后可重试**——失败后再次调用应能重新发起请求
    - **验证：需求 1.1、1.2、1.3、1.4**

- [x] 3. 修复移动端搜索框可见性
  - [x] 3.1 在 `frontend/src/styles/responsive.css` 中添加移动端响应式样式
    - 当视口宽度 ≤ 640px 时，`.topbar-search` 宽度占满可用空间，不被隐藏
    - 当视口宽度 ≤ 640px 时，隐藏非核心 topbar 元素（`.topbar-brand-text`、语言切换按钮），保留搜索框和分析按钮
    - 确保搜索输入框最小触摸目标为 44×44px（WCAG 2.1 AA）
    - _需求：2.1、2.2、2.4、2.5_
  - [x] 3.2 修改 `App.tsx` 中 topbar 的 HTML 结构
    - 为搜索框容器添加响应式 CSS 类，确保在小屏幕下优先显示
    - 为非核心元素（品牌文字、语言切换）添加 `hide-on-mobile` 类
    - _需求：2.1、2.3、2.4_

- [x] 4. 实现 XSS 安全防护（Export 页面）
  - [x] 4.1 安装 `dompurify` 及其 TypeScript 类型定义
    - 在 `frontend/package.json` 中添加 `dompurify` 依赖
    - _需求：3.4_
  - [x] 4.2 修改 `Export.tsx`，在 `dangerouslySetInnerHTML` 前调用 DOMPurify 净化
    - 定义 `ALLOWED_TAGS_CONFIG`，允许 `h1`–`h3`、`p`、`ul`、`li`、`strong`、`em`、`code`、`hr`、`a`，移除所有事件处理属性和 `<script>` 标签
    - 实现动态导入 DOMPurify 的逻辑，加载失败时回退到纯文本渲染（`escapeHtml`）并输出控制台警告
    - _需求：3.1、3.2、3.3、3.5_
  - [x]* 4.3 为 XSS 净化编写属性测试
    - **属性 3：XSS 净化安全性**——任意包含 `<script>`、`onerror`、`javascript:` 的输入，净化后不应包含 XSS 攻击向量
    - 使用 fast-check 生成随机字符串输入
    - **验证：需求 3.1、3.2**

- [x] 5. P0 检查点——确保所有测试通过
  - 确保所有测试通过，如有问题请向用户反馈。

---

### P1：功能补全

- [x] 6. 后端 PDF 导出接口增强
  - [x] 6.1 修改 `backend/main.py`，将 `/api/export/pdf` 改为支持 POST 方式
    - 新增 `ExportPdfRequestModel`，包含 `username`、`language`、`extra_markdown`（可选）字段
    - POST 端点将 `extra_markdown` 拼接到 `resume_markdown` 后再生成 PDF
    - 保留原有 GET 端点以向后兼容
    - _需求：4.1、4.5_
  - [x] 6.2 修改 `Export.tsx`，将 PDF 导出改为调用后端 POST 接口
    - 移除 `html2canvas` + `jsPDF` 的前端截图逻辑
    - 使用 `axios.post('/api/export/pdf', { username, language, extra_markdown }, { responseType: 'blob' })` 调用后端
    - 触发浏览器下载，文件名格式为 `codefolio-{username}-{language}.pdf`
    - 将 `selectedProjects` 的 Markdown 内容作为 `extra_markdown` 传递
    - _需求：4.1、4.2、4.3_
  - [x] 6.3 在 `Export.tsx` 中实现 PDF 导出的加载状态和错误处理
    - PDF 生成期间禁用下载按钮，显示加载状态
    - 后端返回错误时显示具体错误信息和重试按钮
    - _需求：4.4、4.6_

- [x] 7. 数据持久化与工作区导入/导出
  - [x] 7.1 创建 `frontend/src/utils/workspace.ts`
    - 定义 `WorkspaceSnapshot` 类型（含 `version: 1`、`generateCacheEntries`、`resumeProjects`、`benchmarkWorkspaceEntries`、`compareList`、`exportedAt` 字段）
    - 实现 `exportWorkspace(state)` 函数：将状态序列化为 JSON 并触发文件下载，文件名格式为 `codefolio-workspace-{timestamp}.json`
    - 实现 `importWorkspace(file)` 函数：读取并解析 JSON 文件，返回 `WorkspaceSnapshot` 或抛出错误
    - 实现 `validateWorkspaceSnapshot(data)` 类型守卫：验证必要字段存在且类型正确
    - _需求：5.1、5.2、5.3、5.6_
  - [x] 7.2 在 `AppContext.tsx` 中新增 `exportWorkspace` 和 `importWorkspace` 方法
    - `exportWorkspace`：收集当前状态并调用 `workspace.ts` 中的导出函数
    - `importWorkspace`：调用 `workspace.ts` 中的导入函数，验证通过后合并到当前状态，返回导入条目数量
    - 导入失败时不修改当前状态，返回错误信息
    - _需求：5.2、5.3、5.4_
  - [x] 7.3 在 `App.tsx` 或设置面板中添加导入/导出工作区的 UI 入口
    - 在设置面板中添加"导出工作区"按钮和"导入工作区"文件上传控件
    - 导入成功后显示成功提示（含导入条目数量），失败时显示错误提示
    - _需求：5.1、5.2、5.4_
  - [x]* 7.4 为工作区序列化编写属性测试
    - **属性 4：工作区序列化 Round-Trip**——任意有效工作区状态序列化后再反序列化，应得到等价状态
    - **属性 5：无效工作区导入不修改状态**——任意格式不合法的 JSON 输入，导入后状态应保持不变
    - **验证：需求 5.1、5.2、5.3**

- [x] 8. 仓库分析结果缓存提升
  - [x] 8.1 在 `AppContext.tsx` 中新增 `repoAnalysisCache`（`Map<string, RepositoryAnalysisPayload>`）
    - 在 `AppContextType` 接口中新增 `setRepoAnalysis`、`getRepoAnalysis` 方法签名
    - 实现 LRU 淘汰策略：缓存上限 50 条，超出时删除 Map 中最旧的 key（利用 Map 插入顺序）
    - _需求：6.1、6.4、6.5_
  - [x] 8.2 修改 `Repositories.tsx`，将仓库分析结果写入/读取 AppContext 缓存
    - `analyzeRepo` 函数完成后，调用 `setRepoAnalysis("{username}/{repoName}", payload)` 写入缓存
    - 组件挂载时，从 `getRepoAnalysis` 读取已有分析结果，初始化本地 `repoAnalysisMap`
    - _需求：6.2、6.3_
  - [x]* 8.3 为仓库分析缓存编写属性测试
    - **属性 6：仓库分析缓存 Round-Trip**——写入后立即读取，应得到相同数据
    - **属性 7：仓库分析缓存 LRU 容量不变量**——任意数量写入后，缓存条目数 ≤ 50
    - **验证：需求 6.2、6.3、6.5**

- [x] 9. 真实进度指示（SSE 事件驱动）
  - [x] 9.1 在 `backend/main.py` 中新增 `/api/generate/stream` SSE 端点
    - 安装 `sse-starlette` 依赖（或使用 `StreamingResponse`）
    - 实现事件序列：`github_fetched` → `score_calculated` → `ai_generating` → `completed`（含完整结果 JSON）
    - 在各处理阶段完成后 `yield` 对应事件
    - _需求：7.1_
  - [x] 9.2 修改 `App.tsx`，在 `runGenerate` 中尝试使用 SSE 连接
    - 优先使用 `EventSource` 或 `fetch` + `ReadableStream` 连接 `/api/generate/stream`
    - 收到 `github_fetched` 事件时，调用 `setCurrentStep('scoring')`
    - 收到 `score_calculated` 事件时，调用 `setCurrentStep('polishing')`
    - 收到 `completed` 事件时，解析结果数据，隐藏进度条并展示结果
    - _需求：7.2、7.3、7.4_
  - [x] 9.3 实现 SSE 降级逻辑
    - 当 SSE 连接失败或浏览器不支持时，回退到现有的 `progressInterval` 固定时间分段方案
    - 移除 `App.tsx` 中 `progressInterval` 作为主要进度驱动的逻辑，改为仅在降级时使用
    - _需求：7.5、7.6_

- [x] 10. P1 检查点——确保所有测试通过
  - 确保所有测试通过，如有问题请向用户反馈。

---

### P2：功能增强

- [x] 11. GitHub OAuth 登录
  - [x] 11.1 在 `backend/main.py` 中实现 OAuth 登录入口和回调接口
    - 新增 `GET /api/auth/github/login`：生成随机 `state` 参数（存入 Redis/session），返回 GitHub OAuth 授权 URL
    - 新增 `GET /api/auth/github/callback`：验证 `state` 参数防 CSRF，用 `code` 换取 `access_token`，安全存储 Token（不在响应体或日志中明文输出）
    - _需求：8.1、8.7_
  - [x] 11.2 修改 `backend/services/github_service.py`，支持使用用户 Token 调用 GitHub API
    - 当请求头中携带用户 Token 时，优先使用用户 Token 替代服务端单一 Token
    - 使用用户 Token 时，获取私有仓库列表并纳入分析范围
    - _需求：8.2、8.3_
  - [x] 11.3 在前端 `App.tsx` 中添加 OAuth 登录入口
    - 在 topbar 添加"GitHub 登录"按钮，点击后跳转到 `/api/auth/github/login`
    - 用户已登录时，在 topbar 显示用户头像和用户名，替代匿名状态
    - _需求：8.1、8.4_
  - [x] 11.4 实现 Token 过期处理
    - 后端返回 `authentication_error` 错误码时，前端提示用户重新登录
    - _需求：8.5、8.6_

- [x] 12. 简历项目上限可配置化
  - [x] 12.1 修改 `AppContext.tsx`，将简历项目上限从硬编码 `4` 改为从 `config/constants.ts` 导入 `RESUME_PROJECTS_MAX_PER_USER`
    - 修改 `toggleResumeProject` 中的 `.slice(0, 4)` 为 `.slice(0, RESUME_PROJECTS_MAX_PER_USER)`
    - _需求：9.1、9.2、9.4_
  - [x] 12.2 修改 `Repositories.tsx`，在"已选项目"面板中显示 `{count}/{RESUME_PROJECTS_MAX_PER_USER}`
    - 将硬编码的 `/4` 替换为从 `config/constants.ts` 导入的常量
    - _需求：9.3、9.4_
  - [x]* 12.3 为简历项目上限编写属性测试
    - **属性 8：简历项目上限不变量**——任意次数 `toggleResumeProject` 操作后，用户的简历项目数量 ≤ `RESUME_PROJECTS_MAX_PER_USER`
    - **验证：需求 9.2**

- [x] 13. 对比页时间维度（Star 历史趋势折线图）
  - [x] 13.1 修改 `backend/services/github_service.py`，新增按月聚合 star 增长数据的方法
    - 通过 GitHub GraphQL API 获取最近 12 个月的 star 历史数据
    - 返回格式：`List[{"month": "YYYY-MM", "stars": int}]`
    - _需求：10.2_
  - [x] 13.2 修改 `backend/main.py` 的 `/api/generate` 响应，在 `user` 对象中包含 `star_history` 字段
    - _需求：10.2_
  - [x] 13.3 修改 `Compare.tsx`，在雷达图和柱状图之后新增"Star 历史趋势"折线图区域
    - 使用 `recharts` 的 `LineChart` 组件绘制折线图
    - 为每个用户绘制一条独立折线，使用与用户卡片相同的颜色编码（`colors` 数组）
    - 某用户 star 历史数据不可用时，跳过该用户折线，不影响其他用户展示
    - 实现 hover tooltip，显示具体月份和 star 数值
    - _需求：10.1、10.3、10.4、10.5_

- [x] 14. GitScore 算法优化
  - [x] 14.1 修改 `backend/models.py`（或相关模型文件），在 `Contributions` 数据类中新增 `issues_opened_last_year: int = 0` 字段
    - _需求：11.3_
  - [x] 14.2 修改 `backend/services/score_engine.py`，实现算法优化
    - 将 `_calculate_documentation_score` 的上限从 `5.0` 提升至 `10.0`，相应调整各维度上限（Impact: 33, Contribution: 24, Community: 20, Tech Breadth: 13, Documentation: 10）
    - 新增 `_calculate_quality_density` 方法：`log1p(total_stars + total_forks * 2) / log1p(repo_count)`，纳入 Impact 维度计算
    - 在 `_calculate_contribution_score` 中新增 Issue 参与指标（`issues_opened_last_year`），权重不低于 PR 权重的 50%
    - 当仓库数为 0 时，所有维度返回 0.0，不抛出异常
    - _需求：11.1、11.2、11.3、11.4_
  - [x] 14.3 修改 `backend/services/github_service.py`，在抓取用户数据时获取 `issues_opened_last_year`
    - _需求：11.3_
  - [x]* 14.4 为 GitScore 算法编写属性测试
    - **属性 9：GitScore 总分范围不变量**——任意有效 `UserData` 输入，总分满足 `0 ≤ total ≤ 100`
    - **属性 10：GitScore 各维度得分范围不变量**——各维度得分满足 `0 ≤ dimension_score ≤ dimension_max`
    - **属性 11：质量密度单调性**——总 star+fork 与仓库数之比更高的输入，质量密度得分应更高
    - 使用 Hypothesis 生成随机 `UserData` 输入，最少 200 次迭代
    - **验证：需求 11.2、11.4、11.5、11.6**

- [x] 15. P2 检查点——确保所有测试通过
  - 确保所有测试通过，如有问题请向用户反馈。

---

### P3：代码架构改善

- [x] 16. API_BASE_URL 常量统一（需求 13）
  - [x] 16.1 将 `App.tsx`、`Export.tsx`、`Repositories.tsx`、`Compare.tsx` 及其他所有定义 `API_BASE_URL` 的文件中的本地定义替换为从 `frontend/src/config/api.ts` 的导入
    - 搜索所有 `import.meta.env.VITE_API_BASE_URL` 的使用位置，统一替换
    - _需求：13.2、13.4_

- [x] 17. readHistoryItems 函数去重（需求 14）
  - [x] 17.1 创建 `frontend/src/utils/history.ts`，将 `readHistoryItems` 函数从 `App.tsx` 提取到该文件
    - 保持函数签名、错误处理和返回类型与原实现完全一致
    - 同时导出 `HistoryItem` 接口类型
    - _需求：14.1、14.3_
  - [x] 17.2 修改 `App.tsx`，从 `frontend/src/utils/history.ts` 导入 `readHistoryItems`，删除本地副本
    - _需求：14.2_
  - [x]* 17.3 为 readHistoryItems 编写属性测试
    - **属性 12：readHistoryItems 行为一致性**——对任意 localStorage 内容（有效 JSON、无效 JSON、空值），提取后的函数与原内联实现返回相同结果
    - **验证：需求 14.3**

- [x] 18. 类型复用（需求 15）
  - [x] 18.1 修改 `Compare.tsx`，从 `frontend/src/types/generate.ts` 导入 `GenerateResponse` 类型
    - 将 `CompareUser` 接口中与 `GenerateResponse` 重复的字段改为基于 `GenerateResponse` 派生
    - 确保不改变任何运行时行为
    - _需求：15.1、15.2、15.3_

- [x] 19. i18n 框架统一（需求 12）
  - [x] 19.1 安装 `react-i18next` 和 `i18next` 依赖
    - _需求：12.1_
  - [x] 19.2 创建 `frontend/src/locales/en.json` 和 `frontend/src/locales/zh.json`
    - 将 `App.tsx`、`Export.tsx`、`Repositories.tsx`、`Compare.tsx` 等页面中所有 `labels` 对象的文案提取到对应语言文件
    - key 命名与后端 `i18n` 目录保持一致
    - _需求：12.2、12.4、12.5_
  - [x] 19.3 在 `App.tsx` 中初始化 `i18next`，配置语言检测和动态加载
    - 语言切换时动态加载对应语言包，无需刷新页面
    - _需求：12.1、12.3_
  - [x] 19.4 逐页面将 `labels[language].xxx` 替换为 `t('key')` 调用
    - 按页面逐步迁移：`App.tsx` → `Export.tsx` → `Repositories.tsx` → `Compare.tsx`
    - 迁移过程中保持所有现有文案内容不变
    - _需求：12.5_

- [x] 20. 贡献热力图交互增强（需求 16）
  - [x] 20.1 修改 `ContributionHeatmap` 组件，将 `title` 属性替换为自定义 tooltip 实现
    - 实现 tooltip 组件，显示格式为 `{日期}: {n} 次贡献`（中文）或 `{date}: {n} contributions`（英文）
    - tooltip 在视口边缘自动调整位置，不超出屏幕边界
    - _需求：16.1、16.2、16.3、16.4_
  - [x]* 20.2 为热力图 tooltip 格式化函数编写属性测试
    - **属性 13：热力图 Tooltip 格式完整性**——任意日期字符串和贡献数量，tooltip 输出应包含该日期和贡献数量，且格式符合当前语言设置
    - **验证：需求 16.2**

- [x] 21. Social Card 主题传递（需求 17）
  - [x] 21.1 修改 `backend/main.py` 中的 `GenerateRequestModel`，新增 `theme: Literal["dark", "light"] = "dark"` 字段
    - _需求：17.4_
  - [x] 21.2 修改 `backend/main.py` 中的 `generate_localized_output` 函数，将 `theme` 参数传递给 `render_service.generate_social_card_html`
    - 将 `theme="dark"` 硬编码替换为使用请求中传入的 `theme` 参数
    - _需求：17.2、17.3_
  - [x] 21.3 修改 `App.tsx`，在调用 `/api/generate` 时将当前主题（`theme` state）作为 `theme` 字段传递
    - _需求：17.1_
  - [x]* 21.4 为 Social Card 主题传递编写属性测试
    - **属性 14：Social Card 主题参数传递**——任意有效 `CardData` 和 `theme` 参数，深色与浅色主题生成的 HTML 应不同
    - **验证：需求 17.2、17.3**

- [x] 22. 错误边界与离线提示（需求 18）
  - [x] 22.1 创建 `frontend/src/components/ErrorBoundary.tsx`
    - 实现 React Error Boundary 类组件，包含 `getDerivedStateFromError` 和 `componentDidCatch`
    - 降级 UI 显示：错误摘要（不暴露技术细节）、"重新加载"按钮（调用 `window.location.reload()`）、"返回首页"链接
    - _需求：18.1、18.2_
  - [x] 22.2 修改 `App.tsx`，用 `ErrorBoundary` 包裹所有页面级路由组件
    - 在 `<Suspense>` 外层包裹 `<ErrorBoundary>`
    - _需求：18.1_
  - [x] 22.3 创建 `frontend/src/components/OfflineBanner.tsx`
    - 监听 `window` 的 `online` 和 `offline` 事件，检测网络连接状态
    - 网络断线时显示横幅："网络已断开，部分功能不可用"（中文）/ "You are offline. Some features may be unavailable."（英文）
    - 网络恢复时自动隐藏横幅
    - _需求：18.3、18.4、18.5_
  - [x] 22.4 修改 `App.tsx`，在 topbar 中渲染 `OfflineBanner` 组件
    - _需求：18.4_

- [x] 23. 最终检查点——确保所有测试通过
  - 确保所有测试通过，如有问题请向用户反馈。

---

## 备注

- 标有 `*` 的子任务为可选测试任务，可在快速 MVP 迭代时跳过
- 每个任务均引用了具体的需求条款，便于追溯
- 任务 1（共享配置文件）是多个后续任务的前置依赖，应优先执行
- P0 任务（任务 1–5）修复核心体验问题，应在 P1/P2/P3 之前完成
- 属性测试使用后端 Hypothesis 库和前端 fast-check 库，每个属性最少运行 200 次迭代
