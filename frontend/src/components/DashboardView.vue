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
        <button class="nav-item" :class="{ active: activeTab === 'applications' }" @click="setActiveTab('applications')">
          应用管理
        </button>
      </nav>

      <section class="sidebar-hint card">
        <h3>快速提示</h3>
        <p class="hint">在历史任务中可通过应用、状态、时间范围精准定位任务；应用管理支持快速新建或重命名。</p>
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
              <span v-if="matchedUploadApp" class="hint">已选择应用：{{ matchedUploadApp.name }}</span>
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
              <span v-if="matchedUploadApp" class="hint">已选择应用：{{ matchedUploadApp.name }}</span>
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
            <p class="muted">按应用、状态、名称及时间范围筛选任务，快速查看处理进度。</p>
          </div>
        </header>

        <section class="card history-filters">
          <form class="filter-grid" @submit.prevent="applyFilters">
            <label>
              应用
              <select v-model="selectedAppId">
                <option value="">全部应用</option>
                <option v-for="app in applications" :key="`filter-app-${app.id}`" :value="String(app.id)">
                  {{ app.name }}
                </option>
              </select>
            </label>
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
              结束时间（起）
              <input v-model="endedStart" type="date" />
            </label>
            <label>
              结束时间（止）
              <input v-model="endedEnd" type="date" />
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
                <th>应用</th>
                <th>任务名称</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>结束时间</th>
                <th>摘要</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in tasks" :key="task.id">
                <td>{{ task.application?.name || '—' }}</td>
                <td class="task-title">
                  <div class="title-cell">
                    <span class="task-name">{{ task.title }}</span>
                    <span v-if="task.image_url" class="preview">
                      <img :src="task.image_url" alt="任务图片" />
                    </span>
                  </div>
                </td>
                <td>
                  <span class="status-badge" :class="task.status">{{ statusLabel(task.status) }}</span>
                </td>
                <td>{{ formatDate(task.created_at) }}</td>
                <td>{{ formatDate(task.ended_at) }}</td>
                <td class="summary">{{ task.summary || '—' }}</td>
                <td class="actions">
                  <router-link :to="`/tasks/${task.id}`" class="link">详情</router-link>
                  <button class="ghost" @click="openEditor(task)">编辑</button>
                  <button v-if="canCancel(task.status)" class="ghost" @click="cancelTask(task.id)">取消</button>
                  <button class="ghost" @click="deleteTask(task.id)">删除</button>
                </td>
              </tr>
              <tr v-if="!tasks.length">
                <td class="empty" colspan="7">暂无符合条件的任务</td>
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

      <template v-else>
        <header class="content-header">
          <div>
            <h1>应用管理</h1>
            <p class="muted">创建、重命名或删除应用，删除操作会同时移除该应用下的全部任务。</p>
          </div>
        </header>

        <section class="card app-form">
          <form @submit.prevent="createApplication">
            <input v-model="newApplicationName" type="text" placeholder="输入新应用名称" required />
            <button class="primary" type="submit">创建应用</button>
          </form>
        </section>

        <section class="card app-table">
          <table>
            <thead>
              <tr>
                <th>应用名称</th>
                <th>任务数量</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="app in applications" :key="`manage-app-${app.id}`">
                <td>{{ app.name }}</td>
                <td>{{ app.task_count }}</td>
                <td>{{ formatDate(app.created_at) }}</td>
                <td class="actions">
                  <button class="link" @click="renameApplication(app)">重命名</button>
                  <button class="ghost" @click="deleteApplication(app)">删除</button>
                </td>
              </tr>
              <tr v-if="!applications.length">
                <td class="empty" colspan="4">尚未创建任何应用</td>
              </tr>
            </tbody>
          </table>
        </section>
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
            <select v-model="editor.app_id">
              <option v-for="app in applications" :key="`editor-app-${app.id}`" :value="String(app.id)">
                {{ app.name }}
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

const creationMode = ref('upload');
const activeTab = ref('manage');

const showPassword = ref(false);
const passwordForm = reactive({ current_password: '', new_password: '' });
const passwordLoading = ref(false);
const passwordMessage = ref('');

const applications = ref([]);
const templates = ref([]);
const tasks = ref([]);
const pagination = reactive({ page: 1, pages: 1, total: 0 });

const title = ref('');
const applicationInput = ref('');
const selectedTemplateId = ref('');
const file = ref(null);
const uploading = ref(false);
const uploadMessage = ref('');

const metadataForm = reactive({
  summary: '',
  dataPointsText: '',
  tableDataText: ''
});

const selectedAppId = ref('');
const selectedGroupId = ref(null);
const selectedStatus = ref('');
const taskName = ref('');
const createdStart = ref('');
const createdEnd = ref('');
const endedStart = ref('');
const endedEnd = ref('');

const newApplicationName = ref('');

const editor = reactive({
  visible: false,
  taskId: null,
  title: '',
  app_id: '',
  template_id: ''
});

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'queued', label: '排队中' },
  { value: 'processing', label: '处理中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
  { value: 'cancelled', label: '已取消' }
];

const matchedUploadApp = computed(() => {
  const name = applicationInput.value.trim().toLowerCase();
  if (!name) return null;
  return applications.value.find((app) => app.name.toLowerCase() === name) || null;
});

const formatDate = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString();
};

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
      return status || '未知';
  }
};

const canCancel = (status) => ['queued', 'processing'].includes(status);

const setActiveTab = (tab) => {
  if (activeTab.value === tab) {
    if (tab === 'history') {
      loadTasks(1);
    } else if (tab === 'applications') {
      loadApplications();
    }
    return;
  }
  activeTab.value = tab;
  if (tab === 'history') {
    loadTasks(1);
  }
  if (tab === 'applications') {
    loadApplications();
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
    applications.value = data;
    if (selectedAppId.value) {
      const exists = data.some((app) => String(app.id) === selectedAppId.value);
      if (!exists) {
        selectedAppId.value = '';
      }
    }
    if (editor.visible) {
      const exists = data.some((app) => String(app.id) === editor.app_id);
      if (!exists && data.length) {
        editor.app_id = String(data[0].id);
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

const buildDateParam = (value, endOfDay = false) => {
  if (!value) return null;
  return endOfDay ? `${value}T23:59:59` : `${value}T00:00:00`;
};

const loadTasks = async (page = pagination.page) => {
  try {
    const params = { page };
    if (selectedAppId.value) params.app_id = Number(selectedAppId.value);
    if (selectedStatus.value) params.status = selectedStatus.value;
    if (taskName.value.trim()) params.task_name = taskName.value.trim();
    const createdFrom = buildDateParam(createdStart.value);
    const createdTo = buildDateParam(createdEnd.value, true);
    const endedFrom = buildDateParam(endedStart.value);
    const endedTo = buildDateParam(endedEnd.value, true);
    if (createdFrom) params.created_from = createdFrom;
    if (createdTo) params.created_to = createdTo;
    if (endedFrom) params.ended_from = endedFrom;
    if (endedTo) params.ended_to = endedTo;
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
  selectedAppId.value = '';
  selectedStatus.value = '';
  taskName.value = '';
  createdStart.value = '';
  createdEnd.value = '';
  endedStart.value = '';
  endedEnd.value = '';
};

const handleFile = (event) => {
  const [selected] = event.target.files || [];
  file.value = selected || null;
};

const submitTask = async () => {
  const trimmedTitle = title.value.trim();
  if (!trimmedTitle) {
    uploadMessage.value = '任务标题不能为空';
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
      formData.append('title', trimmedTitle);
      formData.append('file', file.value);
      if (selectedTemplateId.value) {
        formData.append('template_id', selectedTemplateId.value);
      }
      if (matchedUploadApp.value) {
        formData.append('application_id', String(matchedUploadApp.value.id));
      } else if (applicationInput.value.trim()) {
        formData.append('application_name', applicationInput.value.trim());
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
        title: trimmedTitle,
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
      if (matchedUploadApp.value) {
        payload.application_id = String(matchedUploadApp.value.id);
      } else if (applicationInput.value.trim()) {
        payload.application_name = applicationInput.value.trim();
      }

      await axios.post('/api/tasks', payload);
      uploadMessage.value = '已保存元数据任务，结果可直接查看。';
      metadataForm.summary = '';
      metadataForm.dataPointsText = '';
      metadataForm.tableDataText = '';
    }

    title.value = '';
    applicationInput.value = '';
    selectedTemplateId.value = '';
    await Promise.all([loadApplications(), loadTasks(1)]);
  } catch (error) {
    uploadMessage.value = error.response?.data?.message || error.message || '创建失败，请稍后再试。';
  } finally {
    uploading.value = false;
  }
};

const openEditor = (task) => {
  editor.visible = true;
  editor.taskId = task.id;
  editor.title = task.title;
  editor.app_id = task.app_id ? String(task.app_id) : (applications.value[0] ? String(applications.value[0].id) : '');
  editor.template_id = task.template?.id ? String(task.template.id) : '';
};

const closeEditor = () => {
  editor.visible = false;
  editor.taskId = null;
  editor.title = '';
  editor.app_id = '';
  editor.template_id = '';
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
    await Promise.all([loadTasks(), loadApplications()]);
  } catch (error) {
    window.alert(error.response?.data?.message || '取消失败');
  }
};

const deleteTask = async (taskId) => {
  if (!window.confirm('确认删除该任务？删除后不可恢复。')) return;
  try {
    await axios.delete(`/api/tasks/${taskId}`);
    await Promise.all([loadTasks(), loadApplications()]);
  } catch (error) {
    window.alert(error.response?.data?.message || '删除失败');
  }
};

const createApplication = async () => {
  const name = newApplicationName.value.trim();
  if (!name) return;
  try {
    await axios.post('/api/applications', { name });
    newApplicationName.value = '';
    await loadApplications();
    if (activeTab.value === 'history') {
      await loadTasks(1);
    }
  } catch (error) {
    window.alert(error.response?.data?.message || '创建失败');
  }
};

const renameApplication = async (app) => {
  const name = window.prompt('新的应用名称', app.name);
  if (!name || !name.trim()) return;
  try {
    await axios.patch(`/api/applications/${app.id}`, { name: name.trim() });
    await loadApplications();
    if (activeTab.value === 'history') {
      await loadTasks(1);
    }
  } catch (error) {
    window.alert(error.response?.data?.message || '重命名失败');
  }
};

const deleteApplication = async (app) => {
  if (!window.confirm(`确认删除应用「${app.name}」及其全部任务？`)) return;
  try {
    await axios.delete(`/api/applications/${app.id}`);
    if (selectedAppId.value === String(app.id)) {
      selectedAppId.value = '';
    }
    await loadApplications();
    if (activeTab.value === 'history') {
      await loadTasks(1);
    }
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

watch([selectedAppId, selectedStatus, createdStart, createdEnd, endedStart, endedEnd], () => {
  scheduleFilterLoad();
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
.filter-grid input,
.filter-grid select,
.dialog input,
.dialog select,
.app-form input {
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
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  padding: 12px;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.nav-item.active {
  background: #2563eb;
  color: #fff;
}

.nav-item:not(.active):hover {
  background: rgba(37, 99, 235, 0.16);
}

.sidebar-hint h3 {
  margin: 0 0 8px;
  font-size: 1.1rem;
  color: #1f2937;
}

.hint {
  color: #64748b;
  font-size: 0.85rem;
  margin-top: 8px;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.content-header h1 {
  margin: 0;
  font-size: 1.75rem;
  color: #1f2937;
}

.upload-form {
  display: grid;
  gap: 16px;
}

.upload-form textarea {
  width: 100%;
  min-height: 96px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 0.95rem;
  resize: vertical;
}

.file-input {
  display: block;
  border: 1px dashed #94a3b8;
  border-radius: 12px;
  padding: 12px;
  text-align: center;
  cursor: pointer;
  color: #2563eb;
  font-weight: 500;
}

.file-input input {
  display: none;
}

.history-filters {
  padding-bottom: 16px;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  align-items: end;
}

.mode-tabs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.mode-tab {
  border: 1px solid #d1d5db;
  background: #f8fafc;
  color: #1f2937;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 600;
}

.mode-tab.active {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.mode-tab:not(.active):hover {
  background: #e5edff;
}

.filter-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  color: #334155;
}

.filter-actions {
  display: flex;
  gap: 12px;
}

.history-table {
  overflow: hidden;
}

.task-table {
  width: 100%;
  border-collapse: collapse;
}

.task-table th,
.task-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: top;
}

.task-table thead th {
  background: #f8fafc;
  font-weight: 600;
  color: #1f2937;
}

.task-title {
  min-width: 220px;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-cell .task-name {
  font-weight: 600;
  color: #0f172a;
}

.title-cell .preview {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  border: 1px solid #e2e8f0;
}

.title-cell .preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.queued {
  background: rgba(59, 130, 246, 0.15);
  color: #1d4ed8;
}

.status-badge.processing {
  background: rgba(16, 185, 129, 0.15);
  color: #047857;
}

.status-badge.completed {
  background: rgba(99, 102, 241, 0.15);
  color: #4c1d95;
}

.status-badge.failed {
  background: rgba(239, 68, 68, 0.15);
  color: #b91c1c;
}

.status-badge.cancelled {
  background: rgba(148, 163, 184, 0.2);
  color: #475569;
}

.summary {
  max-width: 260px;
  color: #475569;
  font-size: 0.9rem;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.empty {
  text-align: center;
  color: #94a3b8;
  padding: 32px 0;
}

.pagination {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: center;
  color: #475569;
}

.app-form form {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.app-form button {
  flex-shrink: 0;
}

.app-table table {
  width: 100%;
  border-collapse: collapse;
}

.app-table th,
.app-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 50;
}

.dialog {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  width: min(420px, 100%);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
  display: grid;
  gap: 16px;
}

.dialog h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #1f2937;
}

.dialog label {
  display: grid;
  gap: 6px;
  font-size: 0.9rem;
  color: #334155;
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

  .content-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .sidebar {
    flex-direction: row;
    overflow-x: auto;
  }

  .sidebar > * {
    min-width: 260px;
  }
}
</style>
