# 无障碍图表工具

这是一个面向开发者的全栈工具，用于将图表图片转换为可直接在 Android Web 视图中集成的无障碍前端组件。平台支持用户上传图表图片，后台异步处理后生成包含数据摘要的无障碍代码片段。每位用户都可以将生成记录分组管理、编辑代码、预览效果并维护任务历史。

## 功能特性

- 用户认证：注册、登录、退出登录以及修改密码。
- 任务管理：创建（上传）、列表查看、取消、中止、删除以及查看详情。
- 异步后台工作线程，用于模拟云端处理流程并提取图表摘要与数据点。
- 自动生成可聚焦数据点的无障碍图表容器代码，以支持屏幕阅读器播报。
- 基于 Vue 3 的前端界面，包含任务看板、图表分组、代码编辑器与实时预览沙箱。
- 基于 SQLAlchemy 的 MySQL 兼容数据库层（本地开发默认使用 SQLite）。

## 项目结构

```
backend/
  app.py              # Flask application factory and bootstrap
  models.py           # SQLAlchemy models for users, groups, and tasks
  tasks.py            # Background worker handling chart processing
  utils/chart_processing.py  # Simulated cloud processing and code generation
  auth/               # Authentication blueprint
  charts/             # Task & group blueprint plus upload serving
frontend/
  src/                # Vue 3 single-page application
  package.json        # Front-end dependencies (Vite + Vue 3)
README.md             # This file
```

## 后端搭建

1. 创建虚拟环境并安装依赖：
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. 按需配置环境变量（或者直接修改 `backend/config.py` 中的默认值，以硬编码本地配置）：
   - `DATABASE_URL`：SQLAlchemy 连接串（例如 `mysql+pymysql://user:pass@localhost/chart_tool`）。
   - `SECRET_KEY`、`JWT_SECRET_KEY`：安全密钥。
   - `UPLOAD_FOLDER`：可选项，自定义图片上传目录。
3. 启动开发服务器：
   ```bash
   flask --app app:create_app run
   ```
   API 将运行在 `http://localhost:5000`，后台工作线程会自动启动。

## 前端搭建

1. 安装依赖并启动 Vite 开发服务器：
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. 前端通过 Vite 配置将 `/api` 请求代理到 `http://localhost:5000`。

## 数据库说明

- 默认使用 SQLite 以方便开发，如需切换到 MySQL，请在启动服务前将 `DATABASE_URL` 设置为有效的 MySQL 连接串。
- 应用启动时会自动创建数据表。生产环境建议结合迁移工具进行管理。

### 表结构概览

系统持久化三个核心实体，下表列出的字段类型与 SQLAlchemy 定义一致，可同时兼容 MySQL 与 SQLite。

| 表名 | 字段 |
| --- | --- |
| `users` | `id`（主键，INT，自增）、`email`（VARCHAR(120)，唯一，非空）、`name`（VARCHAR(120)，非空）、`password_hash`（VARCHAR(255)，非空）、`created_at`（DATETIME，默认当前时间） |
| `chart_groups` | `id`（主键，INT，自增）、`name`（VARCHAR(120)，非空）、`user_id`（外键 → `users.id`，非空）、`created_at`（DATETIME，默认当前时间） |
| `chart_tasks` | `id`（主键，INT，自增）、`title`（VARCHAR(255)，非空）、`status`（VARCHAR(50)，默认 `'pending'`）、`user_id`（外键 → `users.id`，非空）、`group_id`（外键 → `chart_groups.id`，可为空）、`image_path`（VARCHAR(500)）、`summary`（TEXT）、`description`（TEXT）、`data_points`（JSON）、`table_data`（JSON）、`generated_code`（LONGTEXT/TEXT）、`custom_code`（LONGTEXT/TEXT）、`error_message`（TEXT）、`created_at`（DATETIME，默认当前时间）、`updated_at`（DATETIME，默认当前时间并在更新时自动刷新） |

### SQL 建表脚本

若需手动初始化数据库，可运行以下 MySQL 语法的 SQL 脚本来创建全部数据表。如目标数据库不支持 JSON 类型，请酌情调整字段类型。

```sql
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(120) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chart_groups (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  user_id INT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_chart_groups_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chart_tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',
  user_id INT NOT NULL,
  group_id INT NULL,
  image_path VARCHAR(500) NULL,
  summary TEXT NULL,
  description TEXT NULL,
  data_points JSON NULL,
  table_data JSON NULL,
  generated_code LONGTEXT NULL,
  custom_code LONGTEXT NULL,
  error_message TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_chart_tasks_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_chart_tasks_group
    FOREIGN KEY (group_id) REFERENCES chart_groups(id)
    ON DELETE SET NULL
);
```

## 图表处理模拟流程

目前的实现提供了一个模拟的云端处理管线（`backend/utils/chart_processing.py`）。该模块会打开上传图片、生成伪随机的数据点，并构建一段无障碍 HTML 代码。若需接入真实的云端分析服务，只需在 `process_chart` 函数中替换具体实现即可。

## 工作流测试指南

1. 通过前端界面或 API 注册新用户。
2. 视需要创建图表分组，用于管理转换结果。
3. 上传图表图片以创建任务，可通过仪表盘上的刷新按钮获取最新状态。
4. 打开任务详情页查看摘要、检阅生成的无障碍组件代码并进行定制，内嵌预览可用于验证修改效果。
5. 保存自定义代码片段，或基于已有数据点重新生成基线代码。

---

本项目为构建生产级无障碍图表工具链提供了基础，可按需扩展真实的图表分析流程、更严格的校验逻辑以及更多用户协作能力。
