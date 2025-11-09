# 无障碍图表工具 — 实现概览

本文档汇总了当前无障碍图表工具项目的全部主要功能，并详细说明每个模块的实现方式。阅读此文档可以快速理解 Flask 后端、Vue 前端以及负责将上传图表转换为无障碍代码片段的后台工作线程之间的协作流程。

## 系统架构概览

该产品由三层组件构成：

1. **Flask 后端（`backend/`）** — 提供认证、图表任务管理、图片上传、自定义代码持久化等 REST API，并内置一个模拟云端图表分析流程的轻量级后台工作线程。
2. **Vue 3 前端（`frontend/`）** — 使用 Vite 与 Pinia 构建的单页应用，包含登录 / 注册、任务与分组管理看板，以及带有代码编辑和实时预览的详情页。
3. **数据库与文件存储** — 通过 SQLAlchemy 定义关系模型（`users`、`chart_groups`、`chart_tasks`）。上传图片保存在配置的 `UPLOAD_FOLDER` 下（按用户分目录），并通过 Flask 静态路由暴露，供生成的标记引用。

下文将按模块逐项介绍具体实现。

## 后端实现细节

### 应用工厂与配置

- `backend/app.py` 提供 CLI 或 WSGI 入口 `create_app`。该函数负责加载 `backend/config.py` 中的配置、创建上传目录、为 `/api/*` 启用 CORS、初始化 SQLAlchemy 与 JWT 扩展、创建全部数据表、注册认证与图表两个蓝图、暴露健康检查路由，并在最后启动后台工作线程。【F:backend/app.py†L15-L41】
- 配置类（`Config`、`TestConfig`）定义了密钥、数据库 URL、JWT 过期时间、上传目录与请求体大小限制等默认值。所有设置均可通过环境变量覆盖，同时也提供合理的开发默认值，方便开箱运行。【F:backend/config.py†L1-L34】

### 数据模型与关联关系

- `backend/models.py` 定义了 `User`、`ChartGroup` 与 `ChartTask` 三个 SQLAlchemy 模型，并提供辅助方法将记录序列化为 API 响应使用的字典。【F:backend/models.py†L1-L79】
  - `User` 存储注册信息与密码哈希，提供 `set_password` / `check_password` 方法，并维护与分组、任务的关联。【F:backend/models.py†L10-L33】
  - `ChartGroup` 描述用户拥有的任务分组，供图表任务归类使用。【F:backend/models.py†L36-L50】
  - `ChartTask` 记录上传元数据、状态、生成成果（摘要、描述、数据点、表格数据、代码、自定义覆盖）以及时间戳。其 `to_dict` 方法会调用专用的静态资源路由来拼接图片的公开访问地址。【F:backend/models.py†L53-L79】

### 认证流程

- 认证蓝图（`backend/auth/routes.py`）实现了注册、登录与修改密码接口。
  - `POST /api/auth/register` 校验必填字段、防止重复邮箱、存储密码哈希并创建用户。【F:backend/auth/routes.py†L11-L33】
  - `POST /api/auth/login` 校验凭证后返回 JWT 访问令牌与基础用户信息，供前端存储。【F:backend/auth/routes.py†L36-L51】
  - `POST /api/auth/change-password` 需要有效的 JWT，验证当前密码并更新哈希值。【F:backend/auth/routes.py†L54-L71】
- 通过 Flask-JWT-Extended 负责令牌生成与验证。访问令牌长度适合在 SPA 中存储，前端会在 Axios 中自动附加该令牌。

### 图表分组管理

- `GET /api/groups` 获取当前用户的全部分组，按创建时间排序。【F:backend/charts/routes.py†L28-L35】
- `POST /api/groups` 校验请求体、保存新分组，并返回序列化结果。【F:backend/charts/routes.py†L38-L48】
- `DELETE /api/groups/<id>` 在删除前确认所有权、阻止仍有任务引用的分组，并在安全时删除数据库记录。【F:backend/charts/routes.py†L51-L67】

### 任务生命周期接口

- `GET /api/tasks` 支持通过 `group_id` 过滤，让用户按分组查看任务列表。【F:backend/charts/routes.py†L70-L84】
- `POST /api/tasks` 负责文件上传：校验请求、使用 UUID 生成文件名、按用户目录保存图片、创建 `pending` 状态的任务，并将文件路径和公开 URL 入队给后台线程。【F:backend/charts/routes.py†L87-L132】
- `GET /api/tasks/<id>` 在确认所有权后返回单个任务详情。【F:backend/charts/routes.py†L135-L145】
- `DELETE /api/tasks/<id>` 删除数据库记录，并尽量清理对应的本地文件。【F:backend/charts/routes.py†L148-L167】
- `POST /api/tasks/<id>/cancel` 将进行中的任务标记为 `cancelled`，提示后台线程跳过后续处理。【F:backend/charts/routes.py†L170-L187】
- `POST /api/tasks/<id>/custom-code` 保存用户自定义代码，以便后续重新加载。【F:backend/charts/routes.py†L190-L200】
- `POST /api/tasks/<id>/regenerate-code` 根据已存储的摘要和数据点重新生成无障碍标记，让用户无需重新上传即可刷新基线代码。【F:backend/charts/routes.py†L203-L217】

### 后台处理流程

- `backend/tasks.py` 提供带线程安全队列的 `ChartProcessingWorker`。`worker.start(app)` 会在 Flask 应用上下文中启动守护线程，`worker.enqueue` 则用于推送新任务。【F:backend/tasks.py†L13-L46】
- 工作线程循环从数据库加载任务，跳过已取消项，将状态更新为 `processing`，随后调用 `process_chart`。成功时会写回摘要、描述、数据点、表格数据、无障碍代码并将状态标记为 `completed`；出现异常时标记为 `failed` 并记录错误信息。【F:backend/tasks.py†L32-L64】

### 图表分析模拟与代码生成

- `backend/utils/chart_processing.py` 充当真实云端流程的占位实现。`simulate_cloud_processing` 会打开图片、基于伪随机策略生成数据点（包括像素和百分比位置），并构建表格数据。【F:backend/utils/chart_processing.py†L1-L44】
- `build_accessible_code` 渲染无障碍 HTML 模板：包含设置 ARIA 属性的可聚焦容器，以及定位到数据点的隐藏按钮，供屏幕阅读器播报。【F:backend/utils/chart_processing.py†L47-L88】
- `process_chart` 将上述两个辅助函数串联，返回后台线程需要写入数据库的结果。【F:backend/utils/chart_processing.py†L91-L95】

## 前端实现细节

### 应用启动与共享状态

- `frontend/src/main.js` 挂载 Vue 应用、启用 Pinia、通过认证仓库恢复持久化的登录信息，并注册路由。【F:frontend/src/main.js†L1-L17】
- Pinia 认证仓库（`frontend/src/stores/auth.js`）使用 `localStorage` 保存 JWT 与用户信息，自动将令牌附加到 Axios，并提供登录、注册、修改密码、退出登录等操作；`initialise` 辅助函数会在应用启动或路由切换时回放令牌。【F:frontend/src/stores/auth.js†L1-L39】
- 路由器定义了受保护的仪表盘与任务详情页面，未登录用户会被重定向至登录页；已经登录的用户无法再次访问认证页面。【F:frontend/src/router/index.js†L1-L37】

### 认证视图

- **LoginView** 展示样式化的登录表单，提交后调用认证仓库，并在成功后跳转，同时在界面上反馈 API 错误信息。【F:frontend/src/components/LoginView.vue†L1-L76】
- **RegisterView** 收集姓名、邮箱和密码，调用注册动作，并在成功后展示提示消息，随后跳转回登录页面。【F:frontend/src/components/RegisterView.vue†L1-L78】

### 仪表盘工作区

`frontend/src/components/DashboardView.vue` 协调了大部分用户操作：

- **用户面板** — 展示当前用户信息，提供退出登录按钮，并可展开内联的修改密码表单。表单会调用认证仓库的 `changePassword` 方法，并在界面上显示处理结果。【F:frontend/src/components/DashboardView.vue†L3-L85】【F:frontend/src/components/DashboardView.vue†L203-L234】
- **分组管理** — 加载用户的分组、支持创建新分组，并允许在任务列表中按所选分组过滤，同时展示 API 返回的提示信息。【F:frontend/src/components/DashboardView.vue†L23-L72】【F:frontend/src/components/DashboardView.vue†L130-L178】
- **任务上传** — 处理文件选择、绑定可选分组、向 `/api/tasks` 提交表单，并在任务入队后刷新列表。【F:frontend/src/components/DashboardView.vue†L88-L178】
- **任务列表** — 获取任务（可选按分组过滤），以响应式卡片形式展示状态、摘要与操作按钮，可查看详情、取消进行中的任务或直接删除记录。【F:frontend/src/components/DashboardView.vue†L180-L312】

### 任务详情体验

- `frontend/src/components/TaskDetailView.vue` 加载单个任务记录，展示生成的摘要、预览图片和结构化表格数据。【F:frontend/src/components/TaskDetailView.vue†L1-L55】
- 代码编辑区域会在加载时填充生成代码或自定义代码，支持重置为基线、保存自定义 HTML（持久化到后端）、或基于已存储数据重新生成。【F:frontend/src/components/TaskDetailView.vue†L57-L118】
- 沙箱 iframe 会渲染当前代码，方便用户立即验证无障碍调整。刷新预览仅通过更新 key 来强制重渲，而无需整页刷新。【F:frontend/src/components/TaskDetailView.vue†L57-L118】

## 后台任务协同流程

综合来看：

1. 用户在仪表盘提交新的图表任务。前端会将表单发送到后端，后端保存图片、创建 `ChartTask` 记录，并将 `TaskPayload` 入队等待后台线程处理。【F:frontend/src/components/DashboardView.vue†L98-L178】【F:backend/charts/routes.py†L87-L132】
2. 后台线程将任务状态更新为 `processing`，调用模拟分析流程，写回生成成果并将状态标记为 `completed`。若发生异常，则标记为 `failed`。【F:backend/tasks.py†L32-L64】
3. 用户刷新任务列表或打开详情页时，前端会获取最新记录，展示摘要，并填充编辑器与预览，便于后续优化。【F:frontend/src/components/DashboardView.vue†L117-L178】【F:frontend/src/components/TaskDetailView.vue†L25-L118】

## 持久化与存储模型

- 用户只能看到自己的分组和任务，因为所有查询都会依据 JWT 身份过滤 `user_id`，且所有 CRUD 接口都会在返回详情或变更记录前调用 `_ensure_owner` 进行校验。【F:backend/charts/routes.py†L16-L25】【F:backend/charts/routes.py†L70-L217】
- 上传文件存放在 `<UPLOAD_FOLDER>/<user_id>/` 目录下。删除接口会尽量清理对应文件，避免遗留无用资源。【F:backend/charts/routes.py†L148-L166】
- 生成的元数据（摘要、数据点、表格、代码与自定义覆盖）直接存储在任务记录上，用户再次访问时无需重新计算。【F:backend/models.py†L53-L79】

## 系统扩展建议

如需替换模拟流程，只要在 `process_chart` 中调用实际的云端接口，并返回相同的数据结构（摘要、描述、数据点、表格数据与生成代码）。队列、API 响应以及前端渲染逻辑无需做额外调整。【F:backend/utils/chart_processing.py†L91-L95】
