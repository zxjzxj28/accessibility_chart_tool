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
          <button class="primary" type="submit" :disabled="passwordLoading">{{ passwordLoading ? '更新中…' : '确认修改' }}</button>
          <p v-if="passwordMessage" class="hint">{{ passwordMessage }}</p>
        </form>
        <button class="ghost" @click="logout">退出登录</button>
      </section>

      <section class="applications">
        <header>
          <h3>应用与分组</h3>
          <button class="link" @click="loadApplications">刷新</button>
        </header>
        <p class="hint">支持层级分组，点击按钮快速管理。</p>
        <ul class="application-list">
          <li v-for="app in applications" :key="app.id" class="application-item">
            <div class="application-row">
              <button
                class="pill"
                :class="{ active: selectedAppId === app.id && !selectedGroupId }"
                @click="selectApplication(app.id)"
              >
                {{ app.name }}
              </button>
              <div class="app-actions">
                <button class="icon" title="新增分组" @click="createGroup(app.id)">＋</button>
              </div>
            </div>
            <ul v-if="app.flattenedGroups.length" class="group-list">
              <li v-for="group in app.flattenedGroups" :key="group.id">
                <div class="group-row">
                  <button
                    class="pill"
                    :style="{ paddingLeft: `${12 + group.depth * 16}px` }"
                    :class="{ active: selectedGroupId === group.id }"
                    @click="selectGroup(app.id, group.id)"
                  >
                    {{ group.name }}
                  </button>
                  <div class="group-actions">
                    <button class="icon" title="添加子分组" @click="createGroup(app.id, group.id)">＋</button>
                    <button class="icon" title="重命名" @click="renameGroup(group)">✎</button>
                    <button class="icon" title="删除" @click="removeGroup(group)">✕</button>
                  </div>
                </div>
              </li>
            </ul>
          </li>
        </ul>
      </section>
    </aside>

    <main class="content">
      <header class="content-header">
        <div>
          <h1>无障碍图表助手</h1>
          <p class="muted">上传图表图片，系统自动生成摘要、数据点和表格数据。</p>
        </div>
        <div class="header-actions">
          <input
            v-model="keyword"
            type="search"
            placeholder="按关键字检索任务"
            @keyup.enter="loadTasks(1)"
          />
          <router-link class="link" to="/templates">模板管理</router-link>
          <button class="primary" @click="loadTasks()">刷新任务</button>
        </div>
      </header>

      <section class="card">
        <h2>开始一个新任务</h2>
        <form class="upload-form" @submit.prevent="submitTask">
          <label>
            任务标题
            <input v-model="title" type="text" placeholder="示例：季度销售趋势" required />
          </label>
          <label>
            应用名称
            <input
              v-model="applicationInput"
              type="text"
              list="application-options"
              placeholder="可输入新名称或选择已有应用"
            />
            <datalist id="application-options">
              <option v-for="app in applications" :key="app.id" :value="app.name"></option>
            </datalist>
          </label>
          <label>
            所在分组
            <select v-model="selectedUploadGroup">
              <option value="">不分组</option>
              <option
                v-for="group in uploadGroups"
                :key="group.id"
                :value="String(group.id)"
              >
                {{ group.label }}
              </option>
            </select>
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
        <p v-if="uploadMessage" class="hint">{{ uploadMessage }}</p>
      </section>

      <section class="card">
        <header class="card-header">
          <h2>任务列表</h2>
          <div class="filters">
            <button class="pill" :class="{ active: !selectedAppId && !selectedGroupId }" @click="clearFilters">
              全部
            </button>
            <span v-if="currentApplication">{{ currentApplication.name }}</span>
            <span v-if="currentGroup"> / {{ currentGroup.name }}</span>
          </div>
        </header>
        <div class="task-list" v-if="tasks.length">
          <article v-for="task in tasks" :key="task.id" class="task-card">
            <header>
              <span class="status" :class="task.status">{{ statusLabel(task.status) }}</span>
              <h3>{{ task.title }}</h3>
            </header>
            <p class="muted">创建于 {{ formatDate(task.created_at) }}</p>
            <p v-if="task.summary" class="summary">{{ task.summary }}</p>
            <footer class="task-actions">
              <router-link :to="`/tasks/${task.id}`" class="link">查看详情</router-link>
              <button class="ghost" @click="openEditor(task)">编辑</button>
              <button
                v-if="canCancel(task.status)"
                class="ghost"
                @click="cancelTask(task.id)"
              >
                取消
              </button>
              <button class="ghost" @click="deleteTask(task.id)">删除</button>
            </footer>
          </article>
        </div>
        <p v-else class="hint">暂无任务，上传图表即可开始。</p>
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
    </main>

    <div v-if="editor.visible" class="dialog-backdrop" @click.self="closeEditor">
      <div class="dialog">
        <h3>编辑任务</h3>
        <form @submit.prevent="saveEditor">
          <label>
            任务标题
            <input v-model="editor.title" type="text" required />
          </label>
          <label>
            应用
            <select v-model="editor.app_id" @change="onEditorAppChange">
              <option v-for="app in applications" :key="`editor-app-${app.id}`" :value="String(app.id)">
                {{ app.name }}
              </option>
            </select>
          </label>
          <label>
            分组
            <select v-model="editor.group_id">
              <option value="">不分组</option>
              <option
                v-for="group in editorGroups"
                :key="`editor-group-${group.id}`"
                :value="String(group.id)"
              >
                {{ group.label }}
              </option>
            </select>
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
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();
const router = useRouter();

const showPassword = ref(false);
const passwordForm = reactive({ current_password: '', new_password: '' });
const passwordLoading = ref(false);
const passwordMessage = ref('');

const applications = ref([]);
const templates = ref([]);
const tasks = ref([]);
const pagination = reactive({ page: 1, pages: 1, total: 0 });

const selectedAppId = ref(null);
const selectedGroupId = ref(null);
const keyword = ref('');

const title = ref('');
const applicationInput = ref('');
const selectedUploadGroup = ref('');
const selectedTemplateId = ref('');
const file = ref(null);
const uploading = ref(false);
const uploadMessage = ref('');

const editor = reactive({
  visible: false,
  taskId: null,
  title: '',
  app_id: '',
  group_id: '',
  template_id: ''
});

const formatDate = (value) => new Date(value).toLocaleString();

const statusLabel = (status) => {
  switch (status) {
    case 'queued':
      return '排队中';
    case 'processing':
      return '处理中';
    case 'completed':
      return '已完成';
    case 'failed':
      return '失败';
    case 'cancelled':
      return '已取消';
    default:
      return status;
  }
};

const canCancel = (status) => ['queued', 'processing'].includes(status);

const flattenGroups = (groups, depth = 0) => {
  const result = [];
  for (const group of groups || []) {
    if (group.is_deleted) continue;
    result.push({
      id: group.id,
      name: group.name,
      depth,
      app_id: group.app_id,
      parent_id: group.parent_id
    });
    if (group.children && group.children.length) {
      result.push(...flattenGroups(group.children, depth + 1));
    }
  }
  return result;
};

const refreshApplicationCache = (items) => {
  applications.value = items.map((app) => ({
    ...app,
    flattenedGroups: flattenGroups(app.groups)
  }));
};

const currentApplication = computed(() => {
  if (!selectedAppId.value) return null;
  return applications.value.find((app) => app.id === selectedAppId.value) || null;
});

const currentGroup = computed(() => {
  if (!currentApplication.value || !selectedGroupId.value) return null;
  return (
    currentApplication.value.flattenedGroups.find((group) => group.id === selectedGroupId.value) || null
  );
});

const matchedUploadApp = computed(() => {
  const name = applicationInput.value.trim().toLowerCase();
  if (!name) return null;
  return (
    applications.value.find((app) => app.name.toLowerCase() === name) || null
  );
});

const uploadGroups = computed(() => {
  if (!matchedUploadApp.value) return [];
  return matchedUploadApp.value.flattenedGroups.map((group) => ({
    id: group.id,
    label: `${'— '.repeat(group.depth)}${group.name}`
  }));
});

const editorGroups = computed(() => {
  if (!editor.app_id) return [];
  const app = applications.value.find((item) => String(item.id) === editor.app_id);
  if (!app) return [];
  return app.flattenedGroups.map((group) => ({
    id: group.id,
    label: `${'— '.repeat(group.depth)}${group.name}`
  }));
});

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

const loadApplications = async () => {
  try {
    const { data } = await axios.get('/api/applications');
    refreshApplicationCache(data);
    if (selectedAppId.value) {
      const exists = applications.value.some((app) => app.id === selectedAppId.value);
      if (!exists) {
        selectedAppId.value = null;
        selectedGroupId.value = null;
      }
    }
    if (selectedGroupId.value && currentApplication.value) {
      const groupExists = currentApplication.value.flattenedGroups.some(
        (group) => group.id === selectedGroupId.value
      );
      if (!groupExists) {
        selectedGroupId.value = null;
      }
    }
  } catch (error) {
    console.error(error);
  }
};

const loadTemplates = async () => {
  try {
    const { data } = await axios.get('/api/templates');
    templates.value = data;
  } catch (error) {
    console.error(error);
  }
};

const loadTasks = async (page = pagination.page) => {
  try {
    const params = { page };
    if (keyword.value.trim()) params.keyword = keyword.value.trim();
    if (selectedAppId.value) params.app_id = selectedAppId.value;
    if (selectedGroupId.value) params.group_id = selectedGroupId.value;
    const { data } = await axios.get('/api/tasks', { params });
    tasks.value = data.items;
    pagination.page = data.page;
    pagination.pages = data.pages;
    pagination.total = data.total;
  } catch (error) {
    console.error(error);
  }
};

const selectApplication = (appId) => {
  if (selectedAppId.value === appId && !selectedGroupId.value) {
    selectedAppId.value = null;
  } else {
    selectedAppId.value = appId;
  }
  selectedGroupId.value = null;
  loadTasks(1);
};

const selectGroup = (appId, groupId) => {
  selectedAppId.value = appId;
  selectedGroupId.value = groupId;
  loadTasks(1);
};

const clearFilters = () => {
  selectedAppId.value = null;
  selectedGroupId.value = null;
  loadTasks(1);
};

const createGroup = async (appId, parentId = null) => {
  const name = window.prompt(parentId ? '输入子分组名称' : '输入分组名称');
  if (!name || !name.trim()) return;
  try {
    const payload = { name: name.trim(), app_id: appId };
    if (parentId) payload.parent_id = parentId;
    await axios.post('/api/groups', payload);
    await loadApplications();
  } catch (error) {
    window.alert(error.response?.data?.message || '创建失败');
  }
};

const renameGroup = async (group) => {
  const name = window.prompt('新的分组名称', group.name);
  if (!name || !name.trim()) return;
  try {
    await axios.patch(`/api/groups/${group.id}`, { name: name.trim() });
    await loadApplications();
  } catch (error) {
    window.alert(error.response?.data?.message || '重命名失败');
  }
};

const removeGroup = async (group) => {
  if (!window.confirm('删除后该分组及其任务将被移除，是否继续？')) return;
  try {
    await axios.delete(`/api/groups/${group.id}`);
    if (selectedGroupId.value === group.id) {
      selectedGroupId.value = null;
    }
    await loadApplications();
    await loadTasks();
  } catch (error) {
    window.alert(error.response?.data?.message || '删除失败');
  }
};

const handleFile = (event) => {
  const [uploaded] = event.target.files || [];
  file.value = uploaded || null;
};

const submitTask = async () => {
  if (!file.value) {
    uploadMessage.value = '请选择图表图片。';
    return;
  }
  try {
    uploading.value = true;
    uploadMessage.value = '';
    const formData = new FormData();
    formData.append('title', title.value.trim());
    if (applicationInput.value.trim()) {
      formData.append('application_name', applicationInput.value.trim());
    }
    if (matchedUploadApp.value) {
      formData.append('application_id', String(matchedUploadApp.value.id));
    }
    if (selectedUploadGroup.value) {
      formData.append('group_id', selectedUploadGroup.value);
    }
    if (selectedTemplateId.value) {
      formData.append('template_id', selectedTemplateId.value);
    }
    formData.append('file', file.value);

    await axios.post('/api/tasks', formData);
    title.value = '';
    applicationInput.value = '';
    selectedUploadGroup.value = '';
    selectedTemplateId.value = '';
    file.value = null;
    uploadMessage.value = '任务已创建，正在处理。';
    await loadApplications();
    await loadTasks(1);
  } catch (error) {
    uploadMessage.value = error.response?.data?.message || '创建任务失败';
  } finally {
    uploading.value = false;
  }
};

const openEditor = (task) => {
  editor.visible = true;
  editor.taskId = task.id;
  editor.title = task.title;
  editor.app_id = task.app_id ? String(task.app_id) : (applications.value[0] ? String(applications.value[0].id) : '');
  editor.group_id = task.group_id ? String(task.group_id) : '';
  editor.template_id = task.template_id ? String(task.template_id) : '';
};

const closeEditor = () => {
  editor.visible = false;
  editor.taskId = null;
};

const onEditorAppChange = () => {
  editor.group_id = '';
};

const saveEditor = async () => {
  if (!editor.taskId) return;
  try {
    const payload = {
      title: editor.title.trim(),
      app_id: editor.app_id,
      group_id: editor.group_id || null,
      template_id: editor.template_id || null
    };
    await axios.patch(`/api/tasks/${editor.taskId}`, payload);
    await loadApplications();
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
  if (!window.confirm('确认删除该任务？')) return;
  try {
    await axios.delete(`/api/tasks/${taskId}`);
    await loadTasks();
  } catch (error) {
    window.alert(error.response?.data?.message || '删除失败');
  }
};

watch(applicationInput, () => {
  if (!matchedUploadApp.value) {
    selectedUploadGroup.value = '';
  }
});

onMounted(async () => {
  if (!auth.isAuthenticated) {
    router.push('/login');
    return;
  }
  await Promise.all([loadApplications(), loadTemplates(), loadTasks()]);
});
</script>

<style scoped>
.dashboard {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 24px;
  padding: 32px 24px 40px;
  min-height: 100vh;
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
  max-width: 1280px;
  margin: 0 auto;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.user-card,
.applications,
.card {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(4px);
}

.user-card h2 {
  margin: 0;
  font-size: 1.4rem;
}

.muted {
  color: #6b7280;
  font-size: 0.9rem;
}

.link {
  color: #2563eb;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

.ghost {
  background: none;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
}

.primary {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  cursor: pointer;
}

.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 12px 0;
}

.password-form input,
.upload-form input,
.upload-form select,
.header-actions input,
.dialog input,
.dialog select {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.95rem;
}

.applications header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.application-list,
.group-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.application-row,
.group-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.pill {
  background: #eef2ff;
  border: none;
  border-radius: 999px;
  padding: 6px 16px;
  cursor: pointer;
  text-align: left;
  flex: 1;
}

.pill.active {
  background: #2563eb;
  color: #fff;
}

.icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: #6b7280;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.card h2 {
  margin-top: 0;
}

.upload-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.upload-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.9rem;
}

.file-input {
  position: relative;
  border: 1px dashed #cbd5f5;
  border-radius: 8px;
  padding: 12px;
  color: #2563eb;
}

.file-input input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.hint {
  margin-top: 12px;
  color: #6b7280;
  font-size: 0.9rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 0.9rem;
}

.task-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.task-card {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 16px;
  padding: 18px;
  background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.task-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.12);
}

.task-card header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.status {
  font-size: 0.8rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e5e7eb;
}

.status.completed { background: #dcfce7; color: #166534; }
.status.failed { background: #fee2e2; color: #991b1b; }
.status.processing { background: #fef3c7; color: #92400e; }
.status.queued { background: #e0e7ff; color: #3730a3; }
.status.cancelled { background: #e5e7eb; color: #4b5563; }

.summary {
  font-size: 0.95rem;
}

.task-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.dialog {
  background: #fff;
  padding: 24px;
  border-radius: 12px;
  width: min(420px, 90vw);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dialog form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 960px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
  .sidebar {
    order: 2;
  }
  .content {
    order: 1;
  }
}
</style>
