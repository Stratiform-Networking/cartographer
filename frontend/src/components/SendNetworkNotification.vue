<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
      @click.self="$emit('close')"
    >
      <div
        class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[90vh] border border-slate-200/80 dark:border-slate-800/80"
      >
        <!-- Header -->
        <div
          class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl"
        >
          <div class="flex items-center gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 text-violet-500 dark:text-violet-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
            </svg>
            <div>
              <h2 class="font-semibold text-slate-800 dark:text-slate-100">
                Send Network Notification
              </h2>
              <p class="text-xs text-slate-500 dark:text-slate-400">
                Send a notification to all users in this network
              </p>
            </div>
          </div>
          <button
            @click="$emit('close')"
            class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
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

        <!-- Tabs -->
        <div
          class="flex border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50"
        >
          <button
            @click="activeTab = 'compose'"
            :class="[
              'px-6 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'compose'
                ? 'border-violet-500 text-violet-600 dark:text-violet-400 bg-white dark:bg-slate-900'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300',
            ]"
          >
            Compose
          </button>
          <button
            @click="
              activeTab = 'scheduled';
              loadScheduledBroadcasts();
            "
            :class="[
              'px-6 py-3 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2',
              activeTab === 'scheduled'
                ? 'border-violet-500 text-violet-600 dark:text-violet-400 bg-white dark:bg-slate-900'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300',
            ]"
          >
            Scheduled
            <span
              v-if="scheduledBroadcasts.length > 0"
              class="px-1.5 py-0.5 text-xs rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400"
            >
              {{ scheduledBroadcasts.length }}
            </span>
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto p-4">
          <!-- Compose Tab -->
          <div v-if="activeTab === 'compose'" class="space-y-4">
            <!-- Type & Priority row -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Notification Type
                </label>
                <select
                  v-model="form.type"
                  class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
                >
                  <option value="scheduled_maintenance">Maintenance</option>
                  <option value="system_status">System Status</option>
                  <option value="security_alert">Security Alert</option>
                  <option value="isp_issue">ISP Issue</option>
                  <option value="device_offline">Device Offline</option>
                  <option value="device_online">Device Online</option>
                  <option value="device_degraded">Device Degraded</option>
                  <option value="anomaly_detected">Anomaly Detected</option>
                  <option value="high_latency">High Latency</option>
                  <option value="packet_loss">Packet Loss</option>
                  <option value="device_added">Device Added</option>
                  <option value="device_removed">Device Removed</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Priority
                </label>
                <select
                  v-model="form.priority"
                  class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>

            <!-- Title -->
            <div>
              <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Title
              </label>
              <input
                v-model="form.title"
                type="text"
                placeholder="Notification title"
                class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
              />
            </div>

            <!-- Message -->
            <div>
              <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Message
              </label>
              <textarea
                v-model="form.message"
                rows="3"
                placeholder="Notification message"
                class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-white resize-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
              ></textarea>
            </div>

            <!-- Schedule -->
            <div
              class="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-700/50 space-y-2"
            >
              <div class="flex items-center gap-3">
                <input
                  type="radio"
                  id="send-now"
                  value="now"
                  v-model="scheduleMode"
                  class="w-4 h-4 text-violet-600"
                />
                <label for="send-now" class="text-sm text-slate-700 dark:text-slate-300">
                  Send immediately
                </label>
              </div>
              <div class="flex items-center gap-3">
                <input
                  type="radio"
                  id="schedule"
                  value="schedule"
                  v-model="scheduleMode"
                  class="w-4 h-4 text-violet-600"
                />
                <label for="schedule" class="text-sm text-slate-700 dark:text-slate-300">
                  Schedule for later
                </label>
              </div>
              <div v-if="scheduleMode === 'schedule'" class="ml-7 space-y-1.5">
                <input
                  v-model="scheduledDateTime"
                  type="datetime-local"
                  :min="minScheduleDateTime"
                  class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
                />
                <p class="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
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
                  Time is in your local timezone ({{ detectedTimezone }})
                </p>
              </div>
            </div>

            <!-- Error/Success Message -->
            <div
              v-if="error"
              class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200/80 dark:border-red-800/50 rounded-lg"
            >
              <p class="text-sm text-red-700 dark:text-red-400">{{ error }}</p>
            </div>
            <div
              v-if="successMessage"
              class="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200/80 dark:border-emerald-800/50 rounded-lg"
            >
              <p class="text-sm text-emerald-700 dark:text-emerald-400">{{ successMessage }}</p>
            </div>
          </div>

          <!-- Scheduled Tab -->
          <div v-else-if="activeTab === 'scheduled'" class="space-y-3">
            <div v-if="loadingScheduled" class="flex flex-col items-center justify-center py-8">
              <div class="flex gap-1.5 mb-3">
                <span
                  class="w-2 h-2 rounded-full bg-violet-500 animate-bounce"
                  style="animation-delay: 0ms"
                ></span>
                <span
                  class="w-2 h-2 rounded-full bg-violet-500 animate-bounce"
                  style="animation-delay: 150ms"
                ></span>
                <span
                  class="w-2 h-2 rounded-full bg-violet-500 animate-bounce"
                  style="animation-delay: 300ms"
                ></span>
              </div>
              <p class="text-sm text-slate-500 dark:text-slate-400">Loading scheduled...</p>
            </div>

            <div v-else-if="scheduledBroadcasts.length === 0" class="text-center py-8">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-10 w-10 mx-auto text-slate-300 dark:text-slate-600 mb-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="1"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p class="text-sm text-slate-500 dark:text-slate-400">No scheduled broadcasts</p>
              <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">
                Schedule a notification using the Compose tab
              </p>
            </div>

            <div v-else class="space-y-2">
              <div
                v-for="broadcast in scheduledBroadcasts"
                :key="broadcast.id"
                class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50"
                :class="{
                  'border-emerald-300 dark:border-emerald-700/50': broadcast.status === 'sent',
                  'border-amber-300 dark:border-amber-700/50': countdowns[broadcast.id]?.isSending,
                  'border-red-300 dark:border-red-700/50': broadcast.status === 'failed',
                }"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                      <span class="text-base">{{ getTypeIcon(broadcast.event_type) }}</span>
                      <p class="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                        {{ broadcast.title }}
                      </p>
                    </div>
                    <p class="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-2">
                      {{ broadcast.message }}
                    </p>
                    <div class="flex items-center gap-2 flex-wrap">
                      <!-- Status Badge with Countdown -->
                      <span
                        class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium transition-all"
                        :class="getBroadcastStatus(broadcast).class"
                      >
                        <span class="text-sm">{{ getBroadcastStatus(broadcast).icon }}</span>
                        {{ getBroadcastStatus(broadcast).label }}
                      </span>

                      <!-- Scheduled Time (show for pending) -->
                      <span
                        v-if="broadcast.status === 'pending'"
                        class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
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
                            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                          />
                        </svg>
                        {{ formatScheduledTime(broadcast.scheduled_at) }}
                      </span>

                      <!-- Priority -->
                      <span
                        class="px-2 py-0.5 rounded text-xs font-medium"
                        :class="getPriorityClass(broadcast.priority)"
                      >
                        {{ broadcast.priority }}
                      </span>

                      <!-- Timezone -->
                      <span
                        v-if="broadcast.timezone && broadcast.status === 'pending'"
                        class="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
                      >
                        {{ broadcast.timezone }}
                      </span>
                    </div>
                  </div>
                  <!-- Actions (only for pending broadcasts) -->
                  <div
                    v-if="broadcast.status === 'pending' && !countdowns[broadcast.id]?.isSending"
                    class="flex items-center gap-1 flex-shrink-0"
                  >
                    <button
                      @click="openEditModal(broadcast)"
                      class="p-1.5 text-slate-400 hover:text-blue-500 dark:hover:text-blue-400 transition-colors rounded hover:bg-slate-200 dark:hover:bg-slate-800"
                      title="Edit"
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
                      @click="cancelBroadcast(broadcast.id)"
                      class="p-1.5 text-slate-400 hover:text-red-500 dark:hover:text-red-400 transition-colors rounded hover:bg-slate-200 dark:hover:bg-slate-800"
                      title="Cancel"
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
                  <!-- Sending spinner -->
                  <div v-else-if="countdowns[broadcast.id]?.isSending" class="flex-shrink-0">
                    <svg
                      class="animate-spin h-5 w-5 text-amber-500"
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
                  <!-- Sent checkmark -->
                  <div v-else-if="broadcast.status === 'sent'" class="flex-shrink-0">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-5 w-5 text-emerald-500"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div
          v-if="activeTab === 'compose'"
          class="flex items-center justify-end gap-3 px-4 py-3 border-t border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-b-xl"
        >
          <button
            @click="$emit('close')"
            class="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            @click="handleSend"
            :disabled="!isValid || isSending"
            class="px-4 py-1.5 text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 rounded-lg shadow-sm shadow-violet-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg
              v-if="isSending"
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
            {{ isSending ? 'Sending...' : scheduleMode === 'schedule' ? 'Schedule' : 'Send Now' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="editingBroadcast"
        class="fixed inset-0 z-[60] flex items-center justify-center p-4"
      >
        <div class="fixed inset-0 bg-black/60" @click="closeEditModal"></div>
        <div
          class="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200/80 dark:border-slate-800/80"
        >
          <!-- Modal Header -->
          <div
            class="flex items-center gap-2 px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 text-violet-500"
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
            <h3 class="font-semibold text-slate-800 dark:text-slate-100">
              Edit Scheduled Broadcast
            </h3>
            <button
              @click="closeEditModal"
              class="ml-auto p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
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

          <div class="p-4 space-y-3">
            <!-- Title -->
            <div>
              <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
                >Title</label
              >
              <input
                v-model="editForm.title"
                type="text"
                class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
              />
            </div>

            <!-- Message -->
            <div>
              <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
                >Message</label
              >
              <textarea
                v-model="editForm.message"
                rows="3"
                class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent resize-none transition-shadow"
              ></textarea>
            </div>

            <!-- Type & Priority -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
                  >Type</label
                >
                <select
                  v-model="editForm.type"
                  class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
                >
                  <option value="scheduled_maintenance">Maintenance</option>
                  <option value="system_status">System Status</option>
                  <option value="security_alert">Security Alert</option>
                  <option value="isp_issue">ISP Issue</option>
                  <option value="device_offline">Device Offline</option>
                  <option value="device_online">Device Online</option>
                  <option value="device_degraded">Device Degraded</option>
                  <option value="anomaly_detected">Anomaly</option>
                  <option value="high_latency">High Latency</option>
                  <option value="packet_loss">Packet Loss</option>
                  <option value="device_added">Device Added</option>
                  <option value="device_removed">Device Removed</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
                  >Priority</label
                >
                <select
                  v-model="editForm.priority"
                  class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>

            <!-- Scheduled Time -->
            <div>
              <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
                >Scheduled Time</label
              >
              <input
                v-model="editForm.scheduledAt"
                type="datetime-local"
                :min="minScheduleDateTime"
                class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-white focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
              />
              <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Time is in your local timezone ({{ detectedTimezone }})
              </p>
            </div>

            <!-- Edit Error -->
            <div
              v-if="editError"
              class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200/80 dark:border-red-800/50 rounded-lg"
            >
              <p class="text-sm text-red-700 dark:text-red-400">{{ editError }}</p>
            </div>

            <!-- Actions -->
            <div class="flex justify-end gap-3 pt-2">
              <button
                @click="closeEditModal"
                class="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                @click="saveEdit"
                :disabled="
                  savingEdit ||
                  !editForm.title.trim() ||
                  !editForm.message.trim() ||
                  !editForm.scheduledAt
                "
                class="px-4 py-1.5 text-sm font-medium bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white rounded-lg hover:from-violet-500 hover:to-fuchsia-500 shadow-sm shadow-violet-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
              >
                <svg
                  v-if="savingEdit"
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
                {{ savingEdit ? 'Saving...' : 'Save Changes' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue';
import * as notificationsApi from '../api/notifications';

interface ScheduledBroadcast {
  id: string;
  title: string;
  message: string;
  event_type: string;
  priority: string;
  network_id: string;
  scheduled_at: string;
  timezone?: string;
  status: 'pending' | 'sent' | 'cancelled' | 'failed';
  sent_at?: string;
  seen_at?: string; // When a user first viewed this after it was sent (backend-persisted)
  users_notified?: number;
}

const props = defineProps<{
  networkId: string;
}>();

const emit = defineEmits<{
  close: [];
  sent: [];
}>();

// Tab state
const activeTab = ref<'compose' | 'scheduled'>('compose');

// Compose form
const form = ref({
  type: 'scheduled_maintenance',
  priority: 'medium',
  title: '',
  message: '',
});

const scheduleMode = ref<'now' | 'schedule'>('now');
const scheduledDateTime = ref('');
const error = ref<string | null>(null);
const successMessage = ref<string | null>(null);
const isSending = ref(false);

// Scheduled broadcasts
const scheduledBroadcasts = ref<ScheduledBroadcast[]>([]);
const loadingScheduled = ref(false);

// Countdown timers
const countdowns = reactive<Record<string, { timeLeft: number; isSending: boolean }>>({});
let countdownInterval: ReturnType<typeof setInterval> | null = null;
let pollInterval: ReturnType<typeof setInterval> | null = null;

// Track which broadcasts we've already marked as seen (to avoid duplicate API calls)
const markedAsSeenIds = new Set<string>();

// Edit modal
const editingBroadcast = ref<ScheduledBroadcast | null>(null);
const editForm = ref({
  title: '',
  message: '',
  type: 'scheduled_maintenance',
  priority: 'medium',
  scheduledAt: '',
});
const savingEdit = ref(false);
const editError = ref<string | null>(null);

// Detected timezone
const detectedTimezone = computed(() => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return 'UTC';
  }
});

// Minimum schedule datetime (5 minutes from now)
const minScheduleDateTime = computed(() => {
  const now = new Date();
  now.setMinutes(now.getMinutes() + 5);
  return now.toISOString().slice(0, 16);
});

const isValid = computed(() => {
  if (scheduleMode.value === 'schedule' && !scheduledDateTime.value) {
    return false;
  }
  return form.value.title.trim().length > 0 && form.value.message.trim().length > 0;
});

// Mark a broadcast as seen on the backend and return the seen_at timestamp
async function markBroadcastAsSeen(broadcastId: string): Promise<string | null> {
  if (markedAsSeenIds.has(broadcastId)) return null;

  markedAsSeenIds.add(broadcastId);
  try {
    const response = await notificationsApi.markBroadcastAsSeen(broadcastId);
    return response.seen_at || null;
  } catch (e) {
    console.error('Failed to mark broadcast as seen:', e);
    // Remove from set so we can retry
    markedAsSeenIds.delete(broadcastId);
    return null;
  }
}

// Load scheduled broadcasts
async function loadScheduledBroadcasts(showLoading = true) {
  if (showLoading) loadingScheduled.value = true;
  try {
    const response = await notificationsApi.getScheduledBroadcasts(true);
    const allBroadcasts = (response.broadcasts as unknown as ScheduledBroadcast[]).filter(
      (b: ScheduledBroadcast) => b.network_id === props.networkId
    );

    const now = Date.now();
    const SENT_DISPLAY_DURATION = 5000; // Show "Sent" for 5 seconds after being seen

    // Process broadcasts and mark sent ones as seen
    const visibleBroadcasts: ScheduledBroadcast[] = [];
    const markSeenPromises: Promise<void>[] = [];

    for (const b of allBroadcasts) {
      // Always show pending broadcasts
      if (b.status === 'pending') {
        visibleBroadcasts.push(b);
        continue;
      }

      // Show failed broadcasts
      if (b.status === 'failed') {
        visibleBroadcasts.push(b);
        continue;
      }

      // For sent broadcasts, use backend's seen_at for timing
      if (b.status === 'sent') {
        if (!b.seen_at) {
          // Not yet seen - mark as seen on backend
          // Use a closure to capture the broadcast
          const broadcast = b;
          markSeenPromises.push(
            markBroadcastAsSeen(broadcast.id).then((seenAt) => {
              if (seenAt) {
                broadcast.seen_at = seenAt;
              }
            })
          );
          visibleBroadcasts.push(b);
          continue;
        }

        // Check if it's been seen long enough to hide
        // Handle both naive datetimes (no timezone) and UTC datetimes
        // Naive datetimes from the backend should be treated as UTC
        let seenAtStr = b.seen_at;
        if (
          !seenAtStr.includes('Z') &&
          !seenAtStr.includes('+') &&
          !seenAtStr.match(/-\d{2}:\d{2}$/)
        ) {
          seenAtStr += 'Z'; // Treat naive datetime as UTC
        }
        const seenTime = new Date(seenAtStr).getTime();
        const seenDuration = now - seenTime;

        if (seenDuration < SENT_DISPLAY_DURATION) {
          // Still within display window
          visibleBroadcasts.push(b);
        }
        // Otherwise, don't include it (hidden permanently)
      }
    }

    // Wait for all mark-as-seen calls to complete
    await Promise.all(markSeenPromises);

    scheduledBroadcasts.value = visibleBroadcasts;

    // Update countdown states
    updateCountdowns();
  } catch (e) {
    console.error('Failed to load scheduled broadcasts:', e);
  } finally {
    loadingScheduled.value = false;
  }
}

// Update countdown timers for all broadcasts
function updateCountdowns() {
  const now = Date.now();

  for (const broadcast of scheduledBroadcasts.value) {
    const scheduledTime = new Date(broadcast.scheduled_at).getTime();
    const timeLeft = scheduledTime - now;

    // Determine if it's in "sending" state (past due but not yet sent)
    const isSending = broadcast.status === 'pending' && timeLeft <= 0;

    countdowns[broadcast.id] = {
      timeLeft: Math.max(0, timeLeft),
      isSending,
    };
  }

  // Clean up countdowns for removed broadcasts
  for (const id of Object.keys(countdowns)) {
    if (!scheduledBroadcasts.value.find((b) => b.id === id)) {
      delete countdowns[id];
    }
  }
}

// Format countdown for display
function formatCountdown(broadcastId: string): string {
  const countdown = countdowns[broadcastId];
  if (!countdown) return '';

  const timeLeft = countdown.timeLeft;

  if (timeLeft <= 0) return '';

  const seconds = Math.floor(timeLeft / 1000) % 60;
  const minutes = Math.floor(timeLeft / (1000 * 60)) % 60;
  const hours = Math.floor(timeLeft / (1000 * 60 * 60)) % 24;
  const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));

  if (days > 0) {
    return `${days}d ${hours}h`;
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  } else {
    return `${seconds}s`;
  }
}

// Get broadcast status for display
function getBroadcastStatus(broadcast: ScheduledBroadcast): {
  label: string;
  class: string;
  icon: string;
} {
  if (broadcast.status === 'sent') {
    return {
      label: `Sent${broadcast.users_notified ? ` to ${broadcast.users_notified} user${broadcast.users_notified !== 1 ? 's' : ''}` : ''}`,
      class: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
      icon: '✓',
    };
  }

  if (broadcast.status === 'failed') {
    return {
      label: 'Failed',
      class: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
      icon: '✗',
    };
  }

  const countdown = countdowns[broadcast.id];
  if (countdown?.isSending) {
    return {
      label: 'Sending...',
      class: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 animate-pulse',
      icon: '⏳',
    };
  }

  const timeDisplay = formatCountdown(broadcast.id);
  return {
    label: timeDisplay ? `in ${timeDisplay}` : 'Scheduled',
    class: 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400',
    icon: '⏱',
  };
}

// Start countdown timer interval
function startCountdownTimer() {
  if (countdownInterval) return;

  countdownInterval = setInterval(() => {
    updateCountdowns();
  }, 1000);
}

// Start polling for status updates (check every 5 seconds for status changes)
function startPolling() {
  if (pollInterval) return;

  pollInterval = setInterval(async () => {
    // Poll if we have broadcasts that are sending OR recently sent (still visible)
    const hasSending = scheduledBroadcasts.value.some(
      (b) => b.status === 'pending' && countdowns[b.id]?.isSending
    );
    const hasSentVisible = scheduledBroadcasts.value.some((b) => b.status === 'sent');

    if (hasSending || hasSentVisible) {
      await loadScheduledBroadcasts(false);
    }
  }, 1000); // Poll every second for smooth transitions
}

// Stop timers
function stopTimers() {
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

// Send or schedule notification
async function handleSend() {
  if (!isValid.value) return;

  error.value = null;
  successMessage.value = null;
  isSending.value = true;

  try {
    if (scheduleMode.value === 'schedule' && scheduledDateTime.value) {
      // Schedule for later
      const date = new Date(scheduledDateTime.value);
      await notificationsApi.scheduleBroadcast(
        props.networkId,
        form.value.title,
        form.value.message,
        date,
        form.value.type as 'scheduled_maintenance',
        form.value.priority as 'medium',
        detectedTimezone.value
      );

      successMessage.value = `Notification scheduled for ${date.toLocaleString()}`;

      // Reset form
      form.value = { type: 'scheduled_maintenance', priority: 'medium', title: '', message: '' };
      scheduledDateTime.value = '';
      scheduleMode.value = 'now';

      // Refresh scheduled list
      await loadScheduledBroadcasts();

      setTimeout(() => {
        successMessage.value = null;
      }, 5000);
    } else {
      // Send immediately
      await notificationsApi.sendNetworkNotification(props.networkId, {
        title: form.value.title,
        message: form.value.message,
        type: form.value.type,
        priority: form.value.priority,
      });

      emit('sent');
      emit('close');
    }
  } catch (e: unknown) {
    const axiosError = e as { response?: { data?: { detail?: string } }; message?: string };
    error.value =
      axiosError.response?.data?.detail || axiosError.message || 'Failed to send notification';
    setTimeout(() => {
      error.value = null;
    }, 5000);
  } finally {
    isSending.value = false;
  }
}

// Cancel a scheduled broadcast
async function cancelBroadcast(broadcastId: string) {
  try {
    await notificationsApi.cancelScheduledBroadcast(broadcastId);
    await loadScheduledBroadcasts();
  } catch (e: unknown) {
    console.error('Failed to cancel broadcast:', e);
  }
}

// Open edit modal
function openEditModal(broadcast: ScheduledBroadcast) {
  editingBroadcast.value = broadcast;
  editForm.value.title = broadcast.title;
  editForm.value.message = broadcast.message;
  editForm.value.type = broadcast.event_type;
  editForm.value.priority = broadcast.priority;

  // Convert UTC to local datetime-local format
  const date = new Date(broadcast.scheduled_at);
  editForm.value.scheduledAt = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);

  editError.value = null;
}

// Close edit modal
function closeEditModal() {
  editingBroadcast.value = null;
  editError.value = null;
}

// Save edited broadcast
async function saveEdit() {
  if (!editingBroadcast.value) return;

  savingEdit.value = true;
  editError.value = null;

  try {
    const update: Partial<{
      title: string;
      message: string;
      scheduled_at: string;
      timezone: string;
    }> = {};

    if (editForm.value.title !== editingBroadcast.value.title) {
      update.title = editForm.value.title;
    }
    if (editForm.value.message !== editingBroadcast.value.message) {
      update.message = editForm.value.message;
    }

    // Check if scheduled time changed
    const newDate = new Date(editForm.value.scheduledAt);
    const originalDate = new Date(editingBroadcast.value.scheduled_at);
    if (newDate.getTime() !== originalDate.getTime()) {
      update.scheduled_at = newDate.toISOString();
      update.timezone = detectedTimezone.value;
    }

    await notificationsApi.updateScheduledBroadcast(editingBroadcast.value.id, update);

    await loadScheduledBroadcasts();
    closeEditModal();
  } catch (e: unknown) {
    const axiosError = e as { response?: { data?: { detail?: string } }; message?: string };
    editError.value =
      axiosError.response?.data?.detail || axiosError.message || 'Failed to update broadcast';
  } finally {
    savingEdit.value = false;
  }
}

// Format scheduled time for display
function formatScheduledTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString();
}

// Get notification type icon
function getTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    scheduled_maintenance: '🔧',
    system_status: '📊',
    security_alert: '🔒',
    isp_issue: '🌐',
    device_added: '➕',
    device_removed: '➖',
    device_offline: '🔴',
    device_online: '🟢',
    device_degraded: '🟡',
    anomaly_detected: '⚠️',
    high_latency: '🐢',
    packet_loss: '📉',
  };
  return icons[type] || '📢';
}

// Get priority CSS class
function getPriorityClass(priority: string): string {
  const classes: Record<string, string> = {
    low: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
    medium: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
    high: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400',
    critical: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
  };
  return classes[priority] || classes.medium;
}

// Load scheduled broadcasts on mount and start timers
onMounted(() => {
  loadScheduledBroadcasts();
  startCountdownTimer();
  startPolling();
});

// Clean up timers on unmount
onUnmounted(() => {
  stopTimers();
});
</script>
