<template>
  <div class="templates-page">
    <header class="page-header">
      <div>
        <h1>模板管理</h1>
        <p class="muted">维护通用代码模板，保存前会自动检查必需占位符。</p>
      </div>
      <router-link class="ghost" to="/">返回首页</router-link>
    </header>

    <section class="card">
      <header class="card-header">
        <h2>我的模板</h2>
        <button class="primary" @click="startNewTemplate">新增模板</button>
      </header>
      <div class="template-list" v-if="templates.length">
        <article
          v-for="tpl in templates"
          :key="tpl.id"
          class="template-item"
          :class="{ system: tpl.is_system }"
        >
          <h3>{{ tpl.name }}</h3>
          <p class="muted">语言：{{ tpl.language }} · 类型：{{ tpl.type }} · {{ tpl.is_system ? '系统模板' : '自定义模板' }}</p>
          <footer>
            <button class="link" @click="editTemplate(tpl)">编辑</button>
            <button class="link" :disabled="tpl.is_system" @click="duplicateTemplate(tpl)">复制</button>
            <button class="link" :disabled="tpl.is_system" @click="removeTemplate(tpl)">删除</button>
          </footer>
        </article>
      </div>
      <p v-else class="muted">暂无模板。</p>
    </section>

    <section class="card" v-if="editor.visible">
      <header class="card-header">
        <h2>{{ editor.id ? '编辑模板' : '创建模板' }}</h2>
        <div class="actions">
          <button class="ghost" @click="validateContent">格式检查</button>
          <button class="ghost" @click="cancelEdit">取消</button>
        </div>
      </header>
      <form class="editor" @submit.prevent="saveTemplate">
        <label>
          模板名称
          <input v-model="editor.name" type="text" required :disabled="editor.is_system" />
        </label>
        <label>
          语言
          <input v-model="editor.language" type="text" required :disabled="editor.is_system" />
        </label>
        <label>
          类型（数字）
          <input v-model.number="editor.type" type="number" min="0" :disabled="editor.is_system" />
        </label>
        <label>
          模板内容
          <textarea v-model="editor.content" rows="14" required></textarea>
        </label>
        <p v-if="editor.message" :class="{ error: editor.error, hint: !editor.error }">{{ editor.message }}</p>
        <footer class="editor-actions">
          <button class="primary" type="submit">保存模板</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import axios from 'axios';

const templates = ref([]);

const editor = reactive({
  visible: false,
  id: '',
  name: '',
  language: 'java',
  type: 0,
  content: '',
  is_system: false,
  message: '',
  error: false
});

const REQUIRED_PLACEHOLDERS = ['{title}', '{summary}', '{table_data}', '{data_points}'];

const fetchTemplates = async () => {
  const { data } = await axios.get('/api/templates');
  templates.value = data;
};

const startNewTemplate = () => {
  editor.visible = true;
  editor.id = '';
  editor.name = '';
  editor.language = 'java';
  editor.type = 0;
  editor.content = '';
  editor.is_system = false;
  editor.message = `请包含占位符：${REQUIRED_PLACEHOLDERS.join('、')}`;
  editor.error = false;
};

const editTemplate = (tpl) => {
  editor.visible = true;
  editor.id = String(tpl.id);
  editor.name = tpl.name;
  editor.language = tpl.language;
  editor.type = tpl.type ?? 0;
  editor.content = tpl.content;
  editor.is_system = tpl.is_system;
  editor.message = '';
  editor.error = false;
};

const duplicateTemplate = (tpl) => {
  editor.visible = true;
  editor.id = '';
  editor.name = `${tpl.name} 副本`;
  editor.language = tpl.language;
  editor.type = tpl.type ?? 0;
  editor.content = tpl.content;
  editor.is_system = false;
  editor.message = '';
  editor.error = false;
};

const removeTemplate = async (tpl) => {
  if (tpl.is_system) return;
  if (!window.confirm('确定删除该模板？')) return;
  await axios.delete(`/api/templates/${tpl.id}`);
  await fetchTemplates();
};

const cancelEdit = () => {
  editor.visible = false;
};

const validateContent = async () => {
  try {
    const { data } = await axios.post('/api/templates/validate', { content: editor.content });
    if (data.missing && data.missing.length) {
      editor.message = `缺少占位符：${data.missing.join('、')}`;
      editor.error = true;
    } else {
      editor.message = '模板格式检查通过。';
      editor.error = false;
    }
  } catch (error) {
    editor.message = error.response?.data?.message || '格式检查失败';
    editor.error = true;
  }
};

const saveTemplate = async () => {
  try {
    if (editor.id) {
      await axios.patch(`/api/templates/${editor.id}`, {
        name: editor.name,
        language: editor.language,
        type: editor.type,
        content: editor.content
      });
    } else {
      await axios.post('/api/templates', {
        name: editor.name,
        language: editor.language,
        type: editor.type,
        content: editor.content
      });
    }
    editor.message = '模板已保存。';
    editor.error = false;
    await fetchTemplates();
  } catch (error) {
    editor.message = error.response?.data?.message || '保存失败';
    editor.error = true;
  }
};

fetchTemplates().catch(() => {
  // ignore initial load errors，交由界面其他交互处理
});
</script>

<style scoped>
.templates-page {
  max-width: 860px;
  margin: 0 auto;
  padding: var(--spacing-xl, 32px) var(--spacing-md, 16px);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg, 24px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-md, 16px);
  flex-wrap: wrap;
}

.page-header h1 {
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md, 16px);
  flex-wrap: wrap;
}

.card-header h2 {
  margin: 0;
  font-size: var(--text-lg, 16px);
  font-weight: 600;
  color: var(--color-text-primary, #1f2937);
}

.card-header .actions {
  display: flex;
  gap: var(--spacing-sm, 8px);
}

.template-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--spacing-md, 16px);
}

.template-item {
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: var(--radius-md, 6px);
  padding: var(--spacing-md, 16px);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
  background: var(--color-surface, #ffffff);
  transition: border-color 0.15s ease;
}

.template-item:hover {
  border-color: var(--color-text-muted, #6b7280);
}

.template-item h3 {
  margin: 0;
  font-size: var(--text-base, 14px);
  font-weight: 600;
  color: var(--color-text-primary, #1f2937);
}

.template-item.system {
  background: var(--color-bg, #f5f6f7);
}

.template-item .muted {
  margin: 0;
  font-size: var(--text-xs, 12px);
}

.template-item footer {
  display: flex;
  gap: var(--spacing-sm, 8px);
  flex-wrap: wrap;
  margin-top: var(--spacing-xs, 4px);
  padding-top: var(--spacing-sm, 8px);
  border-top: 1px solid var(--color-border-light, #e5e7eb);
}

.editor {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 16px);
}

.editor label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: var(--text-sm, 13px);
  font-weight: 500;
  color: var(--color-text-primary, #1f2937);
}

input,
select,
textarea {
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: var(--radius-md, 6px);
  padding: 9px 12px;
  font-size: var(--text-base, 14px);
  background: var(--color-surface, #ffffff);
  color: var(--color-text-primary, #1f2937);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: var(--color-primary, #374151);
  box-shadow: 0 0 0 2px rgba(55, 65, 81, 0.1);
}

input:disabled,
select:disabled,
textarea:disabled {
  background: var(--color-bg, #f5f6f7);
  color: var(--color-text-muted, #6b7280);
  cursor: not-allowed;
}

textarea {
  font-family: var(--font-mono, 'SF Mono', 'Monaco', 'Consolas', monospace);
  font-size: var(--text-sm, 13px);
  line-height: var(--leading-relaxed, 1.625);
  min-height: 180px;
  resize: vertical;
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
}

.primary:hover:not(:disabled) {
  background: var(--color-primary-hover, #1f2937);
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

.ghost:hover:not(:disabled) {
  background: var(--color-bg, #f5f6f7);
  border-color: var(--color-text-muted, #6b7280);
}

.ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.link {
  background: none;
  border: none;
  color: var(--color-accent, #2563eb);
  cursor: pointer;
  padding: 0;
  font-weight: 500;
  font-size: var(--text-sm, 13px);
  transition: color 0.15s ease;
}

.link:hover:not(:disabled) {
  color: var(--color-accent-hover, #1d4ed8);
  text-decoration: underline;
}

.link:disabled {
  color: var(--color-text-muted, #6b7280);
  cursor: not-allowed;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm, 8px);
  margin-top: var(--spacing-sm, 8px);
}

.hint {
  color: var(--color-info, #0369a1);
  font-size: var(--text-sm, 13px);
  padding: 10px 14px;
  background: var(--color-info-bg, #f0f9ff);
  border-radius: var(--radius-sm, 4px);
  border: 1px solid rgba(3, 105, 161, 0.15);
}

.error {
  color: var(--color-error, #dc2626);
  font-size: var(--text-sm, 13px);
  padding: 10px 14px;
  background: var(--color-error-bg, #fef2f2);
  border-radius: var(--radius-sm, 4px);
  border: 1px solid rgba(220, 38, 38, 0.15);
}

@media (max-width: 640px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .card-header {
    flex-direction: column;
    align-items: stretch;
  }

  .template-list {
    grid-template-columns: 1fr;
  }
}
</style>
