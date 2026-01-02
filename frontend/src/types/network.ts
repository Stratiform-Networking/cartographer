export type DeviceRole =
  | 'gateway/router'
  | 'switch/ap'
  | 'firewall'
  | 'server'
  | 'service'
  | 'nas'
  | 'client'
  | 'unknown';

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
  /** Description of what changed */
  changes: string[];
}

export interface TreeNode {
  id: string;
  name: string;
  role?: DeviceRole | 'group';
  ip?: string;
  hostname?: string;
  children?: TreeNode[];
  /** Freeform layout X position (persisted) */
  fx?: number;
  /** Freeform layout Y position (persisted) */
  fy?: number;
  /** Parent node ID for topology connections */
  parentId?: string;
  /** Connection speed label (e.g., "1GbE", "10GbE") */
  connectionSpeed?: string;
  /** ISO timestamp when node was created */
  createdAt?: string;
  /** ISO timestamp when node was last modified */
  updatedAt?: string;
  /** Version number, increments on each change */
  version?: number;
  /** Previous versions for audit trail */
  history?: NodeVersion[];
  /** Whether to include in health monitoring (default: true) */
  monitoringEnabled?: boolean;
  /** Custom user notes */
  notes?: string;
  /** LAN port configuration for switches/routers */
  lanPorts?: LanPortsConfig;
}

export interface ParsedNetworkMap {
  raw: string;
  gateway?: GatewayInfo;
  devices: DeviceEntry[];
  root: TreeNode;
}

export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';

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
  /** ISO timestamp */
  timestamp: string;
  success: boolean;
  latency_ms?: number;
}

export interface DeviceMetrics {
  ip: string;
  status: HealthStatus;
  /** ISO timestamp of last health check */
  last_check: string;
  ping?: PingResult;
  dns?: DnsResult;
  open_ports: PortCheckResult[];
  uptime_percent_24h?: number;
  avg_latency_24h_ms?: number;
  checks_passed_24h: number;
  checks_failed_24h: number;
  /** Recent check history for timeline display */
  check_history: CheckHistoryEntry[];
  /** ISO timestamp when device was last seen online */
  last_seen_online?: string;
  consecutive_failures: number;
  error_message?: string;
}

/** Gateway Test IP for internet connectivity testing */
export interface GatewayTestIP {
  ip: string;
  /** Friendly name (e.g., "Google DNS", "Cloudflare") */
  label?: string;
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
  /** ISO timestamp */
  last_check: string;
  ping?: PingResult;
  uptime_percent_24h?: number;
  avg_latency_24h_ms?: number;
  checks_passed_24h: number;
  checks_failed_24h: number;
  check_history: CheckHistoryEntry[];
  /** ISO timestamp */
  last_seen_online?: string;
  consecutive_failures: number;
}

export interface GatewayTestIPsResponse {
  gateway_ip: string;
  test_ips: GatewayTestIPMetrics[];
  /** ISO timestamp */
  last_check?: string;
}

export interface SpeedTestResult {
  success: boolean;
  /** ISO timestamp */
  timestamp: string;
  /** Speed in Mbps */
  download_mbps?: number;
  /** Speed in Mbps */
  upload_mbps?: number;
  /** Ping to speed test server in ms */
  ping_ms?: number;
  server_name?: string;
  server_location?: string;
  server_sponsor?: string;
  client_ip?: string;
  client_isp?: string;
  error_message?: string;
  duration_seconds?: number;
}

export type PortType = 'rj45' | 'sfp' | 'sfp+';

/** Port status: blocked = does not exist or permanently disabled */
export type PortStatus = 'active' | 'unused' | 'blocked';

export type PortSpeed =
  | '10M'
  | '100M'
  | '1G'
  | '2.5G'
  | '5G'
  | '10G'
  | '25G'
  | '40G'
  | '100G'
  | 'auto'
  | string;

/** PoE power levels: 802.3af (15W), 802.3at (30W), 802.3bt (60W+) */
export type PoeStatus = 'off' | 'poe' | 'poe+' | 'poe++';

export interface LanPort {
  /** Position row in the grid (1-indexed) */
  row: number;
  /** Position column in the grid (1-indexed) */
  col: number;
  portNumber?: number;
  type: PortType;
  status: PortStatus;
  /** Configured speed */
  speed?: PortSpeed;
  /** Actual negotiated speed (if different from configured) */
  negotiatedSpeed?: PortSpeed;
  poe?: PoeStatus;
  /** ID of the connected TreeNode */
  connectedDeviceId?: string;
  /** Cached name for display */
  connectedDeviceName?: string;
  connectionLabel?: string;
}

export interface LanPortsConfig {
  /** Number of rows (Y axis) */
  rows: number;
  /** Number of columns (X axis) */
  cols: number;
  ports: LanPort[];
  /** Port label format: numeric (1,2,3) or alpha (A,B,C) */
  labelFormat?: 'numeric' | 'alpha' | 'custom';
  /** Starting number for numeric labels (default: 1) */
  startNumber?: number;
}
