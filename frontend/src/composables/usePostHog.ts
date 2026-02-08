import posthog from 'posthog-js';

const POSTHOG_API_KEY =
  import.meta.env.VITE_POSTHOG_API_KEY || 'phc_wva5vQhVaZRCEUh691CYejTmZK60EdyqkRFToNIBVl2';
const POSTHOG_API_HOST = import.meta.env.VITE_POSTHOG_API_HOST || 'https://us.i.posthog.com';
const POSTHOG_DEFAULTS = import.meta.env.VITE_POSTHOG_DEFAULTS || '2025-11-30';

let initialized = false;

export function usePostHog() {
  if (!initialized && typeof window !== 'undefined') {
    posthog.init(POSTHOG_API_KEY, {
      api_host: POSTHOG_API_HOST,
      defaults: POSTHOG_DEFAULTS,
      capture_pageview: false,
      capture_pageleave: true,
    });
    initialized = true;
  }

  return { posthog };
}
