'use client';

import { SidebarTrigger } from '@/components/ui/sidebar';
import { RoleSwitcher } from './role-switcher';
import { MajorSelector } from './major-selector';
import { useAuth } from '@/lib/auth/context';
import { Separator } from '@/components/ui/separator';

export function Header() {
  const { user, currentRole } = useAuth();

  return (
    <header className="flex h-16 shrink-0 items-center gap-4 border-b px-4 bg-background">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="h-6" />
      
      <div className="flex-1" />
      
      {user && (
        <div className="flex items-center gap-4">
          {currentRole !== 'student' && <MajorSelector />}
          <RoleSwitcher />
        </div>
      )}
    </header>
  );
}
