<template>
  <div class="dashboard">
    <aside class="sidebar">
      <section class="user-card">
        <h2>{{ auth.user?.username || '未命名用户' }}</h2>
        <p class="muted">{{ auth.user?.email }}</p>
        <button class="link" @click="togglePassword">{{ showPassword ? '收起修改密码' : '修改密码' }}</button>
        <form v-if="showPassword" class="password-form" @submit.prevent="updatePassword">
          <input v-model="passwordForm.current_password" type="password" placeholder="当前密码" required />
          <input v-model="passwordForm.new_password" type="password" placeholder="新密码" required />
          <button class="primary" type="submit" :disabled="passwordLoading">
            {{ passwordLoading ? '更新中…' : '确认修改' }}
          </button>
          <p v-if="passwordMessage" class="hint">{{ passwordMessage }}</p>
        </form>
        <button class="ghost" @click="logout">退出登录</button>
      </section>

      <nav class="sidebar-nav card">
        <button class="nav-item" :class="{ active: activeTab === 'manage' }" @click="setActiveTab('manage')">
          任务管理
        </button>
        <button class="nav-item" :class="{ active: activeTab === 'history' }" @click="setActiveTab('history')">
          历史任务
        </button>
      </nav>

      <section class="sidebar-hint card">
        <h3>快速提示</h3>
        <p class="hint">在历史任务中可通过状态、名称及时间范围精准定位任务。</p>
      </section>
    </aside>

    <main class="content">
      <template v-if="activeTab === 'manage'">
        <header class="content-header">
          <div>
            <h1>无障碍图表助手</h1>
            <p class="muted">上传图表图片，系统自动生成摘要、数据点和结构化表格。</p>
          </div>
          <router-link class="link" to="/templates">模板管理</router-link>
        </header>

        <section class="card">
          <h2>创建新任务</h2>
          <div class="mode-tabs" role="tablist">
            <button
              role="tab"
              :class="['mode-tab', { active: creationMode === 'upload' }]"
              @click="creationMode = 'upload'"
            >
              上传图表图片
            </button>
            <button
              role="tab"
              :class="['mode-tab', { active: creationMode === 'metadata' }]"
              @click="creationMode = 'metadata'"
            >
              输入图表元数据
            </button>
            <router-link class="link" to="/docs">查看接入说明</router-link>
          </div>

          <form v-if="creationMode === 'upload'" class="upload-form" @submit.prevent="submitTask">
            <label>
              任务名称
              <input v-model="taskNameInput" type="text" placeholder="示例：季度销售趋势" required />
            </label>
            <label>
              代码模板
              <select v-model="selectedTemplateId">
                <option value="">默认模板</option>
                <option v-for="template in templates" :key="template.id" :value="String(template.id)">
                  {{ template.name }} · {{ template.language.toUpperCase() }}
                </option>
              </select>
            </label>
            <label class="file-input">
              <input type="file" accept="image/*" @change="handleFile" required />
              <span>{{ file ? file.name : '选择图表图片' }}</span>
            </label>
            <button class="primary" type="submit" :disabled="uploading">
              {{ uploading ? '处理中…' : '开始转换' }}
            </button>
          </form>

          <form v-else class="upload-form" @submit.prevent="submitTask">
            <label>
              任务名称
              <input v-model="taskNameInput" type="text" placeholder="示例：季度销售趋势" required />
            </label>
            <label>
              代码模板
              <select v-model="selectedTemplateId">
                <option value="">默认模板</option>
                <option v-for="template in templates" :key="template.id" :value="String(template.id)">
                  {{ template.name }} · {{ template.language.toUpperCase() }}
                </option>
              </select>
            </label>
            <label>
              摘要（必填）
              <textarea
                v-model="metadataForm.summary"
                placeholder="示例：2024年一至四月销售趋势总体上升，峰值出现在四月，约五十一万。"
                required
              ></textarea>
            </label>
            <label>
              数据点 JSON（可选）
              <textarea
                v-model="metadataForm.dataPointsText"
                placeholder='[ {"id":1,"x":0.1,"y":0.72,"description":"一月 销售额 23.5 万"} ]'
              ></textarea>
            </label>
            <label>
              表格数据 JSON（可选）
              <textarea
                v-model="metadataForm.tableDataText"
                placeholder='[ ["月份","销售额"], ["一月","23.5 万"] ]'
              ></textarea>
            </label>
            <button class="primary" type="submit" :disabled="uploading">
              {{ uploading ? '提交中…' : '保存元数据任务' }}
            </button>
          </form>
          <p v-if="uploadMessage" class="hint">{{ uploadMessage }}</p>
        </section>
      </template>

      <template v-else-if="activeTab === 'history'">
        <header class="content-header history-header">
          <div>
            <h1>任务总览</h1>
            <p class="muted">按状态、名称及时间范围筛选任务，快速查看处理进度。</p>
          </div>
        </header>

        <section class="card history-filters">
          <form class="filter-grid" @submit.prevent="applyFilters">
            <label>
              任务状态
              <select v-model="selectedStatus">
                <option v-for="option in statusOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>
            <label>
              任务名称
              <input
                v-model="taskName"
                type="search"
                placeholder="输入任务名称"
                @keyup.enter="applyFilters"
              />
            </label>
            <label>
              创建时间（起）
              <input v-model="createdStart" type="date" />
            </label>
            <label>
              创建时间（止）
              <input v-model="createdEnd" type="date" />
            </label>
            <label>
              更新时间（起）
              <input v-model="updatedStart" type="date" />
            </label>
            <label>
              更新时间（止）
              <input v-model="updatedEnd" type="date" />
            </label>
            <div class="filter-actions">
              <button class="primary" type="submit">查询</button>
              <button class="ghost" type="button" @click="resetFilters">重置</button>
            </div>
          </form>
        </section>

        <section class="card history-table">
          <table class="task-table">
            <thead>
              <tr>
                <th>任务名称</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>更新时间</th>
                <th>摘要</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in tasks" :key="task.id">
                <td class="task-title">
                  <div class="title-cell">
                    <span class="task-name">{{ task.name }}</span>
                  </div>
                </td>
                <td>
                  <span class="status-badge" :class="`status-${task.status}`">{{ statusLabel(task.status) }}</span>
                </td>
                <td>{{ formatDate(task.created_at) }}</td>
                <td>{{ formatDate(task.updated_at) }}</td>
                <td class="summary">{{ task.summary || '—' }}</td>
                <td class="actions">
                  <router-link :to="`/tasks/${task.id}`" class="link">详情</router-link>
                  <button class="ghost" @click="openEditor(task)">编辑</button>
                  <button v-if="canCancel(task.status)" class="ghost" @click="cancelTask(task.id)">取消</button>
                  <button class="ghost" @click="deleteTask(task.id)">删除</button>
                </td>
              </tr>
              <tr v-if="!tasks.length">
                <td class="empty" colspan="6">暂无符合条件的任务</td>
              </tr>
            </tbody>
          </table>
          <div class="pagination" v-if="pagination.pages > 1">
            <button class="ghost" :disabled="pagination.page === 1" @click="loadTasks(pagination.page - 1)">
              上一页
            </button>
            <span>第 {{ pagination.page }} / {{ pagination.pages }} 页，共 {{ pagination.total }} 条</span>
            <button
              class="ghost"
              :disabled="pagination.page === pagination.pages"
              @click="loadTasks(pagination.page + 1)"
            >
              下一页
            </button>
          </div>
        </section>
      </template>

    </main>

    <div v-if="editor.visible" class="dialog-backdrop" @click.self="closeEditor">
      <div class="dialog">
        <h3>编辑任务</h3>
        <form @submit.prevent="saveEditor">
          <label>
            任务名称
            <input v-model="editor.name" type="text" required />
          </label>
          <label>
            模板
            <select v-model="editor.template_id">
              <option value="">默认模板</option>
              <option v-for="template in templates" :key="`editor-template-${template.id}`" :value="String(template.id)">
                {{ template.name }} · {{ template.language.toUpperCase() }}
              </option>
            </select>
          </label>
          <footer class="dialog-actions">
            <button class="ghost" type="button" @click="closeEditor">取消</button>
            <button class="primary" type="submit">保存</button>
          </footer>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();
const router = useRouter();

const creationMode = ref('upload');
const activeTab = ref('manage');

const showPassword = ref(false);
const passwordForm = reactive({ current_password: '', new_password: '' });
const passwordLoading = ref(false);
const passwordMessage = ref('');

const templates = ref([]);
const tasks = ref([]);
const pagination = reactive({ page: 1, pages: 1, total: 0 });

const taskNameInput = ref('');
const selectedTemplateId = ref('');
const file = ref(null);
const uploading = ref(false);
const uploadMessage = ref('');

const metadataForm = reactive({
  summary: '',
  dataPointsText: '',
  tableDataText: ''
});

const selectedStatus = ref('');
const taskName = ref('');
const createdStart = ref('');
const createdEnd = ref('');
const updatedStart = ref('');
const updatedEnd = ref('');

const editor = reactive({
  visible: false,
  taskId: null,
  name: '',
  template_id: ''
});

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 0, label: '排队中' },
  { value: 1, label: '处理中' },
  { value: 2, label: '已完成' },
  { value: 3, label: '失败' },
  { value: 4, label: '已取消' }
];

const formatDate = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString();
};

const statusLabel = (status) => {
  const mapping = {
    0: '排队中',
    1: '处理中',
    2: '已完成',
    3: '失败',
    4: '已取消'
  };
  const key = Number(status);
  return mapping[key] || '未知';
};

const canCancel = (status) => [0, 1].includes(Number(status));

const setActiveTab = (tab) => {
  if (activeTab.value === tab) {
    if (tab === 'history') {
      loadTasks(1);
    }
    return;
  }
  activeTab.value = tab;
  if (tab === 'history') {
    loadTasks(1);
  }
};

const togglePassword = () => {
  showPassword.value = !showPassword.value;
  passwordMessage.value = '';
};

const updatePassword = async () => {
  try {
    passwordLoading.value = true;
    await auth.changePassword(passwordForm);
    passwordMessage.value = '密码已更新。';
    passwordForm.current_password = '';
    passwordForm.new_password = '';
  } catch (error) {
    passwordMessage.value = error.response?.data?.message || '更新失败，请稍后再试。';
  } finally {
    passwordLoading.value = false;
  }
};

const logout = () => {
  auth.logout();
  router.push('/login');
};

const loadTemplates = async () => {
  try {
    const { data } = await axios.get('/api/templates');
    templates.value = data;
  } catch (error) {
    console.error(error);
  }
};

const buildDateParam = (value, endOfDay = false) => {
  if (!value) return null;
  return endOfDay ? `${value}T23:59:59` : `${value}T00:00:00`;
};

const loadTasks = async (page = pagination.page) => {
  try {
    const params = { page };
    if (selectedStatus.value !== '') params.status = Number(selectedStatus.value);
    if (taskName.value.trim()) params.task_name = taskName.value.trim();
    const createdFrom = buildDateParam(createdStart.value);
    const createdTo = buildDateParam(createdEnd.value, true);
    const updatedFrom = buildDateParam(updatedStart.value);
    const updatedTo = buildDateParam(updatedEnd.value, true);
    if (createdFrom) params.created_from = createdFrom;
    if (createdTo) params.created_to = createdTo;
    if (updatedFrom) params.updated_from = updatedFrom;
    if (updatedTo) params.updated_to = updatedTo;
    const { data } = await axios.get('/api/tasks', { params });
    tasks.value = data.items;
    pagination.page = data.page;
    pagination.pages = data.pages;
    pagination.total = data.total;
  } catch (error) {
    console.error(error);
  }
};

const applyFilters = () => {
  loadTasks(1);
};

const resetFilters = () => {
  selectedStatus.value = '';
  taskName.value = '';
  createdStart.value = '';
  createdEnd.value = '';
  updatedStart.value = '';
  updatedEnd.value = '';
};

const handleFile = (event) => {
  const [selected] = event.target.files || [];
  file.value = selected || null;
};

const submitTask = async () => {
  const trimmedName = taskNameInput.value.trim();
  if (!trimmedName) {
    uploadMessage.value = '任务名称不能为空';
    return;
  }

  try {
    uploading.value = true;
    uploadMessage.value = '';

    if (creationMode.value === 'upload') {
      if (!file.value) {
        uploadMessage.value = '请先选择图表图片。';
        return;
      }

      const formData = new FormData();
      formData.append('name', trimmedName);
      formData.append('file', file.value);
      if (selectedTemplateId.value) {
        formData.append('template_id', selectedTemplateId.value);
      }

      await axios.post('/api/tasks', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      uploadMessage.value = '任务已创建，正在排队处理。';
      file.value = null;
    } else {
      const parseJsonField = (text, fallback) => {
        const content = (text || '').trim();
        if (!content) return fallback;
        try {
          return JSON.parse(content);
        } catch (err) {
          throw new Error('JSON 解析失败，请检查格式。');
        }
      };

      const payload = {
        mode: 'metadata',
        name: trimmedName,
        summary: metadataForm.summary.trim(),
        data_points: parseJsonField(metadataForm.dataPointsText, []),
        table_data: parseJsonField(metadataForm.tableDataText, [])
      };

      if (!payload.summary) {
        uploadMessage.value = '请填写摘要内容。';
        return;
      }

      if (selectedTemplateId.value) {
        payload.template_id = selectedTemplateId.value;
      }

      await axios.post('/api/tasks', payload);
      uploadMessage.value = '已保存元数据任务，结果可直接查看。';
      metadataForm.summary = '';
      metadataForm.dataPointsText = '';
      metadataForm.tableDataText = '';
    }

    taskNameInput.value = '';
    selectedTemplateId.value = '';
    await loadTasks(1);
  } catch (error) {
    uploadMessage.value = error.response?.data?.message || error.message || '创建失败，请稍后再试。';
  } finally {
    uploading.value = false;
  }
};

const openEditor = (task) => {
  editor.visible = true;
  editor.taskId = task.id;
  editor.name = task.name;
  editor.template_id = task.template?.id ? String(task.template.id) : '';
};

const closeEditor = () => {
  editor.visible = false;
  editor.taskId = null;
  editor.name = '';
  editor.template_id = '';
};

const saveEditor = async () => {
  if (!editor.taskId) return;
  const trimmedName = editor.name.trim();
  if (!trimmedName) {
    window.alert('任务名称不能为空');
    return;
  }
  try {
    const payload = {
      name: trimmedName,
      template_id: editor.template_id ? Number(editor.template_id) : null
    };
    await axios.patch(`/api/tasks/${editor.taskId}`, payload);
    await loadTasks();
    closeEditor();
  } catch (error) {
    window.alert(error.response?.data?.message || '保存失败');
  }
};

const cancelTask = async (taskId) => {
  try {
    await axios.post(`/api/tasks/${taskId}/cancel`);
    await loadTasks();
  } catch (error) {
    window.alert(error.response?.data?.message || '取消失败');
  }
};

const deleteTask = async (taskId) => {
  if (!window.confirm('确认删除该任务？删除后不可恢复。')) return;
  try {
    await axios.delete(`/api/tasks/${taskId}`);
    await loadTasks();
  } catch (error) {
    window.alert(error.response?.data?.message || '删除失败');
  }
};

let filterLoadTimer = null;
const scheduleFilterLoad = () => {
  if (activeTab.value !== 'history') return;
  if (filterLoadTimer) return;
  filterLoadTimer = setTimeout(() => {
    filterLoadTimer = null;
    loadTasks(1);
  }, 0);
};

onUnmounted(() => {
  if (filterLoadTimer) {
    clearTimeout(filterLoadTimer);
    filterLoadTimer = null;
  }
});

watch([selectedStatus, createdStart, createdEnd, updatedStart, updatedEnd], () => {
  scheduleFilterLoad();
});

onMounted(async () => {
  if (!auth.isAuthenticated) {
    router.push('/login');
    return;
  }
  await Promise.all([loadTemplates(), loadTasks()]);
});
</script>

<style scoped>
/* 仪表盘布局 */
.dashboard {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: var(--spacing-lg, 24px);
  padding: var(--spacing-xl, 32px);
  min-height: 100vh;
  background: var(--color-bg, #fafbfc);
  max-width: 1280px;
  margin: 0 auto;
}

/* 侧边栏 */
.sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 16px);
  position: sticky;
  top: var(--spacing-xl, 32px);
  height: fit-content;
}

/* 卡片通用样式 */
.user-card,
.sidebar-nav,
.sidebar-hint,
.card {
  background: var(--color-surface, #ffffff);
  border-radius: var(--radius-lg, 12px);
  padding: var(--spacing-lg, 24px);
  border: 1px solid var(--color-border, #e1e4e8);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(0, 0, 0, 0.05));
}

/* 用户卡片 */
.user-card {
  background: var(--color-surface, #ffffff);
}

.user-card h2 {
  margin: 0 0 var(--spacing-xs, 4px);
  font-size: var(--text-xl, 18px);
  font-weight: 600;
  color: var(--color-text-primary, #24292f);
}

/* 次要文字 */
.muted {
  color: var(--color-text-secondary, #57606a);
  margin: var(--spacing-xs, 4px) 0 var(--spacing-md, 16px);
  font-size: var(--text-sm, 13px);
  line-height: var(--leading-normal, 1.5);
}

/* 链接按钮 */
.link {
  color: var(--color-primary, #2563eb);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-weight: 500;
  font-size: var(--text-sm, 13px);
  transition: color 0.15s ease;
}

.link:hover {
  color: var(--color-primary-hover, #1d4ed8);
  text-decoration: underline;
}

/* 主按钮 */
.primary {
  background: var(--color-primary, #2563eb);
  color: #ffffff;
  border: none;
  border-radius: var(--radius-md, 8px);
  padding: 10px 18px;
  cursor: pointer;
  font-weight: 600;
  font-size: var(--text-sm, 13px);
  transition: background-color 0.15s ease;
}

.primary:hover:not(:disabled) {
  background: var(--color-primary-hover, #1d4ed8);
}

.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 幽灵按钮 */
.ghost {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border, #e1e4e8);
  border-radius: var(--radius-md, 8px);
  padding: 8px 14px;
  cursor: pointer;
  color: var(--color-text-primary, #24292f);
  font-weight: 500;
  font-size: var(--text-sm, 13px);
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.ghost:hover:not(:disabled) {
  background: var(--color-bg, #fafbfc);
  border-color: var(--color-text-muted, #8b949e);
}

.ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 密码表单 */
.password-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
  margin: var(--spacing-md, 16px) 0;
  padding: var(--spacing-md, 16px);
  background: var(--color-bg, #fafbfc);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border, #e1e4e8);
}

/* 表单输入框 */
.password-form input,
.upload-form input,
.upload-form select,
.filter-grid input,
.filter-grid select,
.dialog input,
.dialog select {
  width: 100%;
  border: 1px solid var(--color-border, #e1e4e8);
  border-radius: var(--radius-md, 8px);
  padding: 10px 12px;
  font-size: var(--text-md, 15px);
  background: var(--color-surface, #ffffff);
  color: var(--color-text-primary, #24292f);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.password-form input:focus,
.upload-form input:focus,
.upload-form select:focus,
.filter-grid input:focus,
.filter-grid select:focus,
.dialog input:focus,
.dialog select:focus {
  outline: none;
  border-color: var(--color-primary, #2563eb);
  box-shadow: 0 0 0 3px var(--color-primary-light, #eff6ff);
}

/* 侧边导航 */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
  padding: var(--spacing-sm, 8px);
}

.nav-item {
  width: 100%;
  border: none;
  background: transparent;
  color: var(--color-text-secondary, #57606a);
  padding: 10px 14px;
  border-radius: var(--radius-md, 8px);
  font-weight: 500;
  font-size: var(--text-sm, 13px);
  cursor: pointer;
  text-align: left;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-item.active {
  background: var(--color-primary-light, #eff6ff);
  color: var(--color-primary, #2563eb);
  font-weight: 600;
}

.nav-item:not(.active):hover {
  background: var(--color-bg, #fafbfc);
  color: var(--color-text-primary, #24292f);
}

/* 侧边栏提示 */
.sidebar-hint h3 {
  margin: 0 0 var(--spacing-sm, 8px);
  font-size: var(--text-md, 15px);
  font-weight: 600;
  color: var(--color-text-primary, #24292f);
}

.hint {
  color: var(--color-text-muted, #8b949e);
  font-size: var(--text-xs, 12px);
  margin-top: var(--spacing-sm, 8px);
  line-height: var(--leading-relaxed, 1.75);
}

/* 主内容区 */
.content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg, 24px);
  max-width: 900px;
  width: 100%;
}

/* 内容头部 */
.content-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md, 16px);
  flex-wrap: wrap;
}

.content-header h1 {
  margin: 0;
  font-size: var(--text-3xl, 24px);
  font-weight: 600;
  color: var(--color-text-primary, #24292f);
  letter-spacing: -0.02em;
}

/* 上传表单 */
.upload-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 16px);
}

.upload-form label {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
  font-size: var(--text-sm, 13px);
  font-weight: 500;
  color: var(--color-text-primary, #24292f);
}

.upload-form textarea {
  width: 100%;
  min-height: 100px;
  border: 1px solid var(--color-border, #e1e4e8);
  border-radius: var(--radius-md, 8px);
  padding: 12px 14px;
  font-size: var(--text-md, 15px);
  resize: vertical;
  background: var(--color-surface, #ffffff);
  color: var(--color-text-primary, #24292f);
  font-family: inherit;
  line-height: var(--leading-normal, 1.5);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.upload-form textarea:focus {
  outline: none;
  border-color: var(--color-primary, #2563eb);
  box-shadow: 0 0 0 3px var(--color-primary-light, #eff6ff);
}

/* 文件输入 */
.file-input {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed var(--color-border, #e1e4e8);
  border-radius: var(--radius-md, 8px);
  padding: var(--spacing-lg, 24px);
  text-align: center;
  cursor: pointer;
  color: var(--color-text-secondary, #57606a);
  font-weight: 500;
  font-size: var(--text-sm, 13px);
  background: var(--color-bg, #fafbfc);
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.file-input:hover {
  border-color: var(--color-primary, #2563eb);
  background: var(--color-primary-light, #eff6ff);
  color: var(--color-primary, #2563eb);
}

.file-input input {
  display: none;
}

/* 历史过滤器 */
.history-filters {
  padding-bottom: var(--spacing-md, 16px);
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--spacing-md, 16px);
  align-items: end;
}

.filter-grid label {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
  font-size: var(--text-sm, 13px);
  font-weight: 500;
  color: var(--color-text-primary, #24292f);
}

.filter-actions {
  display: flex;
  gap: var(--spacing-sm, 8px);
  align-items: flex-end;
}

/* 模式标签页 */
.mode-tabs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  margin-bottom: var(--spacing-md, 16px);
  padding: 4px;
  background: var(--color-bg, #fafbfc);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border, #e1e4e8);
  width: fit-content;
}

.mode-tab {
  border: none;
  background: transparent;
  color: var(--color-text-secondary, #57606a);
  padding: 8px 14px;
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  font-weight: 500;
  font-size: var(--text-sm, 13px);
  transition: all 0.15s ease;
}

.mode-tab.active {
  background: var(--color-surface, #ffffff);
  color: var(--color-primary, #2563eb);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(0, 0, 0, 0.05));
  font-weight: 600;
}

.mode-tab:not(.active):hover {
  color: var(--color-text-primary, #24292f);
}

.mode-tabs .link {
  margin-left: var(--spacing-md, 16px);
}

/* 历史表格 */
.history-table {
  overflow-x: auto;
}

.task-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm, 13px);
}

.task-table th,
.task-table td {
  padding: 12px 14px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-light, #eaecef);
  vertical-align: middle;
}

.task-table thead th {
  background: var(--color-bg, #fafbfc);
  font-weight: 600;
  color: var(--color-text-primary, #24292f);
  font-size: var(--text-xs, 12px);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.task-title {
  min-width: 180px;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
}

.title-cell .task-name {
  font-weight: 500;
  color: var(--color-text-primary, #24292f);
}

.title-cell .preview {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md, 8px);
  overflow: hidden;
  flex-shrink: 0;
  border: 1px solid var(--color-border, #e1e4e8);
}

.title-cell .preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 状态徽章 */
.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: var(--text-xs, 12px);
  font-weight: 500;
  white-space: nowrap;
}

.status-badge.status-0 {
  background: var(--color-info-bg, #f0f9ff);
  color: var(--color-info, #0284c7);
}

.status-badge.status-1 {
  background: var(--color-warning-bg, #fefce8);
  color: var(--color-warning, #ca8a04);
}

.status-badge.status-2 {
  background: var(--color-success-bg, #f0fdf4);
  color: var(--color-success, #16a34a);
}

.status-badge.status-3 {
  background: var(--color-error-bg, #fef2f2);
  color: var(--color-error, #dc2626);
}

.status-badge.status-4 {
  background: var(--color-bg, #fafbfc);
  color: var(--color-text-muted, #8b949e);
}

/* 摘要列 */
.summary {
  max-width: 220px;
  color: var(--color-text-secondary, #57606a);
  font-size: var(--text-sm, 13px);
  line-height: var(--leading-normal, 1.5);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 操作列 */
.actions {
  display: flex;
  gap: var(--spacing-sm, 8px);
  flex-wrap: nowrap;
}

.actions .link,
.actions .ghost {
  padding: 6px 10px;
  font-size: var(--text-xs, 12px);
}

/* 空状态 */
.empty {
  text-align: center;
  color: var(--color-text-muted, #8b949e);
  padding: var(--spacing-xl, 32px) 0;
  font-size: var(--text-sm, 13px);
}

/* 分页 */
.pagination {
  display: flex;
  gap: var(--spacing-md, 16px);
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary, #57606a);
  font-size: var(--text-sm, 13px);
  margin-top: var(--spacing-md, 16px);
  padding-top: var(--spacing-md, 16px);
  border-top: 1px solid var(--color-border-light, #eaecef);
}

.pagination .ghost {
  padding: 6px 12px;
}

/* 对话框 */
.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-lg, 24px);
  z-index: 100;
}

.dialog {
  background: var(--color-surface, #ffffff);
  border-radius: var(--radius-lg, 12px);
  padding: var(--spacing-lg, 24px);
  width: 100%;
  max-width: 400px;
  border: 1px solid var(--color-border, #e1e4e8);
  box-shadow: var(--shadow-lg, 0 8px 24px rgba(0, 0, 0, 0.1));
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 16px);
}

.dialog h3 {
  margin: 0;
  font-size: var(--text-xl, 18px);
  font-weight: 600;
  color: var(--color-text-primary, #24292f);
}

.dialog label {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
  font-size: var(--text-sm, 13px);
  font-weight: 500;
  color: var(--color-text-primary, #24292f);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm, 8px);
  margin-top: var(--spacing-sm, 8px);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .dashboard {
    grid-template-columns: 1fr;
    padding: var(--spacing-md, 16px);
  }

  .sidebar {
    position: static;
    flex-direction: row;
    overflow-x: auto;
    gap: var(--spacing-sm, 8px);
    padding-bottom: var(--spacing-sm, 8px);
  }

  .sidebar > * {
    min-width: 220px;
    flex-shrink: 0;
  }

  .content-header {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }

  .task-table {
    font-size: var(--text-xs, 12px);
  }

  .task-table th,
  .task-table td {
    padding: 10px 8px;
  }
}
</style>
