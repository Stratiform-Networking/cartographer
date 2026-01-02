import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { ref, defineComponent } from 'vue';

// Simple mocked NotificationSettings component
const MockedNotificationSettings = defineComponent({
  name: 'MockedNotificationSettings',
  props: {
    isLoading: { type: Boolean, default: false },
    enabled: { type: Boolean, default: true },
    emailEnabled: { type: Boolean, default: true },
    emailConfigured: { type: Boolean, default: true },
    discordEnabled: { type: Boolean, default: false },
    discordConfigured: { type: Boolean, default: true },
    isOwner: { type: Boolean, default: false },
  },
  emits: ['close'],
  template: `
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div class="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 rounded-t-xl">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-violet-600 dark:text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </div>
            <div>
              <h2 class="text-lg font-semibold text-slate-900 dark:text-white">Notification Settings</h2>
              <p class="text-xs text-slate-500 dark:text-slate-400">Configure how you receive alerts</p>
            </div>
          </div>
          <button @click="$emit('close')" class="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto p-6 space-y-6">
          <!-- Loading State -->
          <div v-if="isLoading" class="flex items-center justify-center py-12">
            <svg class="animate-spin h-8 w-8 text-violet-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>

          <template v-else>
            <!-- Master Toggle -->
            <div class="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-violet-600 dark:text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                    </svg>
                  </div>
                  <div>
                    <p class="font-medium text-slate-900 dark:text-white">Enable Notifications</p>
                    <p class="text-sm text-slate-500 dark:text-slate-400">Receive alerts about network events</p>
                  </div>
                </div>
                <button :class="['relative w-12 h-7 rounded-full transition-colors', enabled ? 'bg-violet-500' : 'bg-slate-300 dark:bg-slate-600']">
                  <span :class="['absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform', enabled ? 'translate-x-5' : '']"></span>
                </button>
              </div>
            </div>

            <template v-if="enabled">
              <!-- Email Section -->
              <div class="space-y-4">
                <h3 class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  Email Notifications
                </h3>
                <div class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 space-y-4">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="font-medium text-slate-900 dark:text-white">Enable Email</p>
                      <p class="text-sm text-slate-500 dark:text-slate-400">{{ emailConfigured ? 'Receive email notifications' : 'Email service not configured' }}</p>
                    </div>
                    <button :disabled="!emailConfigured" :class="['relative w-12 h-7 rounded-full transition-colors disabled:opacity-50', emailEnabled && emailConfigured ? 'bg-cyan-500' : 'bg-slate-300 dark:bg-slate-600']">
                      <span :class="['absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform', emailEnabled && emailConfigured ? 'translate-x-5' : '']"></span>
                    </button>
                  </div>
                  <div v-if="emailEnabled && emailConfigured">
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Email Address</label>
                    <div class="flex gap-2">
                      <input type="email" value="user@example.com" class="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white" placeholder="your@email.com" />
                      <button class="px-3 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg text-sm font-medium">Test</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Discord Section -->
              <div class="space-y-4">
                <h3 class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                  <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
                  </svg>
                  Discord Notifications
                </h3>
                <div class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 space-y-4">
                  <div v-if="!discordConfigured" class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700/30">
                    <p class="text-sm text-amber-700 dark:text-amber-400">Discord bot is not configured. Contact your administrator to set up Discord notifications.</p>
                  </div>
                  <div v-else class="flex items-center justify-between">
                    <div>
                      <p class="font-medium text-slate-900 dark:text-white">Enable Discord</p>
                      <p class="text-sm text-slate-500 dark:text-slate-400">Bot connected</p>
                    </div>
                    <button :class="['relative w-12 h-7 rounded-full transition-colors', discordEnabled ? 'bg-indigo-500' : 'bg-slate-300 dark:bg-slate-600']">
                      <span :class="['absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform', discordEnabled ? 'translate-x-5' : '']"></span>
                    </button>
                  </div>
                </div>
              </div>

              <!-- ML Stats -->
              <div class="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700">
                <div class="flex items-center gap-2 mb-3">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  <span class="text-sm font-medium text-slate-700 dark:text-slate-300">ML Anomaly Detection</span>
                </div>
                <div class="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p class="text-2xl font-bold text-slate-900 dark:text-white">12</p>
                    <p class="text-xs text-slate-500 dark:text-slate-400">Devices Tracked</p>
                  </div>
                  <div>
                    <p class="text-2xl font-bold text-slate-900 dark:text-white">3</p>
                    <p class="text-xs text-slate-500 dark:text-slate-400">Anomalies (24h)</p>
                  </div>
                  <div>
                    <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">Active</p>
                    <p class="text-xs text-slate-500 dark:text-slate-400">Model Status</p>
                  </div>
                </div>
              </div>

              <!-- Broadcast Section (Owner Only) -->
              <div v-if="isOwner" class="space-y-4">
                <h3 class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
                  </svg>
                  Send Global Notification
                </h3>
                <div class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700/30 space-y-4">
                  <p class="text-sm text-amber-700 dark:text-amber-400">Send a notification to all users who have notifications enabled.</p>
                  <div>
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Title</label>
                    <input type="text" class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white" placeholder="e.g., Scheduled Maintenance Tonight" />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Message</label>
                    <textarea rows="3" class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white resize-none" placeholder="Enter the notification message..."></textarea>
                  </div>
                  <div class="flex items-center justify-between pt-2">
                    <p class="text-xs text-slate-500 dark:text-slate-400">Will be sent immediately to all users</p>
                    <button class="px-4 py-2 bg-amber-600 text-white rounded-lg font-medium flex items-center gap-2">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                      Send Now
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </template>
        </div>
      </div>
    </div>
  `,
});

const meta: Meta<typeof MockedNotificationSettings> = {
  title: 'Modals/NotificationSettings',
  component: MockedNotificationSettings,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'Comprehensive notification settings modal for configuring email, Discord alerts, quiet hours, and notification type preferences. Owner users can also broadcast messages to all users.',
      },
    },
  },
  decorators: [
    () => ({
      template: '<div style="min-height: 100vh; background: #1e293b;"><story /></div>',
    }),
  ],
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Loading: Story = {
  args: {
    isLoading: true,
  },
};

export const EnabledWithEmail: Story = {
  args: {
    enabled: true,
    emailEnabled: true,
    emailConfigured: true,
  },
};

export const Disabled: Story = {
  args: {
    enabled: false,
  },
};

export const DiscordEnabled: Story = {
  args: {
    enabled: true,
    discordConfigured: true,
    discordEnabled: true,
  },
};

export const DiscordNotConfigured: Story = {
  args: {
    enabled: true,
    discordConfigured: false,
  },
};

export const OwnerWithBroadcast: Story = {
  args: {
    enabled: true,
    emailEnabled: true,
    emailConfigured: true,
    isOwner: true,
  },
  parameters: {
    docs: {
      description: {
        story:
          'Owner users see additional broadcast notification controls to send messages to all users.',
      },
    },
  },
};

export const FullFeatured: Story = {
  args: {
    enabled: true,
    emailEnabled: true,
    emailConfigured: true,
    discordConfigured: true,
    discordEnabled: true,
    isOwner: true,
  },
};
