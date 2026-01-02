<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
      <div
        class="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col"
      >
        <!-- Header -->
        <div
          class="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 rounded-t-xl"
        >
          <div class="flex items-center gap-3">
            <div
              class="w-9 h-9 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-violet-600 dark:text-violet-400"
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
            </div>
            <div>
              <h2 class="text-lg font-semibold text-slate-900 dark:text-white">
                Notification Settings
              </h2>
              <p class="text-xs text-slate-500 dark:text-slate-400">
                Configure how you receive alerts
              </p>
            </div>
          </div>
          <button
            @click="$emit('close')"
            class="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Tab Navigation -->
        <div class="flex border-b border-slate-200 dark:border-slate-700 px-6">
          <button
            @click="activeTab = 'network'"
            :class="[
              'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'network'
                ? 'border-violet-500 text-violet-600 dark:text-violet-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300',
            ]"
          >
            <span class="flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
              Network
            </span>
          </button>
          <button
            @click="activeTab = 'global'"
            :class="[
              'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'global'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300',
            ]"
          >
            <span class="flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              Global
            </span>
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto p-6 space-y-6">
          <!-- Loading State -->
          <div v-if="isLoading" class="flex items-center justify-center py-12">
            <svg
              class="animate-spin h-8 w-8 text-violet-500"
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
          </div>

          <template v-else-if="preferences">
            <!-- ==================== GLOBAL TAB ==================== -->
            <template v-if="activeTab === 'global'">
              <!-- Global Email/Discord Enable -->
              <div class="space-y-4">
                <h3
                  class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-4 w-4"
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
                <p class="text-sm text-slate-500 dark:text-slate-400">
                  Choose how you want to receive global notifications. Your account email will be
                  used for email notifications.
                </p>

                <div
                  class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 space-y-4"
                >
                  <!-- Email Toggle -->
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="font-medium text-slate-900 dark:text-white">Email</p>
                      <p class="text-sm text-slate-500 dark:text-slate-400">
                        {{
                          serviceStatus?.email_configured
                            ? 'Receive via email'
                            : 'Email service not configured'
                        }}
                      </p>
                    </div>
                    <button
                      @click="toggleGlobalEmail"
                      :disabled="!serviceStatus?.email_configured"
                      class="relative w-12 h-7 rounded-full transition-colors disabled:opacity-50"
                      :class="
                        globalPrefs.email_enabled && serviceStatus?.email_configured
                          ? 'bg-blue-500'
                          : 'bg-slate-300 dark:bg-slate-600'
                      "
                    >
                      <span
                        class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform"
                        :class="
                          globalPrefs.email_enabled && serviceStatus?.email_configured
                            ? 'translate-x-5'
                            : ''
                        "
                      ></span>
                    </button>
                  </div>

                  <!-- Discord Section -->
                  <div class="space-y-3">
                    <!-- Discord Status -->
                    <div
                      v-if="!serviceStatus?.discord_configured"
                      class="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700/30"
                    >
                      <p class="text-sm text-amber-700 dark:text-amber-400">
                        Discord bot is not configured. Contact your administrator to set up Discord
                        notifications.
                      </p>
                    </div>

                    <template v-else>
                      <div class="flex items-center justify-between">
                        <div>
                          <p class="font-medium text-slate-900 dark:text-white">Discord</p>
                          <p class="text-sm text-slate-500 dark:text-slate-400">
                            {{
                              serviceStatus?.discord_bot_connected
                                ? 'Bot connected'
                                : 'Bot not connected'
                            }}
                          </p>
                        </div>
                        <button
                          @click="toggleGlobalDiscord"
                          class="relative w-12 h-7 rounded-full transition-colors"
                          :class="
                            globalPrefs.discord_enabled
                              ? 'bg-indigo-500'
                              : 'bg-slate-300 dark:bg-slate-600'
                          "
                        >
                          <span
                            class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform"
                            :class="globalPrefs.discord_enabled ? 'translate-x-5' : ''"
                          ></span>
                        </button>
                      </div>

                      <template v-if="globalPrefs.discord_enabled">
                        <!-- Add Bot to Server -->
                        <div
                          v-if="!serviceStatus?.discord_bot_connected || discordGuilds.length === 0"
                          class="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-700/30"
                        >
                          <div class="flex items-start gap-3">
                            <div
                              class="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center flex-shrink-0"
                            >
                              <svg
                                class="h-5 w-5 text-indigo-600 dark:text-indigo-400"
                                viewBox="0 0 24 24"
                                fill="currentColor"
                              >
                                <path
                                  d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"
                                />
                              </svg>
                            </div>
                            <div class="flex-1">
                              <p class="font-medium text-indigo-900 dark:text-indigo-100">
                                Add Cartographer Bot to your server
                              </p>
                              <p class="text-sm text-indigo-700 dark:text-indigo-300 mt-1">
                                Click the button below to add the Cartographer Bot to your Discord
                                server. Once added, you can select a channel to receive
                                notifications.
                              </p>
                              <a
                                v-if="discordBotInfo?.invite_url"
                                :href="discordBotInfo.invite_url"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
                              >
                                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                                  <path
                                    d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"
                                  />
                                </svg>
                                Add to Discord
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
                                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                  />
                                </svg>
                              </a>
                              <button
                                @click="refreshDiscordGuilds"
                                class="inline-flex items-center gap-2 mt-3 ml-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors text-sm font-medium"
                              >
                                <svg
                                  xmlns="http://www.w3.org/2000/svg"
                                  class="h-4 w-4"
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
                                Refresh
                              </button>
                            </div>
                          </div>
                        </div>

                        <!-- Server & Channel Selection -->
                        <template v-else>
                          <!-- Delivery Method -->
                          <div>
                            <label
                              class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                            >
                              Delivery Method
                            </label>
                            <div class="grid grid-cols-2 gap-2">
                              <button
                                @click="setGlobalDeliveryMethod('channel')"
                                :class="[
                                  'p-3 rounded-lg border-2 transition-colors text-left',
                                  globalPrefs.discord_delivery_method === 'channel'
                                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                                    : 'border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500',
                                ]"
                              >
                                <div class="flex items-center gap-2">
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    class="h-5 w-5 text-slate-600 dark:text-slate-400"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                  >
                                    <path
                                      stroke-linecap="round"
                                      stroke-linejoin="round"
                                      d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"
                                    />
                                  </svg>
                                  <span class="font-medium text-slate-900 dark:text-white"
                                    >Channel</span
                                  >
                                </div>
                                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                  Send to a server channel
                                </p>
                              </button>
                              <button
                                @click="setGlobalDeliveryMethod('dm')"
                                :class="[
                                  'p-3 rounded-lg border-2 transition-colors text-left',
                                  globalPrefs.discord_delivery_method === 'dm'
                                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                                    : 'border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500',
                                ]"
                              >
                                <div class="flex items-center gap-2">
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    class="h-5 w-5 text-slate-600 dark:text-slate-400"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                  >
                                    <path
                                      stroke-linecap="round"
                                      stroke-linejoin="round"
                                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                                    />
                                  </svg>
                                  <span class="font-medium text-slate-900 dark:text-white"
                                    >Direct Message</span
                                  >
                                </div>
                                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                  Send DMs to you
                                </p>
                              </button>
                            </div>
                          </div>

                          <!-- Channel Delivery Settings -->
                          <div
                            v-if="globalPrefs.discord_delivery_method === 'channel'"
                            class="space-y-3"
                          >
                            <div>
                              <label
                                class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                              >
                                Server
                              </label>
                              <select
                                v-model="globalSelectedGuildId"
                                @change="onGlobalGuildChange"
                                class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                              >
                                <option value="">Select a server...</option>
                                <option
                                  v-for="guild in discordGuilds"
                                  :key="guild.id"
                                  :value="guild.id"
                                >
                                  {{ guild.name }}
                                </option>
                              </select>
                            </div>

                            <div v-if="globalSelectedGuildId">
                              <label
                                class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                              >
                                Channel
                              </label>
                              <div class="flex gap-2">
                                <select
                                  v-model="globalSelectedChannelId"
                                  @change="onGlobalChannelChange"
                                  :disabled="loadingGlobalChannels"
                                  class="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50"
                                >
                                  <option value="">
                                    {{
                                      loadingGlobalChannels
                                        ? 'Loading channels...'
                                        : 'Select a channel...'
                                    }}
                                  </option>
                                  <option
                                    v-for="channel in globalDiscordChannels"
                                    :key="channel.id"
                                    :value="channel.id"
                                  >
                                    #{{ channel.name }}
                                  </option>
                                </select>
                                <button
                                  @click="testGlobalDiscord"
                                  :disabled="!globalSelectedChannelId || testingGlobalDiscord"
                                  class="px-3 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors text-sm font-medium"
                                >
                                  {{ testingGlobalDiscord ? 'Sending...' : 'Test' }}
                                </button>
                              </div>
                            </div>
                          </div>

                          <!-- DM Delivery Settings -->
                          <div
                            v-if="globalPrefs.discord_delivery_method === 'dm'"
                            class="space-y-3"
                          >
                            <div>
                              <label
                                class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                              >
                                Your Discord User ID
                              </label>
                              <div class="flex gap-2">
                                <input
                                  v-model="globalPrefs.discord_user_id"
                                  type="text"
                                  placeholder="e.g., 123456789012345678"
                                  class="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                  @change="saveGlobalPrefs"
                                />
                                <button
                                  @click="testGlobalDiscord"
                                  :disabled="!globalPrefs.discord_user_id || testingGlobalDiscord"
                                  class="px-3 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors text-sm font-medium"
                                >
                                  {{ testingGlobalDiscord ? 'Sending...' : 'Test' }}
                                </button>
                              </div>
                              <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                Enable Developer Mode in Discord, right-click your profile, and
                                click "Copy User ID"
                              </p>
                            </div>
                          </div>
                        </template>
                      </template>
                    </template>
                  </div>
                </div>
              </div>

              <!-- Cartographer Status Toggles -->
              <div class="space-y-4">
                <h3
                  class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                  Notification Types
                </h3>
                <p class="text-xs text-slate-500 dark:text-slate-400">
                  Enable/disable notification types and customize their priority. Click the priority
                  badge to change it.
                </p>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <!-- Cartographer Up -->
                  <div
                    :class="[
                      'p-3 rounded-lg border text-left transition-colors',
                      globalPrefs.cartographer_up_enabled
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-slate-200 dark:border-slate-700',
                    ]"
                  >
                    <div class="flex items-center justify-between gap-2">
                      <button
                        @click="toggleGlobalCartographerUp"
                        class="flex items-center gap-2 flex-1 text-left hover:opacity-80 transition-opacity"
                      >
                        <span class="text-lg">✅</span>
                        <span class="font-medium text-slate-900 dark:text-white text-sm"
                          >Cartographer Up</span
                        >
                      </button>
                      <button
                        @click.stop="cycleGlobalCartographerUpPriority"
                        class="px-2 py-0.5 rounded text-xs font-medium transition-colors"
                        :class="getPriorityBadgeClasses(globalPrefs.cartographer_up_priority)"
                        :title="`Priority: ${globalPrefs.cartographer_up_priority} - Click to change`"
                      >
                        {{ PRIORITY_INFO[globalPrefs.cartographer_up_priority].label }}
                      </button>
                    </div>
                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      When Cartographer comes back online
                    </p>
                  </div>

                  <!-- Cartographer Down -->
                  <div
                    :class="[
                      'p-3 rounded-lg border text-left transition-colors',
                      globalPrefs.cartographer_down_enabled
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-slate-200 dark:border-slate-700',
                    ]"
                  >
                    <div class="flex items-center justify-between gap-2">
                      <button
                        @click="toggleGlobalCartographerDown"
                        class="flex items-center gap-2 flex-1 text-left hover:opacity-80 transition-opacity"
                      >
                        <span class="text-lg">🚨</span>
                        <span class="font-medium text-slate-900 dark:text-white text-sm"
                          >Cartographer Down</span
                        >
                      </button>
                      <button
                        @click.stop="cycleGlobalCartographerDownPriority"
                        class="px-2 py-0.5 rounded text-xs font-medium transition-colors"
                        :class="getPriorityBadgeClasses(globalPrefs.cartographer_down_priority)"
                        :title="`Priority: ${globalPrefs.cartographer_down_priority} - Click to change`"
                      >
                        {{ PRIORITY_INFO[globalPrefs.cartographer_down_priority].label }}
                      </button>
                    </div>
                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      When Cartographer goes offline
                    </p>
                  </div>
                </div>
              </div>

              <!-- Global Filters & Limits -->
              <div class="space-y-4">
                <h3
                  class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-4 w-4"
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
                  class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 space-y-4"
                >
                  <!-- Minimum Priority for Global -->
                  <div>
                    <label
                      class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                    >
                      Minimum Priority
                    </label>
                    <div class="flex gap-2">
                      <button
                        v-for="(info, priority) in PRIORITY_INFO"
                        :key="priority"
                        @click="setGlobalPriority(priority)"
                        :class="[
                          'flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition-colors',
                          globalPrefs.minimum_priority === priority
                            ? getBypassPriorityActiveClasses(priority)
                            : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500',
                        ]"
                      >
                        {{ info.label }}
                      </button>
                    </div>
                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-2">
                      Only receive global notifications of this priority or higher
                    </p>
                  </div>

                  <!-- Quiet Hours for Global -->
                  <div class="space-y-3">
                    <div class="flex items-center justify-between">
                      <div>
                        <p class="font-medium text-slate-900 dark:text-white">Quiet Hours</p>
                        <p class="text-sm text-slate-500 dark:text-slate-400">
                          Don't send global notifications during these hours
                        </p>
                      </div>
                      <button
                        @click="toggleGlobalQuietHours"
                        class="relative w-12 h-7 rounded-full transition-colors"
                        :class="
                          globalPrefs.quiet_hours_enabled
                            ? 'bg-blue-500'
                            : 'bg-slate-300 dark:bg-slate-600'
                        "
                      >
                        <span
                          class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform"
                          :class="globalPrefs.quiet_hours_enabled ? 'translate-x-5' : ''"
                        ></span>
                      </button>
                    </div>

                    <div v-if="globalPrefs.quiet_hours_enabled" class="space-y-3">
                      <div class="flex items-center gap-3">
                        <input
                          v-model="globalPrefs.quiet_hours_start"
                          type="time"
                          class="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          @change="saveGlobalPrefs"
                        />
                        <span class="text-slate-500">to</span>
                        <input
                          v-model="globalPrefs.quiet_hours_end"
                          type="time"
                          class="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          @change="saveGlobalPrefs"
                        />
                      </div>

                      <!-- Pass-through alerts -->
                      <div class="pt-2 border-t border-slate-200 dark:border-slate-700">
                        <label
                          class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                        >
                          Pass-through Alerts
                        </label>
                        <p class="text-xs text-slate-500 dark:text-slate-400 mb-2">
                          Allow high-priority alerts to bypass quiet hours
                        </p>
                        <div class="flex flex-wrap gap-2">
                          <button
                            @click="setGlobalBypassPriority(null)"
                            :class="[
                              'px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors',
                              globalPrefs.quiet_hours_bypass_priority === null ||
                              globalPrefs.quiet_hours_bypass_priority === undefined
                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400'
                                : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500',
                            ]"
                          >
                            None
                          </button>
                          <button
                            v-for="(info, priority) in PRIORITY_INFO"
                            :key="priority"
                            @click="setGlobalBypassPriority(priority)"
                            :class="[
                              'px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors',
                              globalPrefs.quiet_hours_bypass_priority === priority
                                ? getBypassPriorityActiveClasses(priority)
                                : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500',
                            ]"
                          >
                            {{ info.label }}+
                          </button>
                        </div>
                        <p class="text-xs text-slate-500 dark:text-slate-400 mt-2">
                          <template v-if="globalPrefs.quiet_hours_bypass_priority">
                            <span class="font-medium">{{
                              PRIORITY_INFO[globalPrefs.quiet_hours_bypass_priority].label
                            }}</span>
                            and higher alerts will still be delivered during quiet hours
                          </template>
                          <template v-else>
                            All notifications will be blocked during quiet hours
                          </template>
                        </p>
                      </div>

                      <!-- Timezone selector -->
                      <div class="pt-2 border-t border-slate-200 dark:border-slate-700">
                        <label
                          class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                        >
                          Timezone
                        </label>
                        <p class="text-xs text-slate-500 dark:text-slate-400 mb-2">
                          Select your timezone for accurate quiet hours
                        </p>
                        <div class="flex gap-2">
                          <select
                            v-model="globalPrefs.timezone"
                            @change="saveGlobalPrefs"
                            class="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                          >
                            <option :value="null">Use server time</option>
                            <option
                              v-for="tz in COMMON_TIMEZONES"
                              :key="tz.value"
                              :value="tz.value"
                            >
                              {{ tz.label }}
                            </option>
                          </select>
                          <button
                            v-if="detectedTimezone"
                            @click="autoDetectGlobalTimezone"
                            class="px-3 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700/30 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors whitespace-nowrap"
                            title="Use your browser's detected timezone"
                          >
                            Auto-detect
                          </button>
                        </div>
                        <p
                          v-if="detectedTimezone"
                          class="text-xs text-slate-500 dark:text-slate-400 mt-1"
                        >
                          <template v-if="globalPrefs.timezone === detectedTimezone">
                            ✓ Using your detected timezone
                          </template>
                          <template v-else-if="!globalPrefs.timezone">
                            ⚠️ Using server time - click Auto-detect to use your timezone ({{
                              detectedTimezone
                            }})
                          </template>
                          <template v-else>
                            Your browser detected: {{ detectedTimezone }}
                          </template>
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <!-- ==================== NETWORK TAB ==================== -->
            <template v-if="activeTab === 'network'">
              <!-- Master Toggle -->
              <div
                class="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <div
                      class="w-10 h-10 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-5 w-5 text-violet-600 dark:text-violet-400"
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
                    </div>
                    <div>
                      <p class="font-medium text-slate-900 dark:text-white">Enable Notifications</p>
                      <p class="text-sm text-slate-500 dark:text-slate-400">
                        Receive alerts about network events
                      </p>
                    </div>
                  </div>
                  <button
                    @click="toggleMaster"
                    class="relative w-12 h-7 rounded-full transition-colors"
                    :class="
                      preferences.enabled ? 'bg-violet-500' : 'bg-slate-300 dark:bg-slate-600'
                    "
                  >
                    <span
                      class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform"
                      :class="preferences.enabled ? 'translate-x-5' : ''"
                    ></span>
                  </button>
                </div>
              </div>

              <template v-if="preferences.enabled">
                <!-- Email Section -->
                <div class="space-y-4">
                  <h3
                    class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                      />
                    </svg>
                    Email Notifications
                  </h3>

                  <div
                    class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 space-y-4"
                  >
                    <div class="flex items-center justify-between">
                      <div>
                        <p class="font-medium text-slate-900 dark:text-white">Enable Email</p>
                        <p class="text-sm text-slate-500 dark:text-slate-400">
                          {{
                            serviceStatus?.email_configured
                              ? 'Receive email notifications'
                              : 'Email service not configured'
                          }}
                        </p>
                      </div>
                      <button
                        @click="toggleEmail"
                        :disabled="!serviceStatus?.email_configured"
                        class="relative w-12 h-7 rounded-full transition-colors disabled:opacity-50"
                        :class="
                          preferences.email.enabled && serviceStatus?.email_configured
                            ? 'bg-cyan-500'
                            : 'bg-slate-300 dark:bg-slate-600'
                        "
                      >
                        <span
                          class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform"
                          :class="
                            preferences.email.enabled && serviceStatus?.email_configured
                              ? 'translate-x-5'
                              : ''
                          "
                        ></span>
                      </button>
                    </div>

                    <div
                      v-if="preferences.email.enabled"
                      class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg"
                    >
                      <div class="flex items-center gap-3">
                        <div
                          class="w-8 h-8 rounded-full bg-cyan-100 dark:bg-cyan-900/30 flex items-center justify-center"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            class="h-4 w-4 text-cyan-600 dark:text-cyan-400"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                            />
                          </svg>
                        </div>
                        <div>
                          <p class="text-sm font-medium text-slate-900 dark:text-white">
                            {{ userEmail || 'Loading...' }}
                          </p>
                          <p class="text-xs text-slate-500 dark:text-slate-400">
                            Using your account email
                          </p>
                        </div>
                      </div>
                      <button
                        @click="testEmail"
                        :disabled="!userEmail || testingEmail"
                        class="px-3 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors text-sm font-medium"
                      >
                        {{ testingEmail ? 'Sending...' : 'Test' }}
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Discord Section -->
                <div class="space-y-4">
                  <h3
                    class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                      <path
                        d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"
                      />
                    </svg>
                    Discord Notifications
                  </h3>

                  <div
                    class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 space-y-4"
                  >
                    <!-- Discord Status -->
                    <div
                      v-if="!serviceStatus?.discord_configured"
                      class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700/30"
                    >
                      <p class="text-sm text-amber-700 dark:text-amber-400">
                        Discord bot is not configured. Contact your administrator to set up Discord
                        notifications.
                      </p>
                    </div>

                    <template v-else>
                      <div class="flex items-center justify-between">
                        <div>
                          <p class="font-medium text-slate-900 dark:text-white">Enable Discord</p>
                          <p class="text-sm text-slate-500 dark:text-slate-400">
                            {{
                              serviceStatus?.discord_bot_connected
                                ? 'Bot connected'
                                : 'Bot not connected'
                            }}
                          </p>
                        </div>
                        <button
                          @click="toggleDiscord"
                          class="relative w-12 h-7 rounded-full transition-colors"
                          :class="
                            preferences.discord.enabled
                              ? 'bg-indigo-500'
                              : 'bg-slate-300 dark:bg-slate-600'
                          "
                        >
                          <span
                            class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform"
                            :class="preferences.discord.enabled ? 'translate-x-5' : ''"
                          ></span>
                        </button>
                      </div>

                      <template v-if="preferences.discord.enabled">
                        <!-- Add Bot to Server -->
                        <div
                          v-if="!serviceStatus?.discord_bot_connected || discordGuilds.length === 0"
                          class="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-700/30"
                        >
                          <div class="flex items-start gap-3">
                            <div
                              class="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center flex-shrink-0"
                            >
                              <svg
                                class="h-5 w-5 text-indigo-600 dark:text-indigo-400"
                                viewBox="0 0 24 24"
                                fill="currentColor"
                              >
                                <path
                                  d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"
                                />
                              </svg>
                            </div>
                            <div class="flex-1">
                              <p class="font-medium text-indigo-900 dark:text-indigo-100">
                                Add Cartographer Bot to your server
                              </p>
                              <p class="text-sm text-indigo-700 dark:text-indigo-300 mt-1">
                                Click the button below to add the Cartographer Bot to your Discord
                                server. Once added, you can select a channel to receive
                                notifications.
                              </p>
                              <a
                                v-if="discordBotInfo?.invite_url"
                                :href="discordBotInfo.invite_url"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
                              >
                                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                                  <path
                                    d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"
                                  />
                                </svg>
                                Add to Discord
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
                                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                  />
                                </svg>
                              </a>
                              <button
                                @click="refreshDiscordGuilds"
                                class="inline-flex items-center gap-2 mt-3 ml-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors text-sm font-medium"
                              >
                                <svg
                                  xmlns="http://www.w3.org/2000/svg"
                                  class="h-4 w-4"
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
                                Refresh
                              </button>
                            </div>
                          </div>
                        </div>

                        <!-- Server & Channel Selection -->
                        <template v-else>
                          <!-- Delivery Method -->
                          <div>
                            <label
                              class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                            >
                              Delivery Method
                            </label>
                            <div class="grid grid-cols-2 gap-2">
                              <button
                                @click="setDeliveryMethod('channel')"
                                :class="[
                                  'p-3 rounded-lg border-2 transition-colors text-left',
                                  preferences.discord.delivery_method === 'channel'
                                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                                    : 'border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500',
                                ]"
                              >
                                <div class="flex items-center gap-2">
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    class="h-5 w-5 text-slate-600 dark:text-slate-400"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                  >
                                    <path
                                      stroke-linecap="round"
                                      stroke-linejoin="round"
                                      d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"
                                    />
                                  </svg>
                                  <span class="font-medium text-slate-900 dark:text-white"
                                    >Channel</span
                                  >
                                </div>
                                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                  Send to a server channel
                                </p>
                              </button>
                              <button
                                @click="setDeliveryMethod('dm')"
                                :class="[
                                  'p-3 rounded-lg border-2 transition-colors text-left',
                                  preferences.discord.delivery_method === 'dm'
                                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                                    : 'border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500',
                                ]"
                              >
                                <div class="flex items-center gap-2">
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    class="h-5 w-5 text-slate-600 dark:text-slate-400"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                  >
                                    <path
                                      stroke-linecap="round"
                                      stroke-linejoin="round"
                                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                                    />
                                  </svg>
                                  <span class="font-medium text-slate-900 dark:text-white"
                                    >Direct Message</span
                                  >
                                </div>
                                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                  Send DMs to you
                                </p>
                              </button>
                            </div>
                          </div>

                          <!-- Channel Delivery Settings -->
                          <div
                            v-if="preferences.discord.delivery_method === 'channel'"
                            class="space-y-3"
                          >
                            <div>
                              <label
                                class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                              >
                                Server
                              </label>
                              <select
                                v-model="selectedGuildId"
                                @change="onGuildChange"
                                class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                              >
                                <option value="">Select a server...</option>
                                <option
                                  v-for="guild in discordGuilds"
                                  :key="guild.id"
                                  :value="guild.id"
                                >
                                  {{ guild.name }}
                                </option>
                              </select>
                            </div>

                            <div v-if="selectedGuildId">
                              <label
                                class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                              >
                                Channel
                              </label>
                              <div class="flex gap-2">
                                <select
                                  v-model="selectedChannelId"
                                  @change="onChannelChange"
                                  :disabled="loadingChannels"
                                  class="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50"
                                >
                                  <option value="">
                                    {{
                                      loadingChannels
                                        ? 'Loading channels...'
                                        : 'Select a channel...'
                                    }}
                                  </option>
                                  <option
                                    v-for="channel in discordChannels"
                                    :key="channel.id"
                                    :value="channel.id"
                                  >
                                    #{{ channel.name }}
                                  </option>
                                </select>
                                <button
                                  @click="testDiscord"
                                  :disabled="!selectedChannelId || testingDiscord"
                                  class="px-3 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors text-sm font-medium"
                                >
                                  {{ testingDiscord ? 'Sending...' : 'Test' }}
                                </button>
                              </div>
                            </div>
                          </div>

                          <!-- DM Delivery Settings -->
                          <div
                            v-if="preferences.discord.delivery_method === 'dm'"
                            class="space-y-3"
                          >
                            <div>
                              <label
                                class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                              >
                                Your Discord User ID
                              </label>
                              <div class="flex gap-2">
                                <input
                                  v-model="preferences.discord.discord_user_id"
                                  type="text"
                                  placeholder="e.g., 123456789012345678"
                                  class="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                  @change="savePreferences"
                                />
                                <button
                                  @click="testDiscord"
                                  :disabled="!preferences.discord.discord_user_id || testingDiscord"
                                  class="px-3 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors text-sm font-medium"
                                >
                                  {{ testingDiscord ? 'Sending...' : 'Test' }}
                                </button>
                              </div>
                              <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                Enable Developer Mode in Discord, right-click your profile, and
                                click "Copy User ID"
                              </p>
                            </div>
                          </div>
                        </template>
                      </template>
                    </template>
                  </div>
                </div>

                <!-- Notification Types -->
                <div class="space-y-4">
                  <h3
                    class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                      />
                    </svg>
                    Notification Types
                  </h3>

                  <p class="text-xs text-slate-500 dark:text-slate-400">
                    Enable/disable notification types and customize their priority. Click the
                    priority badge to change it.
                  </p>

                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div
                      v-for="(info, type) in networkNotificationTypes"
                      :key="type"
                      :class="[
                        'p-3 rounded-lg border text-left transition-colors',
                        preferences.enabled_notification_types.includes(type)
                          ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20'
                          : 'border-slate-200 dark:border-slate-700',
                      ]"
                    >
                      <div class="flex items-center justify-between gap-2">
                        <button
                          @click="toggleNotificationType(type)"
                          class="flex items-center gap-2 flex-1 text-left hover:opacity-80 transition-opacity"
                        >
                          <span class="text-lg">{{ info.icon }}</span>
                          <span class="font-medium text-slate-900 dark:text-white text-sm">{{
                            info.label
                          }}</span>
                        </button>
                        <!-- Priority Badge (clickable to cycle through priorities) -->
                        <button
                          @click.stop="cycleTypePriority(type)"
                          class="px-2 py-0.5 rounded text-xs font-medium transition-colors"
                          :class="getPriorityBadgeClasses(getEffectivePriority(type))"
                          :title="`Priority: ${getEffectivePriority(type)}${isDefaultPriority(type) ? ' (default)' : ' (custom)'} - Click to change`"
                        >
                          {{ PRIORITY_INFO[getEffectivePriority(type)].label }}
                          <span v-if="!isDefaultPriority(type)" class="ml-0.5 opacity-70">*</span>
                        </button>
                      </div>
                      <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        {{ info.description }}
                      </p>
                      <!-- Reset to default priority option -->
                      <button
                        v-if="!isDefaultPriority(type)"
                        @click.stop="resetTypePriority(type)"
                        class="text-xs text-violet-600 dark:text-violet-400 hover:underline mt-1"
                      >
                        Reset to default ({{ info.defaultPriority }})
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Priority & Rate Limiting -->
                <div class="space-y-4">
                  <h3
                    class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4"
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
                    class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 space-y-4"
                  >
                    <!-- Minimum Priority -->
                    <div>
                      <label
                        class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                      >
                        Minimum Priority
                      </label>
                      <div class="flex gap-2">
                        <button
                          v-for="(info, priority) in PRIORITY_INFO"
                          :key="priority"
                          @click="setPriority(priority)"
                          :class="[
                            'flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition-colors',
                            preferences.minimum_priority === priority
                              ? getBypassPriorityActiveClasses(priority)
                              : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500',
                          ]"
                        >
                          {{ info.label }}
                        </button>
                      </div>
                      <p class="text-xs text-slate-500 dark:text-slate-400 mt-2">
                        Only receive notifications of this priority or higher
                      </p>
                    </div>

                    <!-- Rate Limit -->
                    <div>
                      <label
                        class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                      >
                        Max Notifications per Hour
                      </label>
                      <input
                        v-model.number="preferences.max_notifications_per_hour"
                        type="number"
                        min="1"
                        max="100"
                        class="w-32 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                        @change="savePreferences"
                      />
                    </div>

                    <!-- Quiet Hours -->
                    <div class="space-y-3">
                      <div class="flex items-center justify-between">
                        <div>
                          <p class="font-medium text-slate-900 dark:text-white">Quiet Hours</p>
                          <p class="text-sm text-slate-500 dark:text-slate-400">
                            Don't send notifications during these hours
                          </p>
                        </div>
                        <button
                          @click="toggleQuietHours"
                          class="relative w-12 h-7 rounded-full transition-colors"
                          :class="
                            preferences.quiet_hours_enabled
                              ? 'bg-violet-500'
                              : 'bg-slate-300 dark:bg-slate-600'
                          "
                        >
                          <span
                            class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform"
                            :class="preferences.quiet_hours_enabled ? 'translate-x-5' : ''"
                          ></span>
                        </button>
                      </div>

                      <div v-if="preferences.quiet_hours_enabled" class="space-y-3">
                        <div class="flex items-center gap-3">
                          <input
                            v-model="preferences.quiet_hours_start"
                            type="time"
                            class="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                            @change="savePreferences"
                          />
                          <span class="text-slate-500">to</span>
                          <input
                            v-model="preferences.quiet_hours_end"
                            type="time"
                            class="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                            @change="savePreferences"
                          />
                        </div>

                        <!-- Pass-through alerts -->
                        <div class="pt-2 border-t border-slate-200 dark:border-slate-700">
                          <label
                            class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                          >
                            Pass-through Alerts
                          </label>
                          <p class="text-xs text-slate-500 dark:text-slate-400 mb-2">
                            Allow high-priority alerts to bypass quiet hours
                          </p>
                          <div class="flex flex-wrap gap-2">
                            <button
                              @click="setBypassPriority(null)"
                              :class="[
                                'px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors',
                                preferences.quiet_hours_bypass_priority === null ||
                                preferences.quiet_hours_bypass_priority === undefined
                                  ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20 text-violet-700 dark:text-violet-400'
                                  : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500',
                              ]"
                            >
                              None
                            </button>
                            <button
                              v-for="(info, priority) in PRIORITY_INFO"
                              :key="priority"
                              @click="setBypassPriority(priority)"
                              :class="[
                                'px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors',
                                preferences.quiet_hours_bypass_priority === priority
                                  ? getBypassPriorityActiveClasses(priority)
                                  : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500',
                              ]"
                            >
                              {{ info.label }}+
                            </button>
                          </div>
                          <p class="text-xs text-slate-500 dark:text-slate-400 mt-2">
                            <template v-if="preferences.quiet_hours_bypass_priority">
                              <span class="font-medium">{{
                                PRIORITY_INFO[preferences.quiet_hours_bypass_priority].label
                              }}</span>
                              and higher alerts will still be delivered during quiet hours
                            </template>
                            <template v-else>
                              All notifications will be blocked during quiet hours
                            </template>
                          </p>
                        </div>

                        <!-- Timezone selector -->
                        <div class="pt-2 border-t border-slate-200 dark:border-slate-700">
                          <label
                            class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                          >
                            Timezone
                          </label>
                          <p class="text-xs text-slate-500 dark:text-slate-400 mb-2">
                            Select your timezone for accurate quiet hours
                          </p>
                          <div class="flex gap-2">
                            <select
                              v-model="preferences.timezone"
                              @change="savePreferences"
                              class="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent text-sm"
                            >
                              <option :value="null">Use server time</option>
                              <option
                                v-for="tz in COMMON_TIMEZONES"
                                :key="tz.value"
                                :value="tz.value"
                              >
                                {{ tz.label }}
                              </option>
                            </select>
                            <button
                              v-if="detectedTimezone"
                              @click="autoDetectTimezone"
                              class="px-3 py-2 text-sm font-medium text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-700/30 rounded-lg hover:bg-violet-100 dark:hover:bg-violet-900/30 transition-colors whitespace-nowrap"
                              title="Use your browser's detected timezone"
                            >
                              Auto-detect
                            </button>
                          </div>
                          <p
                            v-if="detectedTimezone"
                            class="text-xs text-slate-500 dark:text-slate-400 mt-1"
                          >
                            <template v-if="preferences.timezone === detectedTimezone">
                              ✓ Using your detected timezone
                            </template>
                            <template v-else-if="!preferences.timezone">
                              ⚠️ Using server time - click Auto-detect to use your timezone ({{
                                detectedTimezone
                              }})
                            </template>
                            <template v-else>
                              Your browser detected: {{ detectedTimezone }}
                            </template>
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- ML Stats -->
                <div
                  v-if="serviceStatus?.ml_model_status"
                  class="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700"
                >
                  <div class="flex items-center gap-2 mb-3">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4 text-emerald-500"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                      />
                    </svg>
                    <span class="text-sm font-medium text-slate-700 dark:text-slate-300"
                      >ML Anomaly Detection</span
                    >
                  </div>
                  <div class="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <p class="text-2xl font-bold text-slate-900 dark:text-white">
                        {{ serviceStatus.ml_model_status.devices_tracked }}
                      </p>
                      <p class="text-xs text-slate-500 dark:text-slate-400">Devices Tracked</p>
                    </div>
                    <div>
                      <p class="text-2xl font-bold text-slate-900 dark:text-white">
                        {{ serviceStatus.ml_model_status.anomalies_detected_24h }}
                      </p>
                      <p class="text-xs text-slate-500 dark:text-slate-400">Anomalies (24h)</p>
                    </div>
                    <div>
                      <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                        {{
                          serviceStatus.ml_model_status.is_online_learning
                            ? 'Online Learning'
                            : 'Initializing'
                        }}
                      </p>
                      <p class="text-xs text-slate-500 dark:text-slate-400">Model Status</p>
                    </div>
                  </div>
                </div>

                <!-- Broadcast Notification (Owner Only) -->
                <div v-if="isOwner" class="space-y-4">
                  <h3
                    class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"
                      />
                    </svg>
                    Send Global Notification
                  </h3>

                  <div
                    class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700/30 space-y-4"
                  >
                    <p class="text-sm text-amber-700 dark:text-amber-400">
                      Send a notification to all users who have notifications enabled. Use this for
                      system announcements, maintenance notices, or important updates.
                    </p>

                    <!-- Notification Type -->
                    <div>
                      <label
                        class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                      >
                        Notification Type
                      </label>
                      <select
                        v-model="broadcastType"
                        class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                      >
                        <option value="scheduled_maintenance">🔧 Scheduled Maintenance</option>
                        <option value="system_status">ℹ️ System Status</option>
                        <option value="security_alert">🔒 Security Alert</option>
                        <option value="isp_issue">🌐 ISP Issue</option>
                        <option value="anomaly_detected">⚠️ Anomaly Detected</option>
                        <option value="cartographer_down">🚨 Cartographer Down</option>
                        <option value="cartographer_up">✅ Cartographer Up</option>
                      </select>
                    </div>

                    <!-- Priority -->
                    <div>
                      <label
                        class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                      >
                        Priority
                      </label>
                      <div class="flex gap-2">
                        <button
                          v-for="(info, priority) in PRIORITY_INFO"
                          :key="priority"
                          @click="broadcastPriority = priority"
                          :class="[
                            'flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition-colors',
                            broadcastPriority === priority
                              ? getBypassPriorityActiveClasses(priority)
                              : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500',
                          ]"
                        >
                          {{ info.label }}
                        </button>
                      </div>
                    </div>

                    <!-- Title -->
                    <div>
                      <label
                        class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                      >
                        Title
                      </label>
                      <input
                        v-model="broadcastTitle"
                        type="text"
                        placeholder="e.g., Scheduled Maintenance Tonight"
                        class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                      />
                    </div>

                    <!-- Message -->
                    <div>
                      <label
                        class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                      >
                        Message
                      </label>
                      <textarea
                        v-model="broadcastMessage"
                        rows="3"
                        placeholder="Enter the notification message..."
                        class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent resize-none"
                      ></textarea>
                    </div>

                    <!-- Schedule Toggle -->
                    <div
                      class="flex items-center justify-between pt-2 pb-2 border-t border-amber-200 dark:border-amber-700/30"
                    >
                      <div>
                        <p class="font-medium text-slate-900 dark:text-white text-sm">
                          Schedule for Later
                        </p>
                        <p class="text-xs text-slate-500 dark:text-slate-400">
                          Set a specific time to send this notification
                        </p>
                      </div>
                      <button
                        @click="scheduleMode = !scheduleMode"
                        class="relative w-12 h-7 rounded-full transition-colors"
                        :class="scheduleMode ? 'bg-amber-500' : 'bg-slate-300 dark:bg-slate-600'"
                      >
                        <span
                          class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform"
                          :class="scheduleMode ? 'translate-x-5' : ''"
                        ></span>
                      </button>
                    </div>

                    <!-- Schedule DateTime Picker -->
                    <div v-if="scheduleMode" class="space-y-2">
                      <label class="block text-sm font-medium text-slate-700 dark:text-slate-300">
                        Schedule Date & Time
                      </label>
                      <input
                        v-model="scheduledDateTime"
                        type="datetime-local"
                        :min="minScheduleDateTime"
                        class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                      />
                      <p class="text-xs text-slate-500 dark:text-slate-400">
                        Time is in your local timezone
                      </p>
                    </div>

                    <!-- Send/Schedule Button -->
                    <div class="flex items-center justify-between pt-2">
                      <p class="text-xs text-slate-500 dark:text-slate-400">
                        {{
                          scheduleMode
                            ? 'Will be sent at the scheduled time'
                            : 'Will be sent immediately to all users'
                        }}
                      </p>
                      <button
                        @click="scheduleMode ? scheduleTheBroadcast() : sendBroadcast()"
                        :disabled="
                          sendingBroadcast ||
                          !broadcastTitle.trim() ||
                          !broadcastMessage.trim() ||
                          (scheduleMode && !scheduledDateTime)
                        "
                        class="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center gap-2"
                      >
                        <svg
                          v-if="sendingBroadcast"
                          class="animate-spin h-4 w-4"
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
                        <svg
                          v-else-if="scheduleMode"
                          xmlns="http://www.w3.org/2000/svg"
                          class="h-4 w-4"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          stroke-width="2"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        <svg
                          v-else
                          xmlns="http://www.w3.org/2000/svg"
                          class="h-4 w-4"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          stroke-width="2"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                          />
                        </svg>
                        {{
                          sendingBroadcast
                            ? scheduleMode
                              ? 'Scheduling...'
                              : 'Sending...'
                            : scheduleMode
                              ? 'Schedule Broadcast'
                              : 'Send Now'
                        }}
                      </button>
                    </div>

                    <!-- Broadcast Result -->
                    <Transition
                      enter-active-class="transition ease-out duration-200"
                      enter-from-class="opacity-0"
                      enter-to-class="opacity-100"
                      leave-active-class="transition ease-in duration-150"
                      leave-from-class="opacity-100"
                      leave-to-class="opacity-0"
                    >
                      <div
                        v-if="broadcastResult"
                        class="p-3 rounded-lg"
                        :class="
                          broadcastResult.success
                            ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                            : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                        "
                      >
                        <p
                          v-if="
                            broadcastResult.success && broadcastResult.users_notified !== undefined
                          "
                          class="text-sm font-medium"
                        >
                          ✓ Notification sent to {{ broadcastResult.users_notified }} user(s)
                        </p>
                        <p v-else-if="broadcastResult.success" class="text-sm font-medium">
                          ✓ {{ broadcastResult.error }}
                        </p>
                        <p v-else class="text-sm font-medium">
                          ✗ {{ broadcastResult.error || 'Failed to send notification' }}
                        </p>
                      </div>
                    </Transition>

                    <!-- Scheduled Broadcasts List -->
                    <div
                      v-if="scheduledBroadcasts.length > 0"
                      class="mt-4 pt-4 border-t border-amber-200 dark:border-amber-700/30"
                    >
                      <h4
                        class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          class="h-4 w-4"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          stroke-width="2"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        Scheduled Broadcasts ({{ scheduledBroadcasts.length }})
                      </h4>
                      <div class="space-y-2">
                        <div
                          v-for="broadcast in scheduledBroadcasts"
                          :key="broadcast.id"
                          class="p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700"
                        >
                          <div class="flex items-start justify-between gap-3">
                            <div class="flex-1 min-w-0">
                              <div class="flex items-center gap-2">
                                <span class="text-lg">{{
                                  NOTIFICATION_TYPE_INFO[broadcast.event_type]?.icon || '📢'
                                }}</span>
                                <p
                                  class="font-medium text-slate-900 dark:text-white text-sm truncate"
                                >
                                  {{ broadcast.title }}
                                </p>
                              </div>
                              <p
                                class="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2"
                              >
                                {{ broadcast.message }}
                              </p>
                              <div class="flex items-center gap-2 mt-2 flex-wrap">
                                <span
                                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                                >
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    class="h-3 w-3"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                  >
                                    <path
                                      stroke-linecap="round"
                                      stroke-linejoin="round"
                                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                                    />
                                  </svg>
                                  {{ formatScheduledTime(broadcast.scheduled_at) }}
                                </span>
                                <span
                                  class="px-2 py-0.5 rounded text-xs font-medium"
                                  :class="{
                                    'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400':
                                      broadcast.priority === 'low',
                                    'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400':
                                      broadcast.priority === 'medium',
                                    'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400':
                                      broadcast.priority === 'high',
                                    'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400':
                                      broadcast.priority === 'critical',
                                  }"
                                >
                                  {{ broadcast.priority }}
                                </span>
                                <span
                                  v-if="broadcast.timezone"
                                  class="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
                                >
                                  {{ broadcast.timezone }}
                                </span>
                              </div>
                            </div>
                            <div class="flex items-center gap-1 flex-shrink-0">
                              <button
                                @click="openEditBroadcast(broadcast)"
                                class="p-1.5 text-slate-400 hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
                                title="Edit scheduled broadcast"
                              >
                                <svg
                                  xmlns="http://www.w3.org/2000/svg"
                                  class="h-4 w-4"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                  stroke-width="2"
                                >
                                  <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                  />
                                </svg>
                              </button>
                              <button
                                @click="cancelScheduledBroadcastHandler(broadcast.id)"
                                class="p-1.5 text-slate-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                                title="Cancel scheduled broadcast"
                              >
                                <svg
                                  xmlns="http://www.w3.org/2000/svg"
                                  class="h-4 w-4"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                  stroke-width="2"
                                >
                                  <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M6 18L18 6M6 6l12 12"
                                  />
                                </svg>
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Edit Broadcast Modal -->
                    <Teleport to="body">
                      <Transition
                        enter-active-class="transition ease-out duration-200"
                        enter-from-class="opacity-0"
                        enter-to-class="opacity-100"
                        leave-active-class="transition ease-in duration-150"
                        leave-from-class="opacity-100"
                        leave-to-class="opacity-0"
                      >
                        <div v-if="editingBroadcast" class="fixed inset-0 z-[60] overflow-y-auto">
                          <div class="flex min-h-full items-center justify-center p-4">
                            <div
                              class="fixed inset-0 bg-black/50"
                              @click="closeEditBroadcast"
                            ></div>
                            <div
                              class="relative w-full max-w-md bg-white dark:bg-slate-800 rounded-xl shadow-xl"
                            >
                              <div class="p-6">
                                <div class="flex items-center justify-between mb-4">
                                  <h3 class="text-lg font-semibold text-slate-900 dark:text-white">
                                    Edit Scheduled Broadcast
                                  </h3>
                                  <button
                                    @click="closeEditBroadcast"
                                    class="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                                  >
                                    <svg
                                      xmlns="http://www.w3.org/2000/svg"
                                      class="h-5 w-5"
                                      fill="none"
                                      viewBox="0 0 24 24"
                                      stroke="currentColor"
                                      stroke-width="2"
                                    >
                                      <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M6 18L18 6M6 6l12 12"
                                      />
                                    </svg>
                                  </button>
                                </div>

                                <div class="space-y-4">
                                  <!-- Title -->
                                  <div>
                                    <label
                                      class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                                      >Title</label
                                    >
                                    <input
                                      v-model="editBroadcastTitle"
                                      type="text"
                                      class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                      placeholder="Notification title"
                                    />
                                  </div>

                                  <!-- Message -->
                                  <div>
                                    <label
                                      class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                                      >Message</label
                                    >
                                    <textarea
                                      v-model="editBroadcastMessage"
                                      rows="3"
                                      class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent resize-none"
                                      placeholder="Notification message"
                                    ></textarea>
                                  </div>

                                  <!-- Type & Priority -->
                                  <div class="grid grid-cols-2 gap-3">
                                    <div>
                                      <label
                                        class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                                        >Type</label
                                      >
                                      <select
                                        v-model="editBroadcastType"
                                        class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                      >
                                        <option
                                          v-for="(info, type) in networkNotificationTypes"
                                          :key="type"
                                          :value="type"
                                        >
                                          {{ info.icon }} {{ info.label }}
                                        </option>
                                      </select>
                                    </div>
                                    <div>
                                      <label
                                        class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                                        >Priority</label
                                      >
                                      <select
                                        v-model="editBroadcastPriority"
                                        class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                      >
                                        <option
                                          v-for="(info, priority) in PRIORITY_INFO"
                                          :key="priority"
                                          :value="priority"
                                        >
                                          {{ info.label }}
                                        </option>
                                      </select>
                                    </div>
                                  </div>

                                  <!-- Scheduled Time -->
                                  <div>
                                    <label
                                      class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                                      >Scheduled Time</label
                                    >
                                    <input
                                      v-model="editScheduledDateTime"
                                      type="datetime-local"
                                      :min="minScheduleDateTime"
                                      class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                    />
                                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                      Time is in your local timezone ({{ detectedTimezone }})
                                    </p>
                                  </div>

                                  <!-- Actions -->
                                  <div class="flex justify-end gap-3 pt-2">
                                    <button
                                      @click="closeEditBroadcast"
                                      class="px-4 py-2 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                                    >
                                      Cancel
                                    </button>
                                    <button
                                      @click="saveEditBroadcast"
                                      :disabled="
                                        savingEditBroadcast ||
                                        !editBroadcastTitle.trim() ||
                                        !editBroadcastMessage.trim() ||
                                        !editScheduledDateTime
                                      "
                                      class="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                                    >
                                      <svg
                                        v-if="savingEditBroadcast"
                                        class="animate-spin h-4 w-4"
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
                                      {{ savingEditBroadcast ? 'Saving...' : 'Save Changes' }}
                                    </button>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </Transition>
                    </Teleport>
                  </div>
                </div>
              </template>
            </template>
          </template>

          <!-- Error State -->
          <div
            v-if="error"
            class="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700/30"
          >
            <p class="text-sm text-red-700 dark:text-red-400">{{ error }}</p>
          </div>

          <!-- Test Result Toast -->
          <Transition
            enter-active-class="transition ease-out duration-200"
            enter-from-class="opacity-0 translate-y-2"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition ease-in duration-150"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 translate-y-2"
          >
            <div
              v-if="testResult"
              class="fixed bottom-4 right-4 p-4 rounded-lg shadow-lg"
              :class="testResult.success ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'"
            >
              <p class="font-medium">
                {{ testResult.success ? '✓ Test notification sent!' : '✗ Failed to send' }}
              </p>
              <p v-if="testResult.error" class="text-sm opacity-90">{{ testResult.error }}</p>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, watch } from 'vue';
import * as notificationsApi from '../api/notifications';
import {
  useNotifications,
  NOTIFICATION_TYPE_INFO,
  PRIORITY_INFO,
  type NotificationPreferences,
  type NotificationServiceStatus,
  type DiscordBotInfo,
  type DiscordGuild,
  type DiscordChannel,
  type NotificationType,
  type NotificationPriority,
  type TestNotificationResult,
  type ScheduledBroadcast,
  type ScheduledBroadcastUpdate,
} from '../composables/useNotifications';
import { useAuth } from '../composables/useAuth';

// Common timezones for quiet hours selection
const COMMON_TIMEZONES = [
  // Americas
  { value: 'America/New_York', label: 'Eastern Time (US & Canada)' },
  { value: 'America/Chicago', label: 'Central Time (US & Canada)' },
  { value: 'America/Denver', label: 'Mountain Time (US & Canada)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (US & Canada)' },
  { value: 'America/Anchorage', label: 'Alaska' },
  { value: 'Pacific/Honolulu', label: 'Hawaii' },
  { value: 'America/Toronto', label: 'Eastern Time (Canada)' },
  { value: 'America/Vancouver', label: 'Pacific Time (Canada)' },
  { value: 'America/Mexico_City', label: 'Mexico City' },
  { value: 'America/Sao_Paulo', label: 'São Paulo' },
  { value: 'America/Buenos_Aires', label: 'Buenos Aires' },
  // Europe
  { value: 'Europe/London', label: 'London (GMT/BST)' },
  { value: 'Europe/Paris', label: 'Paris (CET/CEST)' },
  { value: 'Europe/Berlin', label: 'Berlin (CET/CEST)' },
  { value: 'Europe/Amsterdam', label: 'Amsterdam (CET/CEST)' },
  { value: 'Europe/Rome', label: 'Rome (CET/CEST)' },
  { value: 'Europe/Madrid', label: 'Madrid (CET/CEST)' },
  { value: 'Europe/Moscow', label: 'Moscow' },
  // Asia & Pacific
  { value: 'Asia/Dubai', label: 'Dubai' },
  { value: 'Asia/Kolkata', label: 'India (IST)' },
  { value: 'Asia/Singapore', label: 'Singapore' },
  { value: 'Asia/Hong_Kong', label: 'Hong Kong' },
  { value: 'Asia/Shanghai', label: 'China (CST)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Asia/Seoul', label: 'Seoul (KST)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST/AEDT)' },
  { value: 'Australia/Melbourne', label: 'Melbourne (AEST/AEDT)' },
  { value: 'Australia/Perth', label: 'Perth (AWST)' },
  { value: 'Pacific/Auckland', label: 'Auckland (NZST/NZDT)' },
  // UTC
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
];

// Detect user's timezone from browser
const detectedTimezone = computed(() => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return null;
  }
});

const props = defineProps<{
  networkId: string;
}>();

defineEmits<{
  (e: 'close'): void;
}>();

const { isOwner } = useAuth();

const {
  isLoading,
  error,
  getPreferences,
  updatePreferences,
  getServiceStatus,
  getDiscordBotInfo,
  getDiscordGuilds,
  getDiscordChannels,
  sendTestNotification,
  sendBroadcastNotification,
  getScheduledBroadcasts,
  scheduleBroadcast,
  updateScheduledBroadcast,
  cancelScheduledBroadcast,
} = useNotifications(props.networkId);

// Tab state
const activeTab = ref<'network' | 'global'>('network');

// Cartographer Status subscription state
const cartographerStatus = ref<any>(null);
const cartographerStatusLoading = ref(false);
const cartographerStatusEmail = ref('');
const savingCartographerStatus = ref(false);

// Global notification preferences state
const globalPrefs = ref({
  email_enabled: false,
  discord_enabled: false,
  discord_delivery_method: 'dm' as 'channel' | 'dm',
  discord_guild_id: '' as string,
  discord_channel_id: '' as string,
  discord_user_id: '' as string,
  cartographer_up_enabled: true,
  cartographer_down_enabled: true,
  cartographer_up_priority: 'medium' as NotificationPriority,
  cartographer_down_priority: 'critical' as NotificationPriority,
  minimum_priority: 'medium' as NotificationPriority,
  quiet_hours_enabled: false,
  quiet_hours_start: '22:00',
  quiet_hours_end: '08:00',
  quiet_hours_bypass_priority: null as NotificationPriority | null,
  timezone: null as string | null,
});

// Global Discord state
const globalSelectedGuildId = ref('');
const globalSelectedChannelId = ref('');
const globalDiscordChannels = ref<Array<{ id: string; name: string }>>([]);
const loadingGlobalChannels = ref(false);
const testingGlobalDiscord = ref(false);

// User email (from account)
const userEmail = ref('');

// State
const preferences = ref<NotificationPreferences | null>(null);
const serviceStatus = ref<NotificationServiceStatus | null>(null);
const discordBotInfo = ref<DiscordBotInfo | null>(null);
const discordGuilds = ref<DiscordGuild[]>([]);
const discordChannels = ref<DiscordChannel[]>([]);

const selectedGuildId = ref('');
const selectedChannelId = ref('');
const loadingChannels = ref(false);

const testingEmail = ref(false);
const testingDiscord = ref(false);
const testResult = ref<TestNotificationResult | null>(null);

// Broadcast notification state (owner only)
const broadcastTitle = ref('');
const broadcastMessage = ref('');
const broadcastType = ref<NotificationType>('scheduled_maintenance');
const broadcastPriority = ref<NotificationPriority>('medium');
const sendingBroadcast = ref(false);
const broadcastResult = ref<{ success: boolean; users_notified?: number; error?: string } | null>(
  null
);

// Scheduled broadcast state
const scheduleMode = ref(false);
const scheduledDateTime = ref('');
const scheduledBroadcasts = ref<ScheduledBroadcast[]>([]);
const loadingScheduled = ref(false);

// Edit scheduled broadcast state
const editingBroadcast = ref<ScheduledBroadcast | null>(null);
const editBroadcastTitle = ref('');
const editBroadcastMessage = ref('');
const editBroadcastType = ref<NotificationType>('scheduled_maintenance');
const editBroadcastPriority = ref<NotificationPriority>('medium');
const editScheduledDateTime = ref('');
const savingEditBroadcast = ref(false);

// Computed: minimum schedule datetime (5 minutes from now)
const minScheduleDateTime = computed(() => {
  const now = new Date();
  now.setMinutes(now.getMinutes() + 5);
  return now.toISOString().slice(0, 16);
});

// Computed: network-specific notification types (excluding cartographer up/down)
const networkNotificationTypes = computed(() => {
  const excluded = ['cartographer_up', 'cartographer_down'];
  return Object.fromEntries(
    Object.entries(NOTIFICATION_TYPE_INFO).filter(([type]) => !excluded.includes(type))
  ) as typeof NOTIFICATION_TYPE_INFO;
});

// Load user email from account
async function loadUserEmail() {
  try {
    const profile = await notificationsApi.getUserProfile();
    userEmail.value = profile.email || '';
  } catch (e) {
    console.error('Failed to load user email:', e);
  }
}

// Load data
onMounted(async () => {
  try {
    // Load preferences, service status, and user email in parallel
    const [prefs, status] = await Promise.all([
      getPreferences(),
      getServiceStatus(),
      loadUserEmail(),
    ]);

    // Ensure email and discord configs have defaults
    if (!prefs.email) {
      prefs.email = { enabled: false, email_address: '' };
    }
    if (!prefs.discord) {
      prefs.discord = { enabled: false, delivery_method: 'channel' };
    }

    // Auto-set the email address to user's account email
    if (userEmail.value && !prefs.email.email_address) {
      prefs.email.email_address = userEmail.value;
    }

    preferences.value = prefs;
    serviceStatus.value = status;

    // Load Discord info if configured
    if (status.discord_configured) {
      try {
        const [botInfo, guilds] = await Promise.all([getDiscordBotInfo(), getDiscordGuilds()]);
        discordBotInfo.value = botInfo;
        discordGuilds.value = guilds;

        // Restore selected guild/channel from preferences
        if (prefs.discord?.channel_config) {
          selectedGuildId.value = prefs.discord.channel_config.guild_id;
          selectedChannelId.value = prefs.discord.channel_config.channel_id;

          // Load channels for the selected guild
          if (selectedGuildId.value) {
            loadingChannels.value = true;
            discordChannels.value = await getDiscordChannels(selectedGuildId.value);
            loadingChannels.value = false;
          }
        }
      } catch (e) {
        console.error('Failed to load Discord info:', e);
      }
    }

    // Load scheduled broadcasts for owners
    if (isOwner.value) {
      await loadScheduledBroadcasts();
    }

    // Load Cartographer status subscription
    await loadCartographerStatus();
  } catch (e) {
    console.error('Failed to load notification settings:', e);
  }
});

// Save preferences
async function savePreferences() {
  if (!preferences.value) return;

  try {
    // Update local state with server response to stay in sync
    const savedPrefs = await updatePreferences(preferences.value);
    preferences.value = savedPrefs;
  } catch (e) {
    console.error('Failed to save preferences:', e);
  }
}

// Toggle functions
async function toggleMaster() {
  if (!preferences.value) return;
  preferences.value.enabled = !preferences.value.enabled;
  await savePreferences();
}

async function toggleEmail() {
  if (!preferences.value || !serviceStatus.value?.email_configured) return;
  preferences.value.email.enabled = !preferences.value.email.enabled;
  // Auto-set email address to user's account email when enabling
  if (preferences.value.email.enabled && userEmail.value) {
    preferences.value.email.email_address = userEmail.value;
  }
  await savePreferences();
}

async function toggleDiscord() {
  if (!preferences.value) return;
  preferences.value.discord.enabled = !preferences.value.discord.enabled;
  await savePreferences();
}

async function toggleQuietHours() {
  if (!preferences.value) return;
  preferences.value.quiet_hours_enabled = !preferences.value.quiet_hours_enabled;

  // Auto-detect timezone when first enabling quiet hours (if not already set)
  if (
    preferences.value.quiet_hours_enabled &&
    !preferences.value.timezone &&
    detectedTimezone.value
  ) {
    preferences.value.timezone = detectedTimezone.value;
  }

  await savePreferences();
}

async function autoDetectTimezone() {
  if (!preferences.value || !detectedTimezone.value) return;
  preferences.value.timezone = detectedTimezone.value;
  await savePreferences();
}

// Global preference toggles
async function toggleGlobalEmail() {
  if (!serviceStatus.value?.email_configured) return;
  globalPrefs.value.email_enabled = !globalPrefs.value.email_enabled;
  await saveGlobalPrefs();
}

async function toggleGlobalDiscord() {
  if (!serviceStatus.value?.discord_configured) return;
  globalPrefs.value.discord_enabled = !globalPrefs.value.discord_enabled;
  await saveGlobalPrefs();
}

async function setGlobalPriority(priority: NotificationPriority) {
  globalPrefs.value.minimum_priority = priority;
  await saveGlobalPrefs();
}

async function toggleGlobalQuietHours() {
  globalPrefs.value.quiet_hours_enabled = !globalPrefs.value.quiet_hours_enabled;
  await saveGlobalPrefs();
}

async function toggleGlobalCartographerUp() {
  globalPrefs.value.cartographer_up_enabled = !globalPrefs.value.cartographer_up_enabled;
  await saveGlobalPrefs();
}

async function toggleGlobalCartographerDown() {
  globalPrefs.value.cartographer_down_enabled = !globalPrefs.value.cartographer_down_enabled;
  await saveGlobalPrefs();
}

async function setGlobalCartographerUpPriority(priority: NotificationPriority) {
  globalPrefs.value.cartographer_up_priority = priority;
  await saveGlobalPrefs();
}

async function setGlobalCartographerDownPriority(priority: NotificationPriority) {
  globalPrefs.value.cartographer_down_priority = priority;
  await saveGlobalPrefs();
}

async function cycleGlobalCartographerUpPriority() {
  const currentIndex = PRIORITY_ORDER.indexOf(globalPrefs.value.cartographer_up_priority);
  const nextIndex = (currentIndex + 1) % PRIORITY_ORDER.length;
  globalPrefs.value.cartographer_up_priority = PRIORITY_ORDER[nextIndex];
  await saveGlobalPrefs();
}

async function cycleGlobalCartographerDownPriority() {
  const currentIndex = PRIORITY_ORDER.indexOf(globalPrefs.value.cartographer_down_priority);
  const nextIndex = (currentIndex + 1) % PRIORITY_ORDER.length;
  globalPrefs.value.cartographer_down_priority = PRIORITY_ORDER[nextIndex];
  await saveGlobalPrefs();
}

async function setGlobalBypassPriority(priority: NotificationPriority | null) {
  globalPrefs.value.quiet_hours_bypass_priority = priority;
  await saveGlobalPrefs();
}

async function autoDetectGlobalTimezone() {
  if (!detectedTimezone.value) return;
  globalPrefs.value.timezone = detectedTimezone.value;
  await saveGlobalPrefs();
}

async function setGlobalDeliveryMethod(method: 'channel' | 'dm') {
  globalPrefs.value.discord_delivery_method = method;
  await saveGlobalPrefs();
}

async function onGlobalGuildChange() {
  globalSelectedChannelId.value = '';
  globalPrefs.value.discord_guild_id = globalSelectedGuildId.value;
  globalPrefs.value.discord_channel_id = '';

  if (globalSelectedGuildId.value) {
    loadingGlobalChannels.value = true;
    try {
      const response = await notificationsApi.getDiscordGuildChannels(globalSelectedGuildId.value);
      globalDiscordChannels.value = response.channels || [];
    } catch (e) {
      console.error('Failed to load channels:', e);
      globalDiscordChannels.value = [];
    } finally {
      loadingGlobalChannels.value = false;
    }
  } else {
    globalDiscordChannels.value = [];
  }
  await saveGlobalPrefs();
}

async function onGlobalChannelChange() {
  globalPrefs.value.discord_channel_id = globalSelectedChannelId.value;
  await saveGlobalPrefs();
}

async function testGlobalDiscord() {
  testingGlobalDiscord.value = true;
  testResult.value = null;
  try {
    if (globalPrefs.value.discord_delivery_method === 'channel' && globalSelectedChannelId.value) {
      await notificationsApi.testCartographerStatusNotification({
        channel_id: globalSelectedChannelId.value,
      });
    } else if (
      globalPrefs.value.discord_delivery_method === 'dm' &&
      globalPrefs.value.discord_user_id
    ) {
      await notificationsApi.testCartographerStatusNotification({
        user_id: globalPrefs.value.discord_user_id,
      });
    }
    testResult.value = {
      success: true,
      channel: 'discord',
      message: 'Test Discord notification sent!',
    };
    setTimeout(() => {
      testResult.value = null;
    }, 5000);
  } catch (e: unknown) {
    console.error('Failed to send test Discord:', e);
    const error = e instanceof Error ? e.message : 'Unknown error';
    testResult.value = { success: false, channel: 'discord', message: '', error };
    setTimeout(() => {
      testResult.value = null;
    }, 5000);
  } finally {
    testingGlobalDiscord.value = false;
  }
}

async function saveGlobalPrefs() {
  try {
    await notificationsApi.updateCartographerStatusSubscription({
      email_enabled: globalPrefs.value.email_enabled,
      discord_enabled: globalPrefs.value.discord_enabled,
      discord_delivery_method: globalPrefs.value.discord_delivery_method,
      discord_guild_id: globalPrefs.value.discord_guild_id,
      discord_channel_id: globalPrefs.value.discord_channel_id,
      discord_user_id: globalPrefs.value.discord_user_id,
      cartographer_up_enabled: globalPrefs.value.cartographer_up_enabled,
      cartographer_down_enabled: globalPrefs.value.cartographer_down_enabled,
      cartographer_up_priority: globalPrefs.value.cartographer_up_priority,
      cartographer_down_priority: globalPrefs.value.cartographer_down_priority,
      minimum_priority: globalPrefs.value.minimum_priority,
      quiet_hours_enabled: globalPrefs.value.quiet_hours_enabled,
      quiet_hours_start: globalPrefs.value.quiet_hours_start,
      quiet_hours_end: globalPrefs.value.quiet_hours_end,
      quiet_hours_bypass_priority: globalPrefs.value.quiet_hours_bypass_priority,
      timezone: globalPrefs.value.timezone,
    });
  } catch (e: any) {
    console.error('Failed to save global preferences:', e);
  }
}

async function setBypassPriority(priority: NotificationPriority | null) {
  if (!preferences.value) return;
  preferences.value.quiet_hours_bypass_priority = priority;
  await savePreferences();
}

function getBypassPriorityActiveClasses(priority: NotificationPriority): string {
  switch (priority) {
    case 'low':
      return 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400';
    case 'medium':
      return 'border-amber-500 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400';
    case 'high':
      return 'border-orange-500 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400';
    case 'critical':
      return 'border-red-500 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400';
    default:
      return '';
  }
}

async function toggleNotificationType(type: NotificationType) {
  if (!preferences.value) return;

  const index = preferences.value.enabled_notification_types.indexOf(type);
  if (index === -1) {
    preferences.value.enabled_notification_types.push(type);
  } else {
    preferences.value.enabled_notification_types.splice(index, 1);
  }
  await savePreferences();
}

async function setPriority(priority: NotificationPriority) {
  if (!preferences.value) return;
  preferences.value.minimum_priority = priority;
  await savePreferences();
}

// Priority for notification types
const PRIORITY_ORDER: NotificationPriority[] = ['low', 'medium', 'high', 'critical'];

function getEffectivePriority(type: NotificationType): NotificationPriority {
  if (!preferences.value) return NOTIFICATION_TYPE_INFO[type].defaultPriority;
  return (
    preferences.value.notification_type_priorities?.[type] ??
    NOTIFICATION_TYPE_INFO[type].defaultPriority
  );
}

function isDefaultPriority(type: NotificationType): boolean {
  if (!preferences.value?.notification_type_priorities) return true;
  return preferences.value.notification_type_priorities[type] === undefined;
}

async function cycleTypePriority(type: NotificationType) {
  if (!preferences.value) return;

  // Initialize notification_type_priorities if not present
  if (!preferences.value.notification_type_priorities) {
    preferences.value.notification_type_priorities = {};
  }

  const currentPriority = getEffectivePriority(type);
  const currentIndex = PRIORITY_ORDER.indexOf(currentPriority);
  const nextIndex = (currentIndex + 1) % PRIORITY_ORDER.length;
  const nextPriority = PRIORITY_ORDER[nextIndex];

  // If the next priority is the default, remove the override
  if (nextPriority === NOTIFICATION_TYPE_INFO[type].defaultPriority) {
    delete preferences.value.notification_type_priorities[type];
  } else {
    preferences.value.notification_type_priorities[type] = nextPriority;
  }

  await savePreferences();
}

async function resetTypePriority(type: NotificationType) {
  if (!preferences.value?.notification_type_priorities) return;

  delete preferences.value.notification_type_priorities[type];
  await savePreferences();
}

function getPriorityBadgeClasses(priority: NotificationPriority): string {
  const baseClasses = 'cursor-pointer hover:ring-2 hover:ring-offset-1 hover:ring-opacity-50';
  switch (priority) {
    case 'low':
      return `${baseClasses} bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 hover:ring-emerald-400`;
    case 'medium':
      return `${baseClasses} bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 hover:ring-amber-400`;
    case 'high':
      return `${baseClasses} bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 hover:ring-orange-400`;
    case 'critical':
      return `${baseClasses} bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:ring-red-400`;
    default:
      return baseClasses;
  }
}

async function setDeliveryMethod(method: 'channel' | 'dm') {
  if (!preferences.value) return;
  preferences.value.discord.delivery_method = method;
  await savePreferences();
}

// Discord functions
async function refreshDiscordGuilds() {
  try {
    discordGuilds.value = await getDiscordGuilds();
  } catch (e) {
    console.error('Failed to refresh guilds:', e);
  }
}

async function onGuildChange() {
  if (!preferences.value || !selectedGuildId.value) {
    discordChannels.value = [];
    selectedChannelId.value = '';
    return;
  }

  loadingChannels.value = true;
  try {
    discordChannels.value = await getDiscordChannels(selectedGuildId.value);
    selectedChannelId.value = '';

    // Update preferences
    const guild = discordGuilds.value.find((g) => g.id === selectedGuildId.value);
    preferences.value.discord.channel_config = {
      guild_id: selectedGuildId.value,
      channel_id: '',
      guild_name: guild?.name,
    };
    await savePreferences();
  } catch (e) {
    console.error('Failed to load channels:', e);
  } finally {
    loadingChannels.value = false;
  }
}

async function onChannelChange() {
  if (!preferences.value || !selectedChannelId.value) return;

  const channel = discordChannels.value.find((c) => c.id === selectedChannelId.value);
  preferences.value.discord.channel_config = {
    guild_id: selectedGuildId.value,
    channel_id: selectedChannelId.value,
    guild_name: preferences.value.discord.channel_config?.guild_name,
    channel_name: channel?.name,
  };
  await savePreferences();
}

// Test functions
async function testEmail() {
  testingEmail.value = true;
  testResult.value = null;

  try {
    const result = await sendTestNotification('email');
    testResult.value = result;
    setTimeout(() => {
      testResult.value = null;
    }, 5000);
  } catch (e: any) {
    testResult.value = { success: false, channel: 'email', message: '', error: e.message };
    setTimeout(() => {
      testResult.value = null;
    }, 5000);
  } finally {
    testingEmail.value = false;
  }
}

async function testDiscord() {
  testingDiscord.value = true;
  testResult.value = null;

  try {
    const result = await sendTestNotification('discord');
    testResult.value = result;
    setTimeout(() => {
      testResult.value = null;
    }, 5000);
  } catch (e: any) {
    testResult.value = { success: false, channel: 'discord', message: '', error: e.message };
    setTimeout(() => {
      testResult.value = null;
    }, 5000);
  } finally {
    testingDiscord.value = false;
  }
}

// Broadcast notification (owner only)
async function sendBroadcast() {
  if (!broadcastTitle.value.trim() || !broadcastMessage.value.trim()) {
    broadcastResult.value = { success: false, error: 'Title and message are required' };
    setTimeout(() => {
      broadcastResult.value = null;
    }, 5000);
    return;
  }

  sendingBroadcast.value = true;
  broadcastResult.value = null;

  try {
    if (!props.networkId) {
      broadcastResult.value = { success: false, error: 'Network ID is required' };
      return;
    }

    const result = await sendBroadcastNotification(
      props.networkId,
      broadcastTitle.value.trim(),
      broadcastMessage.value.trim(),
      broadcastType.value,
      broadcastPriority.value
    );
    broadcastResult.value = { success: true, users_notified: result.users_notified };

    // Clear form on success
    broadcastTitle.value = '';
    broadcastMessage.value = '';
    broadcastType.value = 'scheduled_maintenance';
    broadcastPriority.value = 'medium';

    setTimeout(() => {
      broadcastResult.value = null;
    }, 5000);
  } catch (e: any) {
    broadcastResult.value = { success: false, error: e.message };
    setTimeout(() => {
      broadcastResult.value = null;
    }, 5000);
  } finally {
    sendingBroadcast.value = false;
  }
}

// Schedule broadcast (owner only)
async function scheduleTheBroadcast() {
  if (!broadcastTitle.value.trim() || !broadcastMessage.value.trim() || !scheduledDateTime.value) {
    broadcastResult.value = {
      success: false,
      error: 'Title, message, and schedule time are required',
    };
    setTimeout(() => {
      broadcastResult.value = null;
    }, 5000);
    return;
  }

  sendingBroadcast.value = true;
  broadcastResult.value = null;

  try {
    if (!props.networkId) {
      broadcastResult.value = { success: false, error: 'Network ID is required' };
      return;
    }

    const scheduleDate = new Date(scheduledDateTime.value);

    await scheduleBroadcast(
      props.networkId,
      broadcastTitle.value.trim(),
      broadcastMessage.value.trim(),
      scheduleDate,
      broadcastType.value,
      broadcastPriority.value
    );

    broadcastResult.value = {
      success: true,
      error: `Broadcast scheduled for ${scheduleDate.toLocaleString()}`,
    };

    // Clear form on success
    broadcastTitle.value = '';
    broadcastMessage.value = '';
    broadcastType.value = 'scheduled_maintenance';
    broadcastPriority.value = 'medium';
    scheduledDateTime.value = '';
    scheduleMode.value = false;

    // Refresh scheduled broadcasts list
    await loadScheduledBroadcasts();

    setTimeout(() => {
      broadcastResult.value = null;
    }, 5000);
  } catch (e: any) {
    broadcastResult.value = { success: false, error: e.message };
    setTimeout(() => {
      broadcastResult.value = null;
    }, 5000);
  } finally {
    sendingBroadcast.value = false;
  }
}

// Load scheduled broadcasts
async function loadScheduledBroadcasts() {
  if (!isOwner.value) return;

  loadingScheduled.value = true;
  try {
    const response = await getScheduledBroadcasts(false);
    scheduledBroadcasts.value = response.broadcasts;
  } catch (e) {
    console.error('Failed to load scheduled broadcasts:', e);
  } finally {
    loadingScheduled.value = false;
  }
}

// Cancel a scheduled broadcast
async function cancelScheduledBroadcastHandler(broadcastId: string) {
  try {
    await cancelScheduledBroadcast(broadcastId);
    await loadScheduledBroadcasts();
  } catch (e: any) {
    console.error('Failed to cancel broadcast:', e);
    broadcastResult.value = { success: false, error: e.message };
    setTimeout(() => {
      broadcastResult.value = null;
    }, 5000);
  }
}

// Open edit modal for a scheduled broadcast
function openEditBroadcast(broadcast: ScheduledBroadcast) {
  editingBroadcast.value = broadcast;
  editBroadcastTitle.value = broadcast.title;
  editBroadcastMessage.value = broadcast.message;
  editBroadcastType.value = broadcast.event_type;
  editBroadcastPriority.value = broadcast.priority;
  // Convert UTC to local datetime-local format
  const date = new Date(broadcast.scheduled_at);
  editScheduledDateTime.value = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}

// Close edit modal
function closeEditBroadcast() {
  editingBroadcast.value = null;
  editBroadcastTitle.value = '';
  editBroadcastMessage.value = '';
  editBroadcastType.value = 'scheduled_maintenance';
  editBroadcastPriority.value = 'medium';
  editScheduledDateTime.value = '';
}

// Save edited broadcast
async function saveEditBroadcast() {
  if (!editingBroadcast.value) return;

  savingEditBroadcast.value = true;
  try {
    const update: ScheduledBroadcastUpdate = {};

    if (editBroadcastTitle.value !== editingBroadcast.value.title) {
      update.title = editBroadcastTitle.value;
    }
    if (editBroadcastMessage.value !== editingBroadcast.value.message) {
      update.message = editBroadcastMessage.value;
    }
    if (editBroadcastType.value !== editingBroadcast.value.event_type) {
      update.event_type = editBroadcastType.value;
    }
    if (editBroadcastPriority.value !== editingBroadcast.value.priority) {
      update.priority = editBroadcastPriority.value;
    }

    // Check if scheduled time changed
    const newScheduledDate = new Date(editScheduledDateTime.value);
    const originalDate = new Date(editingBroadcast.value.scheduled_at);
    if (newScheduledDate.getTime() !== originalDate.getTime()) {
      update.scheduled_at = newScheduledDate.toISOString();
      update.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    }

    await updateScheduledBroadcast(editingBroadcast.value.id, update);
    await loadScheduledBroadcasts();
    closeEditBroadcast();

    broadcastResult.value = { success: true, error: 'Broadcast updated successfully' };
    setTimeout(() => {
      broadcastResult.value = null;
    }, 3000);
  } catch (e: any) {
    console.error('Failed to update broadcast:', e);
    broadcastResult.value = { success: false, error: e.message };
    setTimeout(() => {
      broadcastResult.value = null;
    }, 5000);
  } finally {
    savingEditBroadcast.value = false;
  }
}

// Format date for display
function formatScheduledTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString();
}

// Cartographer Status subscription functions
async function loadCartographerStatus() {
  cartographerStatusLoading.value = true;
  try {
    const data = await notificationsApi.getCartographerStatusSubscription();
    cartographerStatus.value = data;
    if (data.email_address) {
      cartographerStatusEmail.value = data.email_address;
    }
    // Load global prefs from subscription
    globalPrefs.value.email_enabled = data.email_enabled ?? false;
    globalPrefs.value.discord_enabled = data.discord_enabled ?? false;
    globalPrefs.value.discord_delivery_method = data.discord_delivery_method ?? 'dm';
    globalPrefs.value.discord_guild_id = data.discord_guild_id ?? '';
    globalPrefs.value.discord_channel_id = data.discord_channel_id ?? '';
    globalPrefs.value.discord_user_id = data.discord_user_id ?? '';
    globalPrefs.value.cartographer_up_enabled = data.cartographer_up_enabled ?? true;
    globalPrefs.value.cartographer_down_enabled = data.cartographer_down_enabled ?? true;
    globalPrefs.value.cartographer_up_priority =
      ((data as Record<string, unknown>).cartographer_up_priority as string) ?? 'medium';
    globalPrefs.value.cartographer_down_priority =
      ((data as Record<string, unknown>).cartographer_down_priority as string) ?? 'critical';
    globalPrefs.value.minimum_priority =
      ((data as Record<string, unknown>).minimum_priority as string) ?? 'medium';
    globalPrefs.value.quiet_hours_enabled =
      ((data as Record<string, unknown>).quiet_hours_enabled as boolean) ?? false;
    globalPrefs.value.quiet_hours_start =
      ((data as Record<string, unknown>).quiet_hours_start as string) ?? '22:00';
    globalPrefs.value.quiet_hours_end =
      ((data as Record<string, unknown>).quiet_hours_end as string) ?? '08:00';
    globalPrefs.value.quiet_hours_bypass_priority =
      ((data as Record<string, unknown>).quiet_hours_bypass_priority as string) ?? null;
    globalPrefs.value.timezone = ((data as Record<string, unknown>).timezone as string) ?? null;

    // Set up global Discord channel selection if previously configured
    if (globalPrefs.value.discord_guild_id) {
      globalSelectedGuildId.value = globalPrefs.value.discord_guild_id;
      // Load channels for this guild
      try {
        const channelsResponse = await notificationsApi.getDiscordGuildChannels(
          globalPrefs.value.discord_guild_id
        );
        globalDiscordChannels.value = channelsResponse.channels || [];
        if (globalPrefs.value.discord_channel_id) {
          globalSelectedChannelId.value = globalPrefs.value.discord_channel_id;
        }
      } catch (e) {
        console.error('Failed to load global Discord channels:', e);
      }
    }
  } catch (e: unknown) {
    const axiosError = e as { response?: { status?: number } };
    if (axiosError.response?.status === 404) {
      cartographerStatus.value = { subscribed: false };
    } else {
      console.error('Failed to load Cartographer status subscription:', e);
    }
  } finally {
    cartographerStatusLoading.value = false;
  }
}

async function subscribeCartographerStatus() {
  if (!cartographerStatusEmail.value) return;

  savingCartographerStatus.value = true;
  try {
    const data = await notificationsApi.createCartographerStatusSubscription({
      email_address: cartographerStatusEmail.value,
      cartographer_up_enabled: true,
      cartographer_down_enabled: true,
    });
    cartographerStatus.value = data;
  } catch (e: unknown) {
    console.error('Failed to subscribe:', e);
    const axiosError = e as { response?: { data?: { detail?: string } } };
    alert(axiosError.response?.data?.detail || 'Failed to subscribe');
  } finally {
    savingCartographerStatus.value = false;
  }
}

async function updateCartographerStatusEmail() {
  const newEmail = prompt(
    'Enter new email address:',
    cartographerStatus.value?.email_address || ''
  );
  if (!newEmail) return;

  savingCartographerStatus.value = true;
  try {
    const data = await notificationsApi.updateCartographerStatusSubscription({
      email_address: newEmail,
    });
    cartographerStatus.value = data;
    cartographerStatusEmail.value = newEmail;
  } catch (e: unknown) {
    console.error('Failed to update email:', e);
    const axiosError = e as { response?: { data?: { detail?: string } } };
    alert(axiosError.response?.data?.detail || 'Failed to update email');
  } finally {
    savingCartographerStatus.value = false;
  }
}

async function toggleCartographerUp() {
  if (!cartographerStatus.value) return;

  savingCartographerStatus.value = true;
  try {
    const data = await notificationsApi.updateCartographerStatusSubscription({
      cartographer_up_enabled: !cartographerStatus.value.cartographer_up_enabled,
    });
    cartographerStatus.value = data;
  } catch (e: unknown) {
    console.error('Failed to update:', e);
    const axiosError = e as { response?: { data?: { detail?: string } } };
    alert(axiosError.response?.data?.detail || 'Failed to update');
  } finally {
    savingCartographerStatus.value = false;
  }
}

async function toggleCartographerDown() {
  if (!cartographerStatus.value) return;

  savingCartographerStatus.value = true;
  try {
    const data = await notificationsApi.updateCartographerStatusSubscription({
      cartographer_down_enabled: !cartographerStatus.value.cartographer_down_enabled,
    });
    cartographerStatus.value = data;
  } catch (e: unknown) {
    console.error('Failed to update:', e);
    const axiosError = e as { response?: { data?: { detail?: string } } };
    alert(axiosError.response?.data?.detail || 'Failed to update');
  } finally {
    savingCartographerStatus.value = false;
  }
}

async function unsubscribeCartographerStatus() {
  if (!confirm('Are you sure you want to unsubscribe from Cartographer status notifications?')) {
    return;
  }

  savingCartographerStatus.value = true;
  try {
    await notificationsApi.deleteCartographerStatusSubscription();
    cartographerStatus.value = { subscribed: false };
    cartographerStatusEmail.value = '';
  } catch (e: unknown) {
    console.error('Failed to unsubscribe:', e);
    const axiosError = e as { response?: { data?: { detail?: string } } };
    alert(axiosError.response?.data?.detail || 'Failed to unsubscribe');
  } finally {
    savingCartographerStatus.value = false;
  }
}
</script>
