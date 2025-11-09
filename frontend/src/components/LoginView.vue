<template>
  <div class="auth-layout">
    <div class="panel">
      <h1>Accessibility Chart Tool</h1>
      <p class="subtitle">Log in to manage your accessible chart conversions.</p>
      <form @submit.prevent="handleSubmit" class="form">
        <label>
          Email
          <input v-model="email" type="email" required placeholder="you@example.com" />
        </label>
        <label>
          Password
          <input v-model="password" type="password" required placeholder="••••••••" />
        </label>
        <button type="submit" :disabled="loading">
          <span v-if="loading">Signing in...</span>
          <span v-else>Sign In</span>
        </button>
      </form>
      <p class="hint">
        Don't have an account?
        <router-link to="/register">Create one</router-link>
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

const email = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

const handleSubmit = async () => {
  loading.value = true;
  error.value = '';
  try {
    await auth.login({ email: email.value, password: password.value });
    const redirect = route.query.redirect || '/';
    router.push(redirect);
  } catch (err) {
    error.value = err.response?.data?.message || 'Unable to log in.';
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
