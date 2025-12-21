<template>
  <div class="task-detail" v-if="task">
    <header class="header">
      <div>
        <h1>{{ task.name }}</h1>
        <p class="muted">状态：{{ statusLabel(task.status) }} · 创建于 {{ formatDate(task.created_at) }}</p>
      </div>
      <router-link class="ghost" to="/">返回列表</router-link>
    </header>

    <section class="card">
      <h2>任务结果</h2>
      <p v-if="[0, 1].includes(Number(task.status))" class="muted">任务正在处理中，请稍后刷新。</p>
      <p v-else-if="Number(task.status) === 3" class="error">{{ task.result?.error_message || '处理失败' }}</p>
      <template v-else>
        <article class="summary" v-if="task.summary">
          <h3>图表摘要</h3>
          <p>{{ task.summary }}</p>
        </article>
        <article class="data-block" v-if="task.result?.data_points?.length">
          <h3>数据点</h3>
          <ul>
            <li v-for="point in task.result.data_points" :key="point.id">
              <strong>{{ point.label }}</strong>
              <span>值：{{ point.value }}</span>
              <span>描述：{{ point.description }}</span>
            </li>
          </ul>
        </article>
        <article class="data-block" v-if="task.result?.table_data?.length">
          <h3>表格数据</h3>
          <table>
            <thead>
              <tr>
                <th>标签</th>
                <th>数值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in task.result.table_data" :key="row.label">
                <td>{{ row.label }}</td>
                <td>{{ row.value }}</td>
              </tr>
            </tbody>
          </table>
        </article>
      </template>
    </section>

    <section class="card">
      <h2>模板渲染</h2>
      <div class="template-controls">
        <select v-model="selectedTemplateId">
          <option value="">选择模板</option>
          <option v-for="template in templates" :key="template.id" :value="String(template.id)">
            {{ template.name }} · {{ template.language.toUpperCase() }}
          </option>
        </select>
        <button class="primary" :disabled="!selectedTemplateId" @click="renderTemplate">渲染模板</button>
      </div>
      <pre v-if="renderedTemplate" class="rendered">{{ renderedTemplate }}</pre>
      <p v-else class="muted">选择一个模板后即可查看格式化后的内容。</p>
    </section>
  </div>
  <p v-else class="muted">正在加载任务详情…</p>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';

const route = useRoute();
const router = useRouter();

const task = ref(null);
const templates = ref([]);
const selectedTemplateId = ref('');
const renderedTemplate = ref('');

const statusLabel = (status) => {
  const mapping = {
    0: '排队中',
    1: '处理中',
    2: '已完成',
    3: '失败',
    4: '已取消'
  };
  return mapping[status] || '未知';
};

const formatDate = (value) => new Date(value).toLocaleString();

const loadTask = async () => {
  try {
    const { data } = await axios.get(`/api/tasks/${route.params.id}`);
    task.value = data;
  } catch (error) {
    router.replace('/');
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

const renderTemplate = async () => {
  if (!selectedTemplateId.value || !task.value) return;
  try {
    const { data } = await axios.get(`/api/tasks/${task.value.id}/render-template`, {
      params: { template_id: selectedTemplateId.value }
    });
    renderedTemplate.value = data.content;
  } catch (error) {
    renderedTemplate.value = error.response?.data?.message || '渲染失败';
  }
};

onMounted(async () => {
  await Promise.all([loadTask(), loadTemplates()]);
});
</script>

<style scoped>
.task-detail {
  max-width: 780px;
  margin: 0 auto;
  padding: var(--spacing-xl, 32px) var(--spacing-md, 16px);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg, 24px);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-md, 16px);
  flex-wrap: wrap;
}

.header h1 {
  margin: 0;
  font-size: var(--text-2xl, 20px);
  font-weight: 600;
  color: var(--color-text-primary, #1f2937);
  letter-spacing: -0.01em;
}

.muted {
  color: var(--color-text-secondary, #4b5563);
  font-size: var(--text-sm, 13px);
  margin-top: var(--spacing-xs, 4px);
}

.error {
  color: var(--color-error, #dc2626);
  font-size: var(--text-sm, 13px);
  padding: 10px 14px;
  background: var(--color-error-bg, #fef2f2);
  border-radius: var(--radius-sm, 4px);
  border: 1px solid rgba(220, 38, 38, 0.15);
}

.card {
  background: var(--color-surface, #ffffff);
  border-radius: var(--radius-lg, 8px);
  padding: var(--spacing-lg, 24px);
  border: 1px solid var(--color-border, #d1d5db);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(0, 0, 0, 0.04));
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 16px);
}

.card h2 {
  margin: 0;
  font-size: var(--text-lg, 16px);
  font-weight: 600;
  color: var(--color-text-primary, #1f2937);
}

.summary {
  width: 100%;
}

.summary h3 {
  margin: 0 0 var(--spacing-sm, 8px);
  font-size: var(--text-base, 14px);
  font-weight: 600;
  color: var(--color-text-primary, #1f2937);
}

.summary p {
  margin: 0;
  line-height: var(--leading-relaxed, 1.625);
  color: var(--color-text-secondary, #4b5563);
  font-size: var(--text-base, 14px);
}

.data-block {
  width: 100%;
}

.data-block h3 {
  margin: 0 0 var(--spacing-sm, 8px);
  font-size: var(--text-base, 14px);
  font-weight: 600;
  color: var(--color-text-primary, #1f2937);
}

.data-block ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
}

.data-block li {
  padding: var(--spacing-md, 16px);
  border-radius: var(--radius-md, 6px);
  background: var(--color-bg, #f5f6f7);
  border: 1px solid var(--color-border-light, #e5e7eb);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs, 4px);
  font-size: var(--text-sm, 13px);
}

.data-block li strong {
  color: var(--color-text-primary, #1f2937);
  font-weight: 600;
}

.data-block li span {
  color: var(--color-text-secondary, #4b5563);
}

.data-block table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm, 13px);
}

.data-block th,
.data-block td {
  border: 1px solid var(--color-border, #d1d5db);
  padding: 9px 12px;
  text-align: left;
}

.data-block th {
  background: var(--color-bg, #f5f6f7);
  font-weight: 600;
  color: var(--color-text-primary, #1f2937);
}

.data-block td {
  color: var(--color-text-secondary, #4b5563);
}

.template-controls {
  display: flex;
  gap: var(--spacing-sm, 8px);
  align-items: center;
  width: 100%;
}

.template-controls select {
  flex: 1;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: var(--radius-md, 6px);
  padding: 9px 12px;
  font-size: var(--text-base, 14px);
  background: var(--color-surface, #ffffff);
  color: var(--color-text-primary, #1f2937);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.template-controls select:focus {
  outline: none;
  border-color: var(--color-primary, #374151);
  box-shadow: 0 0 0 2px rgba(55, 65, 81, 0.1);
}

.primary {
  background: var(--color-primary, #374151);
  color: #ffffff;
  border: none;
  border-radius: var(--radius-md, 6px);
  padding: 9px 16px;
  cursor: pointer;
  font-weight: 500;
  font-size: var(--text-sm, 13px);
  transition: background-color 0.15s ease;
  white-space: nowrap;
}

.primary:hover:not(:disabled) {
  background: var(--color-primary-hover, #1f2937);
}

.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ghost {
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: var(--radius-md, 6px);
  padding: 7px 12px;
  cursor: pointer;
  color: var(--color-text-primary, #1f2937);
  font-weight: 500;
  font-size: var(--text-sm, 13px);
  text-decoration: none;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.ghost:hover {
  background: var(--color-bg, #f5f6f7);
  border-color: var(--color-text-muted, #6b7280);
}

.rendered {
  width: 100%;
  background: #1e293b;
  color: #e2e8f0;
  border-radius: var(--radius-md, 6px);
  padding: var(--spacing-md, 16px);
  white-space: pre-wrap;
  font-size: var(--text-sm, 13px);
  font-family: var(--font-mono, 'SF Mono', 'Monaco', 'Consolas', monospace);
  line-height: var(--leading-relaxed, 1.625);
  overflow-x: auto;
  border: 1px solid #334155;
}

@media (max-width: 640px) {
  .header {
    flex-direction: column;
    align-items: stretch;
  }

  .template-controls {
    flex-direction: column;
  }

  .template-controls select,
  .template-controls .primary {
    width: 100%;
  }
}
</style>
