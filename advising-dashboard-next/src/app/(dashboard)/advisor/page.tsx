'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth/context';
import { 
  Users, 
  Calendar,
  BookOpen,
  Clock,
  CheckCircle,
  AlertCircle,
  ArrowRight,
  TrendingUp
} from 'lucide-react';
import Link from 'next/link';

export default function AdvisorDashboard() {
  const { user, currentMajor } = useAuth();

  const stats = [
    { label: 'Total Students', value: '156', icon: Users, color: 'text-blue-600', bg: 'bg-blue-100' },
    { label: 'Advised This Period', value: '142', icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100' },
    { label: 'Pending Advising', value: '14', icon: Clock, color: 'text-orange-600', bg: 'bg-orange-100' },
    { label: 'Courses Offered', value: '24', icon: BookOpen, color: 'text-purple-600', bg: 'bg-purple-100' },
  ];

  const recentStudents = [
    { id: '12345', name: 'John Smith', credits: 45, status: 'advised', lastAdvised: '2 days ago' },
    { id: '12346', name: 'Sarah Johnson', credits: 78, status: 'pending', lastAdvised: 'Never' },
    { id: '12347', name: 'Mike Williams', credits: 92, status: 'advised', lastAdvised: '1 week ago' },
    { id: '12348', name: 'Emily Brown', credits: 34, status: 'pending', lastAdvised: 'Never' },
    { id: '12349', name: 'David Lee', credits: 67, status: 'advised', lastAdvised: '3 days ago' },
  ];

  const upcomingGraduates = [
    { name: 'Mike Williams', credits: 92, remaining: 8, courses: 3 },
    { name: 'Lisa Chen', credits: 88, remaining: 12, courses: 4 },
    { name: 'James Taylor', credits: 85, remaining: 15, courses: 5 },
  ];

  if (!currentMajor) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="text-6xl">🎓</div>
        <h2 className="text-2xl font-bold">Select a Major</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Please select a major from the dropdown in the header to view the advisor dashboard.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Advisor Dashboard</h1>
          <p className="text-muted-foreground">
            {currentMajor} • Welcome back, {user?.name}
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link href="/advisor/session">
              <Calendar className="h-4 w-4 mr-2" />
              New Session
            </Link>
          </Button>
        </div>
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

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Students</CardTitle>
              <CardDescription>Students in your advising queue</CardDescription>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link href="/advisor/students">
                View All
                <ArrowRight className="h-4 w-4 ml-2" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentStudents.map((student) => (
                <div 
                  key={student.id} 
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <span className="text-sm font-medium text-primary">
                        {student.name.split(' ').map(n => n[0]).join('')}
                      </span>
                    </div>
                    <div>
                      <p className="font-medium">{student.name}</p>
                      <p className="text-sm text-muted-foreground">
                        ID: {student.id} • {student.credits} credits
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={student.status === 'advised' ? 'default' : 'secondary'}>
                      {student.status === 'advised' ? (
                        <><CheckCircle className="h-3 w-3 mr-1" /> Advised</>
                      ) : (
                        <><Clock className="h-3 w-3 mr-1" /> Pending</>
                      )}
                    </Badge>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/advisor/session?student=${student.id}`}>
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Graduating Soon
            </CardTitle>
            <CardDescription>Students close to completion</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {upcomingGraduates.map((student, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-between">
                    <span className="font-medium text-sm">{student.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {student.remaining} credits left
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-green-500 rounded-full"
                      style={{ width: `${(student.credits / (student.credits + student.remaining)) * 100}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {student.courses} courses remaining
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
