<template>
  <div class="auth-layout">
    <div class="panel">
      <div class="header">
        <h1>创建账号</h1>
        <p class="subtitle">Create Your Account</p>
      </div>
      <form @submit.prevent="handleSubmit" class="form">
        <label>
          <span class="label-text">账号</span>
          <input v-model="username" type="text" required placeholder="请输入账号名称" />
        </label>
        <label>
          <span class="label-text">邮箱</span>
          <input v-model="email" type="email" required placeholder="请输入邮箱地址" />
        </label>
        <label>
          <span class="label-text">密码</span>
          <input v-model="password" type="password" required placeholder="请输入密码" />
        </label>
        <label>
          <span class="label-text">确认密码</span>
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
  background: var(--color-bg, #f5f6f7);
  padding: var(--spacing-lg, 24px);
}

.panel {
  width: 100%;
  max-width: 400px;
  background: var(--color-surface, #ffffff);
  border-radius: var(--radius-lg, 8px);
  padding: 32px;
  border: 1px solid var(--color-border, #d1d5db);
  box-shadow: var(--shadow-md, 0 2px 8px rgba(0, 0, 0, 0.06));
}

.header {
  text-align: center;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border-light, #e5e7eb);
}

h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary, #1f2937);
  letter-spacing: -0.01em;
  line-height: 1.4;
}

.subtitle {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--color-text-muted, #6b7280);
  letter-spacing: 0.02em;
}

.form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 16px);
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label-text {
  font-weight: 500;
  color: var(--color-text-primary, #1f2937);
  font-size: 14px;
}

input[type="text"],
input[type="email"],
input[type="password"] {
  padding: 10px 12px;
  border-radius: var(--radius-md, 6px);
  border: 1px solid var(--color-border, #d1d5db);
  background: var(--color-surface, #ffffff);
  font-size: 14px;
  color: var(--color-text-primary, #1f2937);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

input::placeholder {
  color: var(--color-text-muted, #6b7280);
}

input:focus {
  outline: none;
  border-color: var(--color-primary, #374151);
  box-shadow: 0 0 0 2px rgba(55, 65, 81, 0.1);
}

button[type="submit"] {
  margin-top: 4px;
  background: var(--color-primary, #374151);
  color: #ffffff;
  padding: 11px 20px;
  border: none;
  border-radius: var(--radius-md, 6px);
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.15s ease;
  cursor: pointer;
}

button[type="submit"]:hover:not(:disabled) {
  background: var(--color-primary-hover, #1f2937);
}

button[type="submit"]:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hint {
  margin-top: var(--spacing-lg, 24px);
  color: var(--color-text-secondary, #4b5563);
  text-align: center;
  font-size: 13px;
}

.hint a {
  color: var(--color-accent, #2563eb);
  font-weight: 500;
  transition: color 0.15s ease;
}

.hint a:hover {
  color: var(--color-accent-hover, #1d4ed8);
  text-decoration: underline;
}

.error {
  margin-top: var(--spacing-md, 16px);
  padding: 10px 14px;
  background: var(--color-error-bg, #fef2f2);
  color: var(--color-error, #dc2626);
  text-align: center;
  font-size: 13px;
  border-radius: var(--radius-sm, 4px);
  border: 1px solid rgba(220, 38, 38, 0.15);
}

.success {
  margin-top: var(--spacing-md, 16px);
  padding: 10px 14px;
  background: var(--color-success-bg, #ecfdf5);
  color: var(--color-success, #059669);
  text-align: center;
  font-size: 13px;
  border-radius: var(--radius-sm, 4px);
  border: 1px solid rgba(5, 150, 105, 0.15);
}
</style>
