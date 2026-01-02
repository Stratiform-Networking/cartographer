<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
      <div
        class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col border border-slate-200/80 dark:border-slate-800/80"
      >
        <!-- Header -->
        <div
          class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl"
        >
          <div class="flex items-center gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 text-cyan-500 dark:text-cyan-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
              />
            </svg>
            <div>
              <h2 class="font-semibold text-slate-800 dark:text-slate-100">User Management</h2>
              <p class="text-xs text-slate-500 dark:text-slate-400">Manage users and invitations</p>
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
            @click="switchTab('users')"
            :class="[
              'px-6 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'users'
                ? 'border-cyan-500 text-cyan-600 dark:text-cyan-400 bg-white dark:bg-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300',
            ]"
          >
            Users
          </button>
          <button
            @click="switchTab('invites')"
            :class="[
              'px-6 py-3 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2',
              activeTab === 'invites'
                ? 'border-cyan-500 text-cyan-600 dark:text-cyan-400 bg-white dark:bg-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300',
            ]"
          >
            Invitations
            <span
              v-if="pendingInvites.length > 0"
              class="px-1.5 py-0.5 text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded-full tabular-nums"
            >
              {{ pendingInvites.length }}
            </span>
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto p-4">
          <!-- Users Tab -->
          <template v-if="activeTab === 'users'">
            <!-- Add User Button -->
            <div class="mb-4">
              <button
                @click="showAddUser = true"
                class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-400 hover:to-blue-500 shadow-sm shadow-cyan-500/20 transition-all"
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
                    d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                  />
                </svg>
                Add User
              </button>
            </div>

            <!-- Loading State -->
            <div v-if="isLoading" class="flex items-center justify-center py-12">
              <svg
                class="animate-spin h-8 w-8 text-cyan-500"
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

            <!-- Users List -->
            <div v-else class="space-y-2">
              <div
                v-for="u in users"
                :key="u.id"
                class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50"
              >
                <div class="flex items-center gap-4">
                  <!-- Avatar -->
                  <div
                    class="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
                    :class="
                      u.role === 'owner'
                        ? 'bg-gradient-to-br from-amber-500 to-orange-600'
                        : 'bg-gradient-to-br from-cyan-500 to-blue-600'
                    "
                  >
                    {{ u.first_name.charAt(0).toUpperCase() }}
                  </div>

                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-slate-900 dark:text-white">
                        {{ getFullName(u) }}
                      </span>
                      <span
                        :class="getRoleBadgeClass(u.role)"
                        class="text-xs px-2 py-0.5 rounded-full"
                      >
                        {{ getRoleLabel(u.role) }}
                      </span>
                    </div>
                    <div class="text-sm text-slate-500 dark:text-slate-400">
                      {{ u.email }}
                      <span v-if="u.last_login" class="ml-2">
                        • Last login: {{ formatDate(u.last_login) }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Actions -->
                <div v-if="u.role !== 'owner'" class="flex items-center gap-1">
                  <button
                    @click="editUser(u)"
                    class="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded hover:bg-slate-200 dark:hover:bg-slate-700/60 transition-colors"
                    title="Edit user"
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
                    @click="confirmDelete(u)"
                    class="p-1.5 text-red-400 hover:text-red-600 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                    title="Delete user"
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
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
                <div v-else class="text-xs text-slate-400 dark:text-slate-500 italic">
                  Cannot modify owner
                </div>
              </div>

              <div
                v-if="users.length === 0"
                class="text-center py-8 text-slate-500 dark:text-slate-400"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-10 w-10 mx-auto mb-2 opacity-50"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="1"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
                <p class="text-sm">No users found</p>
              </div>
            </div>
          </template>

          <!-- Invitations Tab -->
          <template v-else-if="activeTab === 'invites'">
            <!-- Invite Button -->
            <div class="mb-4">
              <button
                @click="openInviteForm"
                class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-400 hover:to-blue-500 shadow-sm shadow-cyan-500/20 transition-all"
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
                Send Invitation
              </button>
            </div>

            <!-- Loading State -->
            <div v-if="isLoadingInvites" class="flex items-center justify-center py-12">
              <svg
                class="animate-spin h-8 w-8 text-cyan-500"
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

            <template v-else>
              <!-- Pending Invitations -->
              <div v-if="pendingInvites.length > 0" class="mb-4">
                <h3
                  class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5"
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
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  Pending Invitations
                </h3>
                <div class="space-y-2">
                  <div
                    v-for="invite in pendingInvites"
                    :key="invite.id"
                    class="flex items-center justify-between p-3 bg-amber-50 dark:bg-amber-900/15 rounded-lg border border-amber-200/80 dark:border-amber-800/30"
                  >
                    <div class="flex items-center gap-3">
                      <div
                        class="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white"
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
                      </div>
                      <div>
                        <div class="flex items-center gap-2">
                          <span class="text-sm font-medium text-slate-800 dark:text-slate-200">{{
                            invite.email
                          }}</span>
                          <span
                            :class="getRoleBadgeClass(invite.role)"
                            class="text-xs px-2 py-0.5 rounded-full"
                          >
                            {{ getRoleLabel(invite.role) }}
                          </span>
                        </div>
                        <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                          Sent {{ formatRelativeDate(invite.created_at) }} • Expires in
                          {{ formatExpiresIn(invite.expires_at) }}
                        </div>
                      </div>
                    </div>
                    <div class="flex items-center gap-1">
                      <button
                        @click="onResendInvite(invite)"
                        class="p-1.5 text-slate-400 hover:text-cyan-600 dark:hover:text-cyan-400 rounded hover:bg-white dark:hover:bg-slate-800 transition-colors"
                        title="Resend invitation"
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
                      </button>
                      <button
                        @click="confirmRevokeInvite(invite)"
                        class="p-1.5 text-red-400 hover:text-red-600 rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        title="Revoke invitation"
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

              <!-- Past Invitations -->
              <div v-if="pastInvites.length > 0">
                <h3
                  class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5"
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
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  History
                </h3>
                <div class="space-y-2">
                  <div
                    v-for="invite in pastInvites"
                    :key="invite.id"
                    class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50 opacity-60"
                  >
                    <div class="flex items-center gap-3">
                      <div class="text-sm text-slate-600 dark:text-slate-400">
                        {{ invite.email }}
                      </div>
                      <span
                        :class="getInviteStatusClass(invite.status)"
                        class="text-xs px-2 py-0.5 rounded-full"
                      >
                        {{ getInviteStatusLabel(invite.status) }}
                      </span>
                    </div>
                    <div class="text-xs text-slate-400">
                      {{ formatRelativeDate(invite.created_at) }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- Empty State -->
              <div
                v-if="invites.length === 0"
                class="text-center py-8 text-slate-500 dark:text-slate-400"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-10 w-10 mx-auto mb-2 opacity-50"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="1"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                <p class="text-sm">No invitations sent yet</p>
                <p class="text-xs mt-1">Click "Send Invitation" to invite users via email</p>
              </div>
            </template>
          </template>
        </div>
      </div>
    </div>

    <!-- Add/Edit User Modal -->
    <div
      v-if="showAddUser || editingUser"
      class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60"
    >
      <div
        class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto border border-slate-200/80 dark:border-slate-800/80"
      >
        <!-- Modal Header -->
        <div
          class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl"
        >
          <div class="flex items-center gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 text-cyan-500 dark:text-cyan-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
              />
            </svg>
            <h3 class="font-semibold text-slate-800 dark:text-slate-100">
              {{ editingUser ? 'Edit User' : 'Add New User' }}
            </h3>
          </div>
          <button
            @click="closeUserForm"
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

        <form @submit.prevent="onSubmitUser" class="p-4 space-y-4">
          <!-- Send Invitation Toggle (only for new users) -->
          <div
            v-if="!editingUser"
            class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50"
          >
            <label class="flex items-center justify-between cursor-pointer">
              <div class="flex items-center gap-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4 text-cyan-500"
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
                <span class="text-sm font-medium text-slate-700 dark:text-slate-300"
                  >Send invitation email</span
                >
              </div>
              <button
                type="button"
                @click="userForm.sendInvite = !userForm.sendInvite"
                class="relative w-10 h-6 rounded-full transition-colors"
                :class="userForm.sendInvite ? 'bg-cyan-500' : 'bg-slate-300 dark:bg-slate-600'"
              >
                <span
                  class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
                  :class="userForm.sendInvite ? 'translate-x-4' : ''"
                ></span>
              </button>
            </label>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-2">
              {{
                userForm.sendInvite
                  ? 'User will receive an email to set up their account'
                  : 'You will set the password for this user'
              }}
            </p>
          </div>

          <!-- Email (always required) -->
          <div>
            <label
              class="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5"
            >
              Email
            </label>
            <input
              v-model="userForm.email"
              type="email"
              required
              class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
              placeholder="user@example.com"
            />
          </div>

          <!-- Role (always required) -->
          <div>
            <label
              class="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5"
            >
              Role
            </label>
            <select
              v-model="userForm.role"
              class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
            >
              <option value="member">Member - Can only view the network map</option>
              <option value="admin">Admin - Can view and modify the network map</option>
            </select>
          </div>

          <!-- Fields only shown when NOT sending invite (creating user directly) -->
          <template v-if="!userForm.sendInvite || editingUser">
            <div v-if="!editingUser">
              <label
                class="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5"
              >
                Username
              </label>
              <input
                v-model="userForm.username"
                type="text"
                required
                pattern="^[a-zA-Z][a-zA-Z0-9_-]*$"
                class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
                placeholder="username"
              />
            </div>

            <!-- First Name / Last Name -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label
                  class="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5"
                >
                  First Name
                </label>
                <input
                  v-model="userForm.firstName"
                  type="text"
                  required
                  class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
                  placeholder="John"
                />
              </div>
              <div>
                <label
                  class="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5"
                >
                  Last Name
                </label>
                <input
                  v-model="userForm.lastName"
                  type="text"
                  required
                  class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
                  placeholder="Doe"
                />
              </div>
            </div>

            <div v-if="!editingUser">
              <label
                class="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5"
              >
                Password
              </label>
              <input
                v-model="userForm.password"
                type="password"
                required
                minlength="8"
                class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
                placeholder="••••••••"
              />
              <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">Minimum 8 characters</p>
            </div>

            <div v-if="editingUser">
              <label
                class="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5"
              >
                New Password
                <span class="text-slate-400 normal-case">(leave blank to keep current)</span>
              </label>
              <input
                v-model="userForm.password"
                type="password"
                minlength="8"
                class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
                placeholder="••••••••"
              />
            </div>
          </template>

          <div
            v-if="formError"
            class="p-3 bg-red-50 dark:bg-red-900/15 border border-red-200 dark:border-red-800/50 rounded-lg"
          >
            <p class="text-sm text-red-600 dark:text-red-400">{{ formError }}</p>
          </div>

          <div class="flex gap-3 pt-2">
            <button
              type="button"
              @click="closeUserForm"
              class="flex-1 px-4 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isSubmitting"
              class="flex-1 px-4 py-2 text-sm font-medium bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-400 hover:to-blue-500 shadow-sm shadow-cyan-500/20 disabled:opacity-50 transition-all"
            >
              <template v-if="isSubmitting">Saving...</template>
              <template v-else-if="editingUser">Update User</template>
              <template v-else-if="userForm.sendInvite">Send Invitation</template>
              <template v-else>Create User</template>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="deletingUser"
      class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60"
    >
      <div
        class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-md border border-slate-200/80 dark:border-slate-800/80"
      >
        <!-- Modal Header -->
        <div
          class="flex items-center gap-2 px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5 text-red-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
          <h3 class="font-semibold text-slate-800 dark:text-slate-100">Delete User</h3>
        </div>

        <div class="p-4">
          <p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
            Are you sure you want to delete
            <strong class="text-slate-800 dark:text-slate-200">{{
              getFullName(deletingUser)
            }}</strong
            >? This action cannot be undone.
          </p>

          <div class="flex gap-3">
            <button
              @click="deletingUser = null"
              class="flex-1 px-4 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              @click="onDeleteUser"
              :disabled="isSubmitting"
              class="flex-1 px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-500 shadow-sm shadow-red-500/20 disabled:opacity-50 transition-all"
            >
              {{ isSubmitting ? 'Deleting...' : 'Delete User' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Invite User Modal -->
    <div
      v-if="showInviteForm"
      class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60"
    >
      <div
        class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-md border border-slate-200/80 dark:border-slate-800/80"
      >
        <!-- Modal Header -->
        <div
          class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl"
        >
          <div class="flex items-center gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 text-cyan-500 dark:text-cyan-400"
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
            <h3 class="font-semibold text-slate-800 dark:text-slate-100">Send Invitation</h3>
          </div>
          <button
            @click="closeInviteForm"
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

        <form @submit.prevent="onSubmitInvite" class="p-4 space-y-4">
          <div>
            <label
              class="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5"
            >
              Email Address
            </label>
            <input
              v-model="inviteForm.email"
              type="email"
              required
              class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
              placeholder="user@example.com"
            />
          </div>

          <div>
            <label
              class="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5"
            >
              Role
            </label>
            <select
              v-model="inviteForm.role"
              class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
            >
              <option value="member">Member - Standard user of Cartographer</option>
              <option value="admin">Admin - Can see statistics on networks in Cartographer</option>
            </select>
          </div>

          <div
            class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50"
          >
            <p class="text-xs text-slate-600 dark:text-slate-400">
              An email will be sent with a link to create their account. The invitation expires in
              72 hours.
            </p>
          </div>

          <div
            v-if="inviteFormError"
            class="p-3 bg-red-50 dark:bg-red-900/15 border border-red-200 dark:border-red-800/50 rounded-lg"
          >
            <p class="text-sm text-red-600 dark:text-red-400">{{ inviteFormError }}</p>
          </div>

          <div class="flex gap-3 pt-2">
            <button
              type="button"
              @click="closeInviteForm"
              class="flex-1 px-4 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isSubmittingInvite"
              class="flex-1 px-4 py-2 text-sm font-medium bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-400 hover:to-blue-500 shadow-sm shadow-cyan-500/20 disabled:opacity-50 transition-all"
            >
              {{ isSubmittingInvite ? 'Sending...' : 'Send Invitation' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Revoke Invitation Confirmation Modal -->
    <div
      v-if="revokingInvite"
      class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60"
    >
      <div
        class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-md border border-slate-200/80 dark:border-slate-800/80"
      >
        <!-- Modal Header -->
        <div
          class="flex items-center gap-2 px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5 text-red-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          <h3 class="font-semibold text-slate-800 dark:text-slate-100">Revoke Invitation</h3>
        </div>

        <div class="p-4">
          <p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
            Are you sure you want to revoke the invitation for
            <strong class="text-slate-800 dark:text-slate-200">{{ revokingInvite.email }}</strong
            >? They will no longer be able to use the invitation link.
          </p>

          <div class="flex gap-3">
            <button
              @click="revokingInvite = null"
              class="flex-1 px-4 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              @click="onRevokeInvite"
              :disabled="isSubmittingInvite"
              class="flex-1 px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-500 shadow-sm shadow-red-500/20 disabled:opacity-50 transition-all"
            >
              {{ isSubmittingInvite ? 'Revoking...' : 'Revoke Invitation' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script lang="ts" setup>
import { ref, onMounted, computed } from 'vue';
import { useAuth } from '../composables/useAuth';
import type { User, UserRole, Invite, InviteStatus } from '../types/auth';
import {
  getRoleLabel,
  getFullName,
  getInviteStatusLabel,
  getInviteStatusClass,
} from '../types/auth';

defineEmits<{
  (e: 'close'): void;
}>();

const {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  listInvites,
  createInvite,
  revokeInvite,
  resendInvite,
} = useAuth();

// Tab state
const activeTab = ref<'users' | 'invites'>('users');

// Users state
const users = ref<User[]>([]);
const isLoading = ref(true);
const isSubmitting = ref(false);
const formError = ref<string | null>(null);

const showAddUser = ref(false);
const editingUser = ref<User | null>(null);
const deletingUser = ref<User | null>(null);

const userForm = ref({
  username: '',
  firstName: '',
  lastName: '',
  email: '',
  role: 'member' as UserRole,
  password: '',
  sendInvite: true, // Default to sending invitation
});

// Invites state
const invites = ref<Invite[]>([]);
const isLoadingInvites = ref(false);
const showInviteForm = ref(false);
const inviteFormError = ref<string | null>(null);
const isSubmittingInvite = ref(false);
const revokingInvite = ref<Invite | null>(null);

const inviteForm = ref({
  email: '',
  role: 'member' as UserRole,
});

// Computed
const pendingInvites = computed(() => invites.value.filter((i) => i.status === 'pending'));
const pastInvites = computed(() => invites.value.filter((i) => i.status !== 'pending'));

async function loadUsers() {
  isLoading.value = true;
  try {
    users.value = await listUsers();
  } catch (e) {
    console.error('Failed to load users:', e);
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  loadUsers();
});

function getRoleBadgeClass(role: UserRole): string {
  switch (role) {
    case 'owner':
      return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400';
    case 'admin':
      return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400';
    case 'member':
      return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
    default:
      return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
  }
}

// formatDate - use formatDateTime from utils/formatters
import { formatDateTime } from '../utils/formatters';
const formatDate = (dateStr: string) => formatDateTime(dateStr);

function editUser(user: User) {
  editingUser.value = user;
  userForm.value = {
    username: user.username,
    firstName: user.first_name,
    lastName: user.last_name,
    email: user.email,
    role: user.role,
    password: '',
    sendInvite: false,
  };
  formError.value = null;
}

function confirmDelete(user: User) {
  deletingUser.value = user;
}

function closeUserForm() {
  showAddUser.value = false;
  editingUser.value = null;
  userForm.value = {
    username: '',
    firstName: '',
    lastName: '',
    email: '',
    role: 'member',
    password: '',
    sendInvite: true,
  };
  formError.value = null;
}

async function onSubmitUser() {
  formError.value = null;
  isSubmitting.value = true;

  try {
    if (editingUser.value) {
      // Update existing user
      await updateUser(editingUser.value.id, {
        first_name: userForm.value.firstName,
        last_name: userForm.value.lastName,
        email: userForm.value.email,
        role: userForm.value.role,
        password: userForm.value.password || undefined,
      });
      closeUserForm();
      await loadUsers();
    } else if (userForm.value.sendInvite) {
      // Send invitation instead of creating user directly
      await createInvite({
        email: userForm.value.email,
        role: userForm.value.role,
      });
      closeUserForm();
      // Refresh invites list and switch to invites tab
      await loadInvites();
      activeTab.value = 'invites';
    } else {
      // Create new user directly (with password)
      await createUser({
        username: userForm.value.username,
        first_name: userForm.value.firstName,
        last_name: userForm.value.lastName,
        email: userForm.value.email,
        password: userForm.value.password,
        role: userForm.value.role,
      });
      closeUserForm();
      await loadUsers();
    }
  } catch (e: any) {
    formError.value = e.message || 'Failed to save user';
  } finally {
    isSubmitting.value = false;
  }
}

async function onDeleteUser() {
  if (!deletingUser.value) return;

  isSubmitting.value = true;
  try {
    await deleteUser(deletingUser.value.id);
    deletingUser.value = null;
    await loadUsers();
  } catch (e: any) {
    alert(e.message || 'Failed to delete user');
  } finally {
    isSubmitting.value = false;
  }
}

// ==================== Invite Management ====================

async function loadInvites() {
  isLoadingInvites.value = true;
  try {
    invites.value = await listInvites();
  } catch (e) {
    console.error('Failed to load invites:', e);
  } finally {
    isLoadingInvites.value = false;
  }
}

function openInviteForm() {
  inviteForm.value = { email: '', role: 'member' };
  inviteFormError.value = null;
  showInviteForm.value = true;
}

function closeInviteForm() {
  showInviteForm.value = false;
  inviteForm.value = { email: '', role: 'member' };
  inviteFormError.value = null;
}

async function onSubmitInvite() {
  inviteFormError.value = null;
  isSubmittingInvite.value = true;

  try {
    await createInvite({
      email: inviteForm.value.email,
      role: inviteForm.value.role,
    });
    closeInviteForm();
    await loadInvites();
  } catch (e: any) {
    inviteFormError.value = e.message || 'Failed to send invitation';
  } finally {
    isSubmittingInvite.value = false;
  }
}

function confirmRevokeInvite(invite: Invite) {
  revokingInvite.value = invite;
}

async function onRevokeInvite() {
  if (!revokingInvite.value) return;

  isSubmittingInvite.value = true;
  try {
    await revokeInvite(revokingInvite.value.id);
    revokingInvite.value = null;
    await loadInvites();
  } catch (e: any) {
    alert(e.message || 'Failed to revoke invitation');
  } finally {
    isSubmittingInvite.value = false;
  }
}

async function onResendInvite(invite: Invite) {
  try {
    await resendInvite(invite.id);
    alert('Invitation email resent successfully');
  } catch (e: any) {
    alert(e.message || 'Failed to resend invitation');
  }
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatExpiresIn(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();

  if (diffMs <= 0) return 'expired';

  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffHours < 1) return '< 1 hour';
  if (diffHours < 24) return `${diffHours}h`;
  return `${diffDays}d`;
}

// Load invites when tab changes
function switchTab(tab: 'users' | 'invites') {
  activeTab.value = tab;
  if (tab === 'invites' && invites.value.length === 0) {
    loadInvites();
  }
}
</script>
