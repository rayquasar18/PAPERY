import DashboardLayoutClient from './layout-client';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

/**
 * DashboardLayout — Server component layout for the (dashboard) route group.
 *
 * Thin server wrapper that delegates to the client layout shell.
 * This separation allows the layout to remain a server component at
 * the Next.js level while composing client-side interactive elements.
 */
export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return <DashboardLayoutClient>{children}</DashboardLayoutClient>;
}
