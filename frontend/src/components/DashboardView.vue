<template>
  <div class="dashboard">
    <aside class="sidebar">
      <div class="logo">ACT Studio</div>
      <div class="user-card">
        <h3>{{ auth.user?.name }}</h3>
        <p>{{ auth.user?.email }}</p>
        <button class="secondary" @click="showPassword = !showPassword">
          <span v-if="showPassword">Close password panel</span>
          <span v-else>Change password</span>
        </button>
        <transition name="fade">
          <form v-if="showPassword" class="password-form" @submit.prevent="updatePassword">
            <input v-model="passwordForm.current_password" type="password" placeholder="Current password" required />
            <input v-model="passwordForm.new_password" type="password" placeholder="New password" required />
            <button type="submit" class="primary" :disabled="passwordLoading">
              <span v-if="passwordLoading">Updating...</span>
              <span v-else>Update password</span>
            </button>
            <p v-if="passwordMessage" class="password-message">{{ passwordMessage }}</p>
          </form>
        </transition>
        <button class="ghost" @click="logout">Log out</button>
      </div>
      <div class="group-section">
        <div class="section-title">
          <h4>Groups</h4>
          <button class="icon" @click="refreshGroups" title="Refresh groups">⟳</button>
        </div>
        <div class="group-list">
          <button
            class="group-pill"
            :class="{ active: !selectedGroup }"
            @click="selectGroup(null)"
          >
            All charts
          </button>
          <button
            v-for="group in groups"
            :key="group.id"
            class="group-pill"
            :class="{ active: selectedGroup === group.id }"
            @click="selectGroup(group.id)"
          >
            {{ group.name }}
          </button>
        </div>
        <form class="group-form" @submit.prevent="createGroup">
          <input v-model="newGroupName" type="text" placeholder="New group name" required />
          <button type="submit" class="primary">Add</button>
        </form>
        <p v-if="groupMessage" class="info">{{ groupMessage }}</p>
      </div>
    </aside>
    <main class="content">
      <header class="content-header">
        <div>
          <h1>Accessible chart workspace</h1>
          <p>Upload charts, generate accessible code snippets, and manage your conversion tasks.</p>
        </div>
        <button class="primary" @click="refreshTasks">Refresh tasks</button>
      </header>

      <section class="upload-card">
        <h2>Upload a new chart</h2>
        <p>Supported formats: PNG, JPG. Maximum size 16MB.</p>
        <form @submit.prevent="submitTask" class="upload-form">
          <div class="field-grid">
            <label>
              Chart title
              <input v-model="title" type="text" placeholder="Marketing funnel Q1" required />
            </label>
            <label>
              Assign to group
              <select v-model="selectedGroupForUpload">
                <option :value="null">No group</option>
                <option v-for="group in groups" :key="group.id" :value="group.id">{{ group.name }}</option>
              </select>
            </label>
          </div>
          <label class="file-input">
            <span v-if="!file">Select chart image</span>
            <span v-else>{{ file.name }}</span>
            <input type="file" accept="image/*" @change="handleFile" required />
          </label>
          <button type="submit" class="primary" :disabled="uploading">
            <span v-if="uploading">Uploading...</span>
            <span v-else>Start conversion</span>
          </button>
        </form>
        <p v-if="uploadMessage" class="info">{{ uploadMessage }}</p>
      </section>

      <section class="task-section">
        <h2>Recent tasks</h2>
        <p v-if="taskMessage" class="info">{{ taskMessage }}</p>
        <div class="task-grid">
          <article v-for="task in tasks" :key="task.id" class="task-card">
            <div class="status" :class="task.status">{{ task.status }}</div>
            <h3>{{ task.title }}</h3>
            <p class="timestamp">Created {{ formatDate(task.created_at) }}</p>
            <p v-if="task.summary" class="summary">{{ task.summary }}</p>
            <div class="actions">
              <router-link :to="`/tasks/${task.id}`" class="primary">Open detail</router-link>
              <button v-if="canCancel(task.status)" class="ghost" @click="cancelTask(task.id)">Cancel</button>
              <button class="ghost danger" @click="deleteTask(task.id)">Delete</button>
            </div>
          </article>
          <div v-if="!tasks.length" class="empty">No tasks found. Upload a chart to get started.</div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { useAuthStore } from '../stores/auth';

const auth = useAuthStore();
const router = useRouter();

const groups = ref([]);
const tasks = ref([]);
const selectedGroup = ref(null);
const selectedGroupForUpload = ref(null);
const newGroupName = ref('');
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

const fetchTasks = async () => {
  const params = selectedGroup.value ? { group_id: selectedGroup.value } : {};
  const { data } = await axios.get('/api/tasks', { params });
  tasks.value = data;
};

const fetchGroups = async () => {
  const { data } = await axios.get('/api/groups');
  groups.value = data;
};

const refreshTasks = async () => {
  try {
    await fetchTasks();
    taskMessage.value = '';
  } catch (err) {
    taskMessage.value = err.response?.data?.message || 'Unable to fetch tasks.';
  }
};

const refreshGroups = async () => {
  try {
    await fetchGroups();
  } catch (err) {
    groupMessage.value = err.response?.data?.message || 'Unable to fetch groups.';
  }
};

const selectGroup = async (groupId) => {
  selectedGroup.value = groupId;
  await refreshTasks();
};

const createGroup = async () => {
  if (!newGroupName.value.trim()) return;
  try {
    const { data } = await axios.post('/api/groups', { name: newGroupName.value });
    groups.value.unshift(data);
    groupMessage.value = `Group "${data.name}" created.`;
    newGroupName.value = '';
  } catch (err) {
    groupMessage.value = err.response?.data?.message || 'Unable to create group.';
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
    await axios.post('/api/tasks', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    uploadMessage.value = 'Task created. Processing will continue in the background.';
    title.value = '';
    file.value = null;
    await refreshTasks();
  } catch (err) {
    uploadMessage.value = err.response?.data?.message || 'Unable to create task.';
  } finally {
    uploading.value = false;
  }
};

const cancelTask = async (taskId) => {
  try {
    await axios.post(`/api/tasks/${taskId}/cancel`);
    taskMessage.value = 'Task cancelled.';
    await refreshTasks();
  } catch (err) {
    taskMessage.value = err.response?.data?.message || 'Unable to cancel task.';
  }
};

const deleteTask = async (taskId) => {
  try {
    await axios.delete(`/api/tasks/${taskId}`);
    taskMessage.value = 'Task deleted.';
    await refreshTasks();
  } catch (err) {
    taskMessage.value = err.response?.data?.message || 'Unable to delete task.';
  }
};

const canCancel = (status) => ['pending', 'processing'].includes(status);

const formatDate = (iso) => new Date(iso).toLocaleString();

const logout = () => {
  auth.logout();
  router.push('/login');
};

const updatePassword = async () => {
  passwordLoading.value = true;
  passwordMessage.value = '';
  try {
    await auth.changePassword(passwordForm);
    passwordMessage.value = 'Password updated successfully.';
    passwordForm.current_password = '';
    passwordForm.new_password = '';
  } catch (err) {
    passwordMessage.value = err.response?.data?.message || 'Unable to update password.';
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
}

.group-form input {
  flex: 1;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #d9e2ec;
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

.empty {
  grid-column: 1 / -1;
  padding: 40px;
  text-align: center;
  color: #829ab1;
  border: 2px dashed #d9e2ec;
  border-radius: 18px;
  background: #f8fafc;
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
