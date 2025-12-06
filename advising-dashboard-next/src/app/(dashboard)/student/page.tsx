'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth/context';
import { 
  BookOpen,
  Clock,
  CheckCircle,
  TrendingUp,
  Calendar,
  GraduationCap,
  ArrowRight
} from 'lucide-react';
import Link from 'next/link';

export default function StudentDashboard() {
  const { user } = useAuth();

  const progressStats = {
    completed: 78,
    registered: 12,
    remaining: 30,
    total: 120,
  };

  const advisedCourses = [
    { code: 'PBHL 301', name: 'Epidemiology', credits: 3, type: 'Required' },
    { code: 'PBHL 305', name: 'Biostatistics', credits: 3, type: 'Required' },
    { code: 'PBHL 320', name: 'Health Policy', credits: 3, type: 'Required' },
  ];

  const upcomingDeadlines = [
    { title: 'Spring 2026 Registration Opens', date: 'Dec 15, 2025' },
    { title: 'Advising Appointment', date: 'Dec 10, 2025' },
    { title: 'Final Exams Begin', date: 'Dec 18, 2025' },
  ];

  const completionPercent = ((progressStats.completed + progressStats.registered) / progressStats.total) * 100;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">My Dashboard</h1>
        <p className="text-muted-foreground">Welcome back, {user?.name}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Degree Progress
            </CardTitle>
            <CardDescription>Your progress toward graduation</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Overall Completion</span>
                <span className="font-medium">{completionPercent.toFixed(0)}%</span>
              </div>
              <div className="h-4 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full flex">
                  <div 
                    className="bg-green-500"
                    style={{ width: `${(progressStats.completed / progressStats.total) * 100}%` }}
                  />
                  <div 
                    className="bg-blue-500"
                    style={{ width: `${(progressStats.registered / progressStats.total) * 100}%` }}
                  />
                </div>
              </div>
              <div className="flex gap-4 text-xs">
                <span className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-green-500 rounded" />
                  Completed ({progressStats.completed} credits)
                </span>
                <span className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-blue-500 rounded" />
                  Registered ({progressStats.registered} credits)
                </span>
                <span className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-gray-200 rounded" />
                  Remaining ({progressStats.remaining} credits)
                </span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600">{progressStats.completed}</div>
                <div className="text-sm text-muted-foreground">Credits Completed</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-600">{progressStats.registered}</div>
                <div className="text-sm text-muted-foreground">Credits Registered</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-gray-600">{progressStats.remaining}</div>
                <div className="text-sm text-muted-foreground">Credits Remaining</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Upcoming
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {upcomingDeadlines.map((deadline, i) => (
                <div key={i} className="flex items-start gap-3 pb-3 border-b last:border-0">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <Clock className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{deadline.title}</p>
                    <p className="text-xs text-muted-foreground">{deadline.date}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                Advised Courses
              </CardTitle>
              <CardDescription>Courses your advisor recommended this semester</CardDescription>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link href="/student/advised">
                View All
                <ArrowRight className="h-4 w-4 ml-2" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {advisedCourses.map((course) => (
                <div 
                  key={course.code}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div>
                    <p className="font-medium">{course.code}</p>
                    <p className="text-sm text-muted-foreground">{course.name}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{course.credits} cr</Badge>
                    <Badge>{course.type}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GraduationCap className="h-5 w-5" />
              Graduation Outlook
            </CardTitle>
            <CardDescription>Estimated completion timeline</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-center py-6">
              <div className="text-5xl font-bold text-primary">Spring 2027</div>
              <div className="text-muted-foreground mt-2">Estimated Graduation</div>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-4 border-t">
              <div className="text-center">
                <div className="text-2xl font-bold">3</div>
                <div className="text-sm text-muted-foreground">Semesters Left</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">10</div>
                <div className="text-sm text-muted-foreground">Courses Left</div>
              </div>
            </div>
            <Button className="w-full" asChild>
              <Link href="/student/degree-plan">
                View Degree Plan
                <ArrowRight className="h-4 w-4 ml-2" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
