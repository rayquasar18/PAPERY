'use client';

import {
  LayoutDashboard,
  FolderKanban,
  Settings,
  User,
  LogOut,
  ChevronsUpDown,
} from 'lucide-react';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

// Navigation items for the sidebar
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
 * Uses shadcn/ui Sidebar with collapsible="icon" for responsive behavior:
 * - Desktop: expanded (280px) with labels
 * - Tablet: collapsed to icon-only (56px)
 * - Mobile: Sheet overlay (handled by shadcn/ui internally)
 *
 * Footer contains a DropdownMenu for user actions (profile, settings, sign out)
 * following the shadcn dashboard-01 pattern.
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

      {/* User footer with dropdown menu — shadcn dashboard-01 pattern */}
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                  <Avatar className="size-8 rounded-lg shrink-0">
                    <AvatarFallback className="rounded-lg bg-muted text-muted-foreground text-xs">
                      U
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight min-w-0">
                    <span className="truncate font-medium">User</span>
                    <span className="truncate text-xs text-muted-foreground">user@example.com</span>
                  </div>
                  <ChevronsUpDown className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                side="bottom"
                align="end"
                sideOffset={4}
              >
                <DropdownMenuLabel className="p-0 font-normal">
                  <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                    <Avatar className="size-8 rounded-lg">
                      <AvatarFallback className="rounded-lg bg-muted text-muted-foreground text-xs">
                        U
                      </AvatarFallback>
                    </Avatar>
                    <div className="grid flex-1 text-left text-sm leading-tight">
                      <span className="truncate font-medium">User</span>
                      <span className="truncate text-xs text-muted-foreground">user@example.com</span>
                    </div>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem>
                    <User className="mr-2 size-4" />
                    Profile
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Settings className="mr-2 size-4" />
                    Settings
                  </DropdownMenuItem>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-destructive focus:text-destructive">
                  <LogOut className="mr-2 size-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      {/* Rail for the toggle handle */}
      <SidebarRail />
    </Sidebar>
  );
}
