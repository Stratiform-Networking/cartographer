export type DeviceRole =
	| "gateway/router"
	| "switch/ap"
	| "firewall"
	| "server"
	| "service"
	| "nas"
	| "client"
	| "unknown";

export interface DeviceEntry {
	ip: string;
	hostname: string;
	role: DeviceRole;
	depth: number;
}

export interface GatewayInfo {
	ip: string;
	hostname: string;
	lanInterface?: string;
	subnet?: string;
}

export interface NodeVersion {
	version: number;
	timestamp: string;
	changes: string[]; // Description of what changed
}

export interface TreeNode {
	id: string; // typically ip or synthetic group id
	name: string;
	role?: DeviceRole | "group";
	ip?: string;
	hostname?: string;
	children?: TreeNode[];
	// Freeform layout positions (persisted)
	fx?: number;
	fy?: number;
	// Version management
	createdAt?: string; // ISO timestamp when node was created
	updatedAt?: string; // ISO timestamp when node was last modified
	version?: number; // Increments on each change
	history?: NodeVersion[]; // Previous versions for audit trail
	// Health monitoring
	monitoringEnabled?: boolean; // Whether to include this node in health monitoring (default: true)
	// Gateway-specific: external IPs to test for internet connectivity
	testIps?: string[];
}

export interface ParsedNetworkMap {
	raw: string;
	gateway?: GatewayInfo;
	devices: DeviceEntry[];
	root: TreeNode;
}

// Health monitoring types
export type HealthStatus = "healthy" | "degraded" | "unhealthy" | "unknown";

export interface PingResult {
	success: boolean;
	latency_ms?: number;
	packet_loss_percent: number;
	min_latency_ms?: number;
	max_latency_ms?: number;
	avg_latency_ms?: number;
	jitter_ms?: number;
}

export interface DnsResult {
	success: boolean;
	resolved_hostname?: string;
	reverse_dns?: string;
	resolution_time_ms?: number;
}

export interface PortCheckResult {
	port: number;
	open: boolean;
	service?: string;
	response_time_ms?: number;
}

export interface CheckHistoryEntry {
	timestamp: string; // ISO timestamp
	success: boolean;
	latency_ms?: number;
}

export interface SpeedTestResult {
	download_mbps?: number;
	upload_mbps?: number;
	test_server?: string;
	test_timestamp?: string; // ISO timestamp
	error?: string;
}

export interface DeviceMetrics {
	ip: string;
	status: HealthStatus;
	last_check: string; // ISO timestamp
	
	// Ping metrics
	ping?: PingResult;
	
	// DNS metrics
	dns?: DnsResult;
	
	// Open ports discovered
	open_ports: PortCheckResult[];
	
	// Historical data
	uptime_percent_24h?: number;
	avg_latency_24h_ms?: number;
	checks_passed_24h: number;
	checks_failed_24h: number;
	check_history: CheckHistoryEntry[]; // Recent check history for timeline display
	
	// Speed test results (for external IPs / internet connectivity)
	speed_test?: SpeedTestResult;
	
	// Additional info
	last_seen_online?: string; // ISO timestamp
	consecutive_failures: number;
	error_message?: string;
}


