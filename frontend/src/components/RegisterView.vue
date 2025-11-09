<template>
  <div class="auth-layout">
    <div class="panel">
      <h1>Create your account</h1>
      <p class="subtitle">Join the platform and generate accessible chart components.</p>
      <form @submit.prevent="handleSubmit" class="form">
        <label>
          Name
          <input v-model="name" type="text" required placeholder="Jane Doe" />
        </label>
        <label>
          Email
          <input v-model="email" type="email" required placeholder="you@example.com" />
        </label>
        <label>
          Password
          <input v-model="password" type="password" required placeholder="••••••••" />
        </label>
        <button type="submit" :disabled="loading">
          <span v-if="loading">Creating account...</span>
          <span v-else>Register</span>
        </button>
      </form>
      <p class="hint">
        Already have an account?
        <router-link to="/login">Sign in</router-link>
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
    message.value = 'Account created. Redirecting to sign in...';
    setTimeout(() => router.push('/login'), 1200);
  } catch (err) {
    error.value = err.response?.data?.message || 'Unable to register.';
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
