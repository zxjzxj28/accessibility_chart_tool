<template>
  <div class="auth-layout">
    <div class="panel">
      <h1>创建你的账号</h1>
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
  text-align: center;
}

.form {
  display: grid;
  gap: 18px;
  margin-top: 20px;
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

.success {
  margin-top: 16px;
  color: #0f766e;
  text-align: center;
}
</style>
