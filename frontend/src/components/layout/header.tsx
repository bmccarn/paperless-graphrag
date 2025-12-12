'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  MessageSquare,
  Network,
  Cog,
  FileText,
  Wrench,
  ScrollText,
  Menu,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/chat', label: 'Chat', icon: MessageSquare },
  { href: '/graph', label: 'Graph', icon: Network },
  { href: '/operations', label: 'Operations', icon: Wrench },
  { href: '/logs', label: 'Logs', icon: ScrollText },
  { href: '/settings', label: 'Settings', icon: Cog },
];

export function Header() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMobileMenuOpen(false);
      }
    }

    if (mobileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [mobileMenuOpen]);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-gradient-to-r from-background via-background to-primary/5 backdrop-blur-md supports-[backdrop-filter]:bg-background/80 shadow-sm">
      <div className="container mx-auto max-w-7xl flex h-14 md:h-16 items-center px-4">
        <div className="mr-4 md:mr-8 flex items-center space-x-2 md:space-x-3">
          <div className="p-1.5 md:p-2 rounded-lg bg-primary/10">
            <FileText className="h-4 w-4 md:h-5 md:w-5 text-primary" />
          </div>
          <span className="font-bold text-base md:text-lg bg-gradient-to-r from-foreground to-primary bg-clip-text text-transparent">
            <span className="hidden sm:inline">Paperless GraphRAG</span>
            <span className="sm:hidden">GraphRAG</span>
          </span>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-1">
          {navItems.map((item) => {
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
          {/* Mobile Menu Button */}
          <button
            className="flex md:hidden items-center justify-center p-2 rounded-lg hover:bg-secondary transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Menu */}
      {mobileMenuOpen && (
        <div
          ref={menuRef}
          className="md:hidden border-t bg-background/95 backdrop-blur-md"
        >
          <nav className="container mx-auto max-w-7xl px-4 py-2 flex flex-col space-y-1">
            {navItems.map((item) => {
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
                    'flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-primary text-primary-foreground shadow-md shadow-primary/25'
                      : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
                  )}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      )}
    </header>
  );
}
