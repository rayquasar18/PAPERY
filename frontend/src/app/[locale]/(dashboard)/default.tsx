/**
 * Default fallback for the (dashboard) route group.
 *
 * Required by Next.js when using parallel routes — provides a fallback
 * for the implicit `children` slot on hard navigations where Next.js
 * cannot recover the active state from the URL.
 */
export default function Default() {
  return null;
}
