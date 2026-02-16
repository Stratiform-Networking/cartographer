import posthog from 'posthog-js';

const POSTHOG_API_KEY =
  import.meta.env.VITE_POSTHOG_API_KEY || 'phc_wva5vQhVaZRCEUh691CYejTmZK60EdyqkRFToNIBVl2';
const POSTHOG_API_HOST = import.meta.env.VITE_POSTHOG_API_HOST || 'https://us.i.posthog.com';
const POSTHOG_DEFAULTS = import.meta.env.VITE_POSTHOG_DEFAULTS || '2025-11-30';

let initialized = false;

export interface PostHogUserInfo {
  id?: string | null;
  username?: string | null;
  email?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  role?: string | null;
}

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

function resolveDistinctId(user: PostHogUserInfo): string | null {
  return user.id || user.username || user.email || null;
}

export function syncPostHogUser(user: PostHogUserInfo | null | undefined): void {
  if (!user || typeof window === 'undefined') {
    return;
  }

  const distinctId = resolveDistinctId(user);
  if (!distinctId) {
    return;
  }

  usePostHog();
  posthog.identify(distinctId, {
    username: user.username,
    email: user.email,
    first_name: user.first_name,
    last_name: user.last_name,
    role: user.role,
  });
}

export function resetPostHogUser(): void {
  if (typeof window === 'undefined') {
    return;
  }

  usePostHog();
  posthog.reset();
}
