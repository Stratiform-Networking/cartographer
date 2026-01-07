<template>
  <div
    class="h-screen flex items-center justify-center bg-white dark:bg-slate-950 relative overflow-hidden transition-colors"
  >
    <!-- Animated background elements -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div
        class="absolute top-1/4 -left-20 w-72 h-72 bg-cyan-400/10 dark:bg-cyan-500/10 rounded-full blur-3xl animate-pulse"
      />
      <div
        class="absolute bottom-1/4 -right-20 w-80 h-80 bg-blue-400/10 dark:bg-blue-500/10 rounded-full blur-3xl animate-pulse"
        style="animation-delay: 1s"
      />
    </div>

    <div class="relative text-center">
      <!-- App Logo -->
      <div
        class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-[#0fb685] to-[#0994ae] rounded-2xl shadow-lg shadow-[#0fb685]/30 mb-6"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-8 w-8 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
          />
        </svg>
      </div>

      <!-- Status -->
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white tracking-tight mb-2">
        {{ statusTitle }}
      </h1>

      <!-- Error Message -->
      <div
        v-if="error"
        class="mt-4 p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl max-w-md mx-auto"
      >
        <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
        <button
          @click="goToLogin"
          class="mt-4 px-4 py-2 text-sm text-cyan-600 dark:text-cyan-400 hover:text-cyan-500 dark:hover:text-cyan-300 font-medium"
        >
          Return to Login
        </button>
      </div>

      <!-- Loading Indicator -->
      <div v-else class="flex items-center justify-center gap-2 mt-4">
        <div class="flex gap-1">
          <span
            class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce"
            style="animation-delay: 0ms"
          ></span>
          <span
            class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce"
            style="animation-delay: 150ms"
          ></span>
          <span
            class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce"
            style="animation-delay: 300ms"
          ></span>
        </div>
      </div>
      <p v-if="!error" class="text-sm text-slate-500 dark:text-slate-400 mt-3">
        Completing sign in...
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '../composables/useAuth';
import * as authApi from '../api/auth';

const router = useRouter();
const { loginWithClerkToken, fetchAuthConfig } = useAuth();

const statusTitle = ref('Completing Sign In');
const error = ref<string | null>(null);

function goToLogin() {
  router.push('/');
}

onMounted(async () => {
  try {
    // Get auth config first
    const config = await fetchAuthConfig();

    if (config.provider !== 'cloud' || !config.clerk_publishable_key) {
      error.value = 'OAuth is not enabled for this instance.';
      statusTitle.value = 'OAuth Error';
      return;
    }

    // Initialize Clerk to handle the callback
    const { Clerk } = await import('@clerk/clerk-js');
    const clerk = new Clerk(config.clerk_publishable_key);
    await clerk.load();

    // Handle the OAuth callback - Clerk processes the URL params
    await clerk.handleRedirectCallback();

    // After handling the callback, check if we have a session
    if (clerk.session) {
      statusTitle.value = 'Signing In';

      // Get the session token
      const token = await clerk.session.getToken();

      if (token) {
        // Exchange the Clerk token for our local JWT
        await loginWithClerkToken(token);

        // Redirect to home page
        statusTitle.value = 'Success!';
        router.push('/');
      } else {
        throw new Error('No session token available');
      }
    } else {
      throw new Error('No active session after OAuth callback');
    }
  } catch (e: any) {
    console.error('[OAuth] Callback error:', e);
    error.value = e.message || 'Failed to complete sign in. Please try again.';
    statusTitle.value = 'Sign In Failed';
  }
});
</script>
