/**
 * Network-related utilities
 *
 * IP address parsing, sorting, and network-related helpers.
 */

/**
 * Parse an IP address string into an array of 4 numbers for sorting.
 *
 * @param ipStr - IP address string (e.g., "192.168.1.100")
 * @returns Array of 4 numbers representing each octet, or [0,0,0,0] if invalid
 */
export function parseIpAddress(ipStr: string): [number, number, number, number] {
  const match = ipStr.match(/(\d+)\.(\d+)\.(\d+)\.(\d+)/);
  if (match) {
    return [parseInt(match[1]), parseInt(match[2]), parseInt(match[3]), parseInt(match[4])];
  }
  return [0, 0, 0, 0];
}

/**
 * Compare two IP addresses for sorting.
 * Sorts numerically by each octet (192.168.1.2 < 192.168.1.10).
 *
 * @param ipA - First IP address string
 * @param ipB - Second IP address string
 * @returns Negative if ipA < ipB, positive if ipA > ipB, 0 if equal
 */
export function compareIpAddresses(ipA: string, ipB: string): number {
  const partsA = parseIpAddress(ipA);
  const partsB = parseIpAddress(ipB);

  for (let i = 0; i < 4; i++) {
    if (partsA[i] !== partsB[i]) {
      return partsA[i] - partsB[i];
    }
  }
  return 0;
}

/**
 * Interface for objects with optional ip and id properties.
 * Used for sorting network nodes.
 */
export interface IpIdentifiable {
  id: string;
  ip?: string;
}

/**
 * Compare two network nodes by their IP addresses.
 * Falls back to id if ip is not available.
 *
 * @param a - First node
 * @param b - Second node
 * @returns Comparison result for Array.sort()
 */
export function compareNodesByIp<T extends IpIdentifiable>(a: T, b: T): number {
  const ipA = a.ip || a.id;
  const ipB = b.ip || b.id;
  return compareIpAddresses(ipA, ipB);
}

/**
 * Check if a string is a valid IPv4 address.
 *
 * @param ip - String to validate
 * @returns true if valid IPv4 address
 */
export function isValidIpv4(ip: string): boolean {
  const parts = ip.split('.');
  if (parts.length !== 4) return false;

  return parts.every((part) => {
    const num = parseInt(part, 10);
    return !isNaN(num) && num >= 0 && num <= 255 && part === num.toString();
  });
}

/**
 * Get the subnet of an IP address (first 3 octets).
 *
 * @param ip - IP address string
 * @returns Subnet string (e.g., "192.168.1") or empty string if invalid
 */
export function getSubnet(ip: string): string {
  const parts = parseIpAddress(ip);
  if (parts[0] === 0 && parts[1] === 0 && parts[2] === 0 && parts[3] === 0) {
    return '';
  }
  return `${parts[0]}.${parts[1]}.${parts[2]}`;
}
