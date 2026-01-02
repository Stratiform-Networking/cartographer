<template>
  <router-view />
</template>

<script lang="ts" setup>
import { onMounted } from 'vue';

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

    // Try postMessage first (works if window.opener survived cross-origin navigation)
    if (window.opener) {
      try {
        window.opener.postMessage(callbackData, window.location.origin);
      } catch (e) {
        // postMessage failed, fall through to localStorage
      }
    }

    // Always use localStorage as reliable cross-origin communication
    // The parent window listens for storage events
    localStorage.setItem('discord_oauth_callback', JSON.stringify(callbackData));

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
    if (event.key === 'discord_oauth_callback' && event.newValue) {
      try {
        const data = JSON.parse(event.newValue);
        if (data.type === 'discord_oauth_callback') {
          // Trigger the same custom event
          window.dispatchEvent(
            new CustomEvent('discord-oauth-complete', {
              detail: data,
            })
          );
          // Clear the localStorage item
          localStorage.removeItem('discord_oauth_callback');
        }
      } catch (e) {
        // Invalid JSON, ignore
      }
    }
  });
}
</script>
