<template>
  <div class="auth-layout">
    <div class="panel">
      <h1>无障碍图表工具</h1>
      <p class="subtitle">登录以管理你的无障碍图表转换任务。</p>
      <form @submit.prevent="handleSubmit" class="form">
        <div class="toggle-group">
          <button type="button" :class="{ active: mode === 'email' }" @click="mode = 'email'">邮箱登录</button>
          <button type="button" :class="{ active: mode === 'account' }" @click="mode = 'account'">账号登录</button>
        </div>
        <label v-if="mode === 'email'">
          邮箱
          <input v-model="identifier" type="email" required placeholder="请输入邮箱地址" />
        </label>
        <label v-else>
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
const mode = ref('email');

const handleSubmit = async () => {
  loading.value = true;
  error.value = '';
  try {
    const value = mode.value === 'email' ? identifier.value.trim().toLowerCase() : identifier.value.trim();
    await auth.login({ identifier: value, password: password.value });
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
  background: radial-gradient(circle at top, #e0e8ff, #f4f6fb 60%);
}

.panel {
  width: min(420px, 90%);
  background: white;
  border-radius: 18px;
  padding: 36px;
  box-shadow: 0 25px 45px rgba(15, 23, 42, 0.08);
}

h1 {
  margin: 0;
  font-size: 1.8rem;
  color: #102a43;
}

.subtitle {
  margin: 8px 0 24px;
  color: #829ab1;
}

.form {
  display: grid;
  gap: 18px;
}

.toggle-group {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.toggle-group button {
  border: 1px solid #d9e2ec;
  background: #f8fafc;
  border-radius: 10px;
  padding: 10px 12px;
  font-weight: 600;
  color: #486581;
}

.toggle-group button.active {
  background: linear-gradient(135deg, #4c6ef5, #2b8aeb);
  color: white;
  border-color: #4c6ef5;
}

label {
  font-weight: 600;
  color: #243b53;
  display: grid;
  gap: 6px;
  font-size: 0.95rem;
}

input {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #d9e2ec;
  background: #f8fafc;
  font-size: 1rem;
}

input:focus {
  outline: none;
  border-color: #4c6ef5;
  box-shadow: 0 0 0 3px rgba(76, 110, 245, 0.2);
}

button {
  background: linear-gradient(135deg, #4c6ef5, #2b8aeb);
  color: white;
  padding: 12px 16px;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

button:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 25px rgba(76, 110, 245, 0.3);
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.hint {
  margin-top: 18px;
  color: #486581;
  text-align: center;
}

.hint a {
  color: #4c6ef5;
  font-weight: 600;
}

.error {
  margin-top: 16px;
  color: #d64545;
  text-align: center;
}
</style>
