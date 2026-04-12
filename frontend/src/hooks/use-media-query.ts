import { useState, useEffect } from 'react';

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
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    setMatches(media.matches);

    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, [query]);

  return matches;
}
