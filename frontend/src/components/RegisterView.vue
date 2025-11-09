<template>
  <div class="auth-layout">
    <div class="panel">
      <h1>创建你的账号</h1>
      <p class="subtitle">加入平台，生成可复用的无障碍图表组件。</p>
      <form @submit.prevent="handleSubmit" class="form">
        <label>
          姓名
          <input v-model="name" type="text" required placeholder="张三" />
        </label>
        <label>
          邮箱
          <input v-model="email" type="email" required placeholder="you@example.com" />
        </label>
        <label>
          密码
          <input v-model="password" type="password" required placeholder="••••••••" />
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

const name = ref('');
const email = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');
const message = ref('');

const handleSubmit = async () => {
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    await auth.register({ name: name.value, email: email.value, password: password.value });
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
  background: radial-gradient(circle at top, #ffe8d6, #fdf2e9 60%);
}

.panel {
  width: min(440px, 90%);
  background: white;
  border-radius: 18px;
  padding: 36px;
  box-shadow: 0 25px 45px rgba(204, 102, 51, 0.15);
}

h1 {
  margin: 0;
  font-size: 1.8rem;
  color: #a05a2c;
}

.subtitle {
  margin: 8px 0 24px;
  color: #c08a5b;
}

.form {
  display: grid;
  gap: 18px;
}

label {
  font-weight: 600;
  color: #7f3b1d;
  display: grid;
  gap: 6px;
  font-size: 0.95rem;
}

input {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #f3d9c2;
  background: #fff7f0;
  font-size: 1rem;
}

input:focus {
  outline: none;
  border-color: #f57c00;
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.2);
}

button {
  background: linear-gradient(135deg, #f57c00, #ff9800);
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
  box-shadow: 0 12px 25px rgba(245, 124, 0, 0.35);
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.hint {
  margin-top: 18px;
  color: #b26a3c;
  text-align: center;
}

.hint a {
  color: #f57c00;
  font-weight: 600;
}

.error {
  margin-top: 16px;
  color: #d64545;
  text-align: center;
}

.success {
  margin-top: 16px;
  color: #0f766e;
  text-align: center;
}
</style>
