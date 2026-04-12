'use client';

import { LayoutDashboard, FolderKanban, Settings } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/lib/i18n/navigation';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

// Navigation items for the sidebar (D-07)
const navItems = [
  {
    key: 'dashboard' as const,
    icon: LayoutDashboard,
    href: '/dashboard' as const,
  },
  {
    key: 'projects' as const,
    icon: FolderKanban,
    href: '/projects' as const,
  },
  {
    key: 'settings' as const,
    icon: Settings,
    href: '/settings' as const,
  },
] satisfies Array<{
  key: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
}>;

/**
 * AppSidebar — Main application navigation sidebar.
 *
 * Uses shadcn/ui Sidebar with collapsible="icon" for D-02 behavior:
 * - Desktop: expanded (280px) with labels
 * - Tablet: collapsed to icon-only (56px)
 * - Mobile: Sheet overlay (handled by shadcn/ui internally)
 */
export function AppSidebar() {
  const t = useTranslations('Navigation');
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      {/* Logo + app name */}
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              asChild
              className="font-semibold"
            >
              <Link href="/dashboard">
                {/* Logo mark — simple text icon that collapses gracefully */}
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-xs font-bold shrink-0">
                  P
                </div>
                <span className="text-base font-semibold tracking-tight">PAPERY</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      {/* Navigation items */}
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>{t('dashboard').replace('Dashboard', 'Menu')}</SidebarGroupLabel>
          <SidebarMenu>
            {navItems.map(({ key, icon: Icon, href }) => {
              // Determine active state — match current pathname segment
              const isActive =
                href === '/dashboard'
                  ? pathname === '/dashboard' || pathname === '/'
                  : pathname.startsWith(href);

              return (
                <SidebarMenuItem key={key}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive}
                    tooltip={t(key as 'dashboard' | 'projects' | 'settings')}
                  >
                    <Link href={href}>
                      <Icon className="size-4" />
                      <span>{t(key as 'dashboard' | 'projects' | 'settings')}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>

      {/* User footer placeholder — full auth integration in 09-05 */}
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" className="cursor-default">
              <Avatar className="size-8 rounded-lg shrink-0">
                <AvatarFallback className="rounded-lg bg-muted text-muted-foreground text-xs">
                  U
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col gap-0.5 leading-none min-w-0">
                <span className="font-medium text-sm truncate">User</span>
                <span className="text-xs text-muted-foreground truncate">user@example.com</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      {/* Rail for the toggle handle (D-02) */}
      <SidebarRail />
    </Sidebar>
  );
}
