# 无障碍图表工具

这是一个面向移动开发者的全栈项目，用于将图表图片转换为便于在应用中复用的无障碍素材。平台支持用户上传图表图片，后台异步生成图表摘要、结构化数据（数据点与表格数据），并结合可配置的代码模板输出示例内容。用户可以按目录树管理任务、维护模板，并下载结构化结果。

## 功能特性

- **用户认证**：注册需填写账号与邮箱，登录支持账号或邮箱两种方式，并提供修改密码功能。
- **应用与分组管理**：以“应用”为顶层维度，可在上传任务时自动创建应用；应用内支持多层级分组的新增、重命名与删除。
- **任务管理**：上传图表时可指定应用、分组与模板，支持关键字检索、分页、编辑、取消或删除任务。
- **模板体系**：内置 Java / Kotlin 默认模板，支持自定义模板的新增、编辑、复制、删除以及占位符格式检查。
- **结果展示**：任务详情页提供摘要、数据点、表格数据，并可按模板渲染结果文本或导出压缩包。
- **异步处理**：后台工作线程模拟云端分析流程，生成摘要、数据点与表格数据。
- **前端体验**：Vue 3 + Pinia 构建的中文界面，包含仪表盘、任务详情与模板管理。
- **数据存储**：SQLAlchemy 驱动的关系数据库（默认 SQLite，可切换到 MySQL），应用启动时自动建表。

## 项目结构

```
backend/
  app.py              # Flask 应用工厂
  models.py           # 用户、应用、分组、任务、模板等模型
  tasks.py            # 后台工作线程
  utils/chart_processing.py  # 图表分析模拟
  auth/               # 认证相关蓝图
  charts/             # 应用、分组、任务、模板接口
frontend/
  src/                # Vue 3 单页应用
  package.json        # 前端依赖
README.md             # 项目说明
```

## 后端搭建

1. 创建虚拟环境并安装依赖：
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. 按需配置环境变量（或直接修改 `backend/config.py` 的默认值）：
   - `DATABASE_URL`：SQLAlchemy 连接串，例如 `mysql+pymysql://user:pass@localhost/chart_tool`。
   - `SECRET_KEY`、`JWT_SECRET_KEY`：安全密钥。
   - `UPLOAD_FOLDER`：可选，自定义图片上传目录。
3. 启动开发服务器：
   ```bash
   flask --app app:create_app run
   ```
   API 默认运行在 `http://localhost:5000`，后台工作线程会随应用启动。

## 前端搭建

1. 安装依赖并启动 Vite：
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Vite 已配置将 `/api` 请求代理到 `http://localhost:5000`，确保前后端协同调试。

## 数据库说明

- 默认使用 SQLite，若需切换到 MySQL，请在启动前设置 `DATABASE_URL`。
- 应用启动时会自动创建数据表；生产环境建议配合迁移工具。

### 表结构概览

| 表名 | 关键字段 |
| --- | --- |
| `users` | `id`、`email`、`username`、`password_hash`、`created_at` |
| `chart_applications` | `id`、`name`、`user_id`、`created_at`、`updated_at`、`is_deleted` |
| `chart_groups` | `id`、`name`、`app_id`、`parent_id`、`created_at`、`updated_at`、`is_deleted` |
| `chart_tasks` | `id`、`title`、`status`、`user_id`、`app_id`、`group_id`、`image_path`、`template_id`、`created_at`、`updated_at`、`is_deleted` |
| `chart_task_results` | `id`、`task_id`、`is_success`、`summary`、`table_data`、`data_points`、`error_message` |
| `code_templates` | `id`、`name`、`language`、`content`、`is_system`、`user_id`、`created_at`、`updated_at`、`is_deleted` |

### SQL 建表示例

```sql
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(120) NOT NULL UNIQUE,
  username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chart_applications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  user_id INT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  is_deleted BOOLEAN DEFAULT FALSE,
  CONSTRAINT uq_app UNIQUE (user_id, name),
  CONSTRAINT fk_app_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE chart_groups (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  app_id INT NOT NULL,
  parent_id INT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  is_deleted BOOLEAN DEFAULT FALSE,
  CONSTRAINT fk_group_app FOREIGN KEY (app_id) REFERENCES chart_applications(id) ON DELETE CASCADE,
  CONSTRAINT fk_group_parent FOREIGN KEY (parent_id) REFERENCES chart_groups(id) ON DELETE CASCADE
);

CREATE TABLE chart_tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  status VARCHAR(50) DEFAULT 'queued',
  user_id INT NOT NULL,
  app_id INT NOT NULL,
  group_id INT NULL,
  image_path VARCHAR(500) NULL,
  template_id INT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  is_deleted BOOLEAN DEFAULT FALSE,
  CONSTRAINT fk_task_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_task_app FOREIGN KEY (app_id) REFERENCES chart_applications(id) ON DELETE CASCADE,
  CONSTRAINT fk_task_group FOREIGN KEY (group_id) REFERENCES chart_groups(id) ON DELETE SET NULL,
  CONSTRAINT fk_task_template FOREIGN KEY (template_id) REFERENCES code_templates(id)
);

CREATE TABLE chart_task_results (
  id INT AUTO_INCREMENT PRIMARY KEY,
  task_id INT NOT NULL UNIQUE,
  is_success BOOLEAN DEFAULT FALSE,
  summary TEXT NULL,
  table_data JSON NULL,
  data_points JSON NULL,
  error_message TEXT NULL,
  CONSTRAINT fk_result_task FOREIGN KEY (task_id) REFERENCES chart_tasks(id) ON DELETE CASCADE
);

CREATE TABLE code_templates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  language VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  is_system BOOLEAN DEFAULT FALSE,
  user_id INT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  is_deleted BOOLEAN DEFAULT FALSE,
  CONSTRAINT fk_template_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

### 数据库升级建议

- 旧版本若包含 `language`、`generated_code` 等字段，可在升级时迁移数据至 `chart_task_results` 表或归档后删除。
- 软删除字段（`is_deleted`）可避免误删，必要时可通过后台脚本做物理清理。

## 图表处理模拟流程

`backend/utils/chart_processing.py` 提供了模拟的云端处理逻辑：打开上传图片、生成伪随机数据点和表格信息。若需接入真实服务，可在 `process_chart` 中替换具体实现，同时保持返回结构一致。

## 工作流测试指南

1. 通过前端界面或 API 注册新用户并登录。
2. 在仪表盘创建多级分组，用于组织任务。
3. 上传图表图片以创建任务，可输入新的应用名称或选择既有应用，并挑选模板。
4. 使用任务列表中的“编辑”按钮调整任务标题、应用、分组或模板；必要时可取消或删除任务。
5. 打开任务详情页查看摘要、数据点和表格数据，并根据需要渲染模板或下载压缩包。

---

本项目为构建生产级无障碍图表工具链提供了基础，可按需扩展真实的图表分析流程、更严格的校验逻辑以及更多协作能力。
