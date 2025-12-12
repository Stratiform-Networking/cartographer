<template>
	<div class="min-h-screen bg-gradient-to-br from-slate-100 via-slate-50 to-white dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 flex items-center justify-center p-4 transition-colors">
		<div class="w-full max-w-md">
			<!-- Logo/Header -->
			<div class="text-center mb-8">
				<div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl shadow-lg shadow-cyan-500/30 mb-4">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
					</svg>
				</div>
				<h1 class="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Cartographer</h1>
				<p class="text-slate-500 dark:text-slate-400 mt-2">Network Mapping & Monitoring</p>
			</div>

			<!-- Login Card -->
			<div class="bg-white dark:bg-slate-800/50 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-2xl shadow-xl dark:shadow-2xl p-8">
				<div class="text-center mb-6">
					<h2 class="text-xl font-semibold text-slate-900 dark:text-white">Welcome back</h2>
					<p class="text-slate-500 dark:text-slate-400 text-sm mt-2">
						Sign in to access your network map
					</p>
				</div>

				<form @submit.prevent="onSubmit" class="space-y-5">
					<!-- Username -->
					<div>
						<label for="username" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
							Username
						</label>
						<input
							id="username"
							v-model="form.username"
							type="text"
							required
							autocomplete="username"
							class="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition"
							placeholder="Enter your username"
							:disabled="isSubmitting"
							@keydown.enter="focusPassword"
						/>
					</div>

					<!-- Password -->
					<div>
						<label for="password" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
							Password
						</label>
						<div class="relative">
							<input
								ref="passwordInput"
								id="password"
								v-model="form.password"
								:type="showPassword ? 'text' : 'password'"
								required
								autocomplete="current-password"
								class="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-900/50 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition pr-12"
								placeholder="••••••••"
								:disabled="isSubmitting"
							/>
							<button
								type="button"
								@click="showPassword = !showPassword"
								class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
							>
								<svg v-if="showPassword" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
								</svg>
								<svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
								</svg>
							</button>
						</div>
					</div>

					<!-- Error Message -->
					<div v-if="errorMessage" class="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-500/50 rounded-lg">
						<p class="text-sm text-red-600 dark:text-red-400">{{ errorMessage }}</p>
					</div>

					<!-- Submit Button -->
					<button
						type="submit"
						:disabled="isSubmitting || !isValid"
						class="w-full py-3 px-4 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-lg shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
					>
						<span v-if="isSubmitting" class="flex items-center justify-center gap-2">
							<svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							Signing in...
						</span>
						<span v-else>Sign In</span>
					</button>
				</form>
			</div>

			<!-- Footer -->
			<p class="text-center text-slate-400 dark:text-slate-500 text-sm mt-6">
				Secure access to your network infrastructure
			</p>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { ref, computed } from "vue";
import { useAuth } from "../composables/useAuth";

const emit = defineEmits<{
	(e: "success"): void;
}>();

const { login } = useAuth();

const form = ref({
	username: "",
	password: "",
});

const passwordInput = ref<HTMLInputElement | null>(null);
const showPassword = ref(false);
const isSubmitting = ref(false);
const errorMessage = ref<string | null>(null);

const isValid = computed(() => {
	return form.value.username.length > 0 && form.value.password.length > 0;
});

function focusPassword() {
	passwordInput.value?.focus();
}

async function onSubmit() {
	if (!isValid.value) return;

	isSubmitting.value = true;
	errorMessage.value = null;

	try {
		await login({
			username: form.value.username,
			password: form.value.password,
		});

		emit("success");
	} catch (e: any) {
		errorMessage.value = e.message || "Invalid username or password";
	} finally {
		isSubmitting.value = false;
	}
}
</script>
