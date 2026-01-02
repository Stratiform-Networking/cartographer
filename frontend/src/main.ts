import { createApp } from 'vue';
import { createPinia } from 'pinia';
import axios from 'axios';
import App from './App.vue';
import router from './router';
import { API_BASE } from './config';
import './style.css';

// Configure axios base URL for API calls
// When deployed under /app/, API calls should go to /app/api/...
axios.defaults.baseURL = API_BASE;

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
