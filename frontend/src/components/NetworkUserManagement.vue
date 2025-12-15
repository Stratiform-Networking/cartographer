<template>
	<Teleport to="body">
		<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
			<div class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col border border-slate-200/80 dark:border-slate-800/80">
				<!-- Header -->
				<div class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl">
					<div class="flex items-center gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-cyan-500 dark:text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
						</svg>
						<div>
							<h2 class="font-semibold text-slate-800 dark:text-slate-100">Network Users</h2>
							<p class="text-xs text-slate-500 dark:text-slate-400">Manage who has access to this network</p>
						</div>
					</div>
					<button
						@click="$emit('close')"
						class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>

				<!-- Tabs -->
				<div class="flex border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50">
					<button
						@click="activeTab = 'members'"
						:class="[
							'px-6 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
							activeTab === 'members' 
								? 'border-cyan-500 text-cyan-600 dark:text-cyan-400 bg-white dark:bg-slate-900' 
								: 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
						]"
					>
						Network Members
						<span v-if="networkMembers.length > 0" class="ml-1.5 px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded-full tabular-nums">
							{{ networkMembers.length + 1 }}
						</span>
					</button>
					<button
						@click="activeTab = 'add'"
						:class="[
							'px-6 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
							activeTab === 'add' 
								? 'border-cyan-500 text-cyan-600 dark:text-cyan-400 bg-white dark:bg-slate-900' 
								: 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
						]"
					>
						Add Users
						<span v-if="availableUsers.length > 0" class="ml-1.5 px-1.5 py-0.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full tabular-nums">
							{{ availableUsers.length }}
						</span>
					</button>
				</div>

				<!-- Content -->
				<div class="flex-1 overflow-auto p-4">
					<!-- Loading State -->
					<div v-if="isLoading" class="flex items-center justify-center py-12">
						<svg class="animate-spin h-8 w-8 text-cyan-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
					</div>

					<template v-else>
						<!-- Network Members Tab -->
						<template v-if="activeTab === 'members'">
							<div class="space-y-2">
								<!-- Network Owner -->
								<div v-if="networkOwner" class="flex items-center justify-between p-3 bg-amber-50 dark:bg-amber-900/15 rounded-lg border border-amber-200/80 dark:border-amber-800/30">
									<div class="flex items-center gap-3">
										<div class="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-medium bg-gradient-to-br from-amber-500 to-orange-600">
											{{ networkOwner.first_name.charAt(0).toUpperCase() }}
										</div>
										<div>
											<div class="flex items-center gap-2">
												<span class="text-sm font-medium text-slate-800 dark:text-slate-200">
													{{ networkOwner.first_name }} {{ networkOwner.last_name }}
												</span>
												<span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
													Owner
												</span>
											</div>
											<div class="text-xs text-slate-500 dark:text-slate-400">
												{{ networkOwner.email }}
											</div>
										</div>
									</div>
									<div class="text-xs text-slate-400 dark:text-slate-500 italic">
										Network owner
									</div>
								</div>

								<!-- Other Members -->
								<div
									v-for="member in networkMembers"
									:key="member.permission.id"
									class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50"
								>
									<div class="flex items-center gap-3">
										<div class="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-medium bg-gradient-to-br from-cyan-500 to-blue-600">
											{{ member.user.first_name.charAt(0).toUpperCase() }}
										</div>
										<div>
											<div class="flex items-center gap-2">
												<span class="text-sm font-medium text-slate-800 dark:text-slate-200">
													{{ member.user.first_name }} {{ member.user.last_name }}
												</span>
												<span :class="getRoleBadgeClass(member.permission.role)" class="text-xs px-2 py-0.5 rounded-full">
													{{ getRoleLabel(member.permission.role) }}
												</span>
											</div>
											<div class="text-xs text-slate-500 dark:text-slate-400">
												{{ member.user.email }}
											</div>
										</div>
									</div>

									<!-- Actions -->
									<div class="flex items-center gap-1">
										<!-- Role dropdown -->
										<select
											:value="member.permission.role"
											@change="onChangeRole(member, ($event.target as HTMLSelectElement).value as 'viewer' | 'editor')"
											class="text-xs px-2 py-1.5 border border-slate-300 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
										>
											<option value="viewer">Viewer</option>
											<option value="editor">Editor</option>
										</select>
										<button
											@click="confirmRemove(member)"
											class="p-1.5 text-red-400 hover:text-red-600 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
											title="Remove from network"
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
											</svg>
										</button>
									</div>
								</div>

								<!-- Empty State -->
								<div v-if="networkMembers.length === 0 && networkOwner" class="text-center py-8 text-slate-500 dark:text-slate-400">
									<svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mx-auto mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
										<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
									</svg>
									<p class="text-sm">No other users have access to this network</p>
									<p class="text-xs mt-1">Switch to "Add Users" tab to share this network</p>
								</div>
							</div>
						</template>

						<!-- Add Users Tab -->
						<template v-else-if="activeTab === 'add'">
							<div class="space-y-2">
								<!-- Available Users -->
								<div
									v-for="user in availableUsers"
									:key="user.id"
									class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50"
								>
									<div class="flex items-center gap-3">
										<div class="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-medium bg-gradient-to-br from-slate-400 to-slate-600">
											{{ user.first_name.charAt(0).toUpperCase() }}
										</div>
										<div>
											<div class="flex items-center gap-2">
												<span class="text-sm font-medium text-slate-800 dark:text-slate-200">
													{{ user.first_name }} {{ user.last_name }}
												</span>
												<span class="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
													{{ user.role }}
												</span>
											</div>
											<div class="text-xs text-slate-500 dark:text-slate-400">
												{{ user.email }}
											</div>
										</div>
									</div>

									<!-- Add dropdown -->
									<div class="relative" :ref="el => setDropdownRef(user.id, el)">
										<button
											@click="toggleDropdown(user.id, $event)"
											class="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-400 hover:to-blue-500 shadow-sm shadow-cyan-500/20 transition-all"
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
											</svg>
											Add
											<svg xmlns="http://www.w3.org/2000/svg" class="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
												<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
											</svg>
										</button>
									</div>
								</div>

								<!-- Empty State -->
								<div v-if="availableUsers.length === 0" class="text-center py-8 text-slate-500 dark:text-slate-400">
									<svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mx-auto mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
										<path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
									<p class="text-sm">All users already have access to this network</p>
								</div>
							</div>
						</template>
					</template>
				</div>
			</div>
		</div>

		<!-- Remove Confirmation Modal -->
		<div v-if="removingMember" class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60">
			<div class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-md border border-slate-200/80 dark:border-slate-800/80">
				<!-- Modal Header -->
				<div class="flex items-center gap-2 px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
					</svg>
					<h3 class="font-semibold text-slate-800 dark:text-slate-100">Remove User Access</h3>
				</div>
				
				<div class="p-4">
					<p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
						Are you sure you want to remove <strong class="text-slate-800 dark:text-slate-200">{{ removingMember.user.first_name }} {{ removingMember.user.last_name }}</strong> from this network?
						They will no longer be able to access it.
					</p>
					
					<div class="flex gap-3">
						<button
							@click="removingMember = null"
							class="flex-1 px-4 py-2 text-sm border border-slate-300 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
						>
							Cancel
						</button>
						<button
							@click="onRemoveMember"
							:disabled="isSubmitting"
							class="flex-1 px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-500 shadow-sm shadow-red-500/20 disabled:opacity-50 transition-all"
						>
							{{ isSubmitting ? 'Removing...' : 'Remove Access' }}
						</button>
					</div>
				</div>
			</div>
		</div>

		<!-- Teleported dropdown menu (rendered outside overflow container) -->
		<div
			v-if="openDropdown && dropdownPosition"
			class="fixed w-40 bg-white dark:bg-slate-900 rounded-lg shadow-lg border border-slate-200/80 dark:border-slate-800/80 py-1 z-[70]"
			:style="{ top: dropdownPosition.top + 'px', left: dropdownPosition.left + 'px' }"
		>
			<button
				@click="onAddUserFromDropdown('viewer')"
				class="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
			>
				<div class="font-medium text-slate-800 dark:text-slate-200">Viewer</div>
				<div class="text-xs text-slate-500 dark:text-slate-400">Can view the network</div>
			</button>
			<button
				@click="onAddUserFromDropdown('editor')"
				class="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
			>
				<div class="font-medium text-slate-800 dark:text-slate-200">Editor</div>
				<div class="text-xs text-slate-500 dark:text-slate-400">Can view and modify</div>
			</button>
		</div>
	</Teleport>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useNetworks, type NetworkPermission, type NetworkPermissionRole } from "../composables/useNetworks";
import { useAuth } from "../composables/useAuth";
import type { User } from "../types/auth";

const props = defineProps<{
	networkId: string;
	ownerId: string;
}>();

const emit = defineEmits<{
	(e: "close"): void;
}>();

const { listNetworkPermissions, addNetworkPermission, removeNetworkPermission } = useNetworks();
const { listUsers, user: currentUser } = useAuth();

// State
const activeTab = ref<"members" | "add">("members");
const isLoading = ref(true);
const isSubmitting = ref(false);
const permissions = ref<NetworkPermission[]>([]);
const allUsers = ref<User[]>([]);
const openDropdown = ref<string | null>(null);
const dropdownPosition = ref<{ top: number; left: number } | null>(null);
const selectedDropdownUser = ref<User | null>(null);
const removingMember = ref<{ user: User; permission: NetworkPermission } | null>(null);
const dropdownRefs = ref<Record<string, HTMLElement | null>>({});

// Network owner
const networkOwner = computed(() => {
	return allUsers.value.find(u => u.id === props.ownerId) || null;
});

// Network members (users with permissions, with user info)
const networkMembers = computed(() => {
	return permissions.value
		.map(p => {
			const user = allUsers.value.find(u => u.id === p.user_id);
			return user ? { user, permission: p } : null;
		})
		.filter((m): m is { user: User; permission: NetworkPermission } => m !== null);
});

// Available users to add (not owner, not already in network)
const availableUsers = computed(() => {
	const existingUserIds = new Set([
		props.ownerId,
		...permissions.value.map(p => p.user_id)
	]);
	return allUsers.value.filter(u => !existingUserIds.has(u.id));
});

// Store dropdown refs
function setDropdownRef(userId: string, el: unknown) {
	dropdownRefs.value[userId] = el as HTMLElement | null;
}

// Load data
async function loadData() {
	isLoading.value = true;
	try {
		const [perms, users] = await Promise.all([
			listNetworkPermissions(props.networkId),
			listUsers()
		]);
		permissions.value = perms;
		allUsers.value = users;
	} catch (e) {
		console.error("Failed to load network users:", e);
	} finally {
		isLoading.value = false;
	}
}

onMounted(() => {
	loadData();
	document.addEventListener("click", handleClickOutside);
});

onBeforeUnmount(() => {
	document.removeEventListener("click", handleClickOutside);
});

// Handle click outside dropdown
function handleClickOutside(e: MouseEvent) {
	if (openDropdown.value) {
		const dropdownEl = dropdownRefs.value[openDropdown.value];
		const target = e.target as HTMLElement;
		// Check if click is inside the button container or the teleported dropdown menu
		const isInsideButton = dropdownEl && dropdownEl.contains(target);
		const isInsideDropdown = target.closest('.fixed.w-40'); // The teleported dropdown
		
		if (!isInsideButton && !isInsideDropdown) {
			openDropdown.value = null;
			dropdownPosition.value = null;
			selectedDropdownUser.value = null;
		}
	}
}

function toggleDropdown(userId: string, event: MouseEvent) {
	if (openDropdown.value === userId) {
		openDropdown.value = null;
		dropdownPosition.value = null;
		selectedDropdownUser.value = null;
	} else {
		const button = event.currentTarget as HTMLElement;
		const rect = button.getBoundingClientRect();
		dropdownPosition.value = {
			top: rect.bottom + 4,
			left: rect.right - 160 // 160px = w-40 dropdown width
		};
		openDropdown.value = userId;
		selectedDropdownUser.value = availableUsers.value.find(u => u.id === userId) || null;
	}
}

// Add user to network
async function onAddUser(user: User, role: NetworkPermissionRole) {
	openDropdown.value = null;
	dropdownPosition.value = null;
	selectedDropdownUser.value = null;
	isSubmitting.value = true;
	
	try {
		const newPerm = await addNetworkPermission(props.networkId, {
			user_id: user.id,
			role
		});
		permissions.value.push(newPerm);
	} catch (e: any) {
		alert(e.message || "Failed to add user to network");
	} finally {
		isSubmitting.value = false;
	}
}

// Add user from teleported dropdown
async function onAddUserFromDropdown(role: NetworkPermissionRole) {
	if (!selectedDropdownUser.value) return;
	await onAddUser(selectedDropdownUser.value, role);
}

// Change user role
async function onChangeRole(member: { user: User; permission: NetworkPermission }, newRole: NetworkPermissionRole) {
	if (member.permission.role === newRole) return;
	
	isSubmitting.value = true;
	try {
		// Remove and re-add with new role (API doesn't have update endpoint)
		await removeNetworkPermission(props.networkId, member.user.id);
		const newPerm = await addNetworkPermission(props.networkId, {
			user_id: member.user.id,
			role: newRole
		});
		
		// Update local state
		const idx = permissions.value.findIndex(p => p.id === member.permission.id);
		if (idx !== -1) {
			permissions.value[idx] = newPerm;
		}
	} catch (e: any) {
		alert(e.message || "Failed to update user role");
		// Reload to restore correct state
		await loadData();
	} finally {
		isSubmitting.value = false;
	}
}

function confirmRemove(member: { user: User; permission: NetworkPermission }) {
	removingMember.value = member;
}

async function onRemoveMember() {
	if (!removingMember.value) return;
	
	isSubmitting.value = true;
	try {
		await removeNetworkPermission(props.networkId, removingMember.value.user.id);
		permissions.value = permissions.value.filter(p => p.id !== removingMember.value!.permission.id);
		removingMember.value = null;
	} catch (e: any) {
		alert(e.message || "Failed to remove user from network");
	} finally {
		isSubmitting.value = false;
	}
}

function getRoleBadgeClass(role: NetworkPermissionRole): string {
	switch (role) {
		case "editor":
			return "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400";
		case "viewer":
		default:
			return "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400";
	}
}

function getRoleLabel(role: NetworkPermissionRole): string {
	switch (role) {
		case "editor":
			return "Editor";
		case "viewer":
			return "Viewer";
		default:
			return role;
	}
}
</script>
