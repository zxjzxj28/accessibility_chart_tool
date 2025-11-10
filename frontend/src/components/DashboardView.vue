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
      <div class="group-section">
        <div class="section-title">
          <h4>分组</h4>
          <button class="icon" @click="refreshGroups" title="刷新分组">⟳</button>
        </div>
        <div class="group-list">
          <button
            class="group-pill"
            :class="{ active: !selectedGroup }"
            @click="selectGroup(null)"
          >
            全部图表
          </button>
          <div v-for="group in flatGroups" :key="group.id" class="group-entry">
            <div class="group-entry-main">
              <button
                class="group-pill"
                :class="{ active: selectedGroup === group.id }"
                :style="{ paddingLeft: `${16 + group.depth * 14}px` }"
                @click="selectGroup(group.id)"
              >
                {{ group.name }}
              </button>
              <button class="icon" @click="startEditingGroup(group)" title="重命名">✎</button>
            </div>
            <div v-if="editingGroupId === group.id" class="group-edit">
              <input v-model="editingGroupName" type="text" required />
              <button type="button" class="primary" @click="submitGroupRename(group.id)">保存</button>
              <button type="button" class="ghost" @click="cancelGroupRename">取消</button>
            </div>
          </div>
        </div>
        <form class="group-form" @submit.prevent="createGroup">
          <input v-model="newGroupName" type="text" placeholder="新分组名称" required />
          <select v-model="parentForNewGroup">
            <option :value="null">无父级分组</option>
            <option v-for="group in flatGroups" :key="`parent-${group.id}`" :value="group.id">
              {{ group.indentedName }}
            </option>
          </select>
          <button type="submit" class="primary">添加</button>
        </form>
        <p v-if="groupMessage" class="info">{{ groupMessage }}</p>
      </div>
    </aside>
    <main class="content">
      <header class="content-header">
        <div>
          <h1>无障碍图表工作台</h1>
          <p>上传图表、生成无障碍代码片段，并集中管理所有转换任务。</p>
        </div>
        <button class="primary" @click="refreshTasks">刷新任务</button>
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
              指定分组
              <select v-model="selectedGroupForUpload">
                <option :value="null">不分组</option>
                <option v-for="group in flatGroups" :key="`upload-${group.id}`" :value="group.id">
                  {{ group.indentedName }}
                </option>
              </select>
            </label>
            <label>
              生成语言
              <select v-model="uploadLanguage">
                <option value="java">Java</option>
                <option value="kotlin">Kotlin</option>
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
              所属分组
              <select v-model="taskEditor.group_id">
                <option :value="null">未分组</option>
                <option v-for="group in flatGroups" :key="`edit-${group.id}`" :value="group.id">
                  {{ group.indentedName }}
                </option>
              </select>
            </label>
            <label>
              代码语言
              <select v-model="taskEditor.language">
                <option value="java">Java</option>
                <option value="kotlin">Kotlin</option>
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();
const router = useRouter();

const groupTree = ref([]);
const tasks = ref([]);
const selectedGroup = ref(null);
const selectedGroupForUpload = ref(null);
const newGroupName = ref('');
const parentForNewGroup = ref(null);
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
const uploadLanguage = ref('java');
const editingGroupId = ref(null);
const editingGroupName = ref('');
const taskEditorVisible = ref(false);
const taskEditorLoading = ref(false);
const taskEditorMessage = ref('');
const taskEditor = reactive({ id: null, title: '', group_id: null, language: 'java' });

const statusLabels = {
  pending: '排队中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

const getStatusLabel = (status) => statusLabels[status] || status;

const flatGroups = computed(() => {
  const result = [];
  const traverse = (items, depth = 0) => {
    items.forEach((item) => {
      const indent = depth > 0 ? `${'　'.repeat(depth - 1)}└ ` : '';
      const entry = {
        id: item.id,
        name: item.name,
        depth,
        indentedName: `${indent}${item.name}`
      };
      result.push(entry);
      if (item.children?.length) {
        traverse(item.children, depth + 1);
      }
    });
  };
  traverse(groupTree.value);
  return result;
});

const fetchTasks = async () => {
  const params = { page: pagination.page, page_size: pagination.pageSize };
  if (selectedGroup.value) {
    params.group_id = selectedGroup.value;
  }
  const { data } = await axios.get('/api/tasks', { params });
  tasks.value = data.items;
  pagination.page = data.page;
  pagination.pages = data.pages;
  pagination.total = data.total;
  pagination.pageSize = data.page_size;
};

const fetchGroups = async () => {
  const { data } = await axios.get('/api/groups');
  groupTree.value = data;
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
    await fetchGroups();
  } catch (err) {
    groupMessage.value = err.response?.data?.message || '无法获取分组列表。';
  }
};

const selectGroup = async (groupId) => {
  selectedGroup.value = groupId;
  pagination.page = 1;
  await refreshTasks();
};

const createGroup = async () => {
  if (!newGroupName.value.trim()) return;
  try {
    const payload = { name: newGroupName.value };
    if (parentForNewGroup.value) {
      payload.parent_id = parentForNewGroup.value;
    }
    await axios.post('/api/groups', payload);
    groupMessage.value = `已创建分组「${newGroupName.value}」。`;
    newGroupName.value = '';
    parentForNewGroup.value = null;
    await refreshGroups();
  } catch (err) {
    groupMessage.value = err.response?.data?.message || '无法创建分组。';
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
    await axios.patch(`/api/groups/${groupId}`, { name: editingGroupName.value });
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

const submitTask = async () => {
  if (!file.value) return;
  uploading.value = true;
  uploadMessage.value = '';
  try {
    const formData = new FormData();
    formData.append('image', file.value);
    formData.append('title', title.value);
    if (selectedGroupForUpload.value) {
      formData.append('group_id', selectedGroupForUpload.value);
    }
    formData.append('language', uploadLanguage.value);
    await axios.post('/api/tasks', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    uploadMessage.value = '任务已创建，后台将继续处理。';
    title.value = '';
    file.value = null;
    await refreshTasks();
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
  taskEditor.group_id = task.group_id ?? null;
  taskEditor.language = task.language || 'java';
  taskEditorVisible.value = true;
  taskEditorMessage.value = '';
};

const closeTaskEditor = () => {
  taskEditorVisible.value = false;
  taskEditor.id = null;
  taskEditor.title = '';
  taskEditor.group_id = null;
  taskEditor.language = 'java';
  taskEditorLoading.value = false;
};

const saveTaskEditor = async () => {
  if (!taskEditor.id) return;
  taskEditorLoading.value = true;
  taskEditorMessage.value = '';
  try {
    const payload = {
      title: taskEditor.title,
      group_id: taskEditor.group_id,
      language: taskEditor.language
    };
    await axios.patch(`/api/tasks/${taskEditor.id}`, payload);
    taskEditorMessage.value = '任务信息已更新。';
    await refreshTasks();
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
  await Promise.all([refreshGroups(), refreshTasks()]);
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

.group-section {
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

.group-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.group-entry {
  display: grid;
  gap: 6px;
  width: 100%;
}

.group-entry-main {
  display: flex;
  align-items: center;
  gap: 6px;
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

.group-pill {
  border: none;
  padding: 8px 14px;
  border-radius: 999px;
  background: #edf2ff;
  color: #364fc7;
  font-weight: 600;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.group-pill.active {
  background: linear-gradient(135deg, #4263eb, #5f3dc4);
  color: white;
  box-shadow: 0 10px 18px rgba(66, 99, 235, 0.25);
}

.group-pill:hover {
  transform: translateY(-1px);
}

.group-form {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.group-form input {
  flex: 1;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #d9e2ec;
}

.group-form select {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #d9e2ec;
  min-width: 140px;
  background: #f8fafc;
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
}

.content-header h1 {
  margin: 0 0 6px;
  color: #102a43;
}

.upload-card {
  background: white;
  padding: 28px;
  border-radius: 20px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 18px;
}

.upload-form {
  display: grid;
  gap: 16px;
}

.field-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

label {
  display: grid;
  gap: 8px;
  font-weight: 600;
  color: #243b53;
}

input,
select {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #d9e2ec;
  background: #f8fafc;
}

.file-input {
  position: relative;
  border: 2px dashed #9fb3c8;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  background: #f0f4ff;
  cursor: pointer;
}

.file-input input[type='file'] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.task-section {
  display: grid;
  gap: 18px;
}

.task-grid {
  display: grid;
  gap: 18px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.task-card {
  background: white;
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 12px;
}

.status {
  align-self: start;
  justify-self: start;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
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

.summary {
  color: #486581;
  font-size: 0.95rem;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.pagination button {
  min-width: 90px;
}

.empty {
  grid-column: 1 / -1;
  padding: 40px;
  text-align: center;
  color: #829ab1;
  border: 2px dashed #d9e2ec;
  border-radius: 18px;
  background: #f8fafc;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  width: min(420px, 90%);
  background: white;
  border-radius: 20px;
  padding: 28px;
  box-shadow: 0 25px 45px rgba(15, 23, 42, 0.2);
}

.modal h3 {
  margin-top: 0;
  color: #243b53;
}

.modal-form {
  display: grid;
  gap: 16px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.primary,
.secondary,
.ghost {
  border: none;
  border-radius: 12px;
  padding: 10px 16px;
  font-weight: 600;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.primary {
  background: linear-gradient(135deg, #4c6ef5, #5f3dc4);
  color: white;
}

.secondary {
  background: #edf2ff;
  color: #364fc7;
}

.ghost {
  background: #f8fafc;
  color: #334e68;
}

.ghost.danger {
  color: #e03131;
}

.primary:hover,
.secondary:hover,
.ghost:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(15, 23, 42, 0.1);
}

.icon {
  border: none;
  background: transparent;
  font-size: 1.1rem;
}

.info {
  color: #0f766e;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 1100px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
  .sidebar {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 20px;
  }
}
</style>
