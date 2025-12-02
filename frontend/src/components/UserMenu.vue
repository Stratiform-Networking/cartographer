<template>
	<div class="relative" ref="menuContainer">
		<!-- User Button -->
		<button
			@click="isOpen = !isOpen"
			class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
		>
			<!-- Avatar -->
			<div class="w-7 h-7 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-xs font-semibold shadow-sm">
				{{ userInitial }}
			</div>
			<div class="flex flex-col items-start">
				<span class="text-sm font-medium text-slate-700 dark:text-slate-200 max-w-24 truncate leading-tight">
					{{ displayName }}
				</span>
				<!-- Role Badge -->
				<span :class="roleBadgeClass" class="text-[10px] leading-tight font-medium">
					{{ roleLabel }}
				</span>
			</div>
			<!-- Dropdown Arrow -->
			<svg 
				xmlns="http://www.w3.org/2000/svg" 
				class="h-4 w-4 text-slate-400 transition-transform ml-0.5" 
				:class="{ 'rotate-180': isOpen }"
				fill="none" 
				viewBox="0 0 24 24" 
				stroke="currentColor"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</button>

		<!-- Dropdown Menu -->
		<Transition
			enter-active-class="transition ease-out duration-100"
			enter-from-class="transform opacity-0 scale-95"
			enter-to-class="transform opacity-100 scale-100"
			leave-active-class="transition ease-in duration-75"
			leave-from-class="transform opacity-100 scale-100"
			leave-to-class="transform opacity-0 scale-95"
		>
			<div 
				v-if="isOpen"
				class="absolute right-0 mt-2 w-56 rounded-xl shadow-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 overflow-hidden z-50"
			>
				<!-- User Info Header -->
				<div class="px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
					<div class="flex items-center gap-3">
						<div class="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-base font-semibold shadow-sm">
							{{ userInitial }}
						</div>
						<div class="flex-1 min-w-0">
							<p class="text-sm font-semibold text-slate-900 dark:text-white truncate">
								{{ displayName }}
							</p>
							<p class="text-xs text-slate-500 dark:text-slate-400 truncate">
								{{ user?.email }}
							</p>
						</div>
					</div>
				</div>

				<!-- Menu Items -->
				<div class="py-1">
					<!-- Manage Users (Owner only) -->
					<button
						v-if="isOwner"
						@click="onManageUsers"
						class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
					>
						<div class="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
							</svg>
						</div>
						<div class="flex flex-col items-start">
							<span class="font-medium">Manage Users</span>
							<span class="text-xs text-slate-500 dark:text-slate-400">Add, edit, remove users</span>
						</div>
					</button>

					<!-- Change Password -->
					<button
						@click="onChangePassword"
						class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
					>
						<div class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-slate-600 dark:text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
							</svg>
						</div>
						<div class="flex flex-col items-start">
							<span class="font-medium">Change Password</span>
							<span class="text-xs text-slate-500 dark:text-slate-400">Update your password</span>
						</div>
					</button>
				</div>

				<!-- Logout -->
				<div class="border-t border-slate-200 dark:border-slate-700 p-2">
					<button
						@click="onLogout"
						class="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
						</svg>
						Sign Out
					</button>
				</div>
			</div>
		</Transition>

		<!-- Change Password Modal -->
		<Teleport to="body">
			<Transition
				enter-active-class="transition ease-out duration-200"
				enter-from-class="opacity-0"
				enter-to-class="opacity-100"
				leave-active-class="transition ease-in duration-150"
				leave-from-class="opacity-100"
				leave-to-class="opacity-0"
			>
				<div v-if="showPasswordModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
					<Transition
						enter-active-class="transition ease-out duration-200"
						enter-from-class="opacity-0 scale-95"
						enter-to-class="opacity-100 scale-100"
						leave-active-class="transition ease-in duration-150"
						leave-from-class="opacity-100 scale-100"
						leave-to-class="opacity-0 scale-95"
					>
						<div v-if="showPasswordModal" class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
							<!-- Header -->
							<div class="px-6 py-4 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
								<h3 class="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
									<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
									</svg>
									Change Password
								</h3>
							</div>
							
							<form @submit.prevent="onSubmitPassword" class="p-6 space-y-4">
								<div>
									<label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
										Current Password
									</label>
									<input
										v-model="passwordForm.current"
										type="password"
										required
										class="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
										placeholder="Enter current password"
									/>
								</div>
								
								<div>
									<label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
										New Password
									</label>
									<input
										v-model="passwordForm.new"
										type="password"
										required
										minlength="8"
										class="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
										placeholder="Min. 8 characters"
									/>
								</div>
								
								<div>
									<label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
										Confirm New Password
									</label>
									<input
										v-model="passwordForm.confirm"
										type="password"
										required
										minlength="8"
										class="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
										placeholder="Re-enter new password"
									/>
								</div>

								<Transition
									enter-active-class="transition ease-out duration-200"
									enter-from-class="opacity-0 -translate-y-1"
									enter-to-class="opacity-100 translate-y-0"
									leave-active-class="transition ease-in duration-150"
									leave-from-class="opacity-100 translate-y-0"
									leave-to-class="opacity-0 -translate-y-1"
								>
									<div v-if="passwordError" class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-500/30 rounded-lg">
										<p class="text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
											{{ passwordError }}
										</p>
									</div>
								</Transition>

								<div class="flex gap-3 pt-2">
									<button
										type="button"
										@click="showPasswordModal = false"
										class="flex-1 px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-300 font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
									>
										Cancel
									</button>
									<button
										type="submit"
										:disabled="isSubmitting"
										class="flex-1 px-4 py-2.5 bg-cyan-600 text-white font-medium rounded-lg hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
									>
										<svg v-if="isSubmitting" class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
											<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"></circle>
											<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
										</svg>
										{{ isSubmitting ? 'Updating...' : 'Update Password' }}
									</button>
								</div>
							</form>
						</div>
					</Transition>
				</div>
			</Transition>
		</Teleport>
	</div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useAuth } from "../composables/useAuth";
import { getRoleLabel, getFullName } from "../types/auth";

const emit = defineEmits<{
	(e: "logout"): void;
	(e: "manageUsers"): void;
}>();

const { user, isOwner, logout, changePassword } = useAuth();

const menuContainer = ref<HTMLElement | null>(null);
const isOpen = ref(false);
const showPasswordModal = ref(false);
const isSubmitting = ref(false);
const passwordError = ref<string | null>(null);

const passwordForm = ref({
	current: "",
	new: "",
	confirm: "",
});

const displayName = computed(() => {
	if (user.value) {
		return getFullName(user.value);
	}
	return "User";
});

const userInitial = computed(() => {
	return user.value?.first_name?.charAt(0).toUpperCase() || "U";
});

const roleLabel = computed(() => {
	return user.value ? getRoleLabel(user.value.role) : "";
});

const roleBadgeClass = computed(() => {
	switch (user.value?.role) {
		case "owner":
			return "text-amber-600 dark:text-amber-400";
		case "readwrite":
			return "text-emerald-600 dark:text-emerald-400";
		case "readonly":
			return "text-slate-500 dark:text-slate-400";
		default:
			return "text-slate-500 dark:text-slate-400";
	}
});

function closeOnClickOutside(e: MouseEvent) {
	if (menuContainer.value && !menuContainer.value.contains(e.target as Node)) {
		isOpen.value = false;
	}
}

onMounted(() => {
	document.addEventListener("click", closeOnClickOutside);
});

onUnmounted(() => {
	document.removeEventListener("click", closeOnClickOutside);
});

function onManageUsers() {
	isOpen.value = false;
	emit("manageUsers");
}

function onChangePassword() {
	isOpen.value = false;
	passwordForm.value = { current: "", new: "", confirm: "" };
	passwordError.value = null;
	showPasswordModal.value = true;
}

async function onSubmitPassword() {
	passwordError.value = null;

	if (passwordForm.value.new !== passwordForm.value.confirm) {
		passwordError.value = "New passwords do not match";
		return;
	}

	if (passwordForm.value.new.length < 8) {
		passwordError.value = "Password must be at least 8 characters";
		return;
	}

	isSubmitting.value = true;

	try {
		await changePassword({
			current_password: passwordForm.value.current,
			new_password: passwordForm.value.new,
		});
		showPasswordModal.value = false;
	} catch (e: any) {
		passwordError.value = e.message || "Failed to change password";
	} finally {
		isSubmitting.value = false;
	}
}

async function onLogout() {
	isOpen.value = false;
	await logout();
	emit("logout");
}
</script>
