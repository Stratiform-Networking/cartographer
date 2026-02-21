import { createRouter, createWebHistory } from 'vue-router';
import HomePage from './pages/HomePage.vue';
import NetworkPage from './pages/NetworkPage.vue';
import EmbedPage from './pages/EmbedPage.vue';
import AcceptInvitePage from './pages/AcceptInvitePage.vue';
import OAuthCallbackPage from './pages/OAuthCallbackPage.vue';
import ResetPasswordPage from './pages/ResetPasswordPage.vue';

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage,
  },
  {
    path: '/network/:id',
    name: 'network',
    component: NetworkPage,
    props: true,
  },
  {
    path: '/embed/:embedId',
    name: 'embed',
    component: EmbedPage,
    props: true,
  },
  {
    path: '/accept-invite',
    name: 'accept-invite',
    component: AcceptInvitePage,
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: ResetPasswordPage,
  },
  {
    path: '/oauth-callback',
    name: 'oauth-callback',
    component: OAuthCallbackPage,
  },
];

const router = createRouter({
  // Use BASE_URL from Vite (set via VITE_BASE_PATH env var, defaults to /)
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

export default router;
