import { defineStore } from 'pinia';
import axios from 'axios';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('act_user') || 'null'),
    token: localStorage.getItem('act_token') || ''
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token)
  },
  actions: {
    async login(credentials) {
      const { data } = await axios.post('/api/auth/login', credentials);
      this.user = data.user;
      this.token = data.access_token;
      localStorage.setItem('act_user', JSON.stringify(this.user));
      localStorage.setItem('act_token', this.token);
      axios.defaults.headers.common.Authorization = `Bearer ${this.token}`;
    },
    async register(payload) {
      await axios.post('/api/auth/register', payload);
    },
    async changePassword(payload) {
      await axios.post('/api/auth/change-password', payload);
    },
    logout() {
      this.user = null;
      this.token = '';
      localStorage.removeItem('act_user');
      localStorage.removeItem('act_token');
      delete axios.defaults.headers.common.Authorization;
    },
    initialise() {
      if (this.token) {
        axios.defaults.headers.common.Authorization = `Bearer ${this.token}`;
      }
    }
  }
});
