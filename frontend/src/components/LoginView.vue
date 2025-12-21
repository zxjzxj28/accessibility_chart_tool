<template>
  <div class="auth-layout">
    <div class="panel">
      <div class="header">
        <h1>无障碍图表组件开发工具</h1>
        <p class="subtitle">Accessible Chart Component Development Tool</p>
      </div>
      <form @submit.prevent="handleSubmit" class="form">
        <label>
          <span class="label-text">账号</span>
          <input v-model="identifier" type="text" required placeholder="请输入账号名称" />
        </label>
        <label>
          <span class="label-text">密码</span>
          <input v-model="password" type="password" required placeholder="请输入密码" />
        </label>
        <label class="remember-account">
          <input type="checkbox" v-model="rememberAccount" />
          <span>记住账号</span>
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
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const REMEMBER_KEY = 'act_remember_account';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const identifier = ref('');
const password = ref('');
const rememberAccount = ref(false);
const loading = ref(false);
const error = ref('');

onMounted(() => {
  const saved = localStorage.getItem(REMEMBER_KEY);
  if (saved) {
    identifier.value = saved;
    rememberAccount.value = true;
  }
});

const handleSubmit = async () => {
  loading.value = true;
  error.value = '';
  try {
    await auth.login({ identifier: identifier.value.trim(), password: password.value });

    // 保存或清除记住的账号
    if (rememberAccount.value) {
      localStorage.setItem(REMEMBER_KEY, identifier.value.trim());
    } else {
      localStorage.removeItem(REMEMBER_KEY);
    }

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

.remember-account {
  flex-direction: row;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  font-weight: 400;
  color: var(--color-text-secondary, #4b5563);
  font-size: 13px;
  cursor: pointer;
}

.remember-account input[type="checkbox"] {
  width: 15px;
  height: 15px;
  padding: 0;
  margin: 0;
  cursor: pointer;
  accent-color: var(--color-primary, #374151);
}

.form > button[type="submit"] {
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

.form > button[type="submit"]:hover:not(:disabled) {
  background: var(--color-primary-hover, #1f2937);
}

.form > button[type="submit"]:disabled {
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
</style>
