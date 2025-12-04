<template>
	<aside 
		class="w-96 border-l border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex flex-col overflow-hidden"
	>
		<!-- Header -->
		<div class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
			<div class="flex items-center gap-2 min-w-0">
				<span class="text-lg">{{ roleIcon(node?.role) }}</span>
				<div class="min-w-0">
					<h2 class="font-semibold text-slate-800 dark:text-slate-100 truncate">{{ node?.hostname || node?.name }}</h2>
					<p class="text-xs text-slate-500 dark:text-slate-400 font-mono">{{ node?.ip || node?.id }}</p>
				</div>
			</div>
			<button 
				@click="$emit('close')"
				class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 flex-shrink-0"
				title="Close panel"
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-auto">
			<!-- Health Status Banner -->
			<div 
				class="px-4 py-3 border-b border-slate-200 dark:border-slate-700"
				:class="monitoringEnabled ? statusBannerClass : 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400'"
			>
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<div 
							class="w-3 h-3 rounded-full" 
							:class="monitoringEnabled ? [statusDotClass, 'animate-pulse'] : 'bg-slate-400'"
						></div>
						<span class="font-medium text-sm">{{ monitoringEnabled ? statusLabel : 'Monitoring Disabled' }}</span>
					</div>
					<button 
						v-if="monitoringEnabled"
						@click="refreshHealth"
						:disabled="loading"
						class="p-1.5 rounded hover:bg-white/20 dark:hover:bg-black/20 transition-colors disabled:opacity-50"
						title="Refresh health data"
					>
						<svg 
							xmlns="http://www.w3.org/2000/svg" 
							class="h-4 w-4" 
							:class="{ 'animate-spin': loading }"
							fill="none" 
							viewBox="0 0 24 24" 
							stroke="currentColor" 
							stroke-width="2"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
						</svg>
					</button>
				</div>
				<p v-if="monitoringEnabled && metrics?.last_check" class="text-xs opacity-75 mt-1">
					Last checked: {{ formatTimestamp(metrics.last_check) }}
				</p>
				<p v-else-if="!monitoringEnabled" class="text-xs opacity-75 mt-1">
					Health checks are paused for this device
				</p>
			</div>

			<!-- Loading State (manual fetch in progress) -->
			<div v-if="monitoringEnabled && loading" class="p-8 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400">
				<svg class="animate-spin h-8 w-8 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<p class="text-sm">Checking device health...</p>
			</div>

			<!-- Waiting for cached data -->
			<div v-else-if="monitoringEnabled && !metrics && !error && node?.ip" class="p-8 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400">
				<svg class="animate-spin h-8 w-8 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<p class="text-sm">Waiting for health data...</p>
				<p class="text-xs mt-1">First check in progress</p>
			</div>

			<!-- Metrics Content (also shown when offline or monitoring disabled) -->
			<div v-if="monitoringEnabled && (metrics || isOffline)" class="p-4 space-y-4">
				<!-- Readonly notice -->
				<div v-if="!hasWritePermission" class="bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-lg p-2 text-xs text-slate-500 dark:text-slate-400 text-center">
					View only mode
				</div>

				<!-- Offline Notice -->
				<div v-if="isOffline" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
					<div class="flex items-start gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414" />
						</svg>
						<div>
							<p class="text-sm font-medium text-red-800 dark:text-red-200">Unable to reach device</p>
							<p class="text-xs text-red-600 dark:text-red-400 mt-1">{{ error }}</p>
						</div>
					</div>
				</div>

				<!-- Ping Metrics (only shown when monitoring is enabled) -->
				<section v-if="monitoringEnabled && metrics?.ping">
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
						</svg>
						Connectivity
					</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-2">
						<div class="grid grid-cols-2 gap-3">
							<MetricCard 
								label="Latency" 
								:value="formatLatency(metrics.ping.avg_latency_ms)"
								:sublabel="metrics.ping.min_latency_ms && metrics.ping.max_latency_ms 
									? `${metrics.ping.min_latency_ms.toFixed(1)} - ${metrics.ping.max_latency_ms.toFixed(1)} ms`
									: undefined"
								:status="getLatencyStatus(metrics.ping.avg_latency_ms)"
							/>
							<MetricCard 
								label="Packet Loss" 
								:value="`${metrics.ping.packet_loss_percent.toFixed(1)}%`"
								:status="getPacketLossStatus(metrics.ping.packet_loss_percent)"
							/>
						</div>
						<div v-if="metrics.ping.jitter_ms != null" class="pt-2 border-t border-slate-200 dark:border-slate-700">
							<div class="flex items-center justify-between">
								<span class="text-xs text-slate-500 dark:text-slate-400">Jitter</span>
								<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ metrics.ping.jitter_ms.toFixed(2) }} ms</span>
							</div>
						</div>
					</div>
				</section>

				<!-- 24h Statistics (only shown when monitoring is enabled) -->
				<section v-if="monitoringEnabled && (metrics?.uptime_percent_24h != null || metrics?.check_history?.length)">
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						24h Uptime
					</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-3">
						<!-- Uptime percentage and timeline -->
						<div class="space-y-2">
							<div class="flex items-center justify-between">
								<span class="text-xs text-slate-500 dark:text-slate-400">Uptime</span>
								<span class="text-sm font-medium" :class="getUptimeColor(metrics?.uptime_percent_24h || 0)">
									{{ metrics?.uptime_percent_24h?.toFixed(1) || '0' }}%
								</span>
							</div>
							<!-- Timeline bar showing check history -->
							<div 
								class="h-4 bg-slate-200 dark:bg-slate-700 rounded overflow-hidden flex"
								:title="'Check history over 24h'"
							>
								<template v-if="metrics?.check_history?.length">
									<div
										v-for="(entry, idx) in timelineSegments"
										:key="idx"
										class="h-full transition-all"
										:class="entry.success ? 'bg-emerald-500' : 'bg-red-500'"
										:style="{ width: entry.width + '%' }"
										:title="formatTimelineTooltip(entry)"
									></div>
								</template>
								<template v-else>
									<!-- Fallback to simple percentage bar if no history -->
									<div 
										class="h-full bg-emerald-500 transition-all duration-500"
										:style="{ width: `${metrics?.uptime_percent_24h || 0}%` }"
									></div>
								</template>
							</div>
							<!-- Timeline labels -->
							<div class="flex justify-between text-[10px] text-slate-400 dark:text-slate-500">
								<span>24h ago</span>
								<span>Now</span>
							</div>
						</div>
						<div v-if="metrics?.avg_latency_24h_ms != null" class="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
							<span class="text-xs text-slate-500 dark:text-slate-400">Avg Latency (24h)</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ metrics.avg_latency_24h_ms.toFixed(1) }} ms</span>
						</div>
						<div class="flex items-center justify-between text-xs">
							<span class="text-slate-500 dark:text-slate-400">Checks</span>
							<span class="space-x-2">
								<span class="text-emerald-600 dark:text-emerald-400">{{ metrics?.checks_passed_24h || 0 }} passed</span>
								<span class="text-slate-400">/</span>
								<span class="text-red-600 dark:text-red-400">{{ metrics?.checks_failed_24h || 0 }} failed</span>
							</span>
						</div>
					</div>
				</section>

				<!-- LAN Ports Section (for switches, routers, servers) -->
				<section v-if="showLanPortsSection">
					<div class="flex items-center justify-between mb-2">
						<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
							</svg>
							LAN Ports
						</h3>
						<button
							@click="lanPortsExpanded = !lanPortsExpanded"
							class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-4 w-4 transition-transform duration-200"
								:class="{ 'rotate-180': !lanPortsExpanded }"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
							</svg>
						</button>
					</div>

					<div v-show="lanPortsExpanded" class="space-y-3">
						<!-- Grid Configuration (if no ports configured) -->
						<div v-if="!lanPortsConfig || lanPortsConfig.ports.length === 0" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
							<div v-if="hasWritePermission && !showPortGridSetup" class="text-center">
								<svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto mb-2 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
									<path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
								</svg>
								<p class="text-xs text-slate-500 dark:text-slate-400 mb-3">
									Configure physical LAN ports for this device
								</p>
								<button
									@click="showPortGridSetup = true"
									class="px-3 py-1.5 text-xs rounded bg-cyan-500 hover:bg-cyan-600 text-white transition-colors"
								>
									Configure Ports
								</button>
							</div>

							<!-- Port Grid Setup Form -->
							<div v-else-if="hasWritePermission && showPortGridSetup" class="space-y-3">
								<p class="text-xs text-slate-600 dark:text-slate-400 font-medium">Port Grid Layout</p>
								<div class="grid grid-cols-2 gap-3">
									<div>
										<label class="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Columns (X)</label>
										<input 
											type="number" 
											v-model.number="portGridCols"
											min="1" 
											max="48"
											class="w-full px-2 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-cyan-500"
										/>
									</div>
									<div>
										<label class="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Rows (Y)</label>
										<input 
											type="number" 
											v-model.number="portGridRows"
											min="1" 
											max="8"
											class="w-full px-2 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-cyan-500"
										/>
									</div>
								</div>
								<div>
									<label class="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Default Port Type</label>
									<select 
										v-model="defaultPortType"
										class="w-full px-2 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-cyan-500"
									>
										<option value="rj45">RJ45 (Copper)</option>
										<option value="sfp">SFP (1G Fiber)</option>
										<option value="sfp+">SFP+ (10G Fiber)</option>
									</select>
								</div>
								<!-- Preview grid -->
								<div v-if="portGridCols > 0 && portGridRows > 0" class="mt-3">
									<p class="text-xs text-slate-500 dark:text-slate-400 mb-2">Preview ({{ portGridCols }} × {{ portGridRows }} = {{ portGridCols * portGridRows }} ports)</p>
									<div class="bg-slate-200 dark:bg-slate-700 rounded p-2 pb-3 overflow-x-auto">
										<div 
											class="grid gap-1.5 gap-y-2.5"
											:style="{ gridTemplateColumns: `repeat(${portGridCols}, minmax(20px, 1fr))` }"
										>
											<div 
												v-for="n in portGridCols * portGridRows"
												:key="n"
												class="h-5 text-[9px] flex items-center justify-center font-mono border relative"
												:class="defaultPortType === 'rj45' 
													? 'bg-amber-200 dark:bg-amber-800 text-amber-800 dark:text-amber-200 border-amber-400 dark:border-amber-600 rounded-sm' 
													: 'bg-cyan-200 dark:bg-cyan-800 text-cyan-800 dark:text-cyan-200 border-cyan-400 dark:border-cyan-600 rounded'"
											>
												<!-- RJ45 clip tab (sticks out at bottom) -->
												<div 
													v-if="defaultPortType === 'rj45'"
													class="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1 bg-amber-300 dark:bg-amber-700 border border-amber-400 dark:border-amber-600 rounded-b-sm"
												></div>
												<!-- SFP pull tab -->
												<div 
													v-if="defaultPortType !== 'rj45'"
													class="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-2 h-0.5 bg-current opacity-25 rounded-full"
												></div>
												<span class="relative z-10">{{ n }}</span>
											</div>
										</div>
									</div>
								</div>
								<div class="flex justify-end gap-2 pt-2">
									<button
										@click="showPortGridSetup = false"
										class="px-3 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
									>
										Cancel
									</button>
									<button
										@click="createPortGrid"
										:disabled="portGridCols < 1 || portGridRows < 1"
										class="px-3 py-1 text-xs rounded bg-cyan-500 hover:bg-cyan-600 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
									>
										Create Grid
									</button>
								</div>
							</div>

							<!-- No write permission -->
							<div v-else class="text-center text-xs text-slate-500 dark:text-slate-400 italic">
								No ports configured
							</div>
						</div>

						<!-- Port Grid Display -->
						<div v-else class="space-y-3">
							<!-- Grid Actions & Edit Mode Toggle -->
							<div v-if="hasWritePermission" class="flex items-center justify-between">
								<span class="text-xs text-slate-500 dark:text-slate-400">
									{{ lanPortsConfig.cols }} × {{ lanPortsConfig.rows }} grid ({{ lanPortsConfig.ports.length }} ports)
								</span>
								<div class="flex items-center gap-2">
									<!-- Edit Mode Toggle -->
									<button
										@click="portEditMode = !portEditMode"
										class="flex items-center gap-1.5 px-2 py-1 text-xs rounded transition-colors"
										:class="portEditMode 
											? 'bg-amber-500 text-white' 
											: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
										:title="portEditMode ? 'Exit edit mode' : 'Enter edit mode to configure ports'"
									>
										<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
											<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
										</svg>
										{{ portEditMode ? 'Done' : 'Edit Ports' }}
									</button>
									<button
										@click="showPortGridSetup = true; portGridCols = lanPortsConfig.cols; portGridRows = lanPortsConfig.rows"
										class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline"
									>
										Resize
									</button>
								</div>
							</div>

							<!-- Mode indicator -->
							<div 
								v-if="hasWritePermission"
								class="text-xs px-2 py-1 rounded text-center"
								:class="portEditMode 
									? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400' 
									: 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'"
							>
								{{ portEditMode ? '⚙️ Edit Mode: Click ports to configure type, speed, status & PoE' : '🔌 Click ports to set connections' }}
							</div>

							<!-- Visual Port Grid -->
							<div 
								class="rounded-lg p-3 pb-4 overflow-x-auto transition-colors"
								:class="portEditMode ? 'bg-amber-50 dark:bg-amber-900/10 ring-2 ring-amber-400/50' : 'bg-slate-100 dark:bg-slate-900'"
							>
								<div 
									class="grid gap-2 gap-y-3 min-w-fit"
									:style="{ gridTemplateColumns: `repeat(${lanPortsConfig.cols}, minmax(32px, 1fr))` }"
								>
									<div 
										v-for="port in sortedPorts"
										:key="`${port.row}-${port.col}`"
										@click="hasWritePermission && onPortClick(port)"
										class="relative group cursor-pointer"
									>
										<!-- Port Visual -->
										<div 
											class="h-8 flex items-center justify-center text-[10px] font-mono font-medium border-2 transition-all relative"
											:class="[getPortClasses(port), getPortShape(port)]"
											:title="getPortTooltip(port)"
										>
											<!-- RJ45 clip tab (sticks out at bottom) -->
											<div 
												v-if="port.type === 'rj45' && port.status !== 'blocked'"
												class="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2.5 h-1.5 border-2 rounded-b-sm"
												:class="port.status === 'active' 
													? 'bg-amber-300 dark:bg-amber-700 border-amber-400 dark:border-amber-600' 
													: 'bg-slate-400 dark:bg-slate-600 border-slate-500 dark:border-slate-500'"
											></div>
											<!-- SFP handle/pull tab indicator -->
											<div 
												v-if="(port.type === 'sfp' || port.type === 'sfp+') && port.status !== 'blocked'"
												class="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-3 h-0.5 bg-current opacity-25 rounded-full"
											></div>
											<!-- Port Number/Label -->
											<span v-if="port.status !== 'blocked'" class="relative z-10">
												{{ getPortLabel(port) }}
											</span>
											<span v-else class="text-slate-400 dark:text-slate-600 relative z-10">✕</span>
										</div>
										<!-- Speed indicator (small badge) -->
										<div 
											v-if="port.status === 'active' && getDisplaySpeed(port).speed"
											class="absolute -top-1 -right-1 px-1 py-0.5 text-[8px] font-bold rounded leading-none"
											:class="getDisplaySpeed(port).isInferred 
												? 'bg-purple-600 dark:bg-purple-400 text-white dark:text-slate-900' 
												: 'bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-800'"
											:title="getDisplaySpeed(port).isInferred ? 'Speed inferred from connected device' : 'Configured speed'"
										>
											{{ formatSpeedShort(getDisplaySpeed(port).speed) }}
										</div>
										<!-- PoE indicator (lightning bolt) -->
										<div 
											v-if="port.poe && port.poe !== 'off' && port.status !== 'blocked'"
											class="absolute -top-1 -left-1 text-[10px] leading-none"
											:title="getPoeLabel(port.poe)"
										>
											⚡
										</div>
										<!-- Connection indicator (dot if connected) -->
										<div 
											v-if="port.connectedDeviceId && port.status === 'active'"
											class="absolute -bottom-0.5 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-emerald-500 border border-white dark:border-slate-900"
											:title="port.connectedDeviceName || 'Connected'"
										></div>
									</div>
								</div>
							</div>

							<!-- Legend -->
							<div class="flex flex-wrap gap-3 text-[10px] text-slate-500 dark:text-slate-400">
								<div class="flex items-center gap-1">
									<div class="w-3 h-3 rounded-sm bg-amber-200 dark:bg-amber-800 border border-amber-400 dark:border-amber-600 relative mb-1">
										<div class="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1 bg-amber-300 dark:bg-amber-700 border border-amber-400 dark:border-amber-600 rounded-b-sm"></div>
									</div>
									<span>RJ45</span>
								</div>
								<div class="flex items-center gap-1">
									<div class="w-4 h-2.5 rounded bg-cyan-200 dark:bg-cyan-800 border border-cyan-400 dark:border-cyan-600 relative">
										<div class="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-2 h-0.5 bg-cyan-600 dark:bg-cyan-400 opacity-30 rounded-full"></div>
									</div>
									<span>SFP/SFP+</span>
								</div>
								<div class="flex items-center gap-1">
									<div class="w-3 h-3 rounded bg-slate-300 dark:bg-slate-700 border border-slate-400 dark:border-slate-600"></div>
									<span>Unused</span>
								</div>
								<div class="flex items-center gap-1">
									<div class="w-3 h-3 rounded bg-slate-200 dark:bg-slate-800 border border-dashed border-slate-400 dark:border-slate-600"></div>
									<span>Blocked</span>
								</div>
								<div class="flex items-center gap-1">
									<div class="w-2 h-2 rounded-full bg-emerald-500"></div>
									<span>Connected</span>
								</div>
								<div class="flex items-center gap-1">
									<span>⚡</span>
									<span>PoE</span>
								</div>
								<div class="flex items-center gap-1">
									<div class="px-1 py-0.5 rounded text-[8px] font-bold bg-purple-600 dark:bg-purple-400 text-white dark:text-slate-900">1G</div>
									<span>Inferred Speed</span>
								</div>
							</div>

							<!-- Active Connections List -->
							<div v-if="activeConnections.length > 0" class="space-y-1.5">
								<p class="text-xs text-slate-500 dark:text-slate-400 font-medium">Active Connections</p>
								<div 
									v-for="conn in activeConnections" 
									:key="`${conn.row}-${conn.col}`"
									class="flex items-center justify-between bg-slate-50 dark:bg-slate-800/50 rounded px-2 py-1.5 text-xs"
								>
									<div class="flex items-center gap-2">
										<span class="font-mono font-medium text-slate-700 dark:text-slate-300">
											Port {{ getPortLabel(conn) }}
										</span>
										<span class="text-slate-400">→</span>
										<span class="text-slate-600 dark:text-slate-400">
											{{ conn.connectedDeviceName || conn.connectionLabel || 'Unknown device' }}
										</span>
									</div>
									<div class="flex items-center gap-1.5">
										<span v-if="conn.poe && conn.poe !== 'off'" class="text-[10px]" :title="getPoeLabel(conn.poe)">⚡</span>
										<span 
											v-if="getDisplaySpeed(conn).speed"
											class="px-1.5 py-0.5 rounded text-[10px] font-medium flex items-center gap-0.5"
											:class="getDisplaySpeed(conn).isInferred 
												? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400' 
												: getSpeedBadgeClass(getDisplaySpeed(conn).speed)"
											:title="getDisplaySpeed(conn).isInferred ? 'Speed inferred from connected device' : 'Configured speed'"
										>
											{{ getDisplaySpeed(conn).speed }}
											<span v-if="getDisplaySpeed(conn).isInferred" class="opacity-60">↔</span>
										</span>
										<span 
											class="px-1.5 py-0.5 rounded text-[10px]"
											:class="conn.type === 'rj45' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400' : 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-400'"
										>
											{{ conn.type.toUpperCase() }}
										</span>
									</div>
								</div>
							</div>

							<!-- Clear All Button -->
							<button
								v-if="hasWritePermission"
								@click="confirmClearPorts"
								class="w-full px-3 py-1.5 text-xs rounded border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
							>
								Clear All Ports
							</button>
						</div>
					</div>
				</section>

				<!-- DNS Information -->
				<section v-if="metrics?.dns">
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
						</svg>
						DNS
					</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-2">
						<div v-if="metrics.dns.reverse_dns" class="flex items-start justify-between gap-2">
							<span class="text-xs text-slate-500 dark:text-slate-400 flex-shrink-0">Reverse DNS</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300 text-right break-all">{{ metrics.dns.reverse_dns }}</span>
						</div>
						<div v-if="metrics.dns.resolved_hostname" class="flex items-start justify-between gap-2">
							<span class="text-xs text-slate-500 dark:text-slate-400 flex-shrink-0">Hostname</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300 text-right break-all">{{ metrics.dns.resolved_hostname }}</span>
						</div>
						<div v-if="metrics.dns.resolution_time_ms" class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Resolution Time</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ metrics.dns.resolution_time_ms.toFixed(1) }} ms</span>
						</div>
						<div v-if="!metrics.dns.success && !metrics.dns.reverse_dns && !metrics.dns.resolved_hostname" class="text-xs text-slate-500 dark:text-slate-400 italic">
							No DNS records found
						</div>
					</div>
				</section>

				<!-- Open Ports -->
				<section v-if="metrics?.open_ports && metrics.open_ports.length > 0">
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
						</svg>
						Open Ports
					</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg overflow-hidden">
						<div 
							v-for="port in metrics.open_ports" 
							:key="port.port"
							class="flex items-center justify-between px-3 py-2 border-b border-slate-200 dark:border-slate-700 last:border-b-0"
						>
							<div class="flex items-center gap-2">
								<span class="w-2 h-2 rounded-full bg-emerald-400"></span>
								<span class="text-sm font-mono text-slate-700 dark:text-slate-300">{{ port.port }}</span>
								<span v-if="port.service" class="text-xs text-slate-500 dark:text-slate-400">{{ port.service }}</span>
							</div>
							<span v-if="port.response_time_ms" class="text-xs text-slate-500 dark:text-slate-400">
								{{ port.response_time_ms.toFixed(0) }}ms
							</span>
						</div>
					</div>
				</section>

				<!-- Device Info -->
				<section>
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
						</svg>
						Device Info
					</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-2">
						<div class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Role</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300 capitalize">{{ node?.role?.replace('/', ' / ') || 'Unknown' }}</span>
						</div>
						<div v-if="node?.connectionSpeed" class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Connection Speed</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ node.connectionSpeed }}</span>
						</div>
						<div v-if="metrics?.last_seen_online" class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Last Seen Online</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ formatTimestamp(metrics.last_seen_online) }}</span>
						</div>
						<div v-if="metrics?.consecutive_failures && metrics.consecutive_failures > 0" class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Consecutive Failures</span>
							<span class="text-sm font-medium text-red-600 dark:text-red-400">{{ metrics.consecutive_failures }}</span>
						</div>
						<!-- Monitoring Toggle -->
						<div v-if="node?.ip" class="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
							<span class="text-xs text-slate-500 dark:text-slate-400">Health Monitoring</span>
							<button 
								@click="toggleMonitoring"
								class="relative w-11 h-6 rounded-full transition-colors"
								:class="[
									monitoringEnabled ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600',
									!hasWritePermission ? 'opacity-50 cursor-not-allowed' : ''
								]"
								:disabled="!hasWritePermission"
								:title="!hasWritePermission ? 'Write permission required' : (monitoringEnabled ? 'Click to disable monitoring' : 'Click to enable monitoring')"
							>
								<span 
									class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200"
									:class="monitoringEnabled ? 'translate-x-5' : 'translate-x-0'"
								></span>
							</button>
						</div>
					</div>
				</section>

				<!-- Notes Section -->
				<section>
					<div class="flex items-center justify-between mb-2">
						<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
							</svg>
							Notes
						</h3>
						<button
							v-if="hasWritePermission && !editingNotes && notesText"
							@click="editingNotes = true"
							class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
							title="Edit notes"
						>
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
							</svg>
						</button>
					</div>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3">
						<!-- Editing mode (only for users with write permission) -->
						<div v-if="hasWritePermission && (editingNotes || !notesText)">
							<textarea
								v-model="notesText"
								@input="onNotesInput"
								@blur="onNotesBlur"
								@focus="editingNotes = true"
								class="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
								:class="{ 'min-h-[80px]': editingNotes, 'min-h-[40px]': !editingNotes }"
								placeholder="Add notes about this device..."
								rows="3"
							></textarea>
							<p class="text-xs text-slate-400 dark:text-slate-500 mt-1">
								Notes are saved automatically
							</p>
						</div>
						<!-- Display mode (with edit capability for write users) -->
						<div 
							v-else-if="notesText"
							@click="hasWritePermission && (editingNotes = true)"
							class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap -m-2 p-2 rounded transition-colors"
							:class="hasWritePermission ? 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800' : ''"
							:title="hasWritePermission ? 'Click to edit' : ''"
						>
							{{ notesText }}
						</div>
						<!-- No notes (readonly) -->
						<div v-else class="text-sm text-slate-400 dark:text-slate-500 italic">
							No notes
						</div>
					</div>
				</section>

				<!-- Port Configuration Modal (Edit Mode) -->
				<Teleport to="body">
					<div 
						v-if="editingPort && portEditMode" 
						class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
						@click.self="closePortEditor"
					>
						<div class="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-80 max-h-[80vh] overflow-auto">
							<div class="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between bg-amber-50 dark:bg-amber-900/20">
								<h4 class="font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2">
									<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
										<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
									</svg>
									Configure Port {{ getPortLabel(editingPort) }}
								</h4>
								<button @click="closePortEditor" class="p-1 rounded hover:bg-amber-100 dark:hover:bg-slate-700">
									<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</div>
							<div class="p-4 space-y-4">
								<!-- Port Status -->
								<div>
									<label class="text-xs text-slate-500 dark:text-slate-400 mb-1.5 block font-medium">Status</label>
									<div class="grid grid-cols-3 gap-1">
										<button
											@click="editingPort.status = 'active'"
											class="px-2 py-1.5 text-xs rounded transition-colors"
											:class="editingPort.status === 'active' ? 'bg-emerald-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
										>
											Active
										</button>
										<button
											@click="editingPort.status = 'unused'"
											class="px-2 py-1.5 text-xs rounded transition-colors"
											:class="editingPort.status === 'unused' ? 'bg-slate-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
										>
											Unused
										</button>
										<button
											@click="editingPort.status = 'blocked'"
											class="px-2 py-1.5 text-xs rounded transition-colors"
											:class="editingPort.status === 'blocked' ? 'bg-red-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
										>
											Blocked
										</button>
									</div>
								</div>

								<!-- Port Type -->
								<div v-if="editingPort.status !== 'blocked'">
									<label class="text-xs text-slate-500 dark:text-slate-400 mb-1.5 block font-medium">Port Type</label>
									<div class="grid grid-cols-3 gap-1">
										<button
											@click="editingPort.type = 'rj45'"
											class="px-2 py-1.5 text-xs rounded transition-colors"
											:class="editingPort.type === 'rj45' ? 'bg-amber-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
										>
											RJ45
										</button>
										<button
											@click="editingPort.type = 'sfp'"
											class="px-2 py-1.5 text-xs rounded transition-colors"
											:class="editingPort.type === 'sfp' ? 'bg-cyan-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
										>
											SFP
										</button>
										<button
											@click="editingPort.type = 'sfp+'"
											class="px-2 py-1.5 text-xs rounded transition-colors"
											:class="editingPort.type === 'sfp+' ? 'bg-cyan-600 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
										>
											SFP+
										</button>
									</div>
								</div>

								<!-- Port Speed -->
								<div v-if="editingPort.status !== 'blocked'">
									<label class="text-xs text-slate-500 dark:text-slate-400 mb-1.5 block font-medium">Speed</label>
									<select 
										v-model="editingPort.speed"
										class="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-cyan-500"
									>
										<option value="">Auto-negotiate</option>
										<option value="10M">10 Mbps</option>
										<option value="100M">100 Mbps</option>
										<option value="1G">1 Gbps</option>
										<option value="2.5G">2.5 Gbps</option>
										<option value="5G">5 Gbps</option>
										<option value="10G">10 Gbps</option>
										<option value="25G">25 Gbps</option>
										<option value="40G">40 Gbps</option>
										<option value="100G">100 Gbps</option>
									</select>
								</div>

								<!-- PoE Status -->
								<div v-if="editingPort.status !== 'blocked' && editingPort.type === 'rj45'">
									<label class="text-xs text-slate-500 dark:text-slate-400 mb-1.5 block font-medium">Power over Ethernet (PoE)</label>
									<div class="grid grid-cols-4 gap-1">
										<button
											@click="editingPort.poe = 'off'"
											class="px-2 py-1.5 text-xs rounded transition-colors"
											:class="(!editingPort.poe || editingPort.poe === 'off') ? 'bg-slate-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
										>
											Off
										</button>
										<button
											@click="editingPort.poe = 'poe'"
											class="px-2 py-1.5 text-xs rounded transition-colors"
											:class="editingPort.poe === 'poe' ? 'bg-yellow-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
											title="802.3af - 15W"
										>
											PoE
										</button>
										<button
											@click="editingPort.poe = 'poe+'"
											class="px-2 py-1.5 text-xs rounded transition-colors"
											:class="editingPort.poe === 'poe+' ? 'bg-orange-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
											title="802.3at - 30W"
										>
											PoE+
										</button>
										<button
											@click="editingPort.poe = 'poe++'"
											class="px-2 py-1.5 text-xs rounded transition-colors"
											:class="editingPort.poe === 'poe++' ? 'bg-red-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'"
											title="802.3bt - 60W+"
										>
											PoE++
										</button>
									</div>
									<p class="text-[10px] text-slate-400 mt-1">
										{{ getPoeDescription(editingPort.poe) }}
									</p>
								</div>
							</div>
							<div class="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-2">
								<button
									@click="closePortEditor"
									class="px-3 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
								>
									Cancel
								</button>
								<button
									@click="savePortChanges"
									class="px-3 py-1.5 text-sm rounded bg-amber-500 hover:bg-amber-600 text-white transition-colors"
								>
									Save
								</button>
							</div>
						</div>
					</div>
				</Teleport>

				<!-- Connection Editor Modal (Normal Mode) -->
				<Teleport to="body">
					<div 
						v-if="editingPort && !portEditMode" 
						class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
						@click.self="closePortEditor"
					>
						<div class="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-80 max-h-[80vh] overflow-auto">
							<div class="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
								<h4 class="font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2">
									<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-cyan-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
									</svg>
									Port {{ getPortLabel(editingPort) }} Connection
								</h4>
								<button @click="closePortEditor" class="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700">
									<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</div>

							<!-- Port Info Summary -->
							<div class="px-4 py-2 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
								<div class="flex items-center gap-3 text-xs">
									<span 
										class="px-1.5 py-0.5 rounded"
										:class="editingPort.type === 'rj45' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400' : 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-400'"
									>
										{{ editingPort.type.toUpperCase() }}
									</span>
									<span v-if="editingPort.speed" class="text-slate-600 dark:text-slate-400">
										{{ editingPort.speed }}
									</span>
									<span v-if="editingPort.poe && editingPort.poe !== 'off'" class="flex items-center gap-0.5 text-yellow-600 dark:text-yellow-400">
										⚡ {{ editingPort.poe.toUpperCase() }}
									</span>
									<span 
										class="ml-auto px-1.5 py-0.5 rounded text-[10px]"
										:class="{
											'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400': editingPort.status === 'active',
											'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400': editingPort.status === 'unused',
											'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400': editingPort.status === 'blocked'
										}"
									>
										{{ editingPort.status }}
									</span>
								</div>
							</div>

							<div class="p-4 space-y-4">
								<!-- Warning if port is blocked -->
								<div v-if="editingPort.status === 'blocked'" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-xs text-red-700 dark:text-red-300">
									This port is blocked. Switch to Edit Mode to change its status.
								</div>

								<!-- Connected Device -->
								<div v-if="editingPort.status !== 'blocked'">
									<label class="text-xs text-slate-500 dark:text-slate-400 mb-1.5 block font-medium">Connected Device</label>
									<select 
										v-model="editingPort.connectedDeviceId"
										@change="onConnectedDeviceChange"
										class="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-cyan-500"
									>
										<option value="">Not connected / Unknown</option>
										<option 
											v-for="device in availableDevices" 
											:key="device.id"
											:value="device.id"
										>
											{{ device.name }} {{ device.ip ? `(${device.ip})` : '' }}
										</option>
									</select>
								</div>

								<!-- Connection Label (custom) -->
								<div v-if="editingPort.status !== 'blocked'">
									<label class="text-xs text-slate-500 dark:text-slate-400 mb-1.5 block font-medium">
										Connection Label 
										<span class="font-normal text-slate-400">(optional)</span>
									</label>
									<input 
										type="text"
										v-model="editingPort.connectionLabel"
										placeholder="e.g., Uplink to Core Switch"
										class="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-300 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-cyan-500"
									/>
								</div>

								<!-- Negotiated Speed (actual link speed) -->
								<div v-if="editingPort.status === 'active'">
									<label class="text-xs text-slate-500 dark:text-slate-400 mb-1.5 block font-medium">
										Actual Link Speed
										<span class="font-normal text-slate-400">(negotiated)</span>
									</label>
									<!-- Show inferred speed hint if available -->
									<div 
										v-if="editingPort.connectedDeviceId && !editingPort.negotiatedSpeed && getInferredSpeedFromConnectedDevice(editingPort.connectedDeviceId)"
										class="mb-1.5 px-2 py-1 rounded bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 text-xs text-purple-700 dark:text-purple-300 flex items-center gap-1"
									>
										<span>↔</span>
										<span>Auto-inferred from connected device: <strong>{{ getInferredSpeedFromConnectedDevice(editingPort.connectedDeviceId) }}</strong></span>
									</div>
									<select 
										v-model="editingPort.negotiatedSpeed"
										class="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-cyan-500"
									>
										<option value="">{{ editingPort.connectedDeviceId && getInferredSpeedFromConnectedDevice(editingPort.connectedDeviceId) ? 'Auto-infer from connected device' : 'Same as configured' }}</option>
										<option value="10M">10 Mbps</option>
										<option value="100M">100 Mbps</option>
										<option value="1G">1 Gbps</option>
										<option value="2.5G">2.5 Gbps</option>
										<option value="5G">5 Gbps</option>
										<option value="10G">10 Gbps</option>
										<option value="25G">25 Gbps</option>
										<option value="40G">40 Gbps</option>
										<option value="100G">100 Gbps</option>
									</select>
								</div>
							</div>
							<div class="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex justify-between items-center">
								<button
									@click="portEditMode = true"
									class="text-xs text-amber-600 dark:text-amber-400 hover:underline flex items-center gap-1"
								>
									<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
									</svg>
									Edit port config
								</button>
								<div class="flex gap-2">
									<button
										@click="closePortEditor"
										class="px-3 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
									>
										Cancel
									</button>
									<button
										@click="savePortChanges"
										class="px-3 py-1.5 text-sm rounded bg-cyan-500 hover:bg-cyan-600 text-white transition-colors"
									>
										Save
									</button>
								</div>
							</div>
						</div>
					</div>
				</Teleport>

				<!-- Gateway Test IPs Section (only for gateway/router devices) -->
				<section v-if="isGateway && node?.ip">
					<div class="flex items-center justify-between mb-2">
						<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Internet Test IPs
						</h3>
						<button
							@click="testIPsExpanded = !testIPsExpanded"
							class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-4 w-4 transition-transform duration-200"
								:class="{ 'rotate-180': !testIPsExpanded }"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
							</svg>
						</button>
					</div>
					
					<div v-show="testIPsExpanded" class="space-y-3">
						<!-- Error message -->
						<div v-if="testIPsError" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-2 text-xs text-red-700 dark:text-red-300">
							{{ testIPsError }}
							<button @click="testIPsError = null" class="ml-2 underline">Dismiss</button>
						</div>

						<!-- Test IPs list -->
						<div v-if="testIPs.length > 0" class="space-y-2">
							<div 
								v-for="tip in testIPs" 
								:key="tip.ip"
								class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3"
							>
								<!-- Test IP header -->
								<div class="flex items-center justify-between mb-2">
									<div class="flex items-center gap-2">
										<div 
											class="w-2.5 h-2.5 rounded-full animate-pulse"
											:class="getTestIPStatusColor(getTestIPMetrics(tip.ip)?.status)"
										></div>
										<div>
											<span class="text-sm font-medium text-slate-700 dark:text-slate-300 font-mono">{{ tip.ip }}</span>
											<span v-if="tip.label" class="text-xs text-slate-500 dark:text-slate-400 ml-2">({{ tip.label }})</span>
										</div>
									</div>
									<button
										v-if="hasWritePermission"
										@click="removeTestIP(tip.ip)"
										class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-slate-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
										title="Remove this test IP"
									>
										<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
										</svg>
									</button>
								</div>

								<!-- Test IP metrics (if available) -->
								<template v-if="getTestIPMetrics(tip.ip)">
									<div class="space-y-2">
										<!-- Status -->
										<div class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">Status</span>
											<span 
												class="font-medium"
												:class="{
													'text-emerald-600 dark:text-emerald-400': getTestIPMetrics(tip.ip)?.status === 'healthy',
													'text-amber-600 dark:text-amber-400': getTestIPMetrics(tip.ip)?.status === 'degraded',
													'text-red-600 dark:text-red-400': getTestIPMetrics(tip.ip)?.status === 'unhealthy',
													'text-slate-500 dark:text-slate-400': !getTestIPMetrics(tip.ip)?.status || getTestIPMetrics(tip.ip)?.status === 'unknown'
												}"
											>
												{{ getTestIPStatusLabel(getTestIPMetrics(tip.ip)?.status) }}
											</span>
										</div>

										<!-- Latency -->
										<div v-if="getTestIPMetrics(tip.ip)?.ping?.avg_latency_ms != null" class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">Latency</span>
											<span class="font-medium text-slate-700 dark:text-slate-300">
												{{ getTestIPMetrics(tip.ip)?.ping?.avg_latency_ms?.toFixed(1) }} ms
											</span>
										</div>

										<!-- Packet Loss -->
										<div v-if="getTestIPMetrics(tip.ip)?.ping?.packet_loss_percent != null" class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">Packet Loss</span>
											<span 
												class="font-medium"
												:class="getTestIPMetrics(tip.ip)?.ping?.packet_loss_percent === 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'"
											>
												{{ getTestIPMetrics(tip.ip)?.ping?.packet_loss_percent?.toFixed(1) }}%
											</span>
										</div>

										<!-- Jitter -->
										<div v-if="getTestIPMetrics(tip.ip)?.ping?.jitter_ms != null" class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">Jitter</span>
											<span class="font-medium text-slate-700 dark:text-slate-300">
												{{ getTestIPMetrics(tip.ip)?.ping?.jitter_ms?.toFixed(2) }} ms
											</span>
										</div>

										<!-- 24h Uptime -->
										<div v-if="getTestIPMetrics(tip.ip)?.uptime_percent_24h != null" class="pt-2 border-t border-slate-200 dark:border-slate-700">
											<div class="flex items-center justify-between text-xs mb-1">
												<span class="text-slate-500 dark:text-slate-400">24h Uptime</span>
												<span 
													class="font-medium"
													:class="getUptimeColor(getTestIPMetrics(tip.ip)?.uptime_percent_24h || 0)"
												>
													{{ getTestIPMetrics(tip.ip)?.uptime_percent_24h?.toFixed(1) }}%
												</span>
											</div>
											<!-- Mini timeline -->
											<div 
												v-if="getTestIPMetrics(tip.ip)?.check_history?.length"
												class="h-2 bg-slate-200 dark:bg-slate-700 rounded overflow-hidden flex"
											>
												<div
													v-for="(entry, idx) in getTestIPMetrics(tip.ip)?.check_history?.slice(-50)"
													:key="idx"
													class="h-full"
													:class="entry.success ? 'bg-emerald-500' : 'bg-red-500'"
													:style="{ width: `${100 / Math.min(50, getTestIPMetrics(tip.ip)?.check_history?.length || 1)}%` }"
												></div>
											</div>
										</div>

										<!-- Checks count -->
										<div v-if="getTestIPMetrics(tip.ip)?.checks_passed_24h || getTestIPMetrics(tip.ip)?.checks_failed_24h" class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">24h Checks</span>
											<span class="space-x-1">
												<span class="text-emerald-600 dark:text-emerald-400">{{ getTestIPMetrics(tip.ip)?.checks_passed_24h || 0 }}✓</span>
												<span class="text-slate-400">/</span>
												<span class="text-red-600 dark:text-red-400">{{ getTestIPMetrics(tip.ip)?.checks_failed_24h || 0 }}✗</span>
											</span>
										</div>

										<!-- Last check time -->
										<div v-if="getTestIPMetrics(tip.ip)?.last_check" class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">Last Check</span>
											<span class="text-slate-500 dark:text-slate-400">
												{{ formatTimestamp(getTestIPMetrics(tip.ip)?.last_check || '') }}
											</span>
										</div>
									</div>
								</template>

								<!-- Loading state for this IP -->
								<div v-else-if="testIPsLoading" class="text-xs text-slate-500 dark:text-slate-400 italic">
									Checking...
								</div>

								<!-- No metrics yet -->
								<div v-else class="text-xs text-slate-500 dark:text-slate-400 italic">
									Awaiting first check...
								</div>
							</div>
						</div>

						<!-- Empty state -->
						<div v-else-if="!testIPsLoading" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 text-center">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto mb-2 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<p class="text-xs text-slate-500 dark:text-slate-400 mb-2">
								No test IPs configured
							</p>
							<p class="text-xs text-slate-400 dark:text-slate-500">
								Add external IPs to monitor internet connectivity
							</p>
						</div>

						<!-- Quick add presets (only for users with write permission) -->
						<div v-if="hasWritePermission && !showAddTestIP" class="flex flex-wrap gap-1.5">
							<button
								v-for="preset in presetTestIPs.filter(p => !testIPs.some(t => t.ip === p.ip))"
								:key="preset.ip"
								@click="addPresetTestIP(preset)"
								class="px-2 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:border-blue-400 dark:hover:border-blue-600 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
								:title="`Add ${preset.label}`"
							>
								+ {{ preset.label }}
							</button>
							<button
								@click="showAddTestIP = true"
								class="px-2 py-1 text-xs rounded border border-dashed border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:border-slate-400 dark:hover:border-slate-500 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
							>
								+ Custom IP
							</button>
						</div>

						<!-- Add custom test IP form (only for users with write permission) -->
						<div v-if="hasWritePermission && showAddTestIP" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-2">
							<div class="flex gap-2">
								<input
									v-model="newTestIP"
									type="text"
									placeholder="IP address (e.g., 8.8.8.8)"
									class="flex-1 px-2 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
									@keyup.enter="addTestIP"
								/>
							</div>
							<div class="flex gap-2">
								<input
									v-model="newTestIPLabel"
									type="text"
									placeholder="Label (optional, e.g., Google DNS)"
									class="flex-1 px-2 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
									@keyup.enter="addTestIP"
								/>
							</div>
							<div class="flex justify-end gap-2">
								<button
									@click="showAddTestIP = false; newTestIP = ''; newTestIPLabel = ''; testIPsError = null"
									class="px-3 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
								>
									Cancel
								</button>
								<button
									@click="addTestIP"
									:disabled="!newTestIP.trim()"
									class="px-3 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Add
								</button>
							</div>
						</div>

						<!-- Refresh button -->
						<button
							v-if="testIPs.length > 0"
							@click="checkTestIPsNow"
							:disabled="testIPsLoading"
							class="w-full px-3 py-2 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-3.5 w-3.5" 
								:class="{ 'animate-spin': testIPsLoading }"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
							</svg>
							{{ testIPsLoading ? 'Checking...' : 'Check Now' }}
						</button>
					</div>
				</section>

				<!-- ISP Speed Test Section (only for gateway devices) -->
				<section v-if="isGateway">
					<div class="flex items-center justify-between mb-2">
						<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
							ISP Speed Test
						</h3>
						<button
							@click="speedTestExpanded = !speedTestExpanded"
							class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-4 w-4 transition-transform duration-200"
								:class="{ 'rotate-180': !speedTestExpanded }"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
							</svg>
						</button>
					</div>

					<div v-show="speedTestExpanded" class="space-y-3">
						<!-- Error message -->
						<div v-if="speedTestError" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-2 text-xs text-red-700 dark:text-red-300">
							{{ speedTestError }}
							<button @click="speedTestError = null" class="ml-2 underline">Dismiss</button>
						</div>

						<!-- Speed test results -->
						<div v-if="speedTestResult && speedTestResult.success" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-3">
							<!-- Download/Upload speeds -->
							<div class="grid grid-cols-2 gap-3">
								<div class="text-center p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
									<div class="text-xs text-slate-500 dark:text-slate-400 mb-1">Download</div>
									<div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">
										{{ formatSpeed(speedTestResult.download_mbps) }}
									</div>
								</div>
								<div class="text-center p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
									<div class="text-xs text-slate-500 dark:text-slate-400 mb-1">Upload</div>
									<div class="text-lg font-bold text-blue-600 dark:text-blue-400">
										{{ formatSpeed(speedTestResult.upload_mbps) }}
									</div>
								</div>
							</div>

							<!-- Ping -->
							<div v-if="speedTestResult.ping_ms != null" class="flex items-center justify-between text-xs">
								<span class="text-slate-500 dark:text-slate-400">Ping</span>
								<span class="font-medium text-slate-700 dark:text-slate-300">{{ speedTestResult.ping_ms.toFixed(1) }} ms</span>
							</div>

							<!-- Server info -->
							<div v-if="speedTestResult.server_name || speedTestResult.server_location" class="pt-2 border-t border-slate-200 dark:border-slate-700 space-y-1">
								<div v-if="speedTestResult.server_sponsor" class="flex items-center justify-between text-xs">
									<span class="text-slate-500 dark:text-slate-400">Server</span>
									<span class="font-medium text-slate-700 dark:text-slate-300">{{ speedTestResult.server_sponsor }}</span>
								</div>
								<div v-if="speedTestResult.server_location" class="flex items-center justify-between text-xs">
									<span class="text-slate-500 dark:text-slate-400">Location</span>
									<span class="font-medium text-slate-700 dark:text-slate-300">{{ speedTestResult.server_location }}</span>
								</div>
							</div>

							<!-- ISP info -->
							<div v-if="speedTestResult.client_isp" class="flex items-center justify-between text-xs">
								<span class="text-slate-500 dark:text-slate-400">ISP</span>
								<span class="font-medium text-slate-700 dark:text-slate-300">{{ speedTestResult.client_isp }}</span>
							</div>

							<!-- Test info -->
							<div class="flex items-center justify-between text-xs pt-2 border-t border-slate-200 dark:border-slate-700">
								<span class="text-slate-500 dark:text-slate-400">Tested</span>
								<span class="text-slate-500 dark:text-slate-400">
									{{ formatTimestamp(speedTestResult.timestamp) }}
									<span v-if="speedTestResult.duration_seconds" class="ml-1">({{ speedTestResult.duration_seconds }}s)</span>
								</span>
							</div>
						</div>

						<!-- No results yet / empty state -->
						<div v-else-if="!speedTestRunning" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 text-center">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto mb-2 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
								<path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
							<p class="text-xs text-slate-500 dark:text-slate-400 mb-1">
								Test your internet connection speed
							</p>
							<p class="text-xs text-slate-400 dark:text-slate-500">
								Takes 30-60 seconds to complete
							</p>
						</div>

						<!-- Running state -->
						<div v-if="speedTestRunning" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
							<div class="flex flex-col items-center">
								<svg class="animate-spin h-8 w-8 text-blue-500 mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
								<p class="text-sm font-medium text-slate-700 dark:text-slate-300">Running speed test...</p>
								<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">This may take up to 60 seconds</p>
							</div>
						</div>

						<!-- Run test button -->
						<button
							@click="runSpeedTest"
							:disabled="speedTestRunning"
							class="w-full px-3 py-2 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:border-blue-400 dark:hover:border-blue-600 hover:text-blue-600 dark:hover:text-blue-400 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-3.5 w-3.5"
								:class="{ 'animate-spin': speedTestRunning }"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
							{{ speedTestRunning ? 'Testing...' : (speedTestResult ? 'Run Again' : 'Run Speed Test') }}
						</button>
					</div>
				</section>
			</div>

			<!-- Device Info Only (when monitoring disabled) -->
			<div v-else-if="!monitoringEnabled && node?.ip" class="p-4 space-y-4">
				<!-- Readonly notice -->
				<div v-if="!hasWritePermission" class="bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-lg p-2 text-xs text-slate-500 dark:text-slate-400 text-center">
					View only mode
				</div>

				<section>
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
						</svg>
						Device Info
					</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-2">
						<div class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Role</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300 capitalize">{{ node?.role?.replace('/', ' / ') || 'Unknown' }}</span>
						</div>
						<div v-if="node?.connectionSpeed" class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Connection Speed</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ node.connectionSpeed }}</span>
						</div>
						<!-- Monitoring Toggle -->
						<div class="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
							<span class="text-xs text-slate-500 dark:text-slate-400">Health Monitoring</span>
							<button 
								@click="toggleMonitoring"
								class="relative w-11 h-6 rounded-full transition-colors"
								:class="[
									monitoringEnabled ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600',
									!hasWritePermission ? 'opacity-50 cursor-not-allowed' : ''
								]"
								:disabled="!hasWritePermission"
								:title="!hasWritePermission ? 'Write permission required' : (monitoringEnabled ? 'Click to disable monitoring' : 'Click to enable monitoring')"
							>
								<span 
									class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200"
									:class="monitoringEnabled ? 'translate-x-5' : 'translate-x-0'"
								></span>
							</button>
						</div>
					</div>
				</section>

				<!-- Notes Section -->
				<section>
					<div class="flex items-center justify-between mb-2">
						<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
							</svg>
							Notes
						</h3>
						<button
							v-if="hasWritePermission && !editingNotes && notesText"
							@click="editingNotes = true"
							class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
							title="Edit notes"
						>
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
							</svg>
						</button>
					</div>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3">
						<!-- Editing mode (only for users with write permission) -->
						<div v-if="hasWritePermission && (editingNotes || !notesText)">
							<textarea
								v-model="notesText"
								@input="onNotesInput"
								@blur="onNotesBlur"
								@focus="editingNotes = true"
								class="w-full px-2 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
								:class="{ 'min-h-[80px]': editingNotes, 'min-h-[40px]': !editingNotes }"
								placeholder="Add notes about this device..."
								rows="3"
							></textarea>
							<p class="text-xs text-slate-400 dark:text-slate-500 mt-1">
								Notes are saved automatically
							</p>
						</div>
						<!-- Display mode (with edit capability for write users) -->
						<div 
							v-else-if="notesText"
							@click="hasWritePermission && (editingNotes = true)"
							class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap -m-2 p-2 rounded transition-colors"
							:class="hasWritePermission ? 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800' : ''"
							:title="hasWritePermission ? 'Click to edit' : ''"
						>
							{{ notesText }}
						</div>
						<!-- No notes (readonly) -->
						<div v-else class="text-sm text-slate-400 dark:text-slate-500 italic">
							No notes
						</div>
					</div>
				</section>

				<!-- LAN Ports Section (shown even when device monitoring disabled) -->
				<section v-if="showLanPortsSection">
					<div class="flex items-center justify-between mb-2">
						<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
							</svg>
							LAN Ports
						</h3>
						<button
							@click="lanPortsExpanded = !lanPortsExpanded"
							class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-4 w-4 transition-transform duration-200"
								:class="{ 'rotate-180': !lanPortsExpanded }"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
							</svg>
						</button>
					</div>
					<div v-show="lanPortsExpanded">
						<!-- Simple view showing configured ports or setup prompt -->
						<div v-if="!lanPortsConfig || lanPortsConfig.ports.length === 0" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 text-center">
							<p class="text-xs text-slate-500 dark:text-slate-400">
								{{ hasWritePermission ? 'Enable monitoring to configure LAN ports' : 'No ports configured' }}
							</p>
						</div>
						<div v-else class="bg-slate-100 dark:bg-slate-900 rounded-lg p-2 pb-3 overflow-x-auto">
							<div 
								class="grid gap-1.5 gap-y-2.5 min-w-fit"
								:style="{ gridTemplateColumns: `repeat(${lanPortsConfig.cols}, minmax(24px, 1fr))` }"
							>
								<div 
									v-for="port in sortedPorts"
									:key="`disabled-${port.row}-${port.col}`"
									class="h-6 text-[9px] flex items-center justify-center font-mono border relative"
									:class="[getPortClasses(port), getPortShape(port)]"
									:title="getPortTooltip(port)"
								>
									<!-- RJ45 clip tab (sticks out at bottom) -->
									<div 
										v-if="port.type === 'rj45' && port.status !== 'blocked'"
										class="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1 border rounded-b-sm"
										:class="port.status === 'active' 
											? 'bg-amber-300 dark:bg-amber-700 border-amber-400 dark:border-amber-600' 
											: 'bg-slate-400 dark:bg-slate-600 border-slate-500 dark:border-slate-500'"
									></div>
									<!-- SFP pull tab -->
									<div 
										v-if="(port.type === 'sfp' || port.type === 'sfp+') && port.status !== 'blocked'"
										class="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-2 h-0.5 bg-current opacity-25 rounded-full"
									></div>
									<span v-if="port.status !== 'blocked'" class="relative z-10">{{ getPortLabel(port) }}</span>
									<span v-else class="text-slate-400 dark:text-slate-600 relative z-10">✕</span>
								</div>
							</div>
						</div>
					</div>
				</section>

				<!-- Gateway Test IPs Section (shown even when device monitoring disabled) -->
				<section v-if="isGateway">
					<div class="flex items-center justify-between mb-2">
						<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Internet Test IPs
						</h3>
						<button
							@click="testIPsExpanded = !testIPsExpanded"
							class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-4 w-4 transition-transform duration-200"
								:class="{ 'rotate-180': !testIPsExpanded }"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
							</svg>
						</button>
					</div>
					
					<div v-show="testIPsExpanded" class="space-y-3">
						<!-- Error message -->
						<div v-if="testIPsError" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-2 text-xs text-red-700 dark:text-red-300">
							{{ testIPsError }}
							<button @click="testIPsError = null" class="ml-2 underline">Dismiss</button>
						</div>

						<!-- Test IPs list -->
						<div v-if="testIPs.length > 0" class="space-y-2">
							<div 
								v-for="tip in testIPs" 
								:key="tip.ip"
								class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3"
							>
								<!-- Test IP header -->
								<div class="flex items-center justify-between mb-2">
									<div class="flex items-center gap-2">
										<div 
											class="w-2.5 h-2.5 rounded-full animate-pulse"
											:class="getTestIPStatusColor(getTestIPMetrics(tip.ip)?.status)"
										></div>
										<div>
											<span class="text-sm font-medium text-slate-700 dark:text-slate-300 font-mono">{{ tip.ip }}</span>
											<span v-if="tip.label" class="text-xs text-slate-500 dark:text-slate-400 ml-2">({{ tip.label }})</span>
										</div>
									</div>
									<button
										v-if="hasWritePermission"
										@click="removeTestIP(tip.ip)"
										class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-slate-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
										title="Remove this test IP"
									>
										<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
										</svg>
									</button>
								</div>

								<!-- Test IP metrics (if available) -->
								<template v-if="getTestIPMetrics(tip.ip)">
									<div class="space-y-2">
										<!-- Status -->
										<div class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">Status</span>
											<span 
												class="font-medium"
												:class="{
													'text-emerald-600 dark:text-emerald-400': getTestIPMetrics(tip.ip)?.status === 'healthy',
													'text-amber-600 dark:text-amber-400': getTestIPMetrics(tip.ip)?.status === 'degraded',
													'text-red-600 dark:text-red-400': getTestIPMetrics(tip.ip)?.status === 'unhealthy',
													'text-slate-500 dark:text-slate-400': !getTestIPMetrics(tip.ip)?.status || getTestIPMetrics(tip.ip)?.status === 'unknown'
												}"
											>
												{{ getTestIPStatusLabel(getTestIPMetrics(tip.ip)?.status) }}
											</span>
										</div>

										<!-- Latency -->
										<div v-if="getTestIPMetrics(tip.ip)?.ping?.avg_latency_ms != null" class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">Latency</span>
											<span class="font-medium text-slate-700 dark:text-slate-300">
												{{ getTestIPMetrics(tip.ip)?.ping?.avg_latency_ms?.toFixed(1) }} ms
											</span>
										</div>

										<!-- Packet Loss -->
										<div v-if="getTestIPMetrics(tip.ip)?.ping?.packet_loss_percent != null" class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">Packet Loss</span>
											<span 
												class="font-medium"
												:class="getTestIPMetrics(tip.ip)?.ping?.packet_loss_percent === 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'"
											>
												{{ getTestIPMetrics(tip.ip)?.ping?.packet_loss_percent?.toFixed(1) }}%
											</span>
										</div>

										<!-- Jitter -->
										<div v-if="getTestIPMetrics(tip.ip)?.ping?.jitter_ms != null" class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">Jitter</span>
											<span class="font-medium text-slate-700 dark:text-slate-300">
												{{ getTestIPMetrics(tip.ip)?.ping?.jitter_ms?.toFixed(2) }} ms
											</span>
										</div>

										<!-- 24h Uptime -->
										<div v-if="getTestIPMetrics(tip.ip)?.uptime_percent_24h != null" class="pt-2 border-t border-slate-200 dark:border-slate-700">
											<div class="flex items-center justify-between text-xs mb-1">
												<span class="text-slate-500 dark:text-slate-400">24h Uptime</span>
												<span 
													class="font-medium"
													:class="getUptimeColor(getTestIPMetrics(tip.ip)?.uptime_percent_24h || 0)"
												>
													{{ getTestIPMetrics(tip.ip)?.uptime_percent_24h?.toFixed(1) }}%
												</span>
											</div>
											<!-- Mini timeline -->
											<div 
												v-if="getTestIPMetrics(tip.ip)?.check_history?.length"
												class="h-2 bg-slate-200 dark:bg-slate-700 rounded overflow-hidden flex"
											>
												<div
													v-for="(entry, idx) in getTestIPMetrics(tip.ip)?.check_history?.slice(-50)"
													:key="idx"
													class="h-full"
													:class="entry.success ? 'bg-emerald-500' : 'bg-red-500'"
													:style="{ width: `${100 / Math.min(50, getTestIPMetrics(tip.ip)?.check_history?.length || 1)}%` }"
												></div>
											</div>
										</div>

										<!-- Checks count -->
										<div v-if="getTestIPMetrics(tip.ip)?.checks_passed_24h || getTestIPMetrics(tip.ip)?.checks_failed_24h" class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">24h Checks</span>
											<span class="space-x-1">
												<span class="text-emerald-600 dark:text-emerald-400">{{ getTestIPMetrics(tip.ip)?.checks_passed_24h || 0 }}✓</span>
												<span class="text-slate-400">/</span>
												<span class="text-red-600 dark:text-red-400">{{ getTestIPMetrics(tip.ip)?.checks_failed_24h || 0 }}✗</span>
											</span>
										</div>

										<!-- Last check time -->
										<div v-if="getTestIPMetrics(tip.ip)?.last_check" class="flex items-center justify-between text-xs">
											<span class="text-slate-500 dark:text-slate-400">Last Check</span>
											<span class="text-slate-500 dark:text-slate-400">
												{{ formatTimestamp(getTestIPMetrics(tip.ip)?.last_check || '') }}
											</span>
										</div>
									</div>
								</template>

								<!-- Loading state for this IP -->
								<div v-else-if="testIPsLoading" class="text-xs text-slate-500 dark:text-slate-400 italic">
									Checking...
								</div>

								<!-- No metrics yet -->
								<div v-else class="text-xs text-slate-500 dark:text-slate-400 italic">
									Awaiting first check...
								</div>
							</div>
						</div>

						<!-- Empty state -->
						<div v-else-if="!testIPsLoading" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 text-center">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto mb-2 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<p class="text-xs text-slate-500 dark:text-slate-400 mb-2">
								No test IPs configured
							</p>
							<p class="text-xs text-slate-400 dark:text-slate-500">
								Add external IPs to monitor internet connectivity
							</p>
						</div>

						<!-- Quick add presets (only for users with write permission) -->
						<div v-if="hasWritePermission && !showAddTestIP" class="flex flex-wrap gap-1.5">
							<button
								v-for="preset in presetTestIPs.filter(p => !testIPs.some(t => t.ip === p.ip))"
								:key="preset.ip"
								@click="addPresetTestIP(preset)"
								class="px-2 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:border-blue-400 dark:hover:border-blue-600 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
								:title="`Add ${preset.label}`"
							>
								+ {{ preset.label }}
							</button>
							<button
								@click="showAddTestIP = true"
								class="px-2 py-1 text-xs rounded border border-dashed border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:border-slate-400 dark:hover:border-slate-500 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
							>
								+ Custom IP
							</button>
						</div>

						<!-- Add custom test IP form (only for users with write permission) -->
						<div v-if="hasWritePermission && showAddTestIP" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-2">
							<div class="flex gap-2">
								<input
									v-model="newTestIP"
									type="text"
									placeholder="IP address (e.g., 8.8.8.8)"
									class="flex-1 px-2 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
									@keyup.enter="addTestIP"
								/>
							</div>
							<div class="flex gap-2">
								<input
									v-model="newTestIPLabel"
									type="text"
									placeholder="Label (optional, e.g., Google DNS)"
									class="flex-1 px-2 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
									@keyup.enter="addTestIP"
								/>
							</div>
							<div class="flex justify-end gap-2">
								<button
									@click="showAddTestIP = false; newTestIP = ''; newTestIPLabel = ''; testIPsError = null"
									class="px-3 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
								>
									Cancel
								</button>
								<button
									@click="addTestIP"
									:disabled="!newTestIP.trim()"
									class="px-3 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Add
								</button>
							</div>
						</div>

						<!-- Refresh button -->
						<button
							v-if="testIPs.length > 0"
							@click="checkTestIPsNow"
							:disabled="testIPsLoading"
							class="w-full px-3 py-2 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-3.5 w-3.5" 
								:class="{ 'animate-spin': testIPsLoading }"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
							</svg>
							{{ testIPsLoading ? 'Checking...' : 'Check Now' }}
						</button>
					</div>
				</section>

				<!-- ISP Speed Test Section (shown even when device monitoring disabled) -->
				<section v-if="isGateway">
					<div class="flex items-center justify-between mb-2">
						<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
							ISP Speed Test
						</h3>
						<button
							@click="speedTestExpanded = !speedTestExpanded"
							class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-4 w-4 transition-transform duration-200"
								:class="{ 'rotate-180': !speedTestExpanded }"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
							</svg>
						</button>
					</div>

					<div v-show="speedTestExpanded" class="space-y-3">
						<!-- Error message -->
						<div v-if="speedTestError" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-2 text-xs text-red-700 dark:text-red-300">
							{{ speedTestError }}
							<button @click="speedTestError = null" class="ml-2 underline">Dismiss</button>
						</div>

						<!-- Speed test results -->
						<div v-if="speedTestResult && speedTestResult.success" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-3">
							<!-- Download/Upload speeds -->
							<div class="grid grid-cols-2 gap-3">
								<div class="text-center p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
									<div class="text-xs text-slate-500 dark:text-slate-400 mb-1">Download</div>
									<div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">
										{{ formatSpeed(speedTestResult.download_mbps) }}
									</div>
								</div>
								<div class="text-center p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
									<div class="text-xs text-slate-500 dark:text-slate-400 mb-1">Upload</div>
									<div class="text-lg font-bold text-blue-600 dark:text-blue-400">
										{{ formatSpeed(speedTestResult.upload_mbps) }}
									</div>
								</div>
							</div>

							<!-- Ping -->
							<div v-if="speedTestResult.ping_ms != null" class="flex items-center justify-between text-xs">
								<span class="text-slate-500 dark:text-slate-400">Ping</span>
								<span class="font-medium text-slate-700 dark:text-slate-300">{{ speedTestResult.ping_ms.toFixed(1) }} ms</span>
							</div>

							<!-- Server info -->
							<div v-if="speedTestResult.server_name || speedTestResult.server_location" class="pt-2 border-t border-slate-200 dark:border-slate-700 space-y-1">
								<div v-if="speedTestResult.server_sponsor" class="flex items-center justify-between text-xs">
									<span class="text-slate-500 dark:text-slate-400">Server</span>
									<span class="font-medium text-slate-700 dark:text-slate-300">{{ speedTestResult.server_sponsor }}</span>
								</div>
								<div v-if="speedTestResult.server_location" class="flex items-center justify-between text-xs">
									<span class="text-slate-500 dark:text-slate-400">Location</span>
									<span class="font-medium text-slate-700 dark:text-slate-300">{{ speedTestResult.server_location }}</span>
								</div>
							</div>

							<!-- ISP info -->
							<div v-if="speedTestResult.client_isp" class="flex items-center justify-between text-xs">
								<span class="text-slate-500 dark:text-slate-400">ISP</span>
								<span class="font-medium text-slate-700 dark:text-slate-300">{{ speedTestResult.client_isp }}</span>
							</div>

							<!-- Test info -->
							<div class="flex items-center justify-between text-xs pt-2 border-t border-slate-200 dark:border-slate-700">
								<span class="text-slate-500 dark:text-slate-400">Tested</span>
								<span class="text-slate-500 dark:text-slate-400">
									{{ formatTimestamp(speedTestResult.timestamp) }}
									<span v-if="speedTestResult.duration_seconds" class="ml-1">({{ speedTestResult.duration_seconds }}s)</span>
								</span>
							</div>
						</div>

						<!-- No results yet / empty state -->
						<div v-else-if="!speedTestRunning" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 text-center">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto mb-2 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
								<path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
							<p class="text-xs text-slate-500 dark:text-slate-400 mb-1">
								Test your internet connection speed
							</p>
							<p class="text-xs text-slate-400 dark:text-slate-500">
								Takes 30-60 seconds to complete
							</p>
						</div>

						<!-- Running state -->
						<div v-if="speedTestRunning" class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
							<div class="flex flex-col items-center">
								<svg class="animate-spin h-8 w-8 text-blue-500 mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
								<p class="text-sm font-medium text-slate-700 dark:text-slate-300">Running speed test...</p>
								<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">This may take up to 60 seconds</p>
							</div>
						</div>

						<!-- Run test button -->
						<button
							@click="runSpeedTest"
							:disabled="speedTestRunning"
							class="w-full px-3 py-2 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:border-blue-400 dark:hover:border-blue-600 hover:text-blue-600 dark:hover:text-blue-400 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
						>
							<svg 
								xmlns="http://www.w3.org/2000/svg" 
								class="h-3.5 w-3.5"
								:class="{ 'animate-spin': speedTestRunning }"
								fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
							{{ speedTestRunning ? 'Testing...' : (speedTestResult ? 'Run Again' : 'Run Speed Test') }}
						</button>
					</div>
				</section>
			</div>

			<!-- No IP Warning -->
			<div v-else-if="!node?.ip" class="p-8 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
					<path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
				</svg>
				<p class="text-sm text-center">No IP address assigned</p>
				<p class="text-xs mt-1 text-center">Add an IP address to enable health monitoring</p>
			</div>
		</div>

		<!-- Scan Ports Button (only when monitoring enabled) -->
		<div v-if="monitoringEnabled && node?.ip && metrics && !metrics.open_ports?.length" class="p-3 border-t border-slate-200 dark:border-slate-700">
			<button
				@click="scanPorts"
				:disabled="scanningPorts"
				class="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" :class="{ 'animate-spin': scanningPorts }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				{{ scanningPorts ? 'Scanning...' : 'Scan Ports' }}
			</button>
		</div>
	</aside>
</template>

<script lang="ts" setup>
import { ref, watch, computed, onMounted, onUnmounted } from 'vue';
import axios from 'axios';
import type { TreeNode, DeviceMetrics, HealthStatus, GatewayTestIP, GatewayTestIPMetrics, GatewayTestIPsResponse, SpeedTestResult, LanPortsConfig, LanPort, PortType, PortStatus, PortSpeed, PoeStatus } from '../types/network';
import MetricCard from './MetricCard.vue';
import { useHealthMonitoring } from '../composables/useHealthMonitoring';

const props = defineProps<{
	node?: TreeNode;
	canEdit?: boolean;
	allDevices?: TreeNode[]; // All devices in the network for connection selection
}>();

const emit = defineEmits<{
	(e: 'close'): void;
	(e: 'toggleMonitoring', nodeId: string, enabled: boolean): void;
	(e: 'updateNotes', nodeId: string, notes: string): void;
	(e: 'updateLanPorts', nodeId: string, lanPorts: LanPortsConfig): void;
}>();

// Check if user has write permission
const hasWritePermission = computed(() => props.canEdit !== false);

const { cachedMetrics } = useHealthMonitoring();

// Check if this node is a gateway device
const isGateway = computed(() => props.node?.role === 'gateway/router');

// Test IP state
const testIPs = ref<GatewayTestIP[]>([]);
const testIPMetrics = ref<GatewayTestIPMetrics[]>([]);
const testIPsLoading = ref(false);
const testIPsError = ref<string | null>(null);
const newTestIP = ref('');
const newTestIPLabel = ref('');
const showAddTestIP = ref(false);
const testIPsExpanded = ref(true);
let testIPPollingInterval: ReturnType<typeof setInterval> | null = null;

// Speed test state
const speedTestResult = ref<SpeedTestResult | null>(null);
const speedTestRunning = ref(false);
const speedTestError = ref<string | null>(null);
const speedTestExpanded = ref(true);

// Whether monitoring is enabled for this node (default: true)
const monitoringEnabled = computed(() => {
	return props.node?.monitoringEnabled !== false;
});

function toggleMonitoring() {
	if (!hasWritePermission.value) return;
	if (props.node) {
		const newState = !monitoringEnabled.value;
		emit('toggleMonitoring', props.node.id, newState);
	}
}

const localMetrics = ref<DeviceMetrics | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const scanningPorts = ref(false);

// Notes editing
const editingNotes = ref(false);
const notesText = ref('');
const notesSaveTimeout = ref<ReturnType<typeof setTimeout> | null>(null);

// Initialize notes from node
watch(() => props.node?.notes, (newNotes) => {
	notesText.value = newNotes || '';
}, { immediate: true });

// Also reset when node changes
watch(() => props.node?.id, () => {
	editingNotes.value = false;
	notesText.value = props.node?.notes || '';
});

function onNotesInput() {
	if (!hasWritePermission.value) return;
	// Debounce save - save after 500ms of no typing
	if (notesSaveTimeout.value) {
		clearTimeout(notesSaveTimeout.value);
	}
	notesSaveTimeout.value = setTimeout(() => {
		saveNotes();
	}, 500);
}

function saveNotes() {
	if (!hasWritePermission.value) return;
	if (props.node) {
		emit('updateNotes', props.node.id, notesText.value);
	}
}

function onNotesBlur() {
	// Save immediately on blur
	if (notesSaveTimeout.value) {
		clearTimeout(notesSaveTimeout.value);
		notesSaveTimeout.value = null;
	}
	if (hasWritePermission.value) {
		saveNotes();
	}
	editingNotes.value = false;
}

// Use cached metrics from composable, falling back to local metrics (from manual refresh/port scan)
// Returns null if monitoring is disabled for the device (except for gateway test IPs which are tracked separately)
const metrics = computed(() => {
	const ip = props.node?.ip;
	if (!ip) return null;
	
	// If monitoring is disabled for this device, don't show cached device metrics
	// Note: This doesn't affect gateway test IPs which are tracked independently
	if (!monitoringEnabled.value) return null;
	
	// Prefer local metrics if we have them (from manual refresh or port scan)
	if (localMetrics.value?.ip === ip) {
		return localMetrics.value;
	}
	
	// Otherwise use cached metrics from the health monitoring composable
	return cachedMetrics.value?.[ip] || null;
});

// True when we couldn't reach the node (connection error or unhealthy status with no data)
const isOffline = computed(() => {
	if (error.value && props.node?.ip) return true;
	if (metrics.value?.status === 'unhealthy' && !metrics.value.ping?.success) return true;
	return false;
});

const statusLabel = computed(() => {
	if (isOffline.value) return 'Offline (Unreachable)';
	if (!metrics.value) return 'Unknown';
	const status = metrics.value.status;
	switch (status) {
		case 'healthy': return 'Online';
		case 'degraded': return 'Degraded';
		case 'unhealthy': return 'Offline';
		default: return 'Unknown';
	}
});

const statusBannerClass = computed(() => {
	if (isOffline.value) return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200';
	if (!metrics.value) return 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400';
	const status = metrics.value.status;
	switch (status) {
		case 'healthy': return 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-200';
		case 'degraded': return 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200';
		case 'unhealthy': return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200';
		default: return 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400';
	}
});

const statusDotClass = computed(() => {
	if (isOffline.value) return 'bg-red-500';
	if (!metrics.value) return 'bg-slate-400';
	const status = metrics.value.status;
	switch (status) {
		case 'healthy': return 'bg-emerald-500';
		case 'degraded': return 'bg-amber-500';
		case 'unhealthy': return 'bg-red-500';
		default: return 'bg-slate-400';
	}
});

// Timeline segment for uptime visualization
interface TimelineSegment {
	success: boolean;
	width: number;
	timestamp: string;
	latency_ms?: number;
}

// Convert check history to timeline segments
const timelineSegments = computed((): TimelineSegment[] => {
	const history = metrics.value?.check_history;
	if (!history || history.length === 0) return [];
	
	// Sort by timestamp (oldest first)
	const sorted = [...history].sort((a, b) => 
		new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
	);
	
	// Each segment gets equal width
	const segmentWidth = 100 / sorted.length;
	
	return sorted.map(entry => ({
		success: entry.success,
		width: segmentWidth,
		timestamp: entry.timestamp,
		latency_ms: entry.latency_ms
	}));
});

function formatTimelineTooltip(entry: TimelineSegment): string {
	const date = new Date(entry.timestamp);
	const time = date.toLocaleTimeString(undefined, { 
		hour: '2-digit', 
		minute: '2-digit' 
	});
	const status = entry.success ? 'Online' : 'Offline';
	const latency = entry.latency_ms ? ` (${entry.latency_ms.toFixed(1)}ms)` : '';
	return `${time}: ${status}${latency}`;
}

function roleIcon(role?: string): string {
	const r = role || "unknown";
	switch (r) {
		case "gateway/router": return "📡";
		case "firewall": return "🧱";
		case "switch/ap": return "🔀";
		case "server": return "🖥️";
		case "service": return "⚙️";
		case "nas": return "🗄️";
		case "client": return "💻";
		default: return "❓";
	}
}

function formatTimestamp(isoString: string): string {
	const date = new Date(isoString);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffMins = Math.floor(diffMs / 60000);
	const diffHours = Math.floor(diffMs / 3600000);
	const diffDays = Math.floor(diffMs / 86400000);
	
	if (diffMins < 1) return 'Just now';
	if (diffMins < 60) return `${diffMins}m ago`;
	if (diffHours < 24) return `${diffHours}h ago`;
	if (diffDays < 7) return `${diffDays}d ago`;
	
	return date.toLocaleDateString(undefined, { 
		month: 'short', 
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
}

function formatLatency(ms?: number): string {
	if (ms === undefined || ms === null) return '—';
	if (ms < 1) return '<1 ms';
	return `${ms.toFixed(1)} ms`;
}

function getLatencyStatus(ms?: number): 'good' | 'warning' | 'bad' {
	if (ms === undefined || ms === null) return 'bad';
	if (ms < 50) return 'good';
	if (ms < 150) return 'warning';
	return 'bad';
}

function getPacketLossStatus(percent: number): 'good' | 'warning' | 'bad' {
	if (percent === 0) return 'good';
	if (percent < 5) return 'warning';
	return 'bad';
}

function getUptimeColor(percent: number): string {
	if (percent >= 99) return 'text-emerald-600 dark:text-emerald-400';
	if (percent >= 95) return 'text-amber-600 dark:text-amber-400';
	return 'text-red-600 dark:text-red-400';
}

function getUptimeBarColor(percent: number): string {
	if (percent >= 99) return 'bg-emerald-500';
	if (percent >= 95) return 'bg-amber-500';
	return 'bg-red-500';
}

async function fetchHealth(includePorts = false) {
	const ip = props.node?.ip;
	if (!ip) return;
	
	loading.value = true;
	error.value = null;
	
	try {
		// Call the backend proxy which forwards to health service
		const response = await axios.get<DeviceMetrics>(
			`/api/health/check/${ip}`,
			{ 
				params: { 
					include_ports: includePorts,
					include_dns: true
				},
				timeout: 30000 
			}
		);
		localMetrics.value = response.data;
	} catch (err: any) {
		console.error('Health check failed:', err);
		error.value = err.response?.data?.detail || err.message || 'Failed to connect to health service';
	} finally {
		loading.value = false;
	}
}

async function refreshHealth() {
	// Force a live health check
	await fetchHealth(false);
}

async function scanPorts() {
	scanningPorts.value = true;
	try {
		// Port scanning always requires a live check
		await fetchHealth(true);
	} finally {
		scanningPorts.value = false;
	}
}

// Clear local metrics when node changes (will use cached from parent)
watch(() => props.node?.ip, (newIp, oldIp) => {
	if (newIp !== oldIp) {
		localMetrics.value = null;
		error.value = null;
		// Reset test IP state
		testIPs.value = [];
		testIPMetrics.value = [];
		testIPsError.value = null;
		showAddTestIP.value = false;
		// Reset speed test state
		speedTestResult.value = null;
		speedTestError.value = null;
	}
});

// Load test IPs and speed test results when gateway node is selected
watch([() => props.node?.ip, isGateway], async ([ip, isGw]) => {
	if (ip && isGw) {
		await Promise.all([
			loadTestIPs(),
			loadStoredSpeedTest()
		]);
		startTestIPPolling();
	} else {
		stopTestIPPolling();
		// Reset speed test state when switching away from gateway
		speedTestResult.value = null;
		speedTestError.value = null;
	}
}, { immediate: true });

// Cleanup polling on unmount
onUnmounted(() => {
	stopTestIPPolling();
});

// ==================== Test IP Functions ====================

function startTestIPPolling() {
	stopTestIPPolling();
	// Poll for test IP metrics every 15 seconds
	testIPPollingInterval = setInterval(async () => {
		if (props.node?.ip && isGateway.value) {
			await fetchTestIPMetrics();
		}
	}, 15000);
}

function stopTestIPPolling() {
	if (testIPPollingInterval) {
		clearInterval(testIPPollingInterval);
		testIPPollingInterval = null;
	}
}

async function loadTestIPs() {
	const ip = props.node?.ip;
	if (!ip) return;

	testIPsLoading.value = true;
	testIPsError.value = null;

	try {
		// First try to get configuration
		const configResponse = await axios.get<{ gateway_ip: string; test_ips: GatewayTestIP[]; enabled: boolean }>(
			`/api/health/gateway/${ip}/test-ips`
		);
		testIPs.value = configResponse.data.test_ips || [];

		// Then get cached metrics
		await fetchTestIPMetrics();
	} catch (err: any) {
		if (err.response?.status === 404) {
			// No test IPs configured yet - that's fine
			testIPs.value = [];
			testIPMetrics.value = [];
		} else {
			console.error('Failed to load test IPs:', err);
			testIPsError.value = err.response?.data?.detail || err.message || 'Failed to load test IPs';
		}
	} finally {
		testIPsLoading.value = false;
	}
}

async function fetchTestIPMetrics() {
	const ip = props.node?.ip;
	if (!ip || testIPs.value.length === 0) return;

	try {
		const response = await axios.get<GatewayTestIPsResponse>(
			`/api/health/gateway/${ip}/test-ips/cached`
		);
		testIPMetrics.value = response.data.test_ips || [];
	} catch (err: any) {
		console.error('Failed to fetch test IP metrics:', err);
	}
}

async function saveTestIPs() {
	const ip = props.node?.ip;
	if (!ip) return;

	testIPsLoading.value = true;
	testIPsError.value = null;

	try {
		await axios.post(`/api/health/gateway/${ip}/test-ips`, {
			gateway_ip: ip,
			test_ips: testIPs.value
		});

		// Immediately check the test IPs
		await checkTestIPsNow();
	} catch (err: any) {
		console.error('Failed to save test IPs:', err);
		testIPsError.value = err.response?.data?.detail || err.message || 'Failed to save test IPs';
	} finally {
		testIPsLoading.value = false;
	}
}

async function checkTestIPsNow() {
	const ip = props.node?.ip;
	if (!ip) return;

	testIPsLoading.value = true;

	try {
		const response = await axios.get<GatewayTestIPsResponse>(
			`/api/health/gateway/${ip}/test-ips/check`
		);
		testIPMetrics.value = response.data.test_ips || [];
	} catch (err: any) {
		console.error('Failed to check test IPs:', err);
		testIPsError.value = err.response?.data?.detail || err.message || 'Failed to check test IPs';
	} finally {
		testIPsLoading.value = false;
	}
}

function addTestIP() {
	if (!hasWritePermission.value) return;
	const ip = newTestIP.value.trim();
	if (!ip) return;

	// Basic IP validation
	const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
	if (!ipRegex.test(ip)) {
		testIPsError.value = 'Please enter a valid IP address';
		return;
	}

	// Check for duplicates
	if (testIPs.value.some(t => t.ip === ip)) {
		testIPsError.value = 'This IP is already in the list';
		return;
	}

	testIPs.value.push({
		ip,
		label: newTestIPLabel.value.trim() || undefined
	});

	// Clear form
	newTestIP.value = '';
	newTestIPLabel.value = '';
	showAddTestIP.value = false;
	testIPsError.value = null;

	// Save and check
	saveTestIPs();
}

function removeTestIP(ip: string) {
	if (!hasWritePermission.value) return;
	testIPs.value = testIPs.value.filter(t => t.ip !== ip);
	testIPMetrics.value = testIPMetrics.value.filter(m => m.ip !== ip);

	if (testIPs.value.length === 0) {
		// Remove configuration entirely
		const gatewayIp = props.node?.ip;
		if (gatewayIp) {
			axios.delete(`/api/health/gateway/${gatewayIp}/test-ips`).catch(console.error);
		}
	} else {
		saveTestIPs();
	}
}

function getTestIPMetrics(ip: string): GatewayTestIPMetrics | undefined {
	return testIPMetrics.value.find(m => m.ip === ip);
}

function getTestIPStatusColor(status?: HealthStatus): string {
	switch (status) {
		case 'healthy': return 'bg-emerald-500';
		case 'degraded': return 'bg-amber-500';
		case 'unhealthy': return 'bg-red-500';
		default: return 'bg-slate-400';
	}
}

function getTestIPStatusLabel(status?: HealthStatus): string {
	switch (status) {
		case 'healthy': return 'Online';
		case 'degraded': return 'Degraded';
		case 'unhealthy': return 'Offline';
		default: return 'Unknown';
	}
}

// Preset test IPs for quick add
const presetTestIPs: GatewayTestIP[] = [
	{ ip: '8.8.8.8', label: 'Google DNS' },
	{ ip: '1.1.1.1', label: 'Cloudflare DNS' },
	{ ip: '9.9.9.9', label: 'Quad9 DNS' },
	{ ip: '208.67.222.222', label: 'OpenDNS' },
];

function addPresetTestIP(preset: GatewayTestIP) {
	if (!hasWritePermission.value) return;
	if (testIPs.value.some(t => t.ip === preset.ip)) {
		testIPsError.value = `${preset.label || preset.ip} is already in the list`;
		return;
	}
	testIPs.value.push({ ...preset });
	testIPsError.value = null;
	saveTestIPs();
}

// ==================== Speed Test Functions ====================

async function loadStoredSpeedTest() {
	const ip = props.node?.ip;
	if (!ip) return;

	try {
		const response = await axios.get<SpeedTestResult>(`/api/health/gateway/${ip}/speedtest`);
		speedTestResult.value = response.data;
	} catch (err: any) {
		// 404 means no stored results - that's fine, not an error
		if (err.response?.status !== 404) {
			console.error('Failed to load stored speed test:', err);
		}
		// Don't set error - just means no previous test
		speedTestResult.value = null;
	}
}

async function runSpeedTest() {
	const ip = props.node?.ip;
	speedTestRunning.value = true;
	speedTestError.value = null;

	try {
		// Use gateway-specific endpoint if we have a gateway IP
		const endpoint = ip ? `/api/health/gateway/${ip}/speedtest` : '/api/health/speedtest';
		const response = await axios.post<SpeedTestResult>(endpoint, {}, {
			timeout: 120000 // 2 minute timeout
		});
		speedTestResult.value = response.data;
		
		if (!response.data.success) {
			speedTestError.value = response.data.error_message || 'Speed test failed';
		}
	} catch (err: any) {
		console.error('Speed test failed:', err);
		speedTestError.value = err.response?.data?.detail || err.message || 'Failed to run speed test';
	} finally {
		speedTestRunning.value = false;
	}
}

function formatSpeed(mbps?: number): string {
	if (mbps === undefined || mbps === null) return '—';
	if (mbps >= 1000) {
		return `${(mbps / 1000).toFixed(2)} Gbps`;
	}
	return `${mbps.toFixed(2)} Mbps`;
}

// ==================== LAN Ports Functions ====================

// Show LAN ports section for switches, routers, servers, firewalls
const showLanPortsSection = computed(() => {
	const role = props.node?.role;
	return role === 'switch/ap' || role === 'gateway/router' || role === 'server' || role === 'firewall' || role === 'nas';
});

// State
const lanPortsExpanded = ref(true);
const showPortGridSetup = ref(false);
const portGridCols = ref(8);
const portGridRows = ref(2);
const defaultPortType = ref<PortType>('rj45');
const editingPort = ref<LanPort | null>(null);
const originalEditingPort = ref<LanPort | null>(null);
const portEditMode = ref(false); // Edit mode for configuring port type, speed, status, PoE
const wasInEditModeOnOpen = ref(false); // Track if user was in edit mode when they opened the port editor

// Local copy of lanPorts config that we can modify
const lanPortsConfig = ref<LanPortsConfig | null>(null);

// Initialize from node
watch(() => props.node?.lanPorts, (newConfig) => {
	if (newConfig) {
		lanPortsConfig.value = JSON.parse(JSON.stringify(newConfig)); // Deep copy
	} else {
		lanPortsConfig.value = null;
	}
	showPortGridSetup.value = false;
}, { immediate: true, deep: true });

// Reset state when node changes
watch(() => props.node?.id, () => {
	showPortGridSetup.value = false;
	editingPort.value = null;
	lanPortsExpanded.value = true;
	portEditMode.value = false;
});

// Get sorted ports (row by row, column by column)
const sortedPorts = computed(() => {
	if (!lanPortsConfig.value?.ports) return [];
	return [...lanPortsConfig.value.ports].sort((a, b) => {
		if (a.row !== b.row) return a.row - b.row;
		return a.col - b.col;
	});
});

// Get active connections (ports with connected devices)
const activeConnections = computed(() => {
	return sortedPorts.value.filter(p => p.status === 'active' && (p.connectedDeviceId || p.connectionLabel));
});

// Available devices for connection dropdown (exclude current device)
const availableDevices = computed(() => {
	if (!props.allDevices) return [];
	return props.allDevices
		.filter(d => d.id !== props.node?.id && d.role !== 'group')
		.map(d => ({
			id: d.id,
			name: d.hostname || d.name || d.ip || 'Unknown',
			ip: d.ip
		}));
});

function createPortGrid() {
	if (!hasWritePermission.value || !props.node) return;
	
	const ports: LanPort[] = [];
	let portNum = 1;
	
	for (let row = 1; row <= portGridRows.value; row++) {
		for (let col = 1; col <= portGridCols.value; col++) {
			ports.push({
				row,
				col,
				portNumber: portNum++,
				type: defaultPortType.value,
				status: 'unused'
			});
		}
	}
	
	const config: LanPortsConfig = {
		rows: portGridRows.value,
		cols: portGridCols.value,
		ports,
		labelFormat: 'numeric',
		startNumber: 1
	};
	
	lanPortsConfig.value = config;
	showPortGridSetup.value = false;
	
	// Emit to parent
	emit('updateLanPorts', props.node.id, config);
}

function getPortLabel(port: LanPort): string {
	if (port.portNumber != null) return String(port.portNumber);
	// Calculate from position
	const config = lanPortsConfig.value;
	if (!config) return '?';
	return String((port.row - 1) * config.cols + port.col);
}

function getPortClasses(port: LanPort): string {
	const classes: string[] = [];
	
	if (port.status === 'blocked') {
		classes.push('bg-slate-200 dark:bg-slate-800 border-dashed border-slate-400 dark:border-slate-600 opacity-50');
	} else if (port.status === 'unused') {
		classes.push('bg-slate-300 dark:bg-slate-700 border-slate-400 dark:border-slate-600');
	} else {
		// Active port
		if (port.type === 'rj45') {
			classes.push('bg-amber-200 dark:bg-amber-900/50 border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-200');
		} else {
			// SFP or SFP+
			classes.push('bg-cyan-200 dark:bg-cyan-900/50 border-cyan-400 dark:border-cyan-600 text-cyan-800 dark:text-cyan-200');
		}
		
		if (port.connectedDeviceId) {
			classes.push('ring-2 ring-emerald-400/50');
		}
	}
	
	if (hasWritePermission.value) {
		classes.push('hover:ring-2 hover:ring-cyan-400');
	}
	
	return classes.join(' ');
}

function getPortShape(port: LanPort): string {
	if (port.status === 'blocked') {
		return 'rounded border-dashed';
	}
	
	if (port.type === 'rj45') {
		// RJ45: Square/rectangular shape with slight rounding
		return 'rounded-sm';
	} else {
		// SFP/SFP+: Rectangular shape with slight rounding (not too pill-like)
		return 'rounded';
	}
}

function getPortTooltip(port: LanPort): string {
	const parts: string[] = [`Port ${getPortLabel(port)}`];
	
	if (port.status === 'blocked') {
		parts.push('(Blocked/Does not exist)');
	} else {
		parts.push(`Type: ${port.type.toUpperCase()}`);
		if (port.status === 'active') {
			const displaySpeed = getDisplaySpeed(port);
			if (displaySpeed.speed) {
				if (displaySpeed.isInferred) {
					parts.push(`Speed: ${displaySpeed.speed} (inferred from connected device)`);
				} else {
					parts.push(`Speed: ${displaySpeed.speed}`);
				}
			}
			if (port.poe && port.poe !== 'off') {
				parts.push(`PoE: ${port.poe.toUpperCase()}`);
			}
			if (port.connectedDeviceName) {
				parts.push(`Connected to: ${port.connectedDeviceName}`);
			} else if (port.connectionLabel) {
				parts.push(`Connection: ${port.connectionLabel}`);
			}
		} else {
			parts.push('(Unused)');
		}
	}
	
	return parts.join('\n');
}

function formatSpeedShort(speed?: PortSpeed): string {
	if (!speed) return '';
	// Already short format
	return speed;
}

function getSpeedBadgeClass(speed?: PortSpeed): string {
	if (!speed) return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
	
	// Color code by speed tier
	if (speed.includes('100G') || speed.includes('40G')) {
		return 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400';
	}
	if (speed.includes('25G') || speed.includes('10G')) {
		return 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-400';
	}
	if (speed.includes('5G') || speed.includes('2.5G') || speed.includes('1G')) {
		return 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400';
	}
	if (speed.includes('100M')) {
		return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400';
	}
	return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
}

function onPortClick(port: LanPort) {
	if (!hasWritePermission.value) return;
	// Track whether user was in edit mode when they opened the editor
	wasInEditModeOnOpen.value = portEditMode.value;
	// Create a deep copy for editing
	editingPort.value = JSON.parse(JSON.stringify(port));
	originalEditingPort.value = port;
}

function openPortEditor(port: LanPort) {
	onPortClick(port);
}

function closePortEditor() {
	// Restore edit mode to what it was when the user opened the editor
	portEditMode.value = wasInEditModeOnOpen.value;
	editingPort.value = null;
	originalEditingPort.value = null;
}

function getPoeLabel(poe?: PoeStatus): string {
	switch (poe) {
		case 'poe': return 'PoE (802.3af, 15W)';
		case 'poe+': return 'PoE+ (802.3at, 30W)';
		case 'poe++': return 'PoE++ (802.3bt, 60W+)';
		default: return 'No PoE';
	}
}

function getPoeDescription(poe?: PoeStatus): string {
	switch (poe) {
		case 'poe': return '802.3af - Up to 15W power delivery';
		case 'poe+': return '802.3at - Up to 30W power delivery';
		case 'poe++': return '802.3bt - Up to 60W+ power delivery';
		default: return 'Power over Ethernet disabled';
	}
}

function onConnectedDeviceChange() {
	if (!editingPort.value) return;
	
	// Update the cached device name
	if (editingPort.value.connectedDeviceId) {
		const device = availableDevices.value.find(d => d.id === editingPort.value!.connectedDeviceId);
		if (device) {
			editingPort.value.connectedDeviceName = device.name;
		}
		
		// Try to auto-infer speed from the connected device's port
		const inferredSpeed = getInferredSpeedFromConnectedDevice(editingPort.value.connectedDeviceId);
		if (inferredSpeed && !editingPort.value.negotiatedSpeed) {
			editingPort.value.negotiatedSpeed = inferredSpeed;
		}
	} else {
		editingPort.value.connectedDeviceName = undefined;
	}
}

// Find speed from a connected device's port that links back to this node
function getInferredSpeedFromConnectedDevice(connectedDeviceId: string): PortSpeed | undefined {
	if (!props.node || !props.allDevices) return undefined;
	
	// Find the connected device
	const connectedDevice = props.allDevices.find(d => d.id === connectedDeviceId);
	if (!connectedDevice?.lanPorts?.ports) return undefined;
	
	// Look for a port on that device that connects back to the current node
	const linkBackPort = connectedDevice.lanPorts.ports.find(
		p => p.connectedDeviceId === props.node!.id && p.status === 'active'
	);
	
	if (linkBackPort) {
		// Return the negotiated speed first, then configured speed
		return linkBackPort.negotiatedSpeed || linkBackPort.speed;
	}
	
	return undefined;
}

// Get the display speed for a port, considering inferred speed from connected device
function getDisplaySpeed(port: LanPort): { speed: PortSpeed | undefined; isInferred: boolean } {
	// First check if port has its own speed set
	if (port.negotiatedSpeed) {
		return { speed: port.negotiatedSpeed, isInferred: false };
	}
	if (port.speed) {
		return { speed: port.speed, isInferred: false };
	}
	
	// Try to infer from connected device
	if (port.connectedDeviceId) {
		const inferredSpeed = getInferredSpeedFromConnectedDevice(port.connectedDeviceId);
		if (inferredSpeed) {
			return { speed: inferredSpeed, isInferred: true };
		}
	}
	
	return { speed: undefined, isInferred: false };
}

function savePortChanges() {
	if (!editingPort.value || !originalEditingPort.value || !lanPortsConfig.value || !props.node) return;
	
	// Find and update the port in the config
	const portIndex = lanPortsConfig.value.ports.findIndex(
		p => p.row === originalEditingPort.value!.row && p.col === originalEditingPort.value!.col
	);
	
	if (portIndex >= 0) {
		// Clear connection data if not active
		if (editingPort.value.status !== 'active') {
			editingPort.value.connectedDeviceId = undefined;
			editingPort.value.connectedDeviceName = undefined;
			editingPort.value.connectionLabel = undefined;
			editingPort.value.speed = undefined;
			editingPort.value.negotiatedSpeed = undefined;
		}
		
		// Clear PoE if blocked or not RJ45 (PoE is only for copper ports)
		if (editingPort.value.status === 'blocked' || editingPort.value.type !== 'rj45') {
			editingPort.value.poe = undefined;
		}
		
		lanPortsConfig.value.ports[portIndex] = { ...editingPort.value };
		
		// Emit to parent
		emit('updateLanPorts', props.node.id, lanPortsConfig.value);
	}
	
	closePortEditor();
}

function confirmClearPorts() {
	if (!hasWritePermission.value || !props.node) return;
	
	if (confirm('Are you sure you want to clear all port configuration? This cannot be undone.')) {
		lanPortsConfig.value = null;
		emit('updateLanPorts', props.node.id, null as any);
	}
}
</script>

