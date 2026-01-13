<template>
  <router-view />
</template>

<script lang="ts" setup>
import { onMounted } from 'vue';

const OAUTH_STORAGE_KEY = 'discord_oauth_callback';
const OAUTH_CRYPTO_PASSPHRASE = 'discord-oauth-localstorage-key';

async function getCryptoKey(): Promise<CryptoKey> {
  const encoder = new TextEncoder();
  const passphraseData = encoder.encode(OAUTH_CRYPTO_PASSPHRASE);
  const hash = await crypto.subtle.digest('SHA-256', passphraseData);
  return crypto.subtle.importKey('raw', hash, { name: 'AES-GCM', length: 256 }, false, [
    'encrypt',
    'decrypt',
  ]);
}

async function encryptData(plainText: string): Promise<string> {
  const key = await getCryptoKey();
  const encoder = new TextEncoder();
  const data = encoder.encode(plainText);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, data);
  const buffer = new Uint8Array(iv.byteLength + ciphertext.byteLength);
  buffer.set(iv, 0);
  buffer.set(new Uint8Array(ciphertext), iv.byteLength);
  return btoa(String.fromCharCode(...buffer));
}

async function decryptData(cipherTextB64: string): Promise<string> {
  const key = await getCryptoKey();
  const binary = atob(cipherTextB64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  const iv = bytes.slice(0, 12);
  const ciphertext = bytes.slice(12);
  const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ciphertext);
  const decoder = new TextDecoder();
  return decoder.decode(decrypted);
}

onMounted(() => {
  // Handle Discord OAuth callback in popup window
  const urlParams = new URLSearchParams(window.location.search);

  // Check if this is a Discord OAuth callback (popup returning from OAuth flow)
  if (urlParams.has('discord_oauth')) {
    const status = urlParams.get('discord_oauth');
    const username = urlParams.get('username');
    const message = urlParams.get('message');
    const contextType = urlParams.get('context_type');
    const networkId = urlParams.get('network_id');

    const callbackData = {
      type: 'discord_oauth_callback',
      status: status,
      username: username,
      message: message,
      context_type: contextType,
      network_id: networkId,
      timestamp: Date.now(),
    };

    if (window.opener) {
      try {
        window.opener.postMessage(callbackData, window.location.origin);
      } catch (e) {
        // postMessage failed, fall through to localStorage
      }
    }

    const storageData = {
      type: 'discord_oauth_callback',
      status: status,
      username: username,
      message: message,
      context_type: contextType,
      timestamp: Date.now(),
    };

    // Encrypt data before storing in localStorage to avoid cleartext storage of sensitive info
    encryptData(JSON.stringify(storageData))
      .then((encrypted) => {
        localStorage.setItem(OAUTH_STORAGE_KEY, encrypted);
      })
      .catch(() => {
        // If encryption fails, avoid storing sensitive data in cleartext
      });

    // Close the popup window
    window.close();

    // If window.close() doesn't work (some browsers block it), show a message
    setTimeout(() => {
      document.body.innerHTML = `
				<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: system-ui, sans-serif; background: #1a1a2e; color: #fff;">
					<h2 style="margin-bottom: 16px;">Discord ${status === 'success' ? 'Linked Successfully!' : 'Linking Failed'}</h2>
					<p style="color: #888;">You can close this window and return to the application.</p>
				</div>
			`;
    }, 100);
  }
});

// Listen for messages from popup windows (if this is the parent)
if (typeof window !== 'undefined') {
  // postMessage listener (works when window.opener survives)
  window.addEventListener('message', (event) => {
    // Verify message is from same origin
    if (event.origin !== window.location.origin) {
      return;
    }

    if (event.data && event.data.type === 'discord_oauth_callback') {
      // Trigger a custom event that components can listen to
      window.dispatchEvent(
        new CustomEvent('discord-oauth-complete', {
          detail: event.data,
        })
      );
    }
  });

  // localStorage listener (reliable fallback for cross-origin popup flows)
  window.addEventListener('storage', (event) => {
    if (event.key === OAUTH_STORAGE_KEY && event.newValue) {
      // Decrypt the stored data before parsing
      decryptData(event.newValue)
        .then((plain) => {
          try {
            const data = JSON.parse(plain);
            if (data.type === 'discord_oauth_callback') {
              // Trigger the same custom event
              window.dispatchEvent(
                new CustomEvent('discord-oauth-complete', {
                  detail: data,
                })
              );
              // Clear the localStorage item
              localStorage.removeItem(OAUTH_STORAGE_KEY);
            }
          } catch (e) {
            // Invalid JSON, ignore
          }
        })
        .catch(() => {
          // Decryption failed, ignore
        });
    }
  });
}
</script>
