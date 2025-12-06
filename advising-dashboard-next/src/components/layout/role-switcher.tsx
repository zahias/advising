'use client';

import { useAuth, UserRole } from '@/lib/auth/context';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Shield, Users, GraduationCap } from 'lucide-react';

const roles: { value: UserRole; label: string; icon: React.ElementType; color: string }[] = [
  { value: 'admin', label: 'Administrator', icon: Shield, color: 'bg-red-500' },
  { value: 'advisor', label: 'Advisor', icon: Users, color: 'bg-blue-500' },
  { value: 'student', label: 'Student', icon: GraduationCap, color: 'bg-green-500' },
];

export function RoleSwitcher() {
  const { currentRole, setCurrentRole, user } = useAuth();

  if (!user || user.role !== 'admin') {
    return null;
  }

  const currentRoleData = roles.find(r => r.value === currentRole);

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">Viewing as:</span>
      <Select value={currentRole} onValueChange={(value) => setCurrentRole(value as UserRole)}>
        <SelectTrigger className="w-[180px]">
          <SelectValue>
            {currentRoleData && (
              <div className="flex items-center gap-2">
                <currentRoleData.icon className="h-4 w-4" />
                <span>{currentRoleData.label}</span>
              </div>
            )}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {roles.map((role) => (
            <SelectItem key={role.value} value={role.value}>
              <div className="flex items-center gap-2">
                <role.icon className="h-4 w-4" />
                <span>{role.label}</span>
                <Badge className={`${role.color} text-white text-xs ml-2`}>
                  {role.value}
                </Badge>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
