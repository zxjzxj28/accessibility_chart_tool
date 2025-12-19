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
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.muted {
  color: #6b7280;
}

.error {
  color: #b91c1c;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}

.summary p {
  margin: 0;
  line-height: 1.6;
}

.data-block ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.data-block li {
  padding: 12px;
  border-radius: 8px;
  background: #f9fafb;
  display: grid;
  gap: 4px;
}

.data-block table {
  width: 100%;
  border-collapse: collapse;
}

.data-block th,
.data-block td {
  border: 1px solid #e5e7eb;
  padding: 8px;
  text-align: left;
}

.template-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.template-controls select {
  flex: 1;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 12px;
}

.primary {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  cursor: pointer;
}

.ghost {
  background: none;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
}

.rendered {
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  white-space: pre-wrap;
  font-size: 0.9rem;
}
</style>
