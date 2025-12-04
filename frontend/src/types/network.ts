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
	// Parent connection
	parentId?: string; // ID of parent node for topology connections
	connectionSpeed?: string; // Connection speed label (e.g., "1GbE", "10GbE")
	// Version management
	createdAt?: string; // ISO timestamp when node was created
	updatedAt?: string; // ISO timestamp when node was last modified
	version?: number; // Increments on each change
	history?: NodeVersion[]; // Previous versions for audit trail
	// Health monitoring
	monitoringEnabled?: boolean; // Whether to include this node in health monitoring (default: true)
	// User notes
	notes?: string; // Custom notes attached to this node
	// LAN port configuration (for switches, routers, servers with multiple ports)
	lanPorts?: LanPortsConfig;
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
	
	// Additional info
	last_seen_online?: string; // ISO timestamp
	consecutive_failures: number;
	error_message?: string;
}

// Gateway Test IP types (for internet connectivity testing)
export interface GatewayTestIP {
	ip: string;
	label?: string; // Optional friendly name (e.g., "Google DNS", "Cloudflare")
}

export interface GatewayTestIPConfig {
	gateway_ip: string;
	test_ips: GatewayTestIP[];
	enabled: boolean;
}

export interface GatewayTestIPMetrics {
	ip: string;
	label?: string;
	status: HealthStatus;
	last_check: string; // ISO timestamp
	
	// Ping metrics
	ping?: PingResult;
	
	// Historical data
	uptime_percent_24h?: number;
	avg_latency_24h_ms?: number;
	checks_passed_24h: number;
	checks_failed_24h: number;
	check_history: CheckHistoryEntry[];
	
	// Additional info
	last_seen_online?: string; // ISO timestamp
	consecutive_failures: number;
}

export interface GatewayTestIPsResponse {
	gateway_ip: string;
	test_ips: GatewayTestIPMetrics[];
	last_check?: string; // ISO timestamp
}

// Speed Test types
export interface SpeedTestResult {
	success: boolean;
	timestamp: string; // ISO timestamp
	
	// Speed results (in Mbps)
	download_mbps?: number;
	upload_mbps?: number;
	
	// Ping to speed test server
	ping_ms?: number;
	
	// Server info
	server_name?: string;
	server_location?: string;
	server_sponsor?: string;
	
	// Client info
	client_ip?: string;
	client_isp?: string;
	
	// Error info (if failed)
	error_message?: string;
	
	// Duration of the test
	duration_seconds?: number;
}

// LAN Port Configuration types
export type PortType = "rj45" | "sfp" | "sfp+";

export type PortStatus = "active" | "unused" | "blocked"; // blocked = does not exist or permanently disabled

export type PortSpeed = "10M" | "100M" | "1G" | "2.5G" | "5G" | "10G" | "25G" | "40G" | "100G" | "auto" | string;

export type PoeStatus = "off" | "poe" | "poe+" | "poe++"; // 802.3af (15W), 802.3at (30W), 802.3bt (60W+)

export interface LanPort {
	// Position in the grid (1-indexed)
	row: number;
	col: number;
	
	// Port configuration
	portNumber?: number; // Optional port label/number
	type: PortType;
	status: PortStatus;
	
	// Speed configuration
	speed?: PortSpeed; // Configured speed
	negotiatedSpeed?: PortSpeed; // Actual negotiated speed (if different)
	
	// PoE configuration
	poe?: PoeStatus; // Power over Ethernet status
	
	// Connection info
	connectedDeviceId?: string; // ID of the connected TreeNode
	connectedDeviceName?: string; // Cached name for display
	connectionLabel?: string; // Optional custom label for the connection
}

export interface LanPortsConfig {
	// Grid dimensions
	rows: number; // Number of rows (Y axis)
	cols: number; // Number of columns (X axis)
	
	// Port definitions
	ports: LanPort[];
	
	// Display options
	labelFormat?: "numeric" | "alpha" | "custom"; // How to auto-label ports (1,2,3 or A,B,C)
	startNumber?: number; // Starting number for numeric labels (default: 1)
}


