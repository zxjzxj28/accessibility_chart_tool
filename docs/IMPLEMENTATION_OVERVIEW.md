# 无障碍图表工具 — 实现概览

本文档梳理后端、前端以及后台工作线程的实现细节，帮助你快速定位代码并理解系统协作方式。

## 系统架构

- **Flask 后端**：位于 `backend/`，负责认证、应用与分组管理、任务生命周期、文件上传以及模板渲染接口。
- **后台工作线程**：应用启动后在 `backend/tasks.py` 初始化，串行消费队列中的任务并写回分析结果。
- **Vue 3 前端**：位于 `frontend/`，通过 Axios 调用 `/api` 接口，提供全中文的管理界面。
- **数据存储**：`backend/models.py` 使用 SQLAlchemy 定义用户、应用、分组、任务、任务结果与模板等表，支持 SQLite 与 MySQL。

## 数据模型

1. **User**
   - 字段：`email`、`username`、`password_hash`、`created_at`。
   - 方法：`set_password`、`check_password`、`to_dict`。
2. **ChartApplication / ChartGroup**
   - 应用通过 `is_deleted` 实现软删除，并以 `ChartGroup` 组织目录层级。
   - 分组仅关联应用，可嵌套子分组，删除时会级联标记子分组和任务为删除状态。
3. **ChartTask / ChartTaskResult**
   - 任务记录基础信息、所属应用和模板选择，处理结果统一写入 `chart_task_results` 表。
   - 结果包含摘要、数据点、表格数据及失败原因，方便模板渲染和详情展示。
4. **CodeTemplate**
   - 模板限定语言为 Java 或 Kotlin，支持软删除。
   - 模板内容需要包含 `{title}`、`{summary}`、`{table_data}`、`{data_points}` 等占位符。

## 后端蓝图

### 认证接口（`backend/auth/routes.py`）

- `POST /api/auth/register`：校验邮箱、账号名、密码并创建用户。
- `POST /api/auth/login`：支持邮箱或账号名登录，成功后返回 JWT。
- `POST /api/auth/change-password`：验证旧密码后更新哈希值。

### 业务接口（`backend/charts/routes.py`）

- **应用与分组**
  - `GET /api/applications`：返回当前用户的应用树及分组层级。
  - `POST /api/groups`：在指定应用下创建（子）分组。
  - `PATCH /api/groups/<id>`：重命名或调整父级，包含循环校验。
  - `DELETE /api/groups/<id>`：软删除分组并级联标记子分组与任务。
- **任务**
  - `GET /api/tasks`：分页列出任务，支持关键字检索、应用/分组过滤。
  - `POST /api/tasks`：接收多部分表单，自动创建或复用应用，支持选择分组和模板。
  - `GET /api/tasks/<id>`：返回任务详情及分析结果。
  - `PATCH /api/tasks/<id>`：更新标题、应用、分组或模板。
  - `POST /api/tasks/<id>/cancel`：取消排队或进行中的任务。
  - `DELETE /api/tasks/<id>`：软删除任务。
  - `GET /api/tasks/<id>/download`：导出摘要、数据点和表格数据的压缩包。
  - `GET /api/tasks/<id>/render-template`：按模板渲染任务内容。
- **模板**
  - `GET /api/templates`：列出系统与当前用户可见的模板。
  - `POST /api/templates` / `PATCH /api/templates/<id>`：创建或编辑模板，保存时执行占位符检查。
  - `DELETE /api/templates/<id>`：删除自定义模板。
  - `POST /api/templates/validate`：返回缺失的必需占位符列表。
- **文件服务**
  - `GET /api/uploads/<path>`：提供上传图片的静态访问能力。

### 图表处理模拟（`backend/utils/chart_processing.py`）

- `simulate_cloud_processing`：读取图片尺寸，生成摘要、数据点和表格数据。
- `process_chart`：目前直接返回模拟结果，保留 `public_image_url` 参数以兼容真实服务对接。

### 后台线程（`backend/tasks.py`）

- `ChartProcessingWorker` 维护线程安全队列，依次处理上传任务。
- 工作流程：将任务状态置为 `processing` → 调用 `process_chart` → 写入 `chart_task_results` → 标记完成；若异常则记录失败原因。

## 前端实现

### 状态与路由

- `frontend/src/stores/auth.js`：持久化用户信息与 JWT，提供登录、注册、修改密码、退出登录等动作。
- `frontend/src/router/index.js`：定义登录、注册、仪表盘、任务详情和模板管理页面。

### 仪表盘（`DashboardView.vue`）

- 左侧展示应用与分组树，提供新增、重命名、删除分组等操作。
- 上传任务时可输入或选择应用名称，并选择现有分组与模板。
- 任务列表支持关键字检索、分页、取消/删除任务以及通过弹窗编辑基本信息。

### 任务详情（`TaskDetailView.vue`）

- 展示任务状态、摘要、数据点和表格数据。
- 可选择任意模板进行渲染，查看格式化后的结果文本。

### 模板管理（`TemplateManagementView.vue`）

- 列出所有可用模板，区分系统模板与自定义模板。
- 支持新增、编辑、复制、删除模板，并提供一键格式检查。

## 运行流程

1. 用户在仪表盘上传图表，任务记录写入数据库并入队后台线程。
2. 后台线程模拟分析图表，将摘要、数据点和表格数据写入结果表。
3. 前端刷新任务列表或进入详情页即可查看最新结果，也可通过模板渲染输出定制文本。

## 扩展建议

- 对接真实识别服务时，可在 `process_chart` 中调用外部 API 并补充更多字段。
- 若需扩展模板占位符，可同步修改 `REQUIRED_TEMPLATE_PLACEHOLDERS` 并更新模板校验逻辑。
- 如需团队协作，可在用户模型上新增组织维度，并在查询时增加多租户隔离。
