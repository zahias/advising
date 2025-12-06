'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/auth/context';
import { 
  Users, 
  GraduationCap, 
  BookOpen, 
  Calendar,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

export default function AdminDashboard() {
  const { user } = useAuth();

  const stats = [
    { label: 'Total Majors', value: '4', icon: GraduationCap, color: 'text-purple-600', bg: 'bg-purple-100' },
    { label: 'Active Advisors', value: '12', icon: Users, color: 'text-blue-600', bg: 'bg-blue-100' },
    { label: 'Total Students', value: '847', icon: Users, color: 'text-green-600', bg: 'bg-green-100' },
    { label: 'Total Courses', value: '156', icon: BookOpen, color: 'text-orange-600', bg: 'bg-orange-100' },
  ];

  const recentActivity = [
    { action: 'New advising session created', user: 'Dr. Smith', time: '5 min ago', major: 'PBHL' },
    { action: 'Student imported from Excel', user: 'Dr. Johnson', time: '15 min ago', major: 'SPTH-New' },
    { action: 'Course offerings updated', user: 'Admin', time: '1 hour ago', major: 'NURS' },
    { action: 'Advising period started', user: 'Dr. Williams', time: '2 hours ago', major: 'PBHL' },
  ];

  const majorStats = [
    { code: 'PBHL', name: 'Public Health', students: 234, advised: 189, pending: 45 },
    { code: 'SPTH-New', name: 'Speech Therapy (New)', students: 156, advised: 142, pending: 14 },
    { code: 'SPTH-Old', name: 'Speech Therapy (Old)', students: 89, advised: 85, pending: 4 },
    { code: 'NURS', name: 'Nursing', students: 368, advised: 298, pending: 70 },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        <p className="text-muted-foreground">Welcome back, {user?.name}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.label}
              </CardTitle>
              <div className={`p-2 rounded-lg ${stat.bg}`}>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Major Overview
            </CardTitle>
            <CardDescription>Advising progress across all majors</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {majorStats.map((major) => (
                <div key={major.code} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{major.code}</span>
                    <span className="text-muted-foreground">
                      {major.advised}/{major.students} advised
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${(major.advised / major.students) * 100}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <CheckCircle className="h-3 w-3 text-green-500" />
                      {major.advised} completed
                    </span>
                    <span className="flex items-center gap-1">
                      <AlertCircle className="h-3 w-3 text-orange-500" />
                      {major.pending} pending
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Recent Activity
            </CardTitle>
            <CardDescription>Latest actions across the system</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivity.map((activity, i) => (
                <div key={i} className="flex items-start gap-3 pb-3 border-b last:border-0">
                  <div className="p-2 bg-gray-100 rounded-lg">
                    <Calendar className="h-4 w-4 text-gray-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{activity.action}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{activity.user}</span>
                      <span>•</span>
                      <span>{activity.major}</span>
                      <span>•</span>
                      <span>{activity.time}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
