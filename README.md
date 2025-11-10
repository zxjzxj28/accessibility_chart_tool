# 无障碍图表工具

这是一个面向移动开发者的全栈项目，用于将图表图片转换为便于在 Android 应用中集成的无障碍代码片段。平台支持用户上传图表图片，后台异步生成图表摘要、结构化数据以及 Java/Kotlin 代码示例。用户可以按目录树对任务进行分组管理，为不同语言自定义代码，并一键下载包含集成说明的压缩包。

## 功能特性

- **用户认证**：注册时需填写账号与邮箱，登录支持账号或邮箱两种方式，并提供修改密码功能。
- **分组管理**：树形结构的分组体系，可创建子分组、重命名或删除空分组，并用于筛选任务。
- **任务管理**：上传图表时选择分组与目标语言，支持分页查看历史任务、编辑任务名称或分组、取消运行中的任务并查看详情。
- **代码生成**：后台同时生成 Java 与 Kotlin 代码片段及集成步骤，详情页可针对当前语言保存自定义代码并下载压缩包。
- **异步处理**：后台工作线程模拟云端分析流程，生成摘要、数据点、表格数据与 Android 代码。
- **前端体验**：Vue 3 + Pinia 构建的中文界面，包含仪表盘、任务详情、代码管理与集成说明。
- **数据存储**：SQLAlchemy 驱动的关系数据库（默认 SQLite，可切换到 MySQL），应用启动时自动建表。

## 项目结构

```
backend/
  app.py              # Flask 应用工厂
  models.py           # 用户、分组、任务模型
  tasks.py            # 后台工作线程
  utils/chart_processing.py  # 图表分析与代码生成模拟
  auth/               # 认证相关蓝图
  charts/             # 分组与任务接口
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

| 表名 | 字段 |
| --- | --- |
| `users` | `id`（INT，自增，主键）、`email`（VARCHAR(120)，唯一，非空）、`username`（VARCHAR(80)，唯一，非空）、`name`（VARCHAR(120)，非空）、`password_hash`（VARCHAR(255)，非空）、`created_at`（DATETIME，默认当前时间） |
| `chart_groups` | `id`（INT，自增，主键）、`name`（VARCHAR(120)，非空）、`user_id`（外键 → `users.id`，非空）、`parent_id`（外键 → `chart_groups.id`，可空）、`created_at`（DATETIME，默认当前时间） |
| `chart_tasks` | `id`（INT，自增，主键）、`title`（VARCHAR(255)，非空）、`status`（VARCHAR(50)，默认 `'pending'`）、`language`（VARCHAR(20)，默认 `'java'`）、`user_id`（外键 → `users.id`，非空）、`group_id`（外键 → `chart_groups.id`，可空）、`image_path`（VARCHAR(500)）、`summary`（TEXT）、`description`（TEXT）、`data_points`（JSON）、`table_data`（JSON）、`generated_code`（LONGTEXT/TEXT）、`java_code`（LONGTEXT/TEXT）、`kotlin_code`（LONGTEXT/TEXT）、`integration_doc`（JSON）、`custom_code`（TEXT，存储 JSON 字符串）、`error_message`（TEXT）、`created_at`（DATETIME）、`updated_at`（DATETIME） |

### SQL 建表脚本

```sql
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(120) NOT NULL UNIQUE,
  username VARCHAR(80) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chart_groups (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  user_id INT NOT NULL,
  parent_id INT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_chart_groups_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_chart_groups_parent
    FOREIGN KEY (parent_id) REFERENCES chart_groups(id)
    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS chart_tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',
  language VARCHAR(20) DEFAULT 'java',
  user_id INT NOT NULL,
  group_id INT NULL,
  image_path VARCHAR(500) NULL,
  summary TEXT NULL,
  description TEXT NULL,
  data_points JSON NULL,
  table_data JSON NULL,
  generated_code LONGTEXT NULL,
  java_code LONGTEXT NULL,
  kotlin_code LONGTEXT NULL,
  integration_doc JSON NULL,
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

### 数据库升级脚本

如需从旧版本升级，请执行以下 SQL 为现有数据表补充新字段：

```sql
ALTER TABLE users ADD COLUMN username VARCHAR(80) NOT NULL UNIQUE AFTER email;

ALTER TABLE chart_groups ADD COLUMN parent_id INT NULL AFTER user_id;
ALTER TABLE chart_groups
  ADD CONSTRAINT fk_chart_groups_parent
  FOREIGN KEY (parent_id) REFERENCES chart_groups(id)
  ON DELETE SET NULL;

ALTER TABLE chart_tasks
  ADD COLUMN language VARCHAR(20) DEFAULT 'java' AFTER status,
  ADD COLUMN java_code LONGTEXT NULL AFTER generated_code,
  ADD COLUMN kotlin_code LONGTEXT NULL AFTER java_code,
  ADD COLUMN integration_doc JSON NULL AFTER kotlin_code;
```

## 图表处理模拟流程

`backend/utils/chart_processing.py` 提供了模拟的云端处理逻辑：打开上传图片、生成伪随机数据点和表格信息，并输出 Java/Kotlin 代码及集成步骤。若需接入真实服务，可在 `process_chart` 中替换具体实现，同时保持返回结构一致。

## 工作流测试指南

1. 通过前端界面或 API 注册新用户。
2. 创建多级图表分组，用于管理任务。
3. 上传图表图片以创建任务，选择语言与分组，随后通过仪表盘刷新或分页查看任务状态。
4. 如需调整任务名称或分组，使用仪表盘中的“编辑信息”弹窗。
5. 打开任务详情页查看摘要、数据点、表格数据和 Android 代码；按语言切换并保存自定义代码，或重新生成基线代码。
6. 下载代码压缩包，依据集成说明完成在 Android 项目中的落地验证。

---

本项目为构建生产级无障碍图表工具链提供了基础，可按需扩展真实的图表分析流程、更严格的校验逻辑以及更多用户协作能力。
