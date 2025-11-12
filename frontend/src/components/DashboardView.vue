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

      <nav class="sidebar-nav card">
        <button class="nav-item" :class="{ active: activeTab === 'manage' }" @click="setActiveTab('manage')">
          任务管理
        </button>
        <button class="nav-item" :class="{ active: activeTab === 'history' }" @click="setActiveTab('history')">
          历史任务
        </button>
      </nav>

      <section v-if="activeTab === 'manage'" class="sidebar-hint card">
        <h3>历史任务</h3>
        <p class="hint">切换到“历史任务”标签即可查看和管理全部任务记录。</p>
      </section>
    </aside>

    <main class="content">
      <template v-if="activeTab === 'manage'">
        <header class="content-header">
          <div>
            <h1>无障碍图表助手</h1>
            <p class="muted">上传图表图片，系统自动生成摘要、数据点和表格数据。</p>
          </div>
          <div class="header-actions">
            <router-link class="link" to="/templates">模板管理</router-link>
            <button class="ghost" @click="setActiveTab('history')">查看历史任务</button>
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
      </template>

      <template v-else>
        <header class="content-header history-header">
          <div>
            <h1>历史任务</h1>
            <p class="muted">浏览并管理所有已提交的任务，可按关键字、应用与分组筛选。</p>
          </div>
          <div class="history-actions">
            <input
              v-model="keyword"
              type="search"
              placeholder="按关键字检索任务"
              @keyup.enter="loadTasks(1)"
            />
            <select v-model="selectedAppId">
              <option :value="null">全部应用</option>
              <option v-for="app in applications" :key="`filter-app-${app.id}`" :value="app.id">
                {{ app.name }}
              </option>
            </select>
            <select v-model="selectedGroupId" :disabled="!selectedAppId">
              <option :value="null">全部分组</option>
              <option
                v-for="group in groupFilterOptions"
                :key="`filter-group-${group.id}`"
                :value="group.id"
              >
                {{ group.label }}
              </option>
            </select>
            <button class="primary" @click="loadTasks(1)">搜索</button>
          </div>
        </header>

        <div class="history-layout">
          <aside class="card history-sidebar">
            <header class="history-sidebar-header">
              <h2>应用与分组</h2>
              <button class="link" @click="loadApplications">刷新</button>
            </header>
            <p class="hint">点击应用或分组筛选任务，支持快速增删改。</p>
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
          </aside>

          <section class="card history-content">
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
                  <button v-if="canCancel(task.status)" class="ghost" @click="cancelTask(task.id)">取消</button>
                  <button class="ghost" @click="deleteTask(task.id)">删除</button>
                </footer>
              </article>
            </div>
            <p v-else class="hint">暂无符合条件的任务。</p>
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
        </div>
      </template>
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
              <option v-for="group in editorGroups" :key="`editor-group-${group.id}`" :value="String(group.id)">
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
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();
const router = useRouter();

const activeTab = ref('manage');

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
  return applications.value.find((app) => app.name.toLowerCase() === name) || null;
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

const groupFilterOptions = computed(() => {
  if (!selectedAppId.value) return [];
  const app = applications.value.find((item) => item.id === selectedAppId.value);
  if (!app) return [];
  return app.flattenedGroups.map((group) => ({
    id: group.id,
    label: `${'— '.repeat(group.depth)}${group.name}`
  }));
});

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
};

const selectGroup = (appId, groupId) => {
  selectedAppId.value = appId;
  selectedGroupId.value = groupId;
};

const clearFilters = () => {
  selectedAppId.value = null;
  selectedGroupId.value = null;
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
    setActiveTab('history');
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
  editor.app_id = task.app_id ? String(task.app_id) : '';
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
  const trimmedTitle = editor.title.trim();
  if (!trimmedTitle) {
    window.alert('任务标题不能为空');
    return;
  }
  if (!editor.app_id) {
    window.alert('请选择应用');
    return;
  }
  try {
    const payload = {
      title: trimmedTitle,
      app_id: Number(editor.app_id),
      group_id: editor.group_id ? Number(editor.group_id) : null,
      template_id: editor.template_id ? Number(editor.template_id) : null
    };
    await axios.patch(`/api/tasks/${editor.taskId}`, payload);
    await Promise.all([loadApplications(), loadTasks()]);
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

watch(applicationInput, () => {
  if (!matchedUploadApp.value) {
    selectedUploadGroup.value = '';
  }
});

watch(selectedAppId, (value, oldValue) => {
  if (!value) {
    selectedGroupId.value = null;
  } else if (value !== oldValue) {
    const app = applications.value.find((item) => item.id === value);
    const groupExists = app?.flattenedGroups.some((group) => group.id === selectedGroupId.value);
    if (!groupExists) {
      selectedGroupId.value = null;
    }
  }
  if (value !== oldValue) {
    scheduleFilterLoad();
  }
});

watch(selectedGroupId, (value, oldValue) => {
  if (value !== oldValue) {
    scheduleFilterLoad();
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
.sidebar-nav,
.sidebar-hint,
.card {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(4px);
}

.user-card h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #1f2937;
}

.muted {
  color: #6b7280;
  margin: 4px 0 12px;
  font-size: 0.9rem;
}

.link {
  color: #2563eb;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
}

.primary {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 999px;
  padding: 10px 20px;
  cursor: pointer;
  font-weight: 600;
}

.ghost {
  background: transparent;
  border: 1px solid #d1d5db;
  border-radius: 999px;
  padding: 8px 16px;
  cursor: pointer;
  color: #374151;
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
.history-actions input,
.history-actions select,
.dialog input,
.dialog select {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.95rem;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.nav-item {
  width: 100%;
  border: none;
  border-radius: 999px;
  padding: 10px 16px;
  background: #eef2ff;
  color: #1f2937;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.nav-item.active {
  background: #2563eb;
  color: #fff;
}

.sidebar-hint h3 {
  margin: 0 0 8px;
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
  font-size: 0.85rem;
}

.history-header {
  align-items: center;
}

.history-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.history-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
}

.history-sidebar-header {
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

.history-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.task-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-card header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.task-card h3 {
  margin: 0;
  font-size: 1rem;
  color: #1f2937;
}

.status {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status.queued {
  background: #fef3c7;
  color: #92400e;
}

.status.processing {
  background: #bfdbfe;
  color: #1d4ed8;
}

.status.completed {
  background: #dcfce7;
  color: #166534;
}

.status.failed {
  background: #fee2e2;
  color: #b91c1c;
}

.status.cancelled {
  background: #e5e7eb;
  color: #374151;
}

.summary {
  color: #4b5563;
  font-size: 0.9rem;
}

.task-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  font-size: 0.9rem;
  color: #4b5563;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 1000;
}

.dialog {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dialog h3 {
  margin: 0;
}

.dialog label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.9rem;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 1024px) {
  .dashboard {
    grid-template-columns: 1fr;
  }

  .sidebar {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .content-header,
  .history-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .history-layout {
    grid-template-columns: 1fr;
  }

  .task-list {
    grid-template-columns: 1fr;
  }
}
</style>
