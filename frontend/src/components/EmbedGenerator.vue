<template>
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" @click.self="$emit('close')">
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-indigo-500 to-purple-600">
				<div class="flex items-center gap-3">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
					</svg>
					<h2 class="text-lg font-semibold text-white">Generate Embed</h2>
				</div>
				<button 
					@click="$emit('close')" 
					class="p-1 rounded hover:bg-white/20 text-white/80 hover:text-white transition-colors"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Content -->
			<div class="p-6">
				<p class="text-sm text-slate-600 dark:text-slate-400 mb-6">
					Create a read-only embed of your network topology map. The embed supports panning and zooming but does not allow editing.
				</p>

				<!-- Sensitive Mode Toggle -->
				<div class="mb-6 p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-3">
							<div class="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30">
								<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
								</svg>
							</div>
							<div>
								<div class="font-medium text-slate-800 dark:text-slate-200">Sensitive Mode</div>
								<div class="text-xs text-slate-500 dark:text-slate-400">Hide IP addresses and sensitive details</div>
							</div>
						</div>
						<button 
							@click="sensitiveMode = !sensitiveMode"
							class="relative w-12 h-7 rounded-full transition-colors duration-200"
							:class="sensitiveMode ? 'bg-amber-500' : 'bg-slate-300 dark:bg-slate-600'"
						>
							<span 
								class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform duration-200"
								:class="sensitiveMode ? 'translate-x-5' : 'translate-x-0'"
							></span>
						</button>
					</div>
				</div>

				<!-- Preview Badge -->
				<div v-if="sensitiveMode" class="mb-6 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/50">
					<div class="flex items-start gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						<div class="text-sm text-amber-800 dark:text-amber-200">
							<strong>Sensitive Mode enabled:</strong> IP addresses will be masked as <code class="bg-amber-100 dark:bg-amber-900/50 px-1 rounded">•••.•••.•••.•••</code> and hostnames containing IP patterns will be hidden.
						</div>
					</div>
				</div>

				<!-- Generated URL -->
				<div class="mb-6">
					<label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Embed URL</label>
					<div class="flex gap-2">
						<input 
							type="text" 
							:value="embedUrl" 
							readonly
							class="flex-1 px-3 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-800 dark:text-slate-200 font-mono"
						/>
						<button 
							@click="copyUrl"
							class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-500 transition-colors flex items-center gap-2"
						>
							<svg v-if="!copied" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
							</svg>
							<svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-emerald-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
							</svg>
							{{ copied ? 'Copied!' : 'Copy' }}
						</button>
					</div>
				</div>

				<!-- iframe Code -->
				<div class="mb-6">
					<label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Embed Code (iframe)</label>
					<div class="relative">
						<textarea 
							:value="iframeCode" 
							readonly
							rows="3"
							class="w-full px-3 py-2 text-xs bg-slate-900 border border-slate-700 rounded-lg text-emerald-400 font-mono resize-none"
						></textarea>
						<button 
							@click="copyIframe"
							class="absolute top-2 right-2 px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded hover:bg-slate-600 transition-colors"
						>
							{{ copiedIframe ? '✓' : 'Copy' }}
						</button>
					</div>
				</div>

				<!-- Open in new tab button -->
				<div class="flex justify-end gap-3">
					<button 
						@click="$emit('close')" 
						class="px-4 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
					>
						Cancel
					</button>
					<a 
						:href="embedUrl"
						target="_blank"
						rel="noopener noreferrer"
						class="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-500 transition-colors flex items-center gap-2"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
						</svg>
						Open Preview
					</a>
				</div>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue';

const emit = defineEmits<{
	(e: 'close'): void;
}>();

const sensitiveMode = ref(false);
const copied = ref(false);
const copiedIframe = ref(false);

const embedUrl = computed(() => {
	const baseUrl = window.location.origin;
	const params = sensitiveMode.value ? '?sensitive=true' : '';
	return `${baseUrl}/embed${params}`;
});

const iframeCode = computed(() => {
	return `<iframe src="${embedUrl.value}" width="100%" height="600" frameborder="0" style="border-radius: 8px;"></iframe>`;
});

function copyUrl() {
	navigator.clipboard.writeText(embedUrl.value);
	copied.value = true;
	setTimeout(() => { copied.value = false; }, 2000);
}

function copyIframe() {
	navigator.clipboard.writeText(iframeCode.value);
	copiedIframe.value = true;
	setTimeout(() => { copiedIframe.value = false; }, 2000);
}
</script>
