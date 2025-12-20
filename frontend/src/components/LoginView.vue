<template>
  <div class="auth-layout">
    <div class="panel">
      <h1>无障碍图表组件开发工具</h1>
      <form @submit.prevent="handleSubmit" class="form">
        <label>
          账号
          <input v-model="identifier" type="text" required placeholder="请输入账号名称" />
        </label>
        <label>
          密码
          <input v-model="password" type="password" required placeholder="••••••••" />
        </label>
        <button type="submit" :disabled="loading">
          <span v-if="loading">正在登录...</span>
          <span v-else>登录</span>
        </button>
      </form>
      <p class="hint">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
      </p>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const identifier = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

const handleSubmit = async () => {
  loading.value = true;
  error.value = '';
  try {
    await auth.login({ identifier: identifier.value.trim(), password: password.value });
    const redirect = route.query.redirect || '/';
    router.push(redirect);
  } catch (err) {
    error.value = err.response?.data?.message || '无法完成登录。';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.auth-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg, #fafbfc);
  padding: var(--spacing-lg, 24px);
}

.panel {
  width: 100%;
  max-width: 400px;
  background: var(--color-surface, #ffffff);
  border-radius: var(--radius-lg, 12px);
  padding: var(--spacing-xl, 32px);
  border: 1px solid var(--color-border, #e1e4e8);
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.08));
}

h1 {
  margin: 0;
  font-size: 32px;
  font-weight: 600;
  color: var(--color-text-primary, #24292f);
  letter-spacing: -0.02em;
  text-align: center;
}

.subtitle {
  margin: var(--spacing-sm, 8px) 0 var(--spacing-lg, 24px);
  color: var(--color-text-secondary, #57606a);
  font-size: var(--text-md, 15px);
  line-height: var(--leading-relaxed, 1.75);
}

.form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 16px);
}

label {
  font-weight: 500;
  color: var(--color-text-primary, #24292f);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
  font-size: 16px;
}

input {
  padding: 14px 16px;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border, #e1e4e8);
  background: var(--color-surface, #ffffff);
  font-size: 18px;
  color: var(--color-text-primary, #24292f);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

input::placeholder {
  color: var(--color-text-muted, #8b949e);
}

input:focus {
  outline: none;
  border-color: var(--color-primary, #2563eb);
  box-shadow: 0 0 0 3px var(--color-primary-light, #eff6ff);
}

.form > button[type="submit"] {
  margin-top: var(--spacing-sm, 8px);
  background: var(--color-primary, #2563eb);
  color: #ffffff;
  padding: 14px 24px;
  border: none;
  border-radius: var(--radius-md, 8px);
  font-size: 18px;
  font-weight: 600;
  transition: background-color 0.15s ease;
}

.form > button[type="submit"]:hover:not(:disabled) {
  background: var(--color-primary-hover, #1d4ed8);
}

.form > button[type="submit"]:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hint {
  margin-top: var(--spacing-lg, 24px);
  color: var(--color-text-secondary, #57606a);
  text-align: center;
  font-size: 15px;
}

.hint a {
  color: var(--color-primary, #2563eb);
  font-weight: 600;
}

.hint a:hover {
  text-decoration: underline;
}

.error {
  margin-top: var(--spacing-md, 16px);
  padding: var(--spacing-sm, 8px) var(--spacing-md, 16px);
  background: var(--color-error-bg, #fef2f2);
  color: var(--color-error, #dc2626);
  text-align: center;
  font-size: 15px;
  border-radius: var(--radius-sm, 6px);
  border: 1px solid rgba(220, 38, 38, 0.2);
}
</style>
