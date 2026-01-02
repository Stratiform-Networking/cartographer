<template>
  <div class="space-y-4">
    <!-- Delivery Channels -->
    <div class="space-y-3">
      <h3
        class="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-3.5 w-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        Delivery Channels
      </h3>

      <!-- Email -->
      <div
        class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50"
      >
        <div class="flex items-center justify-between mb-2">
          <div>
            <p class="text-sm font-medium text-slate-800 dark:text-slate-200">Email</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">
              {{
                serviceStatus?.email_configured
                  ? 'Using your account email'
                  : 'Email service not configured'
              }}
            </p>
          </div>
          <button
            @click="toggleEmail"
            :disabled="!serviceStatus?.email_configured"
            class="relative w-10 h-6 rounded-full transition-colors disabled:opacity-50"
            :class="
              preferences?.email_enabled && serviceStatus?.email_configured
                ? 'bg-blue-500'
                : 'bg-slate-300 dark:bg-slate-600'
            "
          >
            <span
              class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
              :class="
                preferences?.email_enabled && serviceStatus?.email_configured ? 'translate-x-4' : ''
              "
            ></span>
          </button>
        </div>
        <button
          v-if="preferences?.email_enabled"
          @click="$emit('test-email')"
          class="px-3 py-1.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
        >
          Send Test Email
        </button>
      </div>

      <!-- Discord -->
      <div
        class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50"
      >
        <div class="flex items-center justify-between mb-2">
          <div>
            <p class="text-sm font-medium text-slate-800 dark:text-slate-200">Discord</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">
              {{
                discordLink?.linked
                  ? `Linked: @${discordLink.discord_username}`
                  : 'Link your Discord account'
              }}
            </p>
          </div>
          <button
            @click="toggleDiscord"
            :disabled="!discordLink?.linked"
            class="relative w-10 h-6 rounded-full transition-colors disabled:opacity-50"
            :class="
              preferences?.discord_enabled && discordLink?.linked
                ? 'bg-indigo-500'
                : 'bg-slate-300 dark:bg-slate-600'
            "
          >
            <span
              class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
              :class="preferences?.discord_enabled && discordLink?.linked ? 'translate-x-4' : ''"
            ></span>
          </button>
        </div>
        <div class="flex gap-2">
          <button
            v-if="!discordLink?.linked"
            @click="$emit('link-discord')"
            class="px-3 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 shadow-sm shadow-indigo-500/20 transition-colors"
          >
            Link Discord Account
          </button>
          <button
            v-else
            @click="$emit('unlink-discord')"
            class="px-3 py-1.5 text-xs font-medium bg-slate-100 dark:bg-slate-700/60 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            Unlink
          </button>
          <button
            v-if="preferences?.discord_enabled && discordLink?.linked"
            @click="$emit('test-discord')"
            class="px-3 py-1.5 text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-lg hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors"
          >
            Send Test
          </button>
        </div>
      </div>
    </div>

    <!-- Notification Types -->
    <div class="space-y-3">
      <div>
        <h3
          class="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          Notification Types
        </h3>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          Click to enable/disable. Click priority badge to change level.
        </p>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div
          v-for="type in globalNotificationTypes"
          :key="type.value"
          @click="toggleType(type.value)"
          class="relative p-3 rounded-lg border cursor-pointer transition-all duration-200"
          :class="
            isTypeEnabled(type.value)
              ? 'bg-violet-50 dark:bg-violet-500/10 border-violet-300/80 dark:border-violet-500/50 hover:border-violet-400 dark:hover:border-violet-400/70'
              : 'bg-slate-50 dark:bg-slate-800/40 border-slate-200/80 dark:border-slate-700/50 hover:border-slate-300 dark:hover:border-slate-600'
          "
        >
          <!-- Priority Badge -->
          <button
            @click.stop="cycleTypePriority(type.value)"
            class="absolute top-2 right-2 px-2 py-0.5 text-[10px] font-medium rounded transition-colors"
            :class="getPriorityBadgeClass(getTypePriority(type.value))"
          >
            {{ capitalizeFirst(getTypePriority(type.value)) }}
          </button>

          <!-- Content -->
          <div class="flex items-start gap-2 pr-14">
            <span class="text-base flex-shrink-0">{{ type.icon }}</span>
            <div class="min-w-0">
              <p class="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                {{ type.label }}
              </p>
              <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                {{ type.description }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="space-y-3">
      <h3
        class="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-3.5 w-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
          />
        </svg>
        Filters & Limits
      </h3>
      <div
        class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50 space-y-3"
      >
        <!-- Minimum Priority -->
        <div>
          <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
            Minimum Priority
          </label>
          <div class="grid grid-cols-4 gap-2">
            <button
              v-for="priority in priorityOptions"
              :key="priority.value"
              @click="updateMinimumPriority(priority.value)"
              class="px-2 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 border"
              :class="
                (preferences?.minimum_priority || 'low') === priority.value
                  ? getPriorityButtonActiveClass(priority.value)
                  : 'bg-white dark:bg-slate-700/50 border-slate-200/80 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-800 dark:hover:text-slate-300'
              "
            >
              {{ priority.label }}
            </button>
          </div>
        </div>

        <!-- Quiet Hours -->
        <div class="space-y-2 pt-2 border-t border-slate-200/80 dark:border-slate-700/50">
          <div class="flex items-center justify-between">
            <label class="text-xs font-medium text-slate-600 dark:text-slate-400">
              Quiet Hours
            </label>
            <button
              @click="toggleQuietHours"
              class="relative w-10 h-6 rounded-full transition-colors"
              :class="
                preferences?.quiet_hours_enabled
                  ? 'bg-violet-500'
                  : 'bg-slate-300 dark:bg-slate-600'
              "
            >
              <span
                class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
                :class="preferences?.quiet_hours_enabled ? 'translate-x-4' : ''"
              ></span>
            </button>
          </div>

          <template v-if="preferences?.quiet_hours_enabled">
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label
                  class="block text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1"
                  >Start</label
                >
                <input
                  type="time"
                  :value="preferences?.quiet_hours_start || '22:00'"
                  @change="updateQuietHoursStart(($event.target as HTMLInputElement).value)"
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                />
              </div>
              <div>
                <label
                  class="block text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1"
                  >End</label
                >
                <input
                  type="time"
                  :value="preferences?.quiet_hours_end || '08:00'"
                  @change="updateQuietHoursEnd(($event.target as HTMLInputElement).value)"
                  class="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                />
              </div>
            </div>
            <div>
              <label
                class="block text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1"
                >Timezone</label
              >
              <select
                :value="preferences?.quiet_hours_timezone || 'UTC'"
                @change="updateQuietHoursTimezone(($event.target as HTMLSelectElement).value)"
                class="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              >
                <option value="UTC">UTC</option>
                <option value="America/New_York">Eastern Time</option>
                <option value="America/Chicago">Central Time</option>
                <option value="America/Denver">Mountain Time</option>
                <option value="America/Los_Angeles">Pacific Time</option>
                <option value="Europe/London">London</option>
                <option value="Europe/Paris">Paris</option>
                <option value="Asia/Tokyo">Tokyo</option>
              </select>
            </div>
            <div>
              <label
                class="block text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5"
                >Pass-through Alerts</label
              >
              <div class="grid grid-cols-5 gap-1.5">
                <button
                  v-for="bypass in bypassOptions"
                  :key="bypass.value"
                  @click="updateQuietHoursBypass(bypass.value)"
                  class="px-1.5 py-1.5 text-[10px] font-medium rounded-lg transition-all duration-200 border"
                  :class="
                    (preferences?.quiet_hours_bypass_priority || '') === bypass.value
                      ? getBypassButtonActiveClass(bypass.value)
                      : 'bg-white dark:bg-slate-700/50 border-slate-200/80 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-800 dark:hover:text-slate-300'
                  "
                >
                  {{ bypass.label }}
                </button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  preferences: any;
  serviceStatus: any;
  discordLink: any;
}>();

const emit = defineEmits<{
  update: [update: any];
  'test-email': [];
  'test-discord': [];
  'link-discord': [];
  'unlink-discord': [];
}>();

const priorityOptions = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
];

const bypassOptions = [
  { value: '', label: 'None' },
  { value: 'low', label: 'Low+' },
  { value: 'medium', label: 'Med+' },
  { value: 'high', label: 'High+' },
  { value: 'critical', label: 'Crit' },
];

const globalNotificationTypes = [
  {
    value: 'cartographer_down',
    label: 'Cartographer Down',
    icon: '🚨',
    description: 'When Cartographer service goes offline',
    defaultPriority: 'critical',
  },
  {
    value: 'cartographer_up',
    label: 'Cartographer Up',
    icon: '✅',
    description: 'When Cartographer service comes back online',
    defaultPriority: 'medium',
  },
];

function capitalizeFirst(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function getPriorityBadgeClass(priority: string): string {
  switch (priority) {
    case 'low':
      return 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30';
    case 'medium':
      return 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30';
    case 'high':
      return 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30';
    case 'critical':
      return 'bg-red-500/20 text-red-400 hover:bg-red-500/30';
    default:
      return 'bg-slate-500/20 text-slate-400 hover:bg-slate-500/30';
  }
}

function getPriorityButtonActiveClass(priority: string): string {
  switch (priority) {
    case 'low':
      return 'bg-emerald-500/30 border-emerald-500 text-emerald-300';
    case 'medium':
      return 'bg-yellow-500/30 border-yellow-500 text-yellow-300';
    case 'high':
      return 'bg-orange-500/30 border-orange-500 text-orange-300';
    case 'critical':
      return 'bg-red-500/30 border-red-500 text-red-300';
    default:
      return 'bg-slate-500/30 border-slate-500 text-slate-300';
  }
}

function getBypassButtonActiveClass(priority: string): string {
  switch (priority) {
    case 'low':
      return 'bg-emerald-500/30 border-emerald-500 text-emerald-300';
    case 'medium':
      return 'bg-yellow-500/30 border-yellow-500 text-yellow-300';
    case 'high':
      return 'bg-orange-500/30 border-orange-500 text-orange-300';
    case 'critical':
      return 'bg-red-500/30 border-red-500 text-red-300';
    default:
      return 'bg-slate-500/30 border-slate-500 text-slate-300';
  }
}

function isTypeEnabled(type: string): boolean {
  // Map to the existing preference fields
  if (type === 'cartographer_up') {
    return props.preferences?.cartographer_up_enabled ?? true;
  }
  if (type === 'cartographer_down') {
    return props.preferences?.cartographer_down_enabled ?? true;
  }
  return true;
}

function getTypePriority(type: string): string {
  const priorities = props.preferences?.type_priorities || {};
  return (
    priorities[type] ||
    globalNotificationTypes.find((t) => t.value === type)?.defaultPriority ||
    'medium'
  );
}

function toggleType(type: string) {
  // Map to the existing preference fields
  if (type === 'cartographer_up') {
    emit('update', { cartographer_up_enabled: !props.preferences?.cartographer_up_enabled });
  } else if (type === 'cartographer_down') {
    emit('update', { cartographer_down_enabled: !props.preferences?.cartographer_down_enabled });
  }
}

function cycleTypePriority(type: string) {
  const currentPriority = getTypePriority(type);
  const priorities = ['low', 'medium', 'high', 'critical'];
  const currentIndex = priorities.indexOf(currentPriority);
  const nextIndex = (currentIndex + 1) % priorities.length;
  const newPriority = priorities[nextIndex];

  const typePriorities = { ...(props.preferences?.type_priorities || {}) };
  const defaultPriority = globalNotificationTypes.find((t) => t.value === type)?.defaultPriority;

  if (newPriority === defaultPriority) {
    delete typePriorities[type];
  } else {
    typePriorities[type] = newPriority;
  }

  emit('update', { type_priorities: typePriorities });
}

function toggleEmail() {
  emit('update', { email_enabled: !props.preferences?.email_enabled });
}

function toggleDiscord() {
  if (!props.discordLink?.linked) return;
  emit('update', { discord_enabled: !props.preferences?.discord_enabled });
}

function updateMinimumPriority(priority: string) {
  emit('update', { minimum_priority: priority });
}

function toggleQuietHours() {
  emit('update', { quiet_hours_enabled: !props.preferences?.quiet_hours_enabled });
}

function updateQuietHoursStart(start: string) {
  emit('update', { quiet_hours_start: start });
}

function updateQuietHoursEnd(end: string) {
  emit('update', { quiet_hours_end: end });
}

function updateQuietHoursTimezone(timezone: string) {
  emit('update', { quiet_hours_timezone: timezone });
}

function updateQuietHoursBypass(priority: string) {
  emit('update', { quiet_hours_bypass_priority: priority || null });
}
</script>
