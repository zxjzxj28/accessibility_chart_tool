<template>
  <div class="detail-page" v-if="task">
    <header class="detail-header">
      <div>
        <button class="ghost" @click="goBack">← Back to dashboard</button>
        <h1>{{ task.title }}</h1>
        <div class="status" :class="task.status">{{ task.status }}</div>
      </div>
      <div class="header-actions">
        <button class="primary" @click="regenerateCode" :disabled="regenerating">Regenerate code</button>
        <button class="secondary" @click="refresh">Refresh</button>
      </div>
    </header>

    <section class="info-grid">
      <article class="card">
        <h2>Chart summary</h2>
        <p>{{ task.summary || 'Summary will appear once processing completes.' }}</p>
        <div class="image-preview" v-if="task.image_path">
          <img :src="imageSource" alt="Chart preview" />
        </div>
      </article>
      <article class="card">
        <h2>Data points</h2>
        <table v-if="task.table_data?.length">
          <thead>
            <tr>
              <th>Label</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in task.table_data" :key="row.label">
              <td>{{ row.label }}</td>
              <td>{{ row.value }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted">No structured data available yet.</p>
      </article>
    </section>

    <section class="editor-grid">
      <article class="card">
        <header class="card-header">
          <div>
            <h2>Accessible component code</h2>
            <p class="muted">Update the code and refresh the preview. Saving stores a custom snippet for this task.</p>
          </div>
          <div class="button-group">
            <button class="ghost" @click="resetToGenerated">Use generated code</button>
            <button class="primary" @click="saveCustomCode">Save custom code</button>
          </div>
        </header>
        <textarea v-model="editedCode" spellcheck="false"></textarea>
      </article>
      <article class="card preview-card">
        <header class="card-header">
          <div>
            <h2>Preview</h2>
            <p class="muted">Rendered with the code above inside a sandboxed frame.</p>
          </div>
          <button class="secondary" @click="refreshPreview">Refresh preview</button>
        </header>
        <iframe
          :key="previewKey"
          class="preview-frame"
          title="Preview"
          sandbox="allow-scripts allow-same-origin"
          :srcdoc="previewHtml"
        ></iframe>
      </article>
    </section>
  </div>
  <div v-else class="loading-state">
    Loading task details...
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';

const route = useRoute();
const router = useRouter();

const task = ref(null);
const editedCode = ref('');
const previewKey = ref(0);
const regenerating = ref(false);

const taskId = route.params.id;

const fetchTask = async () => {
  const { data } = await axios.get(`/api/tasks/${taskId}`);
  task.value = data;
  editedCode.value = data.custom_code || data.generated_code || '';
};

const refresh = async () => {
  await fetchTask();
  refreshPreview();
};

const refreshPreview = () => {
  previewKey.value += 1;
};

const saveCustomCode = async () => {
  await axios.post(`/api/tasks/${taskId}/custom-code`, { custom_code: editedCode.value });
  await fetchTask();
  refreshPreview();
};

const regenerateCode = async () => {
  regenerating.value = true;
  try {
    await axios.post(`/api/tasks/${taskId}/regenerate-code`);
    await fetchTask();
    refreshPreview();
  } finally {
    regenerating.value = false;
  }
};

const resetToGenerated = () => {
  editedCode.value = task.value.generated_code || '';
  refreshPreview();
};

const goBack = () => {
  router.push('/');
};

const imageSource = computed(() => task.value?.image_url || '');

const previewHtml = computed(
  () =>
    editedCode.value ||
    '<p style="font-family: system-ui, sans-serif; color: #475569; padding: 24px;">No code available yet.</p>'
);

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

.preview-card {
  min-height: 340px;
}

.preview-frame {
  width: 100%;
  min-height: 320px;
  border: 1px solid #d9e2ec;
  border-radius: 12px;
  background: white;
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
