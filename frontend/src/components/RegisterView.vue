<template>
  <div class="auth-layout">
    <div class="panel">
      <div class="header">
        <div class="logo-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none">
            <!-- 图表背景圆形 -->
            <circle cx="32" cy="32" r="30" fill="url(#logoGradientReg)" />
            <!-- 坐标轴 -->
            <path d="M16 48V16" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
            <path d="M16 48H48" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
            <!-- 柱状图 -->
            <rect x="22" y="34" width="6" height="14" rx="2" fill="white" opacity="0.9"/>
            <rect x="32" y="24" width="6" height="24" rx="2" fill="white"/>
            <rect x="42" y="30" width="6" height="18" rx="2" fill="white" opacity="0.9"/>
            <!-- 无障碍眼睛符号 -->
            <ellipse cx="32" cy="20" rx="8" ry="5" stroke="white" stroke-width="2" fill="none"/>
            <circle cx="32" cy="20" r="2.5" fill="white"/>
            <!-- 渐变定义 -->
            <defs>
              <linearGradient id="logoGradientReg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#0ea5e9"/>
                <stop offset="100%" stop-color="#2dd4bf"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1>创建你的账号</h1>
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
  background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
  padding: var(--spacing-lg, 24px);
}

.panel {
  width: 100%;
  max-width: 480px;
  background: var(--color-surface, #ffffff);
  border-radius: var(--radius-lg, 16px);
  padding: 32px 40px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.04);
}

.header {
  text-align: center;
  margin-bottom: 24px;
}

.logo-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon svg {
  width: 64px;
  height: 64px;
}

h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary, #24292f);
  letter-spacing: -0.02em;
  text-align: center;
  line-height: 1.3;
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
  padding: 12px 14px;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border, #e1e4e8);
  background: var(--color-surface, #ffffff);
  font-size: 16px;
  color: var(--color-text-primary, #24292f);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

input::placeholder {
  color: var(--color-text-muted, #8b949e);
}

input:focus {
  outline: none;
  border-color: #0ea5e9;
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.15);
}

button[type="submit"] {
  margin-top: 4px;
  background: linear-gradient(135deg, #0ea5e9 0%, #2dd4bf 100%);
  color: #ffffff;
  padding: 12px 24px;
  border: none;
  border-radius: var(--radius-md, 8px);
  font-size: 16px;
  font-weight: 600;
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
  box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3);
  cursor: pointer;
}

button[type="submit"]:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(14, 165, 233, 0.4);
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
  color: #0ea5e9;
  font-weight: 600;
  transition: color 0.15s ease;
}

.hint a:hover {
  color: #0284c7;
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
