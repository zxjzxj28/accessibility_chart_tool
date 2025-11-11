<template>
  <div class="template-page">
    <header class="page-header">
      <div>
        <h1>代码模板管理</h1>
        <p>集中维护 Java 与 Kotlin 模版，支持新增、修改、删除与格式检查。</p>
      </div>
      <div class="header-actions">
        <router-link class="ghost" to="/">← 返回首页</router-link>
        <button class="primary" @click="startNewTemplate('java')">新建模板</button>
      </div>
    </header>

    <section class="template-layout">
      <aside class="template-sidebar">
        <div class="template-group" v-for="lang in ['java', 'kotlin']" :key="`tpl-group-${lang}`">
          <div class="template-group-header">
            <h2>{{ lang === 'java' ? 'Java 模板' : 'Kotlin 模板' }}</h2>
            <button class="icon" @click="startNewTemplate(lang)" title="新增模板">＋</button>
          </div>
          <ul>
            <li v-for="tpl in templatesByLanguage(lang)" :key="`tpl-list-${tpl.id}`">
              <button
                type="button"
                :class="{ active: templateEditor.id === String(tpl.id) }"
                @click="selectTemplateForEditing(tpl)"
              >
                {{ tpl.name }}
                <span v-if="tpl.is_system" class="tag">系统</span>
              </button>
            </li>
            <li v-if="!templatesByLanguage(lang).length" class="empty">暂无模板</li>
          </ul>
        </div>
      </aside>

      <div class="template-editor">
        <form @submit.prevent="saveTemplate" class="template-form">
          <div class="editor-row">
            <label>
              模板名称
              <input v-model="templateEditor.name" type="text" :disabled="templateEditor.is_system" required />
            </label>
            <label>
              代码语言
              <select v-model="templateEditor.language" :disabled="templateEditor.id && templateEditor.is_system">
                <option value="java">Java</option>
                <option value="kotlin">Kotlin</option>
              </select>
            </label>
          </div>

          <label class="copy-control">
            从现有模板填充
            <div class="copy-actions">
              <select v-model="templateCopySource">
                <option value="">选择模板</option>
                <option
                  v-for="tpl in templatesByLanguage(templateEditor.language)"
                  :key="`tpl-copy-${tpl.id}`"
                  :value="String(tpl.id)"
                >
                  {{ tpl.name }}
                </option>
              </select>
              <button type="button" class="ghost" @click="applyTemplateCopy" :disabled="!templateCopySource">填充</button>
            </div>
          </label>

          <label>
            模板内容
            <textarea v-model="templateEditor.content" :readonly="templateEditor.is_system"></textarea>
          </label>

          <div class="placeholder-hint">
            <strong>必需占位符：</strong>
            <span v-if="requiredPlaceholders.length">{{ requiredPlaceholders.join('、') }}</span>
            <span v-else>正在加载...</span>
          </div>

          <div class="template-actions">
            <button type="button" class="ghost" @click="validateTemplate" :disabled="templateEditor.is_system">格式检查</button>
            <button type="submit" class="primary" :disabled="templateEditor.is_system">保存模板</button>
            <button type="button" class="secondary" @click="deleteTemplate" :disabled="!templateEditor.id || templateEditor.is_system">删除模板</button>
          </div>

          <p v-if="templateValidationMessage" class="info">{{ templateValidationMessage }}</p>
          <p v-if="templateEditorMessage" class="info">{{ templateEditorMessage }}</p>
        </form>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import axios from 'axios';

const templates = ref([]);
const requiredPlaceholders = ref([]);

const templateEditor = reactive({ id: '', name: '', language: 'java', content: '', is_system: false });
const templateEditorMessage = ref('');
const templateValidationMessage = ref('');
const templateCopySource = ref('');

const templatesByLanguage = (language) => templates.value.filter((tpl) => tpl.language === language);

const resetMessages = () => {
  templateEditorMessage.value = '';
  templateValidationMessage.value = '';
};

const populateTemplateEditor = (template, preserveMessages = false) => {
  templateEditor.id = String(template.id);
  templateEditor.name = template.name;
  templateEditor.language = template.language;
  templateEditor.content = template.content || '';
  templateEditor.is_system = !!template.is_system;
  templateCopySource.value = '';
  if (!preserveMessages) {
    resetMessages();
  }
};

const startNewTemplate = (language = 'java') => {
  templateEditor.id = '';
  templateEditor.name = '';
  templateEditor.language = language;
  templateEditor.content = '';
  templateEditor.is_system = false;
  templateCopySource.value = '';
  resetMessages();
};

const ensureEditorSelection = () => {
  if (!templates.value.length) {
    startNewTemplate(templateEditor.language || 'java');
    return;
  }
  if (templateEditor.id) {
    const current = templates.value.find((tpl) => String(tpl.id) === templateEditor.id);
    if (current) {
      populateTemplateEditor(current, true);
      return;
    }
  }
  const systemTemplate = templates.value.find((tpl) => tpl.is_system && tpl.language === templateEditor.language);
  if (systemTemplate) {
    populateTemplateEditor(systemTemplate, true);
    return;
  }
  populateTemplateEditor(templates.value[0], true);
};

const fetchTemplates = async () => {
  const { data } = await axios.get('/api/templates');
  templates.value = data.items || [];
  requiredPlaceholders.value = data.required_placeholders || [];
  if (
    templateCopySource.value &&
    !templates.value.some((tpl) => String(tpl.id) === templateCopySource.value)
  ) {
    templateCopySource.value = '';
  }
  ensureEditorSelection();
};

const applyTemplateCopy = () => {
  if (!templateCopySource.value) return;
  const source = templates.value.find((tpl) => String(tpl.id) === templateCopySource.value);
  if (source) {
    templateEditor.language = source.language;
    templateEditor.content = source.content || '';
    if (!templateEditor.name) {
      templateEditor.name = `${source.name} 副本`;
    }
  }
};

const validateTemplate = async () => {
  templateValidationMessage.value = '';
  try {
    const { data } = await axios.post('/api/templates/validate', { content: templateEditor.content });
    if (data.valid) {
      templateValidationMessage.value = '格式检查通过。';
    } else {
      templateValidationMessage.value = `缺少占位符：${(data.missing || []).join('、')}`;
    }
  } catch (err) {
    templateValidationMessage.value = err.response?.data?.message || '无法进行格式检查。';
  }
};

const saveTemplate = async () => {
  if (templateEditor.is_system) {
    templateEditorMessage.value = '系统模板不可修改。';
    return;
  }
  if (!templateEditor.name.trim()) {
    templateEditorMessage.value = '模板名称不能为空。';
    return;
  }

  try {
    const { data } = await axios.post('/api/templates/validate', { content: templateEditor.content });
    if (!data.valid) {
      templateValidationMessage.value = `缺少占位符：${(data.missing || []).join('、')}`;
      templateEditorMessage.value = '格式检查未通过，无法保存。';
      return;
    }
    templateValidationMessage.value = '格式检查通过。';
  } catch (err) {
    templateValidationMessage.value = err.response?.data?.message || '无法进行格式检查。';
    templateEditorMessage.value = '请稍后再试。';
    return;
  }

  const payload = {
    name: templateEditor.name.trim(),
    language: templateEditor.language,
    content: templateEditor.content
  };

  try {
    if (templateEditor.id) {
      await axios.patch(`/api/templates/${templateEditor.id}`, payload);
      templateEditorMessage.value = '模板已保存。';
    } else {
      const { data } = await axios.post('/api/templates', payload);
      templateEditorMessage.value = '模板已创建。';
      templateEditor.id = String(data.id);
    }
    await fetchTemplates();
  } catch (err) {
    templateEditorMessage.value = err.response?.data?.message || '保存模板失败。';
  }
};

const deleteTemplate = async () => {
  if (!templateEditor.id || templateEditor.is_system) return;
  const confirmed = window.confirm('删除模板将影响关联任务，是否继续？');
  if (!confirmed) return;
  try {
    await axios.delete(`/api/templates/${templateEditor.id}`);
    templateEditorMessage.value = '模板已删除。';
    startNewTemplate(templateEditor.language);
    await fetchTemplates();
  } catch (err) {
    templateEditorMessage.value = err.response?.data?.message || '无法删除模板。';
  }
};

const selectTemplateForEditing = (template) => {
  populateTemplateEditor(template, false);
};

onMounted(async () => {
  await fetchTemplates();
});
</script>

<style scoped>
.template-page {
  min-height: 100vh;
  background: #f4f6fb;
  padding: 32px 48px;
  display: grid;
  gap: 32px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h1 {
  margin-bottom: 8px;
  color: #102a43;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.template-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 24px;
}

.template-sidebar {
  background: white;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 20px 60px rgba(15, 35, 95, 0.08);
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.template-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.template-group ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-group button {
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: #f3f6ff;
  color: #1f3a8a;
  transition: all 0.2s ease;
}

.template-group button.active {
  background: #1f3a8a;
  color: white;
  border-color: #1f3a8a;
}

.template-group button:hover {
  border-color: #1f3a8a;
}

.template-group .empty {
  color: #8798ad;
  font-size: 14px;
}

.template-group .tag {
  margin-left: 8px;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.3);
}

.template-editor {
  background: white;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 20px 60px rgba(15, 35, 95, 0.08);
}

.template-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.editor-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.copy-control .copy-actions {
  margin-top: 8px;
  display: flex;
  gap: 12px;
  align-items: center;
}

.template-form textarea {
  min-height: 320px;
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
  line-height: 1.5;
}

.placeholder-hint {
  font-size: 14px;
  color: #334e68;
  background: #f1f5f9;
  padding: 12px;
  border-radius: 12px;
}

.template-actions {
  display: flex;
  gap: 12px;
}

.info {
  color: #1f3a8a;
  background: rgba(31, 58, 138, 0.08);
  padding: 12px;
  border-radius: 12px;
}

.icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  color: #1f3a8a;
}

@media (max-width: 960px) {
  .template-layout {
    grid-template-columns: 1fr;
  }
}
</style>
