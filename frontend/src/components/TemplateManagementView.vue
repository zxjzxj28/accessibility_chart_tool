<template>
  <div class="templates-page">
    <header class="page-header">
      <div>
        <h1>模板管理</h1>
        <p class="muted">维护 Java / Kotlin 代码模板，保存前会自动检查必需占位符。</p>
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
          <p class="muted">语言：{{ tpl.language.toUpperCase() }} · {{ tpl.is_system ? '系统模板' : '自定义模板' }}</p>
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
          <select v-model="editor.language" :disabled="editor.is_system">
            <option value="java">Java</option>
            <option value="kotlin">Kotlin</option>
          </select>
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
        content: editor.content
      });
    } else {
      await axios.post('/api/templates', {
        name: editor.name,
        language: editor.language,
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
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.muted {
  color: #6b7280;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.template-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.template-item {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-item.system {
  background: #f3f4f6;
}

.template-item footer {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.editor label {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

input,
select,
textarea {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.95rem;
}

textarea {
  font-family: 'Fira Code', 'Menlo', monospace;
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

.link {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
}

.hint {
  color: #2563eb;
}

.error {
  color: #b91c1c;
}
</style>
