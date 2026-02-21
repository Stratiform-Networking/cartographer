<template>
  <div
    class="min-h-screen bg-white dark:bg-slate-950 flex items-center justify-center p-6 transition-colors relative overflow-hidden"
  >
    <div
      class="fixed inset-0 bg-mesh-gradient-light dark:bg-mesh-gradient opacity-50 pointer-events-none"
    />
    <div
      class="fixed top-0 right-0 w-[600px] h-[600px] bg-cyan-400/5 dark:bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"
    />
    <div
      class="fixed bottom-0 left-0 w-[600px] h-[600px] bg-blue-400/5 dark:bg-blue-600/5 rounded-full blur-3xl pointer-events-none"
    />

    <div class="relative z-10 w-full max-w-md">
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

      <div class="glass-card p-8 border-gradient">
        <div class="text-center mb-8">
          <h1 class="text-2xl font-display font-bold text-slate-900 dark:text-white mb-2">
            {{ isConfirmMode ? 'Set a new password' : 'Reset your password' }}
          </h1>
          <p class="text-slate-500 dark:text-slate-400">
            {{
              isConfirmMode
                ? 'Create a new password for your account.'
                : 'Enter your account email and we will send a reset link.'
            }}
          </p>
        </div>

        <form v-if="!successMessage" @submit.prevent="onSubmit" class="space-y-5">
          <div v-if="!isConfirmMode">
            <label
              for="email"
              class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
            >
              Email
            </label>
            <input
              id="email"
              v-model="requestForm.email"
              type="email"
              required
              autocomplete="email"
              class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
              placeholder="you@example.com"
              :disabled="isSubmitting"
            />
          </div>

          <template v-else>
            <div>
              <label
                for="new-password"
                class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >
                New Password
              </label>
              <input
                id="new-password"
                v-model="confirmForm.newPassword"
                type="password"
                required
                minlength="8"
                autocomplete="new-password"
                class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
                placeholder="At least 8 characters"
                :disabled="isSubmitting"
              />
            </div>

            <div>
              <label
                for="confirm-password"
                class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >
                Confirm Password
              </label>
              <input
                id="confirm-password"
                v-model="confirmForm.confirmPassword"
                type="password"
                required
                minlength="8"
                autocomplete="new-password"
                class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
                placeholder="Re-enter your new password"
                :disabled="isSubmitting"
              />
            </div>
          </template>

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

          <button
            type="submit"
            :disabled="isSubmitting"
            class="w-full py-3.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-xl shadow-lg shadow-cyan-500/25 transition-all hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-900"
          >
            <span v-if="isSubmitting">{{ isConfirmMode ? 'Resetting...' : 'Sending...' }}</span>
            <span v-else>{{ isConfirmMode ? 'Reset Password' : 'Send Reset Link' }}</span>
          </button>
        </form>

        <div
          v-else
          class="p-4 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 rounded-xl"
        >
          <p class="text-sm text-emerald-700 dark:text-emerald-300">{{ successMessage }}</p>
        </div>

        <div class="mt-6 text-center">
          <router-link
            to="/"
            class="text-cyan-600 dark:text-cyan-400 hover:text-cyan-500 dark:hover:text-cyan-300 transition-colors font-medium"
          >
            Back to sign in
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { confirmPasswordReset, requestPasswordReset } from '../api/auth';
import { extractErrorMessage } from '../api/client';

const route = useRoute();

const token = ref('');
const isSubmitting = ref(false);
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);

const requestForm = ref({
  email: '',
});

const confirmForm = ref({
  newPassword: '',
  confirmPassword: '',
});

const isConfirmMode = computed(() => token.value.length > 0);

watch(
  () => route.query.token,
  (value) => {
    token.value = typeof value === 'string' ? value : '';
    errorMessage.value = null;
    successMessage.value = null;
  },
  { immediate: true }
);

async function onSubmit() {
  errorMessage.value = null;
  successMessage.value = null;
  isSubmitting.value = true;

  try {
    if (!isConfirmMode.value) {
      await requestPasswordReset({
        email: requestForm.value.email.trim(),
      });
      successMessage.value =
        'If an account with that email exists, a password reset link has been sent.';
      return;
    }

    if (confirmForm.value.newPassword.length < 8) {
      throw new Error('Password must be at least 8 characters.');
    }

    if (confirmForm.value.newPassword !== confirmForm.value.confirmPassword) {
      throw new Error('Passwords do not match.');
    }

    await confirmPasswordReset({
      token: token.value,
      new_password: confirmForm.value.newPassword,
    });

    successMessage.value = 'Your password has been reset. You can now sign in.';
  } catch (e) {
    errorMessage.value = extractErrorMessage(e);
  } finally {
    isSubmitting.value = false;
  }
}
</script>
