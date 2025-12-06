'use client';

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
} from '@/components/ui/sidebar';
import { useAuth } from '@/lib/auth/context';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  Users,
  BookOpen,
  GraduationCap,
  Settings,
  Calendar,
  BarChart3,
  FileSpreadsheet,
  Map,
  Clock,
  Mail,
  LogOut,
  Shield,
  UserCog,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export function AppSidebar() {
  const { currentRole, logout, user } = useAuth();
  const pathname = usePathname();

  const adminMenuItems = [
    { title: 'Dashboard', url: '/admin', icon: Home },
    { title: 'Majors', url: '/admin/majors', icon: GraduationCap },
    { title: 'Users', url: '/admin/users', icon: UserCog },
    { title: 'All Courses', url: '/admin/courses', icon: BookOpen },
    { title: 'All Students', url: '/admin/students', icon: Users },
    { title: 'Settings', url: '/admin/settings', icon: Settings },
  ];

  const advisorMenuItems = [
    { title: 'Dashboard', url: '/advisor', icon: Home },
    { title: 'Students', url: '/advisor/students', icon: Users },
    { title: 'Advising Session', url: '/advisor/session', icon: Calendar },
    { title: 'Course Eligibility', url: '/advisor/eligibility', icon: BookOpen },
    { title: 'Degree Map', url: '/advisor/degree-map', icon: Map },
    { title: 'Projections', url: '/advisor/projections', icon: Clock },
    { title: 'Course Planner', url: '/advisor/planner', icon: BarChart3 },
    { title: 'Courses', url: '/advisor/courses', icon: FileSpreadsheet },
    { title: 'Email', url: '/advisor/email', icon: Mail },
  ];

  const studentMenuItems = [
    { title: 'My Dashboard', url: '/student', icon: Home },
    { title: 'My Progress', url: '/student/progress', icon: BarChart3 },
    { title: 'Advised Courses', url: '/student/advised', icon: BookOpen },
    { title: 'Degree Plan', url: '/student/degree-plan', icon: Map },
    { title: 'Remaining Courses', url: '/student/remaining', icon: Clock },
  ];

  const menuItems = currentRole === 'admin' 
    ? adminMenuItems 
    : currentRole === 'advisor' 
      ? advisorMenuItems 
      : studentMenuItems;

  const roleColors = {
    admin: 'bg-red-500',
    advisor: 'bg-blue-500',
    student: 'bg-green-500',
  };

  const roleLabels = {
    admin: 'Administrator',
    advisor: 'Advisor',
    student: 'Student',
  };

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-4 py-4">
        <div className="flex items-center gap-2">
          <GraduationCap className="h-8 w-8 text-primary" />
          <div>
            <h2 className="font-bold text-lg">Advising Dashboard</h2>
            <Badge className={`${roleColors[currentRole]} text-white text-xs`}>
              {roleLabels[currentRole]}
            </Badge>
          </div>
        </div>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={pathname === item.url}>
                    <Link href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {currentRole === 'admin' && (
          <SidebarGroup>
            <SidebarGroupLabel>Quick Access</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild>
                    <Link href="/advisor">
                      <Shield className="h-4 w-4" />
                      <span>View as Advisor</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild>
                    <Link href="/student">
                      <Users className="h-4 w-4" />
                      <span>View as Student</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t p-4">
        {user && (
          <div className="flex flex-col gap-2">
            <div className="text-sm">
              <p className="font-medium">{user.name}</p>
              <p className="text-muted-foreground text-xs">{user.email}</p>
            </div>
            <Button variant="outline" size="sm" onClick={logout} className="w-full">
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
