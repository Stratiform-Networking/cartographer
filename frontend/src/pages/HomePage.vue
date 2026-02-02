<template>
  <!-- Loading State (checking auth) -->
  <div
    v-if="authLoading"
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

      <!-- App Name -->
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white tracking-tight mb-2">
        Cartographer
      </h1>

      <!-- Loading Indicator -->
      <div class="flex items-center justify-center gap-2 mt-4">
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
      <p class="text-sm text-slate-500 dark:text-slate-400 mt-3">Loading your networks...</p>
    </div>
  </div>

  <!-- Setup Wizard (First Run) -->
  <SetupWizard v-else-if="needsSetup" @complete="onSetupComplete" />

  <!-- Login Screen -->
  <LoginScreen v-else-if="!isAuthenticated" :authConfig="authConfig" @success="onLoginSuccess" />

  <!-- Main Dashboard -->
  <div v-else class="min-h-screen bg-white dark:bg-slate-950">
    <!-- Background mesh gradient -->
    <div
      class="fixed inset-0 bg-mesh-gradient-light dark:bg-mesh-gradient opacity-50 dark:opacity-30 pointer-events-none"
    />

    <!-- Navigation Header -->
    <header
      class="fixed top-0 left-0 right-0 z-50 flex items-center h-14 px-4 border-b border-slate-200 dark:border-slate-800/80 bg-white/95 dark:bg-slate-950/95 backdrop-blur-lg"
    >
      <!-- Left: Branding -->
      <div class="flex items-center gap-3 mr-6">
        <router-link to="/" class="flex items-center gap-3">
          <div
            class="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-[#0fb685] to-[#0994ae] shadow-sm"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
              />
            </svg>
          </div>
          <div class="flex flex-col">
            <span class="text-sm font-semibold text-slate-900 dark:text-white tracking-tight"
              >Cartographer</span
            >
            <span class="text-[10px] text-slate-400 dark:text-slate-500 -mt-0.5">Networks</span>
          </div>
        </router-link>
      </div>

      <!-- Center: Spacer -->
      <div class="flex-1"></div>

      <!-- Right: Actions -->
      <div class="flex items-center gap-2">
        <!-- Dark Mode Toggle -->
        <button
          @click="toggleDarkMode"
          class="p-2 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
          :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
        >
          <!-- Sun icon (shown in dark mode - click to go light) -->
          <svg
            v-if="isDark"
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
              d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
            />
          </svg>
          <!-- Moon icon (shown in light mode - click to go dark) -->
          <svg
            v-else
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
              d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
            />
          </svg>
        </button>

        <!-- User Menu -->
        <UserMenu
          @logout="onLogout"
          @manageUsers="showUserManagement = true"
          @notifications="showNotificationSettings = true"
          @updates="showUpdateSettings = true"
        />
      </div>
    </header>

    <!-- Main Content -->
    <main class="relative z-10 pt-20 pb-12 px-6">
      <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <div class="mb-10">
          <h1 class="text-3xl font-display font-bold text-slate-900 dark:text-white mb-2">
            Welcome back, {{ user?.first_name }}!
          </h1>
          <p class="text-slate-600 dark:text-slate-400">
            Select a network to view and manage, or create a new one.
          </p>
        </div>

        <!-- Loading Networks -->
        <div v-if="networksLoading" class="flex flex-col items-center justify-center py-16">
          <div class="flex gap-1.5 mb-3">
            <span
              class="w-2.5 h-2.5 rounded-full bg-cyan-500 animate-bounce"
              style="animation-delay: 0ms"
            ></span>
            <span
              class="w-2.5 h-2.5 rounded-full bg-cyan-500 animate-bounce"
              style="animation-delay: 150ms"
            ></span>
            <span
              class="w-2.5 h-2.5 rounded-full bg-cyan-500 animate-bounce"
              style="animation-delay: 300ms"
            ></span>
          </div>
          <p class="text-sm text-slate-500 dark:text-slate-400">Loading networks...</p>
        </div>

        <!-- No Networks State -->
        <div v-else-if="networks.length === 0" class="text-center py-20">
          <div
            class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/50 flex items-center justify-center"
          >
            <svg
              class="w-10 h-10 text-slate-400 dark:text-slate-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.5"
                d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
              />
            </svg>
          </div>
          <h2 class="text-xl font-display font-bold text-slate-900 dark:text-white mb-3">
            No networks yet
          </h2>
          <p class="text-slate-600 dark:text-slate-400 mb-8 max-w-md mx-auto">
            Create your first network to start mapping and monitoring your devices.
          </p>
          <button
            @click="showCreateModal = true"
            :disabled="!canCreateNetwork"
            :class="[
              'px-6 py-3 font-semibold rounded-xl shadow-lg transition-all',
              canCreateNetwork
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98]'
                : 'bg-slate-300 dark:bg-slate-700 text-slate-500 dark:text-slate-400 cursor-not-allowed',
            ]"
            :title="canCreateNetwork ? '' : 'Network limit reached'"
          >
            Create Network
          </button>
          <p
            v-if="!canCreateNetwork && networkLimit"
            class="mt-3 text-sm text-amber-600 dark:text-amber-400"
          >
            {{
              networkLimit.message ||
              `You've reached your network limit (${networkLimit.limit}). Contact an administrator to increase your limit.`
            }}
          </p>
        </div>

        <!-- Networks Grid -->
        <div v-else>
          <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-4">
              <h2 class="text-xl font-display font-semibold text-slate-900 dark:text-white">
                Your Networks
              </h2>
              <!-- Network limit indicator -->
              <span
                v-if="networkLimit && !networkLimit.is_exempt"
                class="text-xs px-2 py-1 rounded-full"
                :class="
                  networkLimit.remaining <= 0
                    ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                "
                :title="`${networkLimit.used} of ${networkLimit.limit} networks used`"
              >
                {{ networkLimit.used }}/{{ networkLimit.limit }}
              </span>
            </div>
            <button
              @click="showCreateModal = true"
              :disabled="!canCreateNetwork"
              :class="[
                'px-4 py-2 text-sm font-medium rounded-lg shadow-lg transition-all',
                canCreateNetwork
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-cyan-500/20 hover:shadow-cyan-500/30 hover:scale-[1.02] active:scale-[0.98]'
                  : 'bg-slate-300 dark:bg-slate-700 text-slate-500 dark:text-slate-400 cursor-not-allowed',
              ]"
              :title="canCreateNetwork ? 'Create a new network' : 'Network limit reached'"
            >
              + New Network
            </button>
          </div>

          <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="network in networks"
              :key="network.id"
              class="glass-card p-6 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-all group"
            >
              <router-link :to="`/network/${network.id}`" class="block">
                <div class="flex items-start justify-between mb-4">
                  <div
                    class="w-12 h-12 rounded-xl bg-cyan-100 dark:bg-cyan-500/10 flex items-center justify-center"
                  >
                    <svg
                      class="w-6 h-6 text-cyan-600 dark:text-cyan-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="1.5"
                        d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
                      />
                    </svg>
                  </div>
                  <div class="flex flex-col items-end gap-2">
                    <span
                      v-if="network.is_owner"
                      class="px-2 py-0.5 text-xs rounded-full bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400"
                    >
                      Owner
                    </span>
                    <span
                      v-else-if="network.permission"
                      class="px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                    >
                      {{ network.permission }}
                    </span>
                    <!-- Edit & Delete Buttons -->
                    <div
                      v-if="canWriteNetwork(network)"
                      class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <button
                        @click.prevent.stop="openEditModal(network)"
                        class="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600/50 hover:text-slate-700 dark:hover:text-white transition-all"
                        title="Edit network"
                      >
                        <svg
                          class="w-3.5 h-3.5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          />
                        </svg>
                      </button>
                      <button
                        @click.prevent.stop="confirmDeleteNetwork(network)"
                        class="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400 hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-600 dark:hover:text-red-400 transition-all"
                        title="Delete network"
                      >
                        <svg
                          class="w-3.5 h-3.5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>

                <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-1">
                  {{ network.name }}
                </h3>
                <p class="text-sm text-slate-600 dark:text-slate-400 mb-4 line-clamp-2">
                  {{ network.description || 'No description' }}
                </p>

                <div
                  class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-500"
                >
                  <span>Updated {{ formatDate(network.updated_at) }}</span>
                  <svg
                    class="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-cyan-500 dark:group-hover:text-cyan-400 group-hover:translate-x-0.5 transition-all"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Create Network Modal -->
    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-6">
        <div class="absolute inset-0 bg-black/60 dark:bg-slate-950/90" @click="closeCreateModal" />

        <Transition
          enter-active-class="transition duration-200 delay-75"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition duration-150"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="showCreateModal"
            class="relative glass-card p-8 w-full max-w-md border-gradient"
          >
            <h2 class="text-xl font-display font-bold text-slate-900 dark:text-white mb-6">
              Create Network
            </h2>

            <form @submit.prevent="createNetwork" class="space-y-4">
              <div>
                <label
                  for="networkName"
                  class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Network Name
                </label>
                <input
                  id="networkName"
                  v-model="newNetwork.name"
                  type="text"
                  required
                  class="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition"
                  placeholder="Home Network"
                />
              </div>

              <div>
                <label
                  for="networkDescription"
                  class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Description (optional)
                </label>
                <textarea
                  id="networkDescription"
                  v-model="newNetwork.description"
                  rows="3"
                  class="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition resize-none"
                  placeholder="Describe this network..."
                ></textarea>
              </div>

              <Transition
                enter-active-class="transition duration-200"
                enter-from-class="opacity-0"
                enter-to-class="opacity-100"
              >
                <div
                  v-if="createError"
                  class="p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl"
                >
                  <p class="text-sm text-red-600 dark:text-red-400">{{ createError }}</p>
                </div>
              </Transition>

              <div class="flex gap-3 pt-4">
                <button
                  type="button"
                  @click="closeCreateModal"
                  class="flex-1 py-3 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  :disabled="isCreating || !newNetwork.name.trim()"
                  class="flex-1 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-xl shadow-lg shadow-cyan-500/25 transition-all hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  <span v-if="isCreating" class="flex items-center justify-center gap-2">
                    <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                      />
                      <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Creating...
                  </span>
                  <span v-else>Create Network</span>
                </button>
              </div>
            </form>
          </div>
        </Transition>
      </div>
    </Transition>

    <!-- Edit Network Modal -->
    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="showEditModal" class="fixed inset-0 z-50 flex items-center justify-center p-6">
        <div class="absolute inset-0 bg-black/60 dark:bg-slate-950/90" @click="closeEditModal" />

        <Transition
          enter-active-class="transition duration-200 delay-75"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition duration-150"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div v-if="showEditModal" class="relative glass-card p-8 w-full max-w-md border-gradient">
            <h2 class="text-xl font-display font-bold text-slate-900 dark:text-white mb-6">
              Edit Network
            </h2>

            <form @submit.prevent="saveEditNetwork" class="space-y-4">
              <div>
                <label
                  for="editNetworkName"
                  class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Network Name
                </label>
                <input
                  id="editNetworkName"
                  v-model="editNetwork.name"
                  type="text"
                  required
                  class="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition"
                  placeholder="Home Network"
                />
              </div>

              <div>
                <label
                  for="editNetworkDescription"
                  class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Description (optional)
                </label>
                <textarea
                  id="editNetworkDescription"
                  v-model="editNetwork.description"
                  rows="3"
                  class="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition resize-none"
                  placeholder="Describe this network..."
                ></textarea>
              </div>

              <Transition
                enter-active-class="transition duration-200"
                enter-from-class="opacity-0"
                enter-to-class="opacity-100"
              >
                <div
                  v-if="editError"
                  class="p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl"
                >
                  <p class="text-sm text-red-600 dark:text-red-400">{{ editError }}</p>
                </div>
              </Transition>

              <div class="flex gap-3 pt-4">
                <button
                  type="button"
                  @click="closeEditModal"
                  class="flex-1 py-3 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  :disabled="isEditing || !editNetwork.name.trim()"
                  class="flex-1 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-xl shadow-lg shadow-cyan-500/25 transition-all hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  <span v-if="isEditing" class="flex items-center justify-center gap-2">
                    <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                      />
                      <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Saving...
                  </span>
                  <span v-else>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </Transition>
      </div>
    </Transition>

    <!-- Delete Network Confirmation Modal -->
    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="showDeleteModal" class="fixed inset-0 z-50 flex items-center justify-center p-6">
        <div class="absolute inset-0 bg-black/60 dark:bg-slate-950/90" @click="closeDeleteModal" />

        <Transition
          enter-active-class="transition duration-200 delay-75"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition duration-150"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div v-if="showDeleteModal" class="relative glass-card p-8 w-full max-w-md">
            <div class="flex items-center gap-4 mb-6">
              <div
                class="w-12 h-12 rounded-xl bg-red-100 dark:bg-red-500/20 flex items-center justify-center"
              >
                <svg
                  class="w-6 h-6 text-red-600 dark:text-red-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <div>
                <h2 class="text-xl font-display font-bold text-slate-900 dark:text-white">
                  Delete Network
                </h2>
                <p class="text-sm text-slate-500 dark:text-slate-400">
                  This action cannot be undone
                </p>
              </div>
            </div>

            <p class="text-slate-600 dark:text-slate-300 mb-6">
              Are you sure you want to delete
              <span class="font-semibold text-slate-900 dark:text-white"
                >"{{ deletingNetwork?.name }}"</span
              >? All data associated with this network will be permanently removed.
            </p>

            <Transition
              enter-active-class="transition duration-200"
              enter-from-class="opacity-0"
              enter-to-class="opacity-100"
            >
              <div
                v-if="deleteError"
                class="mb-4 p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl"
              >
                <p class="text-sm text-red-600 dark:text-red-400">{{ deleteError }}</p>
              </div>
            </Transition>

            <div class="flex gap-3">
              <button
                type="button"
                @click="closeDeleteModal"
                class="flex-1 py-3 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                @click="executeDeleteNetwork"
                :disabled="isDeleting"
                class="flex-1 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl shadow-lg shadow-red-500/25 transition-all hover:shadow-red-500/40 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
              >
                <span v-if="isDeleting" class="flex items-center justify-center gap-2">
                  <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle
                      class="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      stroke-width="4"
                    />
                    <path
                      class="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Deleting...
                </span>
                <span v-else>Delete Network</span>
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>

    <!-- User Management Modal -->
    <UserManagement v-if="showUserManagement" @close="showUserManagement = false" />
    <NotificationSettingsPanel
      v-if="showNotificationSettings"
      :networkId="null"
      @close="showNotificationSettings = false"
    />
    <UpdateSettings :isOpen="showUpdateSettings" @close="showUpdateSettings = false" />
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue';
import { useAuth } from '../composables/useAuth';
import { useNetworks, type Network } from '../composables/useNetworks';
import { useDarkMode } from '../composables/useDarkMode';
import { formatRelativeTime } from '../utils/formatters';
import { getNetworkLimitStatus, type NetworkLimitStatus } from '../api/networks';
import SetupWizard from '../components/SetupWizard.vue';
import LoginScreen from '../components/LoginScreen.vue';
import UserMenu from '../components/UserMenu.vue';
import NotificationSettingsPanel from '../components/NotificationSettingsPanel.vue';
import UserManagement from '../components/UserManagement.vue';
import UpdateSettings from '../components/UpdateSettings.vue';

const { isAuthenticated, user, initAuthState, authConfig } = useAuth();
const {
  networks,
  loading: networksLoading,
  clearNetworks,
  fetchNetworks,
  createNetwork: createNetworkApi,
  updateNetwork: updateNetworkApi,
  deleteNetwork: deleteNetworkApi,
  canWriteNetwork,
} = useNetworks();
const { isDark, toggleDarkMode, syncFromServer } = useDarkMode();

// Auth state
const authLoading = ref(true);
const needsSetup = ref(false);
const showUserManagement = ref(false);
const showNotificationSettings = ref(false);
const showUpdateSettings = ref(false);

// Create Modal state
const showCreateModal = ref(false);
const isCreating = ref(false);
const createError = ref('');

const newNetwork = reactive({
  name: '',
  description: '',
});

// Edit Modal state
const showEditModal = ref(false);
const isEditing = ref(false);
const editError = ref('');
const editingNetworkId = ref<string | null>(null);

const editNetwork = reactive({
  name: '',
  description: '',
});

// Delete Modal state
const showDeleteModal = ref(false);
const isDeleting = ref(false);
const deleteError = ref('');
const deletingNetwork = ref<Network | null>(null);

// Network limit state
const networkLimit = ref<NetworkLimitStatus | null>(null);
const canCreateNetwork = computed(() => {
  if (!networkLimit.value) return true; // Allow if limit not loaded yet
  if (networkLimit.value.is_exempt) return true;
  return networkLimit.value.remaining > 0;
});

async function fetchNetworkLimit() {
  try {
    networkLimit.value = await getNetworkLimitStatus();
  } catch (e) {
    console.error('[HomePage] Failed to fetch network limit:', e);
    // Allow creation if limit check fails
    networkLimit.value = null;
  }
}

// Check auth status on mount using composable helper
async function initAuth() {
  authLoading.value = true;
  try {
    const result = await initAuthState();
    needsSetup.value = result.needsSetup;
  } finally {
    authLoading.value = false;
  }
}

function onSetupComplete() {
  needsSetup.value = false;
}

async function onLoginSuccess() {
  // Check for pending agent connection code (from cloud agent flow)
  // If user was trying to connect an agent, redirect back to cloud connect page
  const pendingAgentCode = sessionStorage.getItem('cartographer_pending_agent_code');
  if (pendingAgentCode) {
    console.log('[HomePage] Pending agent code found, redirecting to cloud connect page');
    // Redirect to cloud connect page with the code
    window.location.href = `/connect?code=${pendingAgentCode}`;
    return;
  }

  // Otherwise, the watcher on isAuthenticated will handle loading networks
}

function onLogout() {
  clearNetworks();
  window.location.reload();
}

// formatDate - use formatRelativeTime from utils/formatters
const formatDate = (dateStr: string) => formatRelativeTime(dateStr);

function closeCreateModal() {
  showCreateModal.value = false;
  createError.value = '';
  newNetwork.name = '';
  newNetwork.description = '';
}

async function createNetwork() {
  if (!newNetwork.name.trim()) return;

  isCreating.value = true;
  createError.value = '';

  try {
    await createNetworkApi({
      name: newNetwork.name.trim(),
      description: newNetwork.description.trim() || undefined,
    });

    closeCreateModal();
    // Refresh network limit after creation
    await fetchNetworkLimit();
  } catch (e: unknown) {
    const error = e as { response?: { data?: { detail?: string } } };
    createError.value =
      error.response?.data?.detail || (e instanceof Error ? e.message : 'Failed to create network');
  } finally {
    isCreating.value = false;
  }
}

function openEditModal(network: Network) {
  editingNetworkId.value = network.id;
  editNetwork.name = network.name;
  editNetwork.description = network.description || '';
  editError.value = '';
  showEditModal.value = true;
}

function closeEditModal() {
  showEditModal.value = false;
  editError.value = '';
  editingNetworkId.value = null;
  editNetwork.name = '';
  editNetwork.description = '';
}

async function saveEditNetwork() {
  if (!editNetwork.name.trim() || editingNetworkId.value === null) return;

  isEditing.value = true;
  editError.value = '';

  try {
    await updateNetworkApi(editingNetworkId.value, {
      name: editNetwork.name.trim(),
      description: editNetwork.description.trim() || undefined,
    });

    closeEditModal();
  } catch (e: unknown) {
    editError.value = e instanceof Error ? e.message : 'Failed to update network';
  } finally {
    isEditing.value = false;
  }
}

function confirmDeleteNetwork(network: Network) {
  deletingNetwork.value = network;
  deleteError.value = '';
  showDeleteModal.value = true;
}

function closeDeleteModal() {
  showDeleteModal.value = false;
  deleteError.value = '';
  deletingNetwork.value = null;
}

async function executeDeleteNetwork() {
  if (!deletingNetwork.value) return;

  isDeleting.value = true;
  deleteError.value = '';

  try {
    await deleteNetworkApi(deletingNetwork.value.id);
    closeDeleteModal();
    // Refresh network limit after deletion
    await fetchNetworkLimit();
  } catch (e: unknown) {
    deleteError.value = e instanceof Error ? e.message : 'Failed to delete network';
  } finally {
    isDeleting.value = false;
  }
}

// Watch for authentication state changes to reload networks
// This handles the case when user logs in/out without page reload
watch(isAuthenticated, async (newValue, oldValue) => {
  console.log('[HomePage] Auth state changed:', oldValue, '->', newValue);
  if (newValue && !oldValue) {
    // User just became authenticated
    // First check for pending agent connection code
    const pendingAgentCode = sessionStorage.getItem('cartographer_pending_agent_code');
    if (pendingAgentCode) {
      console.log(
        '[HomePage] Pending agent code found in watcher, redirecting to cloud connect page'
      );
      window.location.href = `/connect?code=${pendingAgentCode}`;
      return; // Stop processing, we're navigating away
    }

    // No pending agent code, proceed with normal flow - load networks
    console.log('[HomePage] User authenticated, loading networks...');
    clearNetworks();
    await nextTick();
    try {
      await Promise.all([fetchNetworks(), fetchNetworkLimit()]);
      console.log('[HomePage] Networks loaded:', networks.value.length);
    } catch (e) {
      console.error('[HomePage] Failed to load networks:', e);
    }
  } else if (!newValue && oldValue) {
    // User just logged out - clear networks
    console.log('[HomePage] User logged out, clearing networks');
    clearNetworks();
  }
});

onMounted(async () => {
  await initAuth();

  // Check for pending agent connection code FIRST
  // If user was trying to connect an agent and is now authenticated, redirect to connect page
  if (isAuthenticated.value) {
    const pendingAgentCode = sessionStorage.getItem('cartographer_pending_agent_code');
    if (pendingAgentCode) {
      console.log(
        '[HomePage] Pending agent code found on mount, redirecting to cloud connect page'
      );
      window.location.href = `/connect?code=${pendingAgentCode}`;
      return; // Stop processing, we're navigating away
    }
  }

  // If already authenticated on mount, load networks and sync preferences
  // (The watcher won't fire for the initial value)
  if (isAuthenticated.value) {
    console.log('[HomePage] Already authenticated on mount, loading networks...');
    clearNetworks();
    try {
      // Sync dark mode preference from server for cross-device consistency
      await syncFromServer();
      await Promise.all([fetchNetworks(), fetchNetworkLimit()]);
      console.log('[HomePage] Networks loaded:', networks.value.length);
    } catch (e) {
      console.error('[HomePage] Failed to load networks:', e);
    }
  }
});
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
