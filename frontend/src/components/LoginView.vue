<template>
  <div class="auth-layout">
    <div class="panel">
      <div class="header">
        <div class="logo-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 3v18h18"/>
            <path d="M18 17V9"/>
            <path d="M13 17V5"/>
            <path d="M8 17v-3"/>
          </svg>
        </div>
        <h1>无障碍图表组件开发工具</h1>
        <p class="subtitle">登录以继续使用</p>
      </div>
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: var(--spacing-lg, 24px);
}

.panel {
  width: 100%;
  max-width: 420px;
  background: var(--color-surface, #ffffff);
  border-radius: var(--radius-lg, 16px);
  padding: 40px 36px;
  border: none;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 8px 25px rgba(0, 0, 0, 0.1);
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.35);
}

.logo-icon svg {
  width: 32px;
  height: 32px;
  color: #ffffff;
}

h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary, #24292f);
  letter-spacing: -0.02em;
  text-align: center;
  line-height: 1.3;
}

.subtitle {
  margin: 12px 0 0;
  color: var(--color-text-secondary, #57606a);
  font-size: 15px;
  line-height: 1.5;
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
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
}

.form > button[type="submit"] {
  margin-top: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #ffffff;
  padding: 14px 24px;
  border: none;
  border-radius: var(--radius-md, 8px);
  font-size: 18px;
  font-weight: 600;
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.35);
  cursor: pointer;
}

.form > button[type="submit"]:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.45);
}

.form > button[type="submit"]:active:not(:disabled) {
  transform: translateY(0);
}

.form > button[type="submit"]:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.hint {
  margin-top: var(--spacing-lg, 24px);
  color: var(--color-text-secondary, #57606a);
  text-align: center;
  font-size: 15px;
}

.hint a {
  color: #667eea;
  font-weight: 600;
  transition: color 0.15s ease;
}

.hint a:hover {
  color: #764ba2;
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
