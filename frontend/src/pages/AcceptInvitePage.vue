<template>
  <div
    class="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950 flex items-center justify-center p-4"
  >
    <div class="w-full max-w-md">
      <!-- Loading State -->
      <div
        v-if="isLoading"
        class="bg-white/95 dark:bg-slate-800/95 backdrop-blur-sm rounded-2xl shadow-2xl p-8 text-center border border-slate-200/80 dark:border-slate-700/80"
      >
        <!-- App Logo -->
        <div
          class="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-[#0fb685] to-[#0994ae] rounded-xl shadow-lg shadow-[#0fb685]/30 mb-5"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-7 w-7 text-white"
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

        <!-- Loading Indicator -->
        <div class="flex items-center justify-center gap-1.5 mb-3">
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
        <p class="text-sm text-slate-500 dark:text-slate-400">Verifying invitation...</p>
      </div>

      <!-- Invalid/Expired Token -->
      <div
        v-else-if="error"
        class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-8 text-center"
      >
        <div
          class="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-8 w-8 text-red-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">
          Invalid Invitation
        </h2>
        <p class="text-slate-600 dark:text-slate-400 mb-6">{{ error }}</p>
        <a
          href="/"
          class="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors"
        >
          Go to Login
        </a>
      </div>

      <!-- Success State -->
      <div
        v-else-if="success"
        class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-8 text-center"
      >
        <div
          class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-8 w-8 text-green-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">Account Created!</h2>
        <p class="text-slate-600 dark:text-slate-400 mb-6">
          Your account has been created successfully. You can now log in with your credentials.
        </p>
        <a
          href="/"
          class="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors"
        >
          Go to Login
        </a>
      </div>

      <!-- Accept Invite Form -->
      <div
        v-else-if="inviteInfo"
        class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl overflow-hidden"
      >
        <!-- Header -->
        <div class="px-8 py-6 bg-gradient-to-r from-cyan-600 to-teal-600 text-white text-center">
          <h1 class="text-2xl font-bold mb-1">🗺️ Cartographer</h1>
          <p class="text-cyan-100 text-sm">Network Mapping Tool</p>
        </div>

        <!-- Invitation Info -->
        <div class="px-8 pt-6 pb-4 border-b border-slate-200 dark:border-slate-700">
          <p class="text-slate-600 dark:text-slate-400 text-center">
            <strong class="text-slate-900 dark:text-white">{{ inviteInfo.invited_by_name }}</strong>
            has invited you to join with
            <span
              class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
              :class="getRoleBadgeClass(inviteInfo.role)"
            >
              {{ getRoleLabel(inviteInfo.role) }}
            </span>
            access.
          </p>
        </div>

        <!-- Form -->
        <form @submit.prevent="onSubmit" class="p-8 space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
              >Email</label
            >
            <input
              type="email"
              :value="inviteInfo.email"
              disabled
              class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-slate-100 dark:bg-slate-900 text-slate-500 dark:text-slate-400"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
              >Username</label
            >
            <input
              v-model="form.username"
              type="text"
              required
              pattern="^[a-zA-Z][a-zA-Z0-9_-]*$"
              minlength="3"
              maxlength="50"
              class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="Choose a username"
            />
            <p class="text-xs text-slate-500 mt-1">
              Letters, numbers, underscores, and hyphens only
            </p>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                >First Name</label
              >
              <input
                v-model="form.firstName"
                type="text"
                required
                maxlength="50"
                class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                placeholder="John"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                >Last Name</label
              >
              <input
                v-model="form.lastName"
                type="text"
                required
                maxlength="50"
                class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                placeholder="Doe"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
              >Password</label
            >
            <input
              v-model="form.password"
              type="password"
              required
              minlength="8"
              class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="••••••••"
            />
            <p class="text-xs text-slate-500 mt-1">Minimum 8 characters</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
              >Confirm Password</label
            >
            <input
              v-model="form.confirmPassword"
              type="password"
              required
              minlength="8"
              class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="••••••••"
            />
          </div>

          <div
            v-if="formError"
            class="p-3 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-500/50 rounded-lg"
          >
            <p class="text-sm text-red-600 dark:text-red-400">{{ formError }}</p>
          </div>

          <button
            type="submit"
            :disabled="isSubmitting"
            class="w-full px-4 py-3 bg-cyan-600 text-white font-medium rounded-lg hover:bg-cyan-700 disabled:opacity-50 transition-colors"
          >
            {{ isSubmitting ? 'Creating Account...' : 'Create Account' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuth } from '../composables/useAuth';
import type { InviteTokenInfo } from '../types/auth';
import { getRoleLabel } from '../types/auth';

const route = useRoute();
const { verifyInviteToken, acceptInvite } = useAuth();

const isLoading = ref(true);
const error = ref<string | null>(null);
const success = ref(false);
const inviteInfo = ref<InviteTokenInfo | null>(null);
const formError = ref<string | null>(null);
const isSubmitting = ref(false);

const form = ref({
  username: '',
  firstName: '',
  lastName: '',
  password: '',
  confirmPassword: '',
});

function getRoleBadgeClass(role: string): string {
  switch (role) {
    case 'readwrite':
      return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400';
    case 'readonly':
      return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
    default:
      return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
  }
}

async function verifyToken() {
  const token = route.query.token as string;

  if (!token) {
    error.value = 'No invitation token provided';
    isLoading.value = false;
    return;
  }

  try {
    const info = await verifyInviteToken(token);

    if (!info.is_valid) {
      error.value = 'This invitation has expired or is no longer valid';
      isLoading.value = false;
      return;
    }

    inviteInfo.value = info;
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Invalid invitation token';
  } finally {
    isLoading.value = false;
  }
}

async function onSubmit() {
  formError.value = null;

  // Validate passwords match
  if (form.value.password !== form.value.confirmPassword) {
    formError.value = 'Passwords do not match';
    return;
  }

  const token = route.query.token as string;
  if (!token) {
    formError.value = 'Missing invitation token';
    return;
  }

  isSubmitting.value = true;

  try {
    await acceptInvite({
      token,
      username: form.value.username,
      first_name: form.value.firstName,
      last_name: form.value.lastName,
      password: form.value.password,
    });

    success.value = true;
  } catch (e: unknown) {
    formError.value = e instanceof Error ? e.message : 'Failed to create account';
  } finally {
    isSubmitting.value = false;
  }
}

onMounted(() => {
  verifyToken();
});
</script>
