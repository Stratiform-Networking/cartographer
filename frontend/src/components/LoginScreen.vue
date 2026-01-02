<template>
  <div
    class="min-h-screen bg-white dark:bg-slate-950 flex items-center justify-center p-6 transition-colors relative overflow-hidden"
  >
    <!-- Background effects -->
    <div
      class="fixed inset-0 bg-mesh-gradient-light dark:bg-mesh-gradient opacity-50 dark:opacity-50 pointer-events-none"
    />
    <div
      class="fixed top-0 right-0 w-[600px] h-[600px] bg-cyan-400/5 dark:bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"
    />
    <div
      class="fixed bottom-0 left-0 w-[600px] h-[600px] bg-blue-400/5 dark:bg-blue-600/5 rounded-full blur-3xl pointer-events-none"
    />

    <div class="relative z-10 w-full max-w-md">
      <!-- Logo/Header -->
      <router-link to="/" class="flex items-center justify-center gap-3 mb-10">
        <div
          class="w-12 h-12 bg-gradient-to-br from-[#0fb685] to-[#0994ae] rounded-2xl flex items-center justify-center shadow-lg shadow-[#0fb685]/30"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-6 w-6 text-white"
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
        <span class="text-2xl font-display font-bold text-slate-900 dark:text-white"
          >Cartographer</span
        >
      </router-link>

      <!-- Login Card -->
      <div class="glass-card p-8 border-gradient">
        <div class="text-center mb-8">
          <h1 class="text-2xl font-display font-bold text-slate-900 dark:text-white mb-2">
            Welcome back
          </h1>
          <p class="text-slate-500 dark:text-slate-400">Sign in to access your network map</p>
        </div>

        <form @submit.prevent="onSubmit" class="space-y-5">
          <!-- Username -->
          <div>
            <label
              for="username"
              class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
            >
              Username
            </label>
            <input
              id="username"
              v-model="form.username"
              type="text"
              required
              autocomplete="username"
              class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
              placeholder="Enter your username"
              :disabled="isSubmitting"
              @keydown.enter="focusPassword"
            />
          </div>

          <!-- Password -->
          <div>
            <label
              for="password"
              class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
            >
              Password
            </label>
            <div class="relative">
              <input
                ref="passwordInput"
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                required
                autocomplete="current-password"
                class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow pr-12"
                placeholder="••••••••"
                :disabled="isSubmitting"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              >
                <svg
                  v-if="showPassword"
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                  />
                </svg>
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
              </button>
            </div>
          </div>

          <!-- Error Message -->
          <Transition
            enter-active-class="transition duration-200"
            enter-from-class="opacity-0 -translate-y-2"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition duration-150"
            leave-from-class="opacity-100"
            leave-to-class="opacity-0"
          >
            <div
              v-if="errorMessage"
              class="p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl"
            >
              <p class="text-sm text-red-600 dark:text-red-400">{{ errorMessage }}</p>
            </div>
          </Transition>

          <!-- Submit Button -->
          <button
            type="submit"
            :disabled="isSubmitting || !isValid"
            class="w-full py-3.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-xl shadow-lg shadow-cyan-500/25 transition-all hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-900"
          >
            <span v-if="isSubmitting" class="flex items-center justify-center gap-2">
              <svg
                class="animate-spin h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Signing in...
            </span>
            <span v-else>Sign In</span>
          </button>
        </form>

        <div class="mt-6 text-center">
          <p class="text-slate-500 dark:text-slate-400">
            Don't have an account?
            <a
              href="/signup"
              class="text-cyan-600 dark:text-cyan-400 hover:text-cyan-500 dark:hover:text-cyan-300 transition-colors font-medium"
            >
              Sign up
            </a>
          </p>
        </div>
      </div>

      <!-- Footer -->
      <p class="text-center text-slate-400 dark:text-slate-500 text-sm mt-8">
        Secure access to your network infrastructure
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue';
import { useAuth } from '../composables/useAuth';

const emit = defineEmits<{
  (e: 'success'): void;
}>();

const { login } = useAuth();

const form = ref({
  username: '',
  password: '',
});

const passwordInput = ref<HTMLInputElement | null>(null);
const showPassword = ref(false);
const isSubmitting = ref(false);
const errorMessage = ref<string | null>(null);

const isValid = computed(() => {
  return form.value.username.length > 0 && form.value.password.length > 0;
});

function focusPassword() {
  passwordInput.value?.focus();
}

async function onSubmit() {
  if (!isValid.value) return;

  isSubmitting.value = true;
  errorMessage.value = null;

  try {
    await login({
      username: form.value.username,
      password: form.value.password,
    });

    emit('success');
  } catch (e: any) {
    errorMessage.value = e.message || 'Invalid username or password';
  } finally {
    isSubmitting.value = false;
  }
}
</script>
