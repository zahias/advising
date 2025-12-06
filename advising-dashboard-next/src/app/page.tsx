'use client';

import { useAuth, UserRole } from '@/lib/auth/context';
import { useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { GraduationCap, Shield, Users, BookOpen } from 'lucide-react';

export default function LoginPage() {
  const { login, user } = useAuth();
  const router = useRouter();
  const [name, setName] = useState('');
  const [selectedRole, setSelectedRole] = useState<UserRole>('admin');

  useEffect(() => {
    if (user) {
      const redirectPath = user.role === 'admin' ? '/admin' : user.role === 'advisor' ? '/advisor' : '/student';
      router.push(redirectPath);
    }
  }, [user, router]);

  if (user) {
    return null;
  }

  const handleLogin = () => {
    if (name.trim()) {
      login(selectedRole, name.trim());
      const redirectPath = selectedRole === 'admin' ? '/admin' : selectedRole === 'advisor' ? '/advisor' : '/student';
      router.push(redirectPath);
    }
  };

  const roles = [
    {
      value: 'admin' as UserRole,
      label: 'Administrator',
      description: 'Full access to all majors, users, and settings',
      icon: Shield,
      color: 'border-red-500 bg-red-50 hover:bg-red-100',
      selectedColor: 'border-red-500 bg-red-100 ring-2 ring-red-500',
    },
    {
      value: 'advisor' as UserRole,
      label: 'Advisor',
      description: 'Manage students and advising sessions for assigned majors',
      icon: Users,
      color: 'border-blue-500 bg-blue-50 hover:bg-blue-100',
      selectedColor: 'border-blue-500 bg-blue-100 ring-2 ring-blue-500',
    },
    {
      value: 'student' as UserRole,
      label: 'Student',
      description: 'View your progress, advised courses, and degree plan',
      icon: BookOpen,
      color: 'border-green-500 bg-green-50 hover:bg-green-100',
      selectedColor: 'border-green-500 bg-green-100 ring-2 ring-green-500',
    },
  ];

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200 p-4">
      <Card className="w-full max-w-2xl shadow-xl">
        <CardHeader className="text-center space-y-4 pb-8">
          <div className="flex justify-center">
            <div className="p-4 bg-primary/10 rounded-full">
              <GraduationCap className="h-12 w-12 text-primary" />
            </div>
          </div>
          <CardTitle className="text-3xl font-bold">Advising Dashboard</CardTitle>
          <CardDescription className="text-lg">
            Phoenix University Academic Advising System
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-base">Your Name</Label>
            <Input
              id="name"
              placeholder="Enter your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-12 text-lg"
            />
          </div>

          <div className="space-y-3">
            <Label className="text-base">Select Your Role</Label>
            <div className="grid gap-3">
              {roles.map((role) => (
                <button
                  key={role.value}
                  onClick={() => setSelectedRole(role.value)}
                  className={`flex items-center gap-4 p-4 rounded-lg border-2 transition-all text-left ${
                    selectedRole === role.value ? role.selectedColor : role.color
                  }`}
                >
                  <role.icon className="h-8 w-8 shrink-0" />
                  <div>
                    <div className="font-semibold text-lg">{role.label}</div>
                    <div className="text-sm text-muted-foreground">{role.description}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <Button
            onClick={handleLogin}
            disabled={!name.trim()}
            className="w-full h-12 text-lg font-semibold"
            size="lg"
          >
            Enter Dashboard
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Demo Mode: Select any role to explore the dashboard.
            <br />
            In production, Microsoft 365 login will be enabled.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
