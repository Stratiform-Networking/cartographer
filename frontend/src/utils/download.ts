/**
 * File download utilities
 *
 * Helpers for downloading files from the API.
 */

import client from '../api/client';

/**
 * Download a file from the API and trigger a browser download.
 *
 * @param url - API URL to fetch the file from
 * @param filename - Name for the downloaded file
 * @param mimeType - MIME type for the blob (default: 'text/plain')
 * @returns Promise that resolves when download is triggered
 * @throws Error if download fails
 */
export async function downloadFile(
  url: string,
  filename: string,
  mimeType: string = 'text/plain'
): Promise<void> {
  const response = await client.get(url, { responseType: 'blob' });

  const blob = new Blob([response.data], { type: mimeType });
  const blobUrl = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();

  URL.revokeObjectURL(blobUrl);
  document.body.removeChild(a);
}

/**
 * Download a network map file from the API.
 *
 * @param url - API URL for the network map
 * @returns Promise that resolves when download is triggered
 * @throws Error if download fails
 */
export async function downloadNetworkMap(url: string): Promise<void> {
  return downloadFile(url, 'network_map.txt', 'text/plain');
}

/**
 * Download JSON data as a file.
 *
 * @param data - Object to serialize as JSON
 * @param filename - Name for the downloaded file
 */
export function downloadJson(data: unknown, filename: string): void {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const blobUrl = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();

  URL.revokeObjectURL(blobUrl);
  document.body.removeChild(a);
}
