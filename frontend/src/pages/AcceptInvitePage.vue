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
      <div class="flex items-center justify-center gap-3 mb-10">
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
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="glass-card p-8 border-gradient text-center">
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
      <div v-else-if="error" class="glass-card p-8 border-gradient text-center">
        <div
          class="w-14 h-14 mx-auto mb-5 rounded-xl bg-red-100 dark:bg-red-500/20 flex items-center justify-center"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-7 w-7 text-red-500 dark:text-red-400"
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
        <h2 class="text-xl font-display font-bold text-slate-900 dark:text-white mb-2">
          Invalid Invitation
        </h2>
        <p class="text-slate-600 dark:text-slate-400 mb-6">{{ error }}</p>
        <a
          href="/"
          class="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-xl shadow-lg shadow-cyan-500/25 transition-all hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98]"
        >
          Go to Login
        </a>
      </div>

      <!-- Success State -->
      <div v-else-if="success" class="glass-card p-8 border-gradient text-center">
        <div
          class="w-14 h-14 mx-auto mb-5 rounded-xl bg-green-100 dark:bg-green-500/20 flex items-center justify-center"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-7 w-7 text-green-500 dark:text-green-400"
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
        <h2 class="text-xl font-display font-bold text-slate-900 dark:text-white mb-2">
          Account Created!
        </h2>
        <p class="text-slate-600 dark:text-slate-400 mb-6">
          Your account has been created successfully. You can now log in with your credentials.
        </p>
        <a
          href="/"
          class="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-xl shadow-lg shadow-cyan-500/25 transition-all hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98]"
        >
          Go to Login
        </a>
      </div>

      <!-- Accept Invite Form -->
      <div v-else-if="inviteInfo" class="glass-card p-8 border-gradient">
        <div class="text-center mb-8">
          <h1 class="text-2xl font-display font-bold text-slate-900 dark:text-white mb-2">
            Accept Invitation
          </h1>
          <p class="text-slate-500 dark:text-slate-400">
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
        <form @submit.prevent="onSubmit" class="space-y-5">
          <div>
            <label
              for="email"
              class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >Email</label
            >
            <input
              id="email"
              type="email"
              :value="inviteInfo.email"
              disabled
              class="w-full px-4 py-3 bg-slate-100 dark:bg-slate-900/80 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-500 dark:text-slate-400 cursor-not-allowed"
            />
          </div>

          <div>
            <label
              for="username"
              class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >Username</label
            >
            <input
              id="username"
              v-model="form.username"
              type="text"
              required
              pattern="^[a-zA-Z][a-zA-Z0-9_-]*$"
              minlength="3"
              maxlength="50"
              class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
              placeholder="Choose a username"
            />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">
              Letters, numbers, underscores, and hyphens only
            </p>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label
                for="firstName"
                class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >First Name</label
              >
              <input
                id="firstName"
                v-model="form.firstName"
                type="text"
                required
                maxlength="50"
                class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
                placeholder="John"
              />
            </div>
            <div>
              <label
                for="lastName"
                class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >Last Name</label
              >
              <input
                id="lastName"
                v-model="form.lastName"
                type="text"
                required
                maxlength="50"
                class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
                placeholder="Doe"
              />
            </div>
          </div>

          <div>
            <label
              for="password"
              class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >Password</label
            >
            <input
              id="password"
              v-model="form.password"
              type="password"
              required
              minlength="8"
              class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
              placeholder="Enter a password"
            />
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5">Minimum 8 characters</p>
          </div>

          <div>
            <label
              for="confirmPassword"
              class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >Confirm Password</label
            >
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              type="password"
              required
              minlength="8"
              class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
              placeholder="Confirm your password"
            />
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
              v-if="formError"
              class="p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl"
            >
              <p class="text-sm text-red-600 dark:text-red-400">{{ formError }}</p>
            </div>
          </Transition>

          <button
            type="submit"
            :disabled="isSubmitting"
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
              Creating Account...
            </span>
            <span v-else>Create Account</span>
          </button>
        </form>

        <div class="mt-6 text-center">
          <p class="text-slate-500 dark:text-slate-400">
            Already have an account?
            <a
              href="/"
              class="text-cyan-600 dark:text-cyan-400 hover:text-cyan-500 dark:hover:text-cyan-300 transition-colors font-medium"
            >
              Sign in
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
import { ref, onMounted } from 'vue';
import { useHead } from '@unhead/vue';
import { useRoute } from 'vue-router';
import { useAuth } from '../composables/useAuth';
import type { InviteTokenInfo } from '../types/auth';
import { getRoleLabel } from '../types/auth';

useHead({
  title: 'Accept Invitation — Cartographer',
  meta: [
    {
      name: 'description',
      content: 'Accept your invitation to join a Cartographer network and start collaborating.',
    },
    { property: 'og:title', content: 'Accept Invitation — Cartographer' },
    {
      property: 'og:description',
      content: 'Accept your invitation to join a Cartographer network and start collaborating.',
    },
    { property: 'og:type', content: 'website' },
  ],
});

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
