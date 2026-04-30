import { useSyncExternalStore } from 'react';

/**
 * useMediaQuery — Reactive media query hook.
 *
 * Returns true when the CSS media query matches the current viewport.
 * Starts as false during SSR to prevent hydration mismatches, then
 * updates on the client after mount.
 *
 * @param query - A valid CSS media query string, e.g. '(min-width: 1024px)'
 */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onStoreChange) => {
      const media = window.matchMedia(query);
      media.addEventListener('change', onStoreChange);
      return () => media.removeEventListener('change', onStoreChange);
    },
    () => window.matchMedia(query).matches,
    () => false
  );
}
