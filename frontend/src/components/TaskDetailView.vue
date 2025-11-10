<template>
  <div class="detail-page" v-if="task">
    <header class="detail-header">
      <div>
        <button class="ghost" @click="goBack">← 返回仪表盘</button>
        <h1>{{ task.title }}</h1>
        <div class="status" :class="task.status">{{ statusLabel }}</div>
      </div>
      <div class="header-actions">
        <button class="primary" @click="regenerateCode" :disabled="regenerating">重新生成代码</button>
        <button class="secondary" @click="refresh">刷新</button>
        <button class="ghost" @click="downloadPackage">下载代码压缩包</button>
      </div>
    </header>

    <section class="info-grid">
      <article class="card">
        <h2>图表摘要</h2>
        <p>{{ task.summary || '处理中完成后将显示摘要。' }}</p>
        <div class="image-preview" v-if="task.image_path">
          <img :src="imageSource" alt="图表预览" />
        </div>
      </article>
      <article class="card">
        <h2>数据点</h2>
        <table v-if="task.table_data?.length">
          <thead>
            <tr>
              <th>标签</th>
              <th>数值</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in task.table_data" :key="row.label">
              <td>{{ row.label }}</td>
              <td>{{ row.value }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted">暂未生成结构化数据。</p>
      </article>
    </section>

    <section class="editor-grid">
      <article class="card">
        <header class="card-header">
          <div>
            <h2>Android 代码片段</h2>
            <p class="muted">为当前语言调优代码，保存后即可在下载包中获取自定义版本。</p>
          </div>
          <div class="button-group">
            <div class="language-tabs">
              <button
                type="button"
                :class="{ active: activeLanguage === 'java' }"
                @click="switchLanguage('java')"
              >Java</button>
              <button
                type="button"
                :class="{ active: activeLanguage === 'kotlin' }"
                @click="switchLanguage('kotlin')"
              >Kotlin</button>
            </div>
            <button class="ghost" @click="resetToGenerated">恢复生成代码</button>
            <button class="primary" @click="saveCustomCode">保存自定义代码</button>
          </div>
        </header>
        <textarea v-model="editedCode" spellcheck="false"></textarea>
        <p v-if="saveMessage" class="info">{{ saveMessage }}</p>
      </article>
      <article class="card integration-card">
        <header class="card-header">
          <div>
            <h2>集成说明</h2>
            <p class="muted">根据语言选择相应步骤完成在 Android 项目中的落地。</p>
          </div>
        </header>
        <div class="integration-block">
          <h3>Java 集成步骤</h3>
          <ol>
            <li v-for="(step, index) in javaSteps" :key="`java-${index}`">{{ step }}</li>
            <li v-if="!javaSteps.length" class="muted">暂无说明。</li>
          </ol>
        </div>
        <div class="integration-block">
          <h3>Kotlin 集成步骤</h3>
          <ol>
            <li v-for="(step, index) in kotlinSteps" :key="`kotlin-${index}`">{{ step }}</li>
            <li v-if="!kotlinSteps.length" class="muted">暂无说明。</li>
          </ol>
        </div>
        <p v-if="downloadMessage" class="info">{{ downloadMessage }}</p>
      </article>
    </section>
  </div>
  <div v-else class="loading-state">
    正在加载任务详情...
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';

const route = useRoute();
const router = useRouter();

const task = ref(null);
const editedCode = ref('');
const activeLanguage = ref('java');
const regenerating = ref(false);
const saveMessage = ref('');
const downloadMessage = ref('');

const statusLabels = {
  pending: '排队中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

const taskId = route.params.id;

const fetchTask = async () => {
  const { data } = await axios.get(`/api/tasks/${taskId}`);
  task.value = data;
  activeLanguage.value = data.language || 'java';
  applyLanguageCode();
};

const refresh = async () => {
  await fetchTask();
};

const saveCustomCode = async () => {
  saveMessage.value = '';
  try {
    await axios.post(`/api/tasks/${taskId}/custom-code`, {
      language: activeLanguage.value,
      code: editedCode.value
    });
    await fetchTask();
    saveMessage.value = '自定义代码已保存。';
  } catch (err) {
    saveMessage.value = err.response?.data?.message || '保存失败，请稍后重试。';
  }
};

const regenerateCode = async () => {
  regenerating.value = true;
  try {
    await axios.post(`/api/tasks/${taskId}/regenerate-code`, { language: activeLanguage.value });
    await fetchTask();
    saveMessage.value = `已重新生成 ${activeLanguage.value === 'java' ? 'Java' : 'Kotlin'} 代码。`;
  } catch (err) {
    saveMessage.value = err.response?.data?.message || '重新生成失败，请稍后再试。';
  } finally {
    regenerating.value = false;
  }
};

const resetToGenerated = () => {
  const base = getBaseCode(activeLanguage.value);
  editedCode.value = base;
};

const goBack = () => {
  router.push('/');
};

const statusLabel = computed(() => statusLabels[task.value?.status] || task.value?.status || '');

const javaSteps = computed(() => task.value?.integration_doc?.java || []);
const kotlinSteps = computed(() => task.value?.integration_doc?.kotlin || []);

const imageSource = computed(() => task.value?.image_url || '');

const getBaseCode = (language) => {
  if (!task.value) return '';
  const base = language === 'java' ? task.value.java_code : task.value.kotlin_code;
  const custom = task.value.custom_code?.[language];
  return custom || base || '';
};

const applyLanguageCode = () => {
  editedCode.value = getBaseCode(activeLanguage.value);
};

const switchLanguage = (language) => {
  if (activeLanguage.value === language) return;
  activeLanguage.value = language;
  applyLanguageCode();
  saveMessage.value = '';
};

watch(
  () => task.value?.custom_code,
  () => {
    applyLanguageCode();
  }
);

const downloadPackage = async () => {
  downloadMessage.value = '';
  try {
    const response = await axios.get(`/api/tasks/${taskId}/download`, { responseType: 'blob' });
    const blob = new Blob([response.data], { type: 'application/zip' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `task_${taskId}.zip`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    downloadMessage.value = err.response?.data?.message || '下载失败，请稍后再试。';
  }
};

onMounted(async () => {
  await refresh();
});
</script>

<style scoped>
.detail-page {
  padding: 32px 48px;
  display: grid;
  gap: 32px;
  background: #f4f6fb;
  min-height: 100vh;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-header h1 {
  margin: 8px 0;
  color: #102a43;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.info-grid {
  display: grid;
  gap: 24px;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.editor-grid {
  display: grid;
  gap: 24px;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
}

.card {
  background: white;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.button-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.card-header h2 {
  margin: 0;
  color: #243b53;
}

.muted {
  color: #829ab1;
  margin: 0;
}

textarea {
  width: 100%;
  min-height: 340px;
  border-radius: 12px;
  border: 1px solid #d9e2ec;
  padding: 16px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.95rem;
  background: #f8fafc;
}

.language-tabs {
  display: flex;
  gap: 8px;
}

.language-tabs button {
  border: 1px solid #d9e2ec;
  background: #f8fafc;
  color: #486581;
  padding: 8px 14px;
  border-radius: 999px;
  font-weight: 600;
}

.language-tabs button.active {
  background: linear-gradient(135deg, #4c6ef5, #5f3dc4);
  color: white;
  border-color: #4c6ef5;
}

.integration-card {
  gap: 12px;
}

.integration-block {
  display: grid;
  gap: 10px;
}

.integration-block h3 {
  margin: 0;
  color: #243b53;
}

.integration-block ol {
  margin: 0;
  padding-left: 1.2rem;
  display: grid;
  gap: 6px;
}

.info {
  color: #0f766e;
  margin: 0;
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
  background: #edf2ff;
  color: #364fc7;
}

button.ghost {
  background: transparent;
  color: #334e68;
}

button:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(15, 23, 42, 0.1);
}

.image-preview img {
  width: 100%;
  border-radius: 12px;
  border: 1px solid #d9e2ec;
}

.table {
  width: 100%;
}

table {
  width: 100%;
  border-collapse: collapse;
}

td,
th {
  text-align: left;
  padding: 8px 12px;
  border-bottom: 1px solid #e5e9f2;
}

.loading-state {
  display: grid;
  place-items: center;
  min-height: 60vh;
  font-size: 1.2rem;
  color: #829ab1;
}
</style>
