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
            <p class="muted">在模板和语言之间切换，必要时保存自定义代码。</p>
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
            <select class="template-select" v-model="selectedTemplates[activeLanguage]" @change="onTemplateChange">
              <option value="">原始生成代码</option>
              <option v-for="template in templatesByLanguage(activeLanguage)" :key="template.id" :value="String(template.id)">
                {{ templateLabel(template) }}
              </option>
            </select>
            <button class="ghost" @click="resetToGenerated">恢复生成代码</button>
            <button class="primary" @click="saveCustomCode">保存自定义代码</button>
          </div>
        </header>
        <textarea v-model="editedCode" spellcheck="false"></textarea>
        <p v-if="templateMessage" class="info">{{ templateMessage }}</p>
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
import { computed, onMounted, reactive, ref, watch } from 'vue';
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
const templateMessage = ref('');
const templates = ref([]);

const selectedTemplates = reactive({ java: '', kotlin: '' });
const templateCache = reactive({ java: new Map(), kotlin: new Map() });

const statusLabels = {
  pending: '排队中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消'
};

const taskId = route.params.id;

const fetchTemplates = async () => {
  const { data } = await axios.get('/api/templates');
  templates.value = data.items;
};

const templateLabel = (template) => `${template.name} · ${template.language.toUpperCase()}`;

const templatesByLanguage = (language) => templates.value.filter((tpl) => tpl.language === language);

const clearTemplateCache = () => {
  templateCache.java.clear();
  templateCache.kotlin.clear();
};

const fetchTask = async () => {
  const { data } = await axios.get(`/api/tasks/${taskId}`);
  task.value = data;
  activeLanguage.value = data.template?.language || data.language || 'java';
  initializeTemplateSelection();
  await applyLanguageCode();
};

const initializeTemplateSelection = () => {
  if (!task.value) return;
  clearTemplateCache();
  selectedTemplates.java = '';
  selectedTemplates.kotlin = '';
  if (task.value.template && task.value.template.language) {
    selectedTemplates[task.value.template.language] = String(task.value.template.id);
  }
  const systemJava = templatesByLanguage('java').find((tpl) => tpl.is_system) || templatesByLanguage('java')[0];
  const systemKotlin = templatesByLanguage('kotlin').find((tpl) => tpl.is_system) || templatesByLanguage('kotlin')[0];
  if (!selectedTemplates.java && systemJava) {
    selectedTemplates.java = String(systemJava.id);
  }
  if (!selectedTemplates.kotlin && systemKotlin) {
    selectedTemplates.kotlin = String(systemKotlin.id);
  }
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
  selectedTemplates[activeLanguage.value] = '';
  editedCode.value = getBaseCode(activeLanguage.value);
  templateMessage.value = '';
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
  if (language === 'java') {
    return task.value.java_code || '';
  }
  return task.value.kotlin_code || '';
};

const applyLanguageCode = async () => {
  if (!task.value) return;
  templateMessage.value = '';
  const language = activeLanguage.value;
  const custom = task.value.custom_code?.[language];
  if (custom) {
    editedCode.value = custom;
    return;
  }
  const templateId = selectedTemplates[language];
  if (templateId) {
    await handleTemplateSelection(language, templateId, true);
  } else {
    editedCode.value = getBaseCode(language);
  }
};

const handleTemplateSelection = async (language, templateId, fromApply = false) => {
  if (!task.value) return;
  if (!templateId) {
    if (activeLanguage.value === language) {
      editedCode.value = getBaseCode(language);
    }
    return;
  }
  if (task.value.status !== 'completed') {
    if (activeLanguage.value === language) {
      templateMessage.value = '任务尚未完成，无法应用模板。';
    }
    return;
  }
  const cache = templateCache[language];
  if (cache.has(templateId)) {
    if (activeLanguage.value === language) {
      editedCode.value = cache.get(templateId);
    }
    return;
  }
  try {
    const { data } = await axios.post(`/api/tasks/${taskId}/render-template`, { template_id: Number(templateId) });
    cache.set(templateId, data.code);
    if (activeLanguage.value === language) {
      editedCode.value = data.code;
      if (!fromApply) {
        templateMessage.value = '';
      }
    }
  } catch (err) {
    const message = err.response?.data?.message || '模板渲染失败。';
    if (activeLanguage.value === language) {
      templateMessage.value = message;
      editedCode.value = getBaseCode(language);
    }
  }
};

const onTemplateChange = async () => {
  await applyLanguageCode();
};

const switchLanguage = async (language) => {
  if (activeLanguage.value === language) return;
  activeLanguage.value = language;
  await applyLanguageCode();
  saveMessage.value = '';
};

watch(
  () => task.value?.custom_code,
  async () => {
    await applyLanguageCode();
  }
);

watch(
  () => activeLanguage.value,
  async () => {
    await applyLanguageCode();
  }
);

watch(
  () => selectedTemplates.java,
  async () => {
    if (!task.value) return;
    if (activeLanguage.value === 'java') {
      await applyLanguageCode();
    } else if (selectedTemplates.java) {
      await handleTemplateSelection('java', selectedTemplates.java);
    }
  }
);

watch(
  () => selectedTemplates.kotlin,
  async () => {
    if (!task.value) return;
    if (activeLanguage.value === 'kotlin') {
      await applyLanguageCode();
    } else if (selectedTemplates.kotlin) {
      await handleTemplateSelection('kotlin', selectedTemplates.kotlin);
    }
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
  await fetchTemplates();
  await fetchTask();
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
  align-items: center;
}

.button-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
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

.template-select {
  padding: 8px 12px;
  border-radius: 12px;
  border: 1px solid #d9e2ec;
  background: #f8fafc;
  color: #364fc7;
  font-weight: 600;
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

.loading-state {
  padding: 32px;
  text-align: center;
  color: #486581;
}
</style>
