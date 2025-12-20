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
        <h1>创建你的账号</h1>
        <p class="subtitle">注册以开始使用无障碍图表工具</p>
      </div>
      <form @submit.prevent="handleSubmit" class="form">
        <label>
          账号
          <input v-model="username" type="text" required placeholder="请输入账号名称" />
        </label>
        <label>
          邮箱
          <input v-model="email" type="email" required placeholder="请输入邮箱地址" />
        </label>
        <label>
          密码
          <input v-model="password" type="password" required placeholder="••••••••" />
        </label>
        <label>
          确认密码
          <input v-model="confirmPassword" type="password" required placeholder="请再次输入密码" />
        </label>
        <button type="submit" :disabled="loading">
          <span v-if="loading">正在创建账号...</span>
          <span v-else>注册</span>
        </button>
      </form>
      <p class="hint">
        已经有账号了？
        <router-link to="/login">前往登录</router-link>
      </p>
      <p v-if="message" class="success">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const auth = useAuthStore();

const email = ref('');
const username = ref('');
const password = ref('');
const confirmPassword = ref('');
const loading = ref(false);
const error = ref('');
const message = ref('');

const handleSubmit = async () => {
  loading.value = true;
  error.value = '';
  message.value = '';
  if (password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致。';
    loading.value = false;
    return;
  }

  try {
    await auth.register({
      email: email.value,
      username: username.value,
      password: password.value
    });
    message.value = '账号已创建，即将跳转到登录页...';
    setTimeout(() => router.push('/login'), 1200);
  } catch (err) {
    error.value = err.response?.data?.message || '注册失败，请稍后重试。';
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

button[type="submit"] {
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

button[type="submit"]:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.45);
}

button[type="submit"]:active:not(:disabled) {
  transform: translateY(0);
}

button[type="submit"]:disabled {
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

.success {
  margin-top: var(--spacing-md, 16px);
  padding: var(--spacing-sm, 8px) var(--spacing-md, 16px);
  background: var(--color-success-bg, #f0fdf4);
  color: var(--color-success, #16a34a);
  text-align: center;
  font-size: 15px;
  border-radius: var(--radius-sm, 6px);
  border: 1px solid rgba(22, 163, 74, 0.2);
}
</style>
