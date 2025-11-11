<template>
  <div class="dashboard">
    <aside class="sidebar">
      <div class="logo">ACT 工作室</div>
      <div class="user-card">
        <h3>{{ auth.user?.name }}</h3>
        <p>{{ auth.user?.email }}</p>
        <button class="secondary" @click="showPassword = !showPassword">
          <span v-if="showPassword">收起修改密码</span>
          <span v-else>修改密码</span>
        </button>
        <transition name="fade">
          <form v-if="showPassword" class="password-form" @submit.prevent="updatePassword">
            <input v-model="passwordForm.current_password" type="password" placeholder="当前密码" required />
            <input v-model="passwordForm.new_password" type="password" placeholder="新密码" required />
            <button type="submit" class="primary" :disabled="passwordLoading">
              <span v-if="passwordLoading">正在更新...</span>
              <span v-else>确认修改</span>
            </button>
            <p v-if="passwordMessage" class="password-message">{{ passwordMessage }}</p>
          </form>
        </transition>
        <button class="ghost" @click="logout">退出登录</button>
      </div>

      <div class="application-section">
        <div class="section-title">
          <h4>应用与分组</h4>
          <button class="icon" @click="refreshGroups" title="刷新">⟳</button>
        </div>
        <p class="hint">右键应用或分组可以创建、重命名或删除。</p>
        <div class="filter-bar">
          <button
            class="group-pill"
            :class="{ active: !selectedApplicationId && !selectedGroupId }"
            @click="selectAllTasks"
          >
            全部任务
          </button>
        </div>
        <div class="application-list">
          <div
            v-for="app in applicationEntries"
            :key="app.id"
            class="application-entry"
          >
            <button
              class="app-pill"
              :class="{ active: selectedApplicationId === app.id && !selectedGroupId }"
              @click="selectApplication(app.id)"
              @contextmenu.prevent="openContextMenu($event, 'application', app)"
            >
              {{ app.name }}
            </button>
            <div
              v-if="app.flattenedGroups.length"
              class="group-stack"
            >
              <div
                v-for="group in app.flattenedGroups"
                :key="group.id"
                class="group-entry"
              >
                <div class="group-entry-main">
                  <button
                    class="group-pill"
                    :class="{ active: selectedGroupId === group.id }"
                    :style="{ paddingLeft: `${16 + group.depth * 14}px` }"
                    @click="selectGroup(app.id, group.id)"
                    @contextmenu.prevent="openContextMenu($event, 'group', { applicationId: app.id, group })"
                  >
                    {{ group.name }}
                  </button>
                  <button class="icon" @click="startEditingGroup(group)">✎</button>
                </div>
                <div v-if="editingGroupId === group.id" class="group-edit">
                  <input v-model="editingGroupName" type="text" required />
                  <button type="button" class="primary" @click="submitGroupRename(group.id)">保存</button>
                  <button type="button" class="ghost" @click="cancelGroupRename">取消</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <p v-if="groupMessage" class="info">{{ groupMessage }}</p>
      </div>
    </aside>

    <main class="content">
      <header class="content-header">
        <div>
          <h1>无障碍图表工作台</h1>
          <p>上传图表、生成无障碍代码片段，并集中管理所有转换任务。</p>
        </div>
        <div class="header-actions">
          <input
            v-model="taskSearch"
            type="search"
            placeholder="按关键字检索任务"
            @keyup.enter="refreshTasks"
          />
          <router-link class="secondary" to="/templates">模板管理</router-link>
          <button class="primary" @click="refreshTasks">刷新任务</button>
        </div>
      </header>

      <section class="upload-card">
        <h2>上传新的图表</h2>
        <p>支持 PNG、JPG，文件大小不超过 16MB。</p>
        <form @submit.prevent="submitTask" class="upload-form">
          <div class="field-grid">
            <label>
              图表标题
              <input v-model="title" type="text" placeholder="示例：一季度营销漏斗" required />
            </label>
            <label>
              所属应用
              <div class="combo-field">
                <input
                  v-model="applicationInput"
                  type="text"
                  list="application-options"
                  placeholder="留空则使用默认应用，或直接输入新应用名称"
                />
                <datalist id="application-options">
                  <option v-for="app in applications" :key="`option-app-${app.id}`" :value="app.name"></option>
                </datalist>
              </div>
            </label>
            <label>
              指定分组
              <select v-model="selectedGroupForUpload" :disabled="!uploadGroups.length">
                <option value="">不分组</option>
                <option v-for="group in uploadGroups" :key="`upload-group-${group.id}`" :value="String(group.id)">
                  {{ group.indentedName }}
                </option>
              </select>
            </label>
            <label>
              代码模板
              <select v-model="selectedTemplateId">
                <option value="">使用默认模板</option>
                <option v-for="template in templates" :key="`tpl-${template.id}`" :value="String(template.id)">
                  {{ templateLabel(template) }}
                </option>
              </select>
            </label>
          </div>
          <label class="file-input">
            <span v-if="!file">选择图表图片</span>
            <span v-else>{{ file.name }}</span>
            <input type="file" accept="image/*" @change="handleFile" required />
          </label>
          <button type="submit" class="primary" :disabled="uploading">
            <span v-if="uploading">正在上传...</span>
            <span v-else>开始转换</span>
          </button>
        </form>
        <p v-if="uploadMessage" class="info">{{ uploadMessage }}</p>
      </section>

      <section class="task-section">
        <h2>最新任务</h2>
        <p v-if="taskMessage" class="info">{{ taskMessage }}</p>
        <div class="task-grid">
          <article v-for="task in tasks" :key="task.id" class="task-card">
            <div class="status" :class="task.status">{{ getStatusLabel(task.status) }}</div>
            <h3>{{ task.title }}</h3>
            <p class="meta">应用：{{ task.application?.name || '未指定' }}</p>
            <p class="timestamp">创建于 {{ formatDate(task.created_at) }}</p>
            <p v-if="task.summary" class="summary">{{ task.summary }}</p>
            <div class="actions">
              <router-link :to="`/tasks/${task.id}`" class="primary">查看详情</router-link>
              <button v-if="canCancel(task.status)" class="ghost" @click="cancelTask(task.id)">取消任务</button>
              <button class="ghost" @click="openTaskEditor(task)">编辑信息</button>
            </div>
          </article>
          <div v-if="!tasks.length" class="empty">暂无任务，请上传图表开始体验。</div>
        </div>
        <div class="pagination" v-if="pagination.pages > 1">
          <button class="ghost" :disabled="pagination.page === 1" @click="changePage(pagination.page - 1)">上一页</button>
          <span>第 {{ pagination.page }} / {{ pagination.pages }} 页，共 {{ pagination.total }} 条</span>
          <button class="ghost" :disabled="pagination.page === pagination.pages" @click="changePage(pagination.page + 1)">下一页</button>
        </div>
      </section>
    </main>

    <transition name="fade">
      <div v-if="taskEditorVisible" class="modal-backdrop">
        <div class="modal">
          <h3>编辑任务</h3>
          <form @submit.prevent="saveTaskEditor" class="modal-form">
            <label>
              任务名称
              <input v-model="taskEditor.title" type="text" required />
            </label>
            <label>
              所属应用
              <select v-model="taskEditor.application_id" @change="onTaskEditorApplicationChange">
                <option v-for="app in applications" :key="`edit-app-${app.id}`" :value="String(app.id)">
                  {{ app.name }}
                </option>
              </select>
            </label>
            <label>
              所属分组
              <select v-model="taskEditor.group_id">
                <option value="">未分组</option>
                <option v-for="group in editorGroups" :key="`edit-group-${group.id}`" :value="String(group.id)">
                  {{ group.indentedName }}
                </option>
              </select>
            </label>
            <label>
              默认模板
              <select v-model="taskEditor.template_id">
                <option value="">无（保留当前模板设置）</option>
                <option v-for="template in templates" :key="`edit-tpl-${template.id}`" :value="String(template.id)">
                  {{ templateLabel(template) }}
                </option>
              </select>
            </label>
            <div class="modal-actions">
              <button type="submit" class="primary" :disabled="taskEditorLoading">保存</button>
              <button type="button" class="ghost" @click="closeTaskEditor">取消</button>
            </div>
            <p v-if="taskEditorMessage" class="info">{{ taskEditorMessage }}</p>
          </form>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <ul
        v-if="contextMenu.visible"
        class="context-menu"
        :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
      >
        <li v-for="option in contextOptions" :key="option.key" @click="handleContextAction(option.key)">
          {{ option.label }}
        </li>
      </ul>
    </transition>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();
const router = useRouter();

const applications = ref([]);
const templates = ref([]);
const tasks = ref([]);

const selectedApplicationId = ref(null);
const selectedGroupId = ref(null);
const applicationInput = ref('');
const selectedGroupForUpload = ref('');
const selectedTemplateId = ref('');
const taskSearch = ref('');

const groupMessage = ref('');
const uploadMessage = ref('');
const taskMessage = ref('');
const title = ref('');
const file = ref(null);
const uploading = ref(false);

const showPassword = ref(false);
const passwordLoading = ref(false);
const passwordMessage = ref('');
const passwordForm = reactive({ current_password: '', new_password: '' });

const pagination = reactive({ page: 1, pages: 1, total: 0, pageSize: 10 });

const editingGroupId = ref(null);
const editingGroupName = ref('');

const taskEditorVisible = ref(false);
const taskEditorLoading = ref(false);
const taskEditorMessage = ref('');
const taskEditor = reactive({ id: null, title: '', application_id: '', group_id: '', template_id: '' });

const contextMenu = reactive({ visible: false, x: 0, y: 0, type: null, target: null });

const statusLabels = {
  pending: '排队中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消'
};

function buildFlattenedGroups(groups = []) {
  const result = [];
  const traverse = (items, depth = 0) => {
    items.forEach((item) => {
      const indent = depth > 0 ? `${'　'.repeat(depth - 1)}└ ` : '';
      result.push({
        id: item.id,
        name: item.name,
        depth,
        application_id: item.application_id,
        indentedName: `${indent}${item.name}`,
        children: item.children || []
      });
      if (item.children && item.children.length) {
        traverse(item.children, depth + 1);
      }
    });
  };
  traverse(groups, 0);
  return result;
}

function hasGroup(groups = [], targetId) {
  for (const group of groups) {
    if (group.id === targetId) {
      return true;
    }
    if (group.children && hasGroup(group.children, targetId)) {
      return true;
    }
  }
  return false;
}

const applicationEntries = computed(() =>
  applications.value.map((app) => ({
    ...app,
    flattenedGroups: buildFlattenedGroups(app.groups || [])
  }))
);

const selectedApplication = computed(() => {
  if (!selectedApplicationId.value) return null;
  return applications.value.find((app) => app.id === selectedApplicationId.value) || null;
});

const currentGroups = computed(() => {
  if (!selectedApplication.value) return [];
  return buildFlattenedGroups(selectedApplication.value.groups || []);
});

const matchedUploadApplication = computed(() => {
  const name = applicationInput.value.trim();
  if (!name) return null;
  return applications.value.find((app) => app.name === name) || null;
});

const uploadGroups = computed(() => {
  const match = matchedUploadApplication.value;
  if (!match) return [];
  return buildFlattenedGroups(match.groups || []);
});

const editorGroups = computed(() => {
  if (!taskEditor.application_id) return [];
  const appId = Number(taskEditor.application_id);
  const app = applications.value.find((item) => item.id === appId);
  if (!app) return [];
  return buildFlattenedGroups(app.groups || []);
});

const contextOptions = computed(() => {
  if (!contextMenu.visible) return [];
  if (contextMenu.type === 'application') {
    return [{ key: 'create', label: '新建分组' }];
  }
  if (contextMenu.type === 'group') {
    return [
      { key: 'create', label: '新建子分组' },
      { key: 'rename', label: '重命名分组' },
      { key: 'delete', label: '删除分组' }
    ];
  }
  return [];
});

const templateLabel = (template) => `${template.name} · ${template.language.toUpperCase()}`;

const getStatusLabel = (status) => statusLabels[status] || status;

const ensureTemplateSelections = () => {
  if (selectedTemplateId.value && !templates.value.some((tpl) => String(tpl.id) === selectedTemplateId.value)) {
    selectedTemplateId.value = templates.value.length ? String(templates.value[0].id) : '';
  }
  if (taskEditor.template_id && !templates.value.some((tpl) => String(tpl.id) === taskEditor.template_id)) {
    taskEditor.template_id = '';
  }
};

const fetchApplications = async () => {
  const { data } = await axios.get('/api/applications');
  applications.value = data;
  if (applications.value.length === 0) {
    selectedApplicationId.value = null;
  } else if (
    selectedApplicationId.value &&
    !applications.value.some((app) => app.id === selectedApplicationId.value)
  ) {
    selectedApplicationId.value = applications.value[0].id;
  }
  if (selectedGroupId.value) {
    const exists = applications.value.some((app) => hasGroup(app.groups || [], selectedGroupId.value));
    if (!exists) {
      selectedGroupId.value = null;
    }
  }
};

const fetchTemplates = async () => {
  const { data } = await axios.get('/api/templates');
  templates.value = data.items;
  if (!selectedTemplateId.value && templates.value.length) {
    const systemJava = templates.value.find((tpl) => tpl.is_system && tpl.language === 'java');
    selectedTemplateId.value = systemJava ? String(systemJava.id) : String(templates.value[0].id);
  }
  ensureTemplateSelections();
};

const fetchTasks = async () => {
  const params = { page: pagination.page, page_size: pagination.pageSize };
  if (selectedApplicationId.value) {
    params.application_id = selectedApplicationId.value;
  }
  if (selectedGroupId.value) {
    params.group_id = selectedGroupId.value;
  }
  if (taskSearch.value.trim()) {
    params.q = taskSearch.value.trim();
  }
  const { data } = await axios.get('/api/tasks', { params });
  tasks.value = data.items;
  pagination.page = data.page;
  pagination.pages = data.pages;
  pagination.total = data.total;
  pagination.pageSize = data.page_size;
};

const refreshTasks = async () => {
  try {
    await fetchTasks();
    taskMessage.value = '';
  } catch (err) {
    taskMessage.value = err.response?.data?.message || '无法获取任务列表。';
  }
};

const refreshGroups = async () => {
  try {
    await fetchApplications();
    groupMessage.value = '';
  } catch (err) {
    groupMessage.value = err.response?.data?.message || '无法获取应用和分组信息。';
  }
};

const selectAllTasks = async () => {
  selectedApplicationId.value = null;
  selectedGroupId.value = null;
  pagination.page = 1;
  await refreshTasks();
};

const selectApplication = async (applicationId) => {
  selectedApplicationId.value = applicationId;
  selectedGroupId.value = null;
  pagination.page = 1;
  await refreshTasks();
};

const selectGroup = async (applicationId, groupId) => {
  selectedApplicationId.value = applicationId;
  selectedGroupId.value = groupId;
  pagination.page = 1;
  await refreshTasks();
};

const openContextMenu = (event, type, payload) => {
  event.preventDefault();
  contextMenu.visible = true;
  contextMenu.x = event.clientX;
  contextMenu.y = event.clientY;
  contextMenu.type = type;
  contextMenu.target = payload;
};

const closeContextMenu = () => {
  contextMenu.visible = false;
  contextMenu.type = null;
  contextMenu.target = null;
};

const promptCreateGroup = async (applicationId, parentId = null) => {
  const name = window.prompt('请输入新的分组名称');
  if (!name || !name.trim()) {
    return;
  }
  try {
    const payload = { name: name.trim(), application_id: applicationId };
    if (parentId) {
      payload.parent_id = parentId;
    }
    await axios.post('/api/groups', payload);
    groupMessage.value = `已创建分组「${name.trim()}」。`;
    await refreshGroups();
  } catch (err) {
    groupMessage.value = err.response?.data?.message || '无法创建分组。';
  }
};

const deleteGroup = async (groupId) => {
  const confirmed = window.confirm('删除该分组会清除其下所有任务，是否继续？');
  if (!confirmed) return;
  try {
    await axios.delete(`/api/groups/${groupId}`);
    groupMessage.value = '分组已删除。';
    if (selectedGroupId.value === groupId) {
      selectedGroupId.value = null;
    }
    await Promise.all([refreshGroups(), refreshTasks()]);
  } catch (err) {
    groupMessage.value = err.response?.data?.message || '无法删除分组。';
  }
};

const handleContextAction = async (action) => {
  const target = contextMenu.target;
  const type = contextMenu.type;
  closeContextMenu();
  if (!target) return;
  if (type === 'application') {
    if (action === 'create') {
      await promptCreateGroup(target.id, null);
    }
    return;
  }
  if (type === 'group') {
    if (action === 'create') {
      await promptCreateGroup(target.applicationId, target.group.id);
    } else if (action === 'rename') {
      startEditingGroup(target.group);
    } else if (action === 'delete') {
      await deleteGroup(target.group.id);
    }
  }
};

const startEditingGroup = (group) => {
  editingGroupId.value = group.id;
  editingGroupName.value = group.name;
};

const cancelGroupRename = () => {
  editingGroupId.value = null;
  editingGroupName.value = '';
};

const submitGroupRename = async (groupId) => {
  if (!editingGroupName.value.trim()) {
    groupMessage.value = '分组名称不能为空。';
    return;
  }
  try {
    await axios.patch(`/api/groups/${groupId}`, { name: editingGroupName.value.trim() });
    groupMessage.value = '分组名称已更新。';
    await refreshGroups();
  } catch (err) {
    groupMessage.value = err.response?.data?.message || '无法更新分组名称。';
  } finally {
    cancelGroupRename();
  }
};

const handleFile = (event) => {
  const [selected] = event.target.files;
  file.value = selected || null;
};

watch(applicationInput, () => {
  selectedGroupForUpload.value = '';
});

const submitTask = async () => {
  if (!file.value) return;
  uploading.value = true;
  uploadMessage.value = '';
  try {
    const formData = new FormData();
    formData.append('image', file.value);
    formData.append('title', title.value);
    const match = matchedUploadApplication.value;
    const trimmedName = applicationInput.value.trim();
    if (match) {
      formData.append('application_id', String(match.id));
    } else if (trimmedName) {
      formData.append('application_name', trimmedName);
    }
    if (selectedGroupForUpload.value && match) {
      formData.append('group_id', selectedGroupForUpload.value);
    }
    if (selectedTemplateId.value) {
      formData.append('template_id', selectedTemplateId.value);
    }
    await axios.post('/api/tasks', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    uploadMessage.value = '任务已创建，后台将继续处理。';
    title.value = '';
    file.value = null;
    if (!match && trimmedName) {
      applicationInput.value = trimmedName;
    } else if (match) {
      applicationInput.value = match.name;
    } else {
      applicationInput.value = '';
    }
    selectedGroupForUpload.value = '';
    selectedTemplateId.value = '';
    await Promise.all([refreshTasks(), refreshGroups()]);
  } catch (err) {
    uploadMessage.value = err.response?.data?.message || '无法创建任务。';
  } finally {
    uploading.value = false;
  }
};

const cancelTask = async (taskId) => {
  try {
    await axios.post(`/api/tasks/${taskId}/cancel`);
    taskMessage.value = '任务已取消。';
    await refreshTasks();
  } catch (err) {
    taskMessage.value = err.response?.data?.message || '无法取消任务。';
  }
};

const canCancel = (status) => ['pending', 'processing'].includes(status);

const formatDate = (iso) => new Date(iso).toLocaleString();

const logout = () => {
  auth.logout();
  router.push('/login');
};

const openTaskEditor = (task) => {
  taskEditor.id = task.id;
  taskEditor.title = task.title;
  taskEditor.application_id = task.application_id ? String(task.application_id) : (applications.value[0] ? String(applications.value[0].id) : '');
  taskEditor.group_id = task.group_id ? String(task.group_id) : '';
  taskEditor.template_id = task.template_id ? String(task.template_id) : '';
  taskEditorVisible.value = true;
  taskEditorMessage.value = '';
};

const closeTaskEditor = () => {
  taskEditorVisible.value = false;
  taskEditor.id = null;
  taskEditor.title = '';
  taskEditor.application_id = applications.value[0] ? String(applications.value[0].id) : '';
  taskEditor.group_id = '';
  taskEditor.template_id = '';
  taskEditorLoading.value = false;
};

const onTaskEditorApplicationChange = () => {
  taskEditor.group_id = '';
};

const saveTaskEditor = async () => {
  if (!taskEditor.id) return;
  taskEditorLoading.value = true;
  taskEditorMessage.value = '';
  try {
    const applicationId = Number(taskEditor.application_id);
    if (!applicationId) {
      taskEditorMessage.value = '请选择应用。';
      taskEditorLoading.value = false;
      return;
    }
    const payload = {
      title: taskEditor.title,
      application_id: applicationId
    };
    payload.group_id = taskEditor.group_id ? Number(taskEditor.group_id) : '';
    payload.template_id = taskEditor.template_id ? Number(taskEditor.template_id) : '';
    await axios.patch(`/api/tasks/${taskEditor.id}`, payload);
    taskEditorMessage.value = '任务信息已更新。';
    await Promise.all([refreshTasks(), refreshGroups()]);
    setTimeout(() => {
      closeTaskEditor();
    }, 500);
  } catch (err) {
    taskEditorMessage.value = err.response?.data?.message || '无法更新任务信息。';
  } finally {
    taskEditorLoading.value = false;
  }
};

const changePage = async (target) => {
  pagination.page = target;
  await refreshTasks();
};

const updatePassword = async () => {
  passwordLoading.value = true;
  passwordMessage.value = '';
  try {
    await auth.changePassword(passwordForm);
    passwordMessage.value = '密码修改成功。';
    passwordForm.current_password = '';
    passwordForm.new_password = '';
  } catch (err) {
    passwordMessage.value = err.response?.data?.message || '无法修改密码。';
  } finally {
    passwordLoading.value = false;
  }
};

onMounted(async () => {
  window.addEventListener('click', closeContextMenu);
  await Promise.all([fetchTemplates(), refreshGroups(), refreshTasks()]);
});

onBeforeUnmount(() => {
  window.removeEventListener('click', closeContextMenu);
});
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 320px 1fr;
  background: #f4f6fb;
}

.sidebar {
  background: white;
  border-right: 1px solid #e5e9f2;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 32px;
  position: relative;
}

.logo {
  font-weight: 700;
  font-size: 1.4rem;
  color: #334e68;
}

.user-card {
  background: linear-gradient(160deg, #f5f7ff 0%, #fff 100%);
  border-radius: 18px;
  padding: 20px;
  display: grid;
  gap: 12px;
  box-shadow: inset 0 0 0 1px rgba(76, 110, 245, 0.1);
}

.user-card button {
  width: 100%;
}

.password-form {
  display: grid;
  gap: 10px;
}

.password-form input {
  padding: 10px 12px;
  border: 1px solid #dfe3ec;
  border-radius: 10px;
}

.password-message {
  font-size: 0.85rem;
  color: #0b7285;
}

.application-section {
  display: grid;
  gap: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title h4 {
  margin: 0;
  color: #243b53;
}

.hint {
  margin: 0;
  font-size: 0.85rem;
  color: #829ab1;
}

.application-list {
  display: grid;
  gap: 10px;
}

.application-entry {
  display: grid;
  gap: 6px;
}

.app-pill {
  border: none;
  padding: 10px 16px;
  border-radius: 14px;
  background: #f1f4ff;
  color: #2f52d1;
  font-weight: 600;
  text-align: left;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.app-pill.active {
  background: linear-gradient(135deg, #4263eb, #5f3dc4);
  color: white;
  box-shadow: 0 10px 18px rgba(66, 99, 235, 0.25);
}

.app-pill:hover {
  transform: translateY(-1px);
}

.group-stack {
  display: grid;
  gap: 6px;
}

.group-entry {
  display: grid;
  gap: 6px;
}

.group-entry-main {
  display: flex;
  align-items: center;
  gap: 6px;
}

.group-pill {
  border: none;
  padding: 8px 14px;
  border-radius: 999px;
  background: #edf2ff;
  color: #364fc7;
  font-weight: 600;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  text-align: left;
  width: 100%;
}

.group-pill.active {
  background: linear-gradient(135deg, #4263eb, #5f3dc4);
  color: white;
  box-shadow: 0 10px 18px rgba(66, 99, 235, 0.25);
}

.group-pill:hover {
  transform: translateY(-1px);
}

.group-entry .icon {
  border: none;
  background: transparent;
  color: #5f6c7b;
  font-size: 0.9rem;
  padding: 6px;
}

.group-entry .icon:hover {
  color: #364fc7;
}

.group-edit {
  display: flex;
  gap: 6px;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.info {
  color: #0f766e;
  margin: 0;
}

.content {
  padding: 40px 48px;
  display: grid;
  gap: 32px;
}

.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.content-header h1 {
  margin: 0 0 6px;
  color: #102a43;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.header-actions input {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #d9e2ec;
  min-width: 240px;
}

.upload-card {
  background: white;
  border-radius: 24px;
  padding: 28px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 18px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.field-grid label {
  display: grid;
  gap: 8px;
  font-weight: 600;
  color: #243b53;
}

.combo-field {
  display: flex;
  flex-direction: column;
}

.combo-field input {
  width: 100%;
}

.field-grid input,
.field-grid select {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #d9e2ec;
  background: #f8fafc;
}

.file-input {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 14px 18px;
  border: 1px dashed #9fb3c8;
  border-radius: 16px;
  cursor: pointer;
  color: #486581;
}

.file-input input {
  display: none;
}

.task-section {
  display: grid;
  gap: 18px;
}

.template-card {
  background: white;
  border-radius: 24px;
  padding: 28px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 20px;
}

.template-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 20px;
}

.template-sidebar {
  display: grid;
  gap: 16px;
}

.template-group {
  background: #f8faff;
  border-radius: 16px;
  padding: 12px;
  display: grid;
  gap: 12px;
}

.template-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.template-group-header h3 {
  margin: 0;
  font-size: 1rem;
  color: #243b53;
}

.template-group-header .icon {
  border: none;
  background: transparent;
  color: #5f6c7b;
  font-size: 1.1rem;
}

.template-group-header .icon:hover {
  color: #364fc7;
}

.template-group ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.template-group ul li button {
  width: 100%;
  text-align: left;
  padding: 8px 12px;
  border-radius: 10px;
  border: none;
  background: #fff;
  color: #364fc7;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.template-group ul li button.active {
  background: linear-gradient(135deg, #4c6ef5, #5f3dc4);
  color: white;
}

.template-group ul li.empty {
  font-size: 0.85rem;
  color: #829ab1;
}

.template-editor {
  background: #f9fbff;
  border-radius: 20px;
  padding: 18px;
}

.template-form {
  display: grid;
  gap: 16px;
}

.editor-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.template-form label {
  display: grid;
  gap: 8px;
  font-weight: 600;
  color: #243b53;
}

.template-form input,
.template-form select,
.template-form textarea {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #d9e2ec;
  background: #fff;
}

.template-form textarea {
  min-height: 200px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.copy-control .copy-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.template-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.tag {
  background: rgba(76, 110, 245, 0.12);
  color: #3b5bdb;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.75rem;
}

.task-grid {
  display: grid;
  gap: 18px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.task-card {
  background: white;
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 12px;
}

.task-card h3 {
  margin: 0;
  color: #102a43;
}

.task-card .meta {
  margin: 0;
  color: #486581;
  font-size: 0.9rem;
}

.summary {
  margin: 0;
  color: #51616f;
}

.timestamp {
  margin: 0;
  color: #829ab1;
  font-size: 0.85rem;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.empty {
  text-align: center;
  color: #829ab1;
  padding: 40px 0;
  grid-column: 1 / -1;
}

.pagination {
  display: flex;
  justify-content: center;
  gap: 12px;
  align-items: center;
  font-weight: 600;
  color: #486581;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 30;
}

.modal {
  background: white;
  border-radius: 24px;
  padding: 28px;
  width: min(520px, 90vw);
  display: grid;
  gap: 18px;
}

.modal-form {
  display: grid;
  gap: 16px;
}

.modal-form label {
  display: grid;
  gap: 6px;
}

.modal-form input,
.modal-form select {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #d9e2ec;
  background: #f8fafc;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.context-menu {
  position: fixed;
  z-index: 40;
  list-style: none;
  margin: 0;
  padding: 8px 0;
  background: white;
  border: 1px solid #d9e2ec;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
  min-width: 160px;
}

.context-menu li {
  padding: 8px 16px;
  cursor: pointer;
  color: #243b53;
}

.context-menu li:hover {
  background: #eef2ff;
  color: #3b5bdb;
}

button.primary,
button.secondary,
button.ghost {
  border: none;
  border-radius: 12px;
  padding: 10px 18px;
  font-weight: 600;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

button.primary {
  background: linear-gradient(135deg, #4c6ef5, #5f3dc4);
  color: white;
}

button.secondary {
  background: #f1f5f9;
  color: #3b5bdb;
}

button.ghost {
  background: #f8fafc;
  color: #486581;
}

button.primary:hover,
button.secondary:hover,
button.ghost:hover {
  transform: translateY(-1px);
}

.status {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
}

.status.pending {
  background: #fff7e6;
  color: #f59f00;
}

.status.processing {
  background: #e7f5ff;
  color: #1c7ed6;
}

.status.completed {
  background: #ebfbee;
  color: #2f9e44;
}

.status.failed {
  background: #fff5f5;
  color: #e03131;
}

.status.cancelled {
  background: #f1f3f5;
  color: #868e96;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
