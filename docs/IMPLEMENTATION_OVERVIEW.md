# 无障碍图表工具 — 实现概览

本文档梳理后端、前端以及后台工作线程的实现细节，帮助你快速定位代码并理解系统的协作方式。

## 系统架构

- **Flask 后端**：位于 `backend/`，负责认证、分组管理、任务生命周期、文件上传以及代码压缩包下载。
- **后台工作线程**：在应用启动时初始化（`backend/tasks.py`），使用队列顺序处理上传任务并写回分析结果。
- **Vue 3 前端**：位于 `frontend/`，通过 Axios 调用 `/api` 接口，提供全中文的管理界面。
- **数据存储**：`backend/models.py` 使用 SQLAlchemy 定义 `User`、`ChartGroup`、`ChartTask` 三张表，支持 SQLite 与 MySQL。

## 数据模型

1. **User**
   - 字段：`email`、`username`、`name`、`password_hash`、`created_at`。
   - 方法：`set_password`、`check_password`、`to_dict`。
2. **ChartGroup**
   - 字段：`name`、`user_id`、`parent_id`、`created_at`。
   - 关系：自关联 `children` 与外键 `parent`，同时与 `ChartTask` 建立一对多关系。
3. **ChartTask**
   - 核心字段：`title`、`status`、`language`、`image_path`、`summary`、`description`、`data_points`、`table_data`、`generated_code`（默认存储 web 片段）、`java_code`、`kotlin_code`、`integration_doc`、`custom_code`（JSON 字符串）。
   - `to_dict` 会解析自定义代码 JSON，并为图片生成可直接访问的绝对路径。

## 后端蓝图

### 认证接口（`backend/auth/routes.py`）

- `POST /api/auth/register`：校验姓名、邮箱、账号、密码并创建用户。
- `POST /api/auth/login`：根据传入的 `identifier` 判断是邮箱还是账号名，验证密码后签发 JWT。
- `POST /api/auth/change-password`：需要登录态，校验旧密码并写入新的哈希值。

### 分组与任务接口（`backend/charts/routes.py`）

- **分组**
  - `GET /api/groups`：返回当前用户的树形分组结构。
  - `POST /api/groups`：创建分组，可选传入 `parent_id` 挂载到父节点。
  - `PATCH /api/groups/<id>`：支持重命名或调整父级，包含循环引用校验。
  - `DELETE /api/groups/<id>`：仅允许删除没有子分组和任务的节点。
- **任务**
  - `GET /api/tasks`：分页返回任务列表（`page`、`page_size`），支持按分组树过滤。
  - `POST /api/tasks`：接收多部分表单，存储图片并创建任务记录，允许指定 `group_id` 与 `language`。
  - `GET /api/tasks/<id>`：返回任务详情，包含摘要、数据点及全部代码字段。
  - `PATCH /api/tasks/<id>`：更新任务标题、分组或语言，语言切换会同步更新 `generated_code`。
  - `POST /api/tasks/<id>/cancel`：将进行中的任务标记为 `cancelled`。
  - `POST /api/tasks/<id>/custom-code`：按语言保存自定义代码，`custom_code` 字段以 JSON 形式存储映射。
  - `POST /api/tasks/<id>/regenerate-code`：基于现有摘要和数据点重新生成指定语言的代码，并刷新集成文档。
  - `GET /api/tasks/<id>/download`：生成包含 README、Java/Kotlin 源文件及集成说明的 zip 压缩包并返回给前端。
  - `GET /api/uploads/<path>`：提供图片静态访问能力。

### 图表处理模拟（`backend/utils/chart_processing.py`）

- `simulate_cloud_processing`：读取图片尺寸，基于伪随机数生成固定数量的数据点与表格数据。
- `build_accessible_code`：返回字典，包含 web 片段、Java 代码、Kotlin 代码以及集成步骤。
- `process_chart`：组合上述函数，供后台线程写回任务结果。

### 后台线程（`backend/tasks.py`）

- `ChartProcessingWorker` 维护线程安全队列，逐个消费上传任务。
- 对每个任务：标记为 `processing`、调用 `process_chart`、写入摘要/代码/集成说明；若任务已取消或发生异常则跳过或标记 `failed`。

## 前端实现

### 状态与路由

- `frontend/src/stores/auth.js`：持久化用户信息与 JWT，提供登录、注册、修改密码、退出登录等动作。
- `frontend/src/router/index.js`：定义登录、注册、仪表盘、任务详情页面，并在守卫中恢复 JWT。

### 认证视图

- `LoginView.vue`：提供邮箱/账号两种登录模式切换。
- `RegisterView.vue`：新增账号名输入框，注册成功后提示并跳转登录页。

### 仪表盘（`DashboardView.vue`）

- 加载分组树并以缩进列表展示，支持创建子分组与重命名。
- 上传任务时可选择分组与语言。
- 任务列表支持分页、取消任务、打开详情以及通过弹窗编辑任务基本信息。
- 侧边栏提供密码修改与退出登录功能。

### 任务详情（`TaskDetailView.vue`）

- 展示任务状态、摘要、表格数据及上传图片。
- 代码编辑区域提供语言切换按钮，分别加载 Java/Kotlin 代码及对应的自定义内容。
- 支持保存自定义代码、重新生成基线代码以及下载压缩包。
- 集成说明卡片列出两种语言的落地步骤，并反馈下载结果。

## 运行流程

1. 用户在仪表盘上传图表，任务记录写入数据库并入队后台线程。
2. 后台线程处理图片，生成摘要、数据点、代码片段与集成说明，将状态标记为 `completed`。
3. 前端定期刷新任务列表或打开任务详情，展示最新处理结果；用户可继续编辑代码、移动分组或下载压缩包。

## 扩展建议

- 若需要接入真实的图表识别服务，可在 `process_chart` 中替换模拟逻辑，同时补充额外字段。
- 可以将自定义代码存储升级为结构化 JSON 列（如 MySQL 的 `JSON` 类型），以便支持更多语言或版本。
- 如需实现团队协作，可在用户模型上新增组织维度，并在查询时增加多租户隔离。
