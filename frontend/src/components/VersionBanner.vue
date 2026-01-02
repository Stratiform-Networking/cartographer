<template>
  <Transition
    enter-active-class="transform transition-all duration-300 ease-out"
    enter-from-class="-translate-y-full opacity-0"
    enter-to-class="translate-y-0 opacity-100"
    leave-active-class="transform transition-all duration-200 ease-in"
    leave-from-class="translate-y-0 opacity-100"
    leave-to-class="-translate-y-full opacity-0"
  >
    <div
      v-if="shouldShowBanner"
      :class="[
        'relative z-50 flex items-center justify-center gap-3 px-4 py-2 text-sm font-medium cursor-pointer',
        'transition-colors duration-200',
        bannerClasses,
      ]"
      @click="openChangelog"
    >
      <!-- Update icon -->
      <div class="flex-shrink-0">
        <svg
          v-if="versionInfo.updateType === 'major'"
          class="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
          />
        </svg>
        <svg
          v-else-if="versionInfo.updateType === 'minor'"
          class="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <svg
          v-else
          class="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      </div>

      <!-- Message -->
      <span>
        <strong>{{ getUpdateTypeLabel(versionInfo.updateType) }}</strong>
        available — v{{ versionInfo.latest }}
        <span class="hidden sm:inline opacity-75">(you're on v{{ versionInfo.current }})</span>
      </span>

      <!-- View changelog hint -->
      <span
        class="hidden md:inline-flex items-center gap-1 opacity-75 hover:opacity-100 transition-opacity"
      >
        <span>View changelog</span>
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
          />
        </svg>
      </span>

      <!-- Close button -->
      <button
        @click.stop="dismissUpdate"
        class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors hover:bg-black/10 dark:hover:bg-white/10"
        title="Dismiss this notification"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <!-- Settings button -->
      <button
        @click.stop="showSettings = true"
        class="absolute right-10 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors hover:bg-black/10 dark:hover:bg-white/10"
        title="Configure update notifications"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      </button>
    </div>
  </Transition>

  <!-- Settings Modal -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showSettings"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/60"
        @click.self="showSettings = false"
      >
        <Transition
          enter-active-class="transition-all duration-200"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition-all duration-150"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="showSettings"
            class="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden"
          >
            <!-- Header -->
            <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <h3 class="text-lg font-semibold text-slate-900 dark:text-white">
                Update Notifications
              </h3>
              <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Choose which types of updates you want to be notified about
              </p>
            </div>

            <!-- Options -->
            <div class="px-6 py-4 space-y-3">
              <label
                v-for="option in versionOptions"
                :key="option.type"
                class="flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors"
                :class="[
                  isTypeEnabled(option.type)
                    ? 'bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800'
                    : 'bg-slate-50 dark:bg-slate-700/50 border border-transparent hover:bg-slate-100 dark:hover:bg-slate-700',
                ]"
              >
                <input
                  type="checkbox"
                  :checked="isTypeEnabled(option.type)"
                  @change="toggleVersionType(option.type)"
                  class="mt-0.5 h-4 w-4 rounded border-slate-300 dark:border-slate-600 text-cyan-600 focus:ring-cyan-500 focus:ring-offset-0 dark:bg-slate-700"
                />
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="font-medium text-slate-900 dark:text-white">
                      {{ option.label }}
                    </span>
                    <span :class="['text-xs px-1.5 py-0.5 rounded font-medium', option.badgeClass]">
                      {{ option.badge }}
                    </span>
                  </div>
                  <p class="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                    {{ option.description }}
                  </p>
                </div>
              </label>
            </div>

            <!-- Footer -->
            <div
              class="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between"
            >
              <button
                @click="clearDismissed"
                class="text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
              >
                Reset dismissed
              </button>
              <button
                @click="showSettings = false"
                class="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue';
import { useVersionCheck, type VersionType } from '../composables/useVersionCheck';

const {
  versionInfo,
  shouldShowBanner,
  dismissUpdate,
  toggleVersionType,
  isTypeEnabled,
  clearDismissed,
  getUpdateTypeLabel,
  CHANGELOG_URL,
} = useVersionCheck();

const showSettings = ref(false);

// Version type options for settings
const versionOptions = [
  {
    type: 'major' as VersionType,
    label: 'Major Updates',
    badge: 'x.0.0',
    badgeClass: 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-400',
    description: 'Significant changes, new features, or breaking changes',
  },
  {
    type: 'minor' as VersionType,
    label: 'Minor Updates',
    badge: '0.x.0',
    badgeClass: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
    description: 'New features and improvements',
  },
  {
    type: 'patch' as VersionType,
    label: 'Patch Updates',
    badge: '0.0.x',
    badgeClass: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
    description: 'Bug fixes and small improvements',
  },
];

// Dynamic banner colors based on update type
const bannerClasses = computed(() => {
  switch (versionInfo.value.updateType) {
    case 'major':
      return 'bg-gradient-to-r from-rose-500 to-pink-500 text-white shadow-lg shadow-rose-500/20';
    case 'minor':
      return 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/20';
    case 'patch':
      return 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-lg shadow-emerald-500/20';
    default:
      return 'bg-slate-700 text-white';
  }
});

function openChangelog() {
  window.open(CHANGELOG_URL, '_blank', 'noopener,noreferrer');
}
</script>
