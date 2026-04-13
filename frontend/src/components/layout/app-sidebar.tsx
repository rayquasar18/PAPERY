'use client';

import {
  LayoutDashboard,
  FolderKanban,
  Settings,
  HelpCircle,
  FolderPlus,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/lib/i18n/navigation';
import { NavUser } from '@/components/layout/nav-user';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { useAuth } from '@/hooks/use-auth';

/**
 * AppSidebar -- Main navigation sidebar adapted from shadcn dashboard-01.
 *
 * Uses collapsible="offcanvas" with variant="inset" for the shadcn inset layout.
 * Header: PAPERY logo ("P" square + "PAPERY" text)
 * Content: Quick Create button + main nav items + secondary nav at bottom
 * Footer: NavUser component with real user data from auth hook
 */
export function AppSidebar(props: React.ComponentProps<typeof Sidebar>) {
  const t = useTranslations('Navigation');
  const pathname = usePathname();
  const { user } = useAuth();

  // Main navigation items
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
  ];

  // Secondary navigation at bottom
  const secondaryItems = [
    {
      key: 'settings' as const,
      icon: Settings,
      href: '/settings' as const,
    },
    {
      key: 'help' as const,
      icon: HelpCircle,
      href: '/help' as const,
      label: 'Help',
    },
  ];

  // Build user data for NavUser from auth state
  const userData = {
    name: user?.display_name || 'User',
    email: user?.email || 'user@example.com',
    avatar: user?.avatar_url || undefined,
  };

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      {/* Logo + app name */}
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:!p-1.5"
            >
              <Link href="/dashboard">
                <div className="flex aspect-square size-5 items-center justify-center rounded-md bg-primary text-primary-foreground text-xs font-bold">
                  P
                </div>
                <span className="text-base font-semibold">PAPERY</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {/* Quick Create + main nav */}
        <SidebarGroup>
          <SidebarGroupContent className="flex flex-col gap-2">
            <SidebarMenu>
              <SidebarMenuItem className="flex items-center gap-2">
                <SidebarMenuButton
                  tooltip="Quick Create"
                  className="min-w-8 bg-primary text-primary-foreground duration-200 ease-linear hover:bg-primary/90 hover:text-primary-foreground active:bg-primary/90 active:text-primary-foreground"
                >
                  <FolderPlus />
                  <span>Quick Create</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
            <SidebarMenu>
              {navItems.map(({ key, icon: Icon, href }) => {
                const isActive =
                  href === '/dashboard'
                    ? pathname === '/dashboard' || pathname === '/'
                    : pathname.startsWith(href);

                return (
                  <SidebarMenuItem key={key}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      tooltip={t(key)}
                    >
                      <Link href={href}>
                        <Icon />
                        <span>{t(key)}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Secondary nav at bottom */}
        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              {secondaryItems.map(({ key, icon: Icon, href, label }) => {
                const isActive = pathname.startsWith(href);
                // Use translation for known keys, fallback to label
                const displayLabel =
                  key === 'settings' || key === 'help'
                    ? key === 'help'
                      ? (label ?? key)
                      : t(key)
                    : key;

                return (
                  <SidebarMenuItem key={key}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <Link href={href}>
                        <Icon />
                        <span>{displayLabel}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* User footer */}
      <SidebarFooter>
        <NavUser user={userData} />
      </SidebarFooter>
    </Sidebar>
  );
}
