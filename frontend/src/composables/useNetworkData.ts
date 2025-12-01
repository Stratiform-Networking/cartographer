import type { DeviceEntry, DeviceRole, GatewayInfo, ParsedNetworkMap, TreeNode, NodeVersion } from "../types/network";

function parseGateway(section: string): GatewayInfo | undefined {
	const ipHost = /Gateway:\s*([0-9.]+)\s*\(([^)]+)\)/i.exec(section);
	const lanIf = /LAN Interface:\s*([^\n]+)/i.exec(section);
	const subnet = /Subnet:\s*([^\n]+)/i.exec(section);
	if (!ipHost) return undefined;
	return {
		ip: ipHost[1],
		hostname: ipHost[2],
		lanInterface: lanIf?.[1]?.trim(),
		subnet: subnet?.[1]?.trim(),
	};
}

function parseDevices(section: string): DeviceEntry[] {
	const devices: DeviceEntry[] = [];
	const lines = section.split("\n");
	for (const line of lines) {
		// 172.16.191.1    | routerboard.com.lan                 | role=gateway/router  | depth=0
		const m = /^\s*([0-9.]+)\s*\|\s*([^\|]+?)\s*\|\s*role=([a-z\/-]+)\s*\|\s*depth=(\d+)/i.exec(line);
		if (m) {
			const ip = m[1].trim();
			const hostnameRaw = m[2].trim();
			const role = m[3].trim() as DeviceRole;
			const depth = parseInt(m[4].trim(), 10);
			devices.push({
				ip,
				hostname: hostnameRaw === "Unknown" ? "Unknown" : hostnameRaw,
				role,
				depth,
			});
		}
	}
	return devices;
}

function parseHeuristicTree(section: string): Record<string, { ip: string; hostname: string; role: DeviceRole }[]> {
	// Extract groups like "Infrastructure (depth 1: switches / AP / firewall):" followed by list lines
	const groups: Record<string, { ip: string; hostname: string; role: DeviceRole }[]> = {};
	let currentKey: string | null = null;
	const roleFromBracket = (s: string): DeviceRole => {
		const r = s.toLowerCase();
		if (r.includes("gateway")) return "gateway/router";
		if (r.includes("switch")) return "switch/ap";
		if (r.includes("firewall")) return "firewall";
		if (r.includes("server")) return "server";
		if (r.includes("service")) return "service";
		if (r.includes("nas")) return "nas";
		if (r.includes("client")) return "client";
		return "unknown";
	};
	for (const line of section.split("\n")) {
		const header = /^\s*([A-Za-z \/()0-9:\-]+):\s*$/.exec(line);
		if (header) {
			currentKey = header[1].trim();
			groups[currentKey] = [];
			continue;
		}
		//  - 172.16.191.106  (tl-sg108e.lan) [switch/ap]
		const item = /^\s*-\s*([0-9.]+)\s*\(([^)]+)\)\s*\[([^\]]+)\]/.exec(line);
		if (currentKey && item) {
			groups[currentKey].push({
				ip: item[1],
				hostname: item[2],
				role: roleFromBracket(item[3]),
			});
		}
	}
	return groups;
}

function initializeNodeVersion(node: TreeNode): void {
	const now = new Date().toISOString();
	node.createdAt = now;
	node.updatedAt = now;
	node.version = 1;
	node.history = [{
		version: 1,
		timestamp: now,
		changes: ['Node discovered by network mapper']
	}];
}

function buildTree(gateway: GatewayInfo | undefined, groups: Record<string, { ip: string; hostname: string; role: DeviceRole }[]>): TreeNode {
	const now = new Date().toISOString();
	const root: TreeNode = {
		id: gateway ? gateway.ip : "root",
		name: gateway ? `${gateway.ip} (${gateway.hostname})` : "Network",
		role: gateway ? "gateway/router" : "group",
		ip: gateway?.ip,
		hostname: gateway?.hostname,
		children: [],
		createdAt: now,
		updatedAt: now,
		version: 1,
		history: [{
			version: 1,
			timestamp: now,
			changes: ['Gateway discovered by network mapper']
		}]
	};
	for (const [groupName, items] of Object.entries(groups)) {
		if (!items.length) continue;
		const groupNode: TreeNode = {
			id: `group:${groupName}`,
			name: groupName,
			role: "group",
			children: [],
		};
		for (const it of items) {
			const deviceNode: TreeNode = {
				id: it.ip,
				name: `${it.ip} (${it.hostname})`,
				role: it.role,
				ip: it.ip,
				hostname: it.hostname,
				children: [],
			};
			initializeNodeVersion(deviceNode);
			groupNode.children!.push(deviceNode);
		}
		root.children!.push(groupNode);
	}
	return root;
}

export function useNetworkData() {
	function parseNetworkMap(raw: string): ParsedNetworkMap {
		const gatewaySection = raw; // gateway lines are near the top
		const devicesSection = (() => {
			const start = raw.indexOf("=== Devices Found ===");
			if (start === -1) return "";
			const rest = raw.slice(start);
			const endIdx = rest.indexOf("\n\n");
			const seg = endIdx === -1 ? rest : rest.slice(0, endIdx);
			return seg;
		})();
		const heuristicSection = (() => {
			const start = raw.indexOf("=== Heuristic Topology Tree ===");
			if (start === -1) return "";
			return raw.slice(start);
		})();

		const gateway = parseGateway(gatewaySection);
		const devices = parseDevices(devicesSection);
		const groups = parseHeuristicTree(heuristicSection);
		const root = buildTree(gateway, groups);
		return {
			raw,
			gateway,
			devices,
			root,
		};
	}

	return { parseNetworkMap };
}


