'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  MessageSquare,
  Network,
  Cog,
  FileText,
  Wrench,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/chat', label: 'Chat', icon: MessageSquare },
  { href: '/graph', label: 'Graph', icon: Network },
  { href: '/operations', label: 'Operations', icon: Wrench },
  { href: '/settings', label: 'Settings', icon: Cog },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-gradient-to-r from-background via-background to-primary/5 backdrop-blur-md supports-[backdrop-filter]:bg-background/80 shadow-sm">
      <div className="container mx-auto max-w-7xl flex h-16 items-center px-4">
        <div className="mr-8 flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <span className="font-bold text-lg bg-gradient-to-r from-foreground to-primary bg-clip-text text-transparent">Paperless GraphRAG</span>
        </div>

        <nav className="flex items-center space-x-1">
          {navItems.map((item) => {
            // Handle trailing slashes from Next.js config
            const normalizedPathname = pathname?.replace(/\/$/, '') || '/';
            const normalizedHref = item.href.replace(/\/$/, '') || '/';
            const isActive = normalizedPathname === normalizedHref ||
              (item.href === '/' && pathname === '/');
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer',
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-md shadow-primary/25'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center space-x-4">
          {/* Future: Add theme toggle, user menu, etc. */}
        </div>
      </div>
    </header>
  );
}
