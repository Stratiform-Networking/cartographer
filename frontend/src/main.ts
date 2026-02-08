import { createApp } from 'vue';
import { createPinia } from 'pinia';
import axios from 'axios';
import App from './App.vue';
import router from './router';
import { API_BASE } from './config';
import { usePostHog } from './composables/usePostHog';
import './style.css';

// Configure axios base URL for API calls
// When deployed under /app/, API calls should go to /app/api/...
axios.defaults.baseURL = API_BASE;

const { posthog } = usePostHog();

try {
  const authState = localStorage.getItem('cartographer_auth');
  if (authState) {
    const parsed = JSON.parse(authState) as {
      user?: { id?: string; username?: string; email?: string };
    };
    const distinctId = parsed.user?.id || parsed.user?.username || parsed.user?.email;
    if (distinctId) {
      posthog.identify(distinctId, {
        username: parsed.user?.username,
        email: parsed.user?.email,
      });
    }
  }
} catch {
  // Ignore malformed local auth state.
}

router.afterEach((to) => {
  posthog.capture('$pageview', {
    app: 'cartographer',
    route_name: String(to.name || ''),
    path: to.fullPath,
  });
});

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
