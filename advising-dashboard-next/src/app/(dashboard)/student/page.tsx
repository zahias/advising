'use client';

import { useState, useEffect } from 'react';
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
  ArrowRight,
  Loader2
} from 'lucide-react';
import Link from 'next/link';

interface Student {
  id: string;
  studentId: string;
  name: string;
  email?: string;
  standing?: string;
  creditsCompleted: number;
  creditsRegistered: number;
  creditsRemaining: number;
  courseStatuses: Record<string, string>;
}

interface Session {
  advisedCourses: string[];
  optionalCourses: string[];
  repeatCourses: string[];
  note?: string;
}

interface Course {
  code: string;
  name: string;
  credits: number;
  type: string;
}

export default function StudentDashboard() {
  const { user, currentMajor, currentStudentId, setCurrentStudentId } = useAuth();
  const [loading, setLoading] = useState(true);
  const [student, setStudent] = useState<Student | null>(null);
  const [advisedCourses, setAdvisedCourses] = useState<Course[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const majorsRes = await fetch('/api/majors');
        const majorsData = await majorsRes.json();
        const major = majorsData.find((m: { code: string }) => m.code === currentMajor);
        
        if (!major) {
          setLoading(false);
          return;
        }

        const [studentsRes, coursesRes] = await Promise.all([
          fetch(`/api/students?majorId=${major.id}`),
          fetch(`/api/courses?majorId=${major.id}`)
        ]);

        const studentsData = await studentsRes.json();
        const coursesData = await coursesRes.json();

        setCourses(coursesData);

        if (studentsData.length > 0) {
          let matchedStudent = null;
          
          if (currentStudentId) {
            matchedStudent = studentsData.find((s: Student) => s.id === currentStudentId);
          }
          
          if (!matchedStudent && user?.email) {
            matchedStudent = studentsData.find((s: Student) => 
              s.email?.toLowerCase() === user.email.toLowerCase()
            );
          }
          
          if (matchedStudent && matchedStudent.id !== currentStudentId) {
            setCurrentStudentId(matchedStudent.id);
          }
          
          setStudent(matchedStudent);

          const periodsRes = await fetch(`/api/periods?majorId=${major.id}&activeOnly=true`);
          const periodsData = await periodsRes.json();
          
          if (periodsData.length > 0) {
            const sessionRes = await fetch(`/api/sessions?studentId=${matchedStudent.id}&periodId=${periodsData[0].id}`);
            const sessionData = await sessionRes.json();
            
            if (sessionData.length > 0) {
              const session = sessionData[0];
              const allAdvised = [
                ...(session.advisedCourses || []),
                ...(session.optionalCourses || []),
                ...(session.repeatCourses || [])
              ];
              
              const advisedCourseDetails = allAdvised.map(code => {
                const course = coursesData.find((c: Course) => c.code === code);
                return course || { code, name: 'Unknown', credits: 0, type: 'unknown' };
              });
              
              setAdvisedCourses(advisedCourseDetails);
            }
          }
        }
      } catch (err) {
        console.error('Failed to fetch data:', err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [currentMajor]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!student) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="text-center">
          <h2 className="text-2xl font-bold">Student Record Not Found</h2>
          <p className="text-muted-foreground mt-2">
            We couldn&apos;t find your student record. Please contact your advisor for assistance.
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            Email: {user?.email}
          </p>
        </div>
      </div>
    );
  }

  const progressStats = {
    completed: student.creditsCompleted,
    registered: student.creditsRegistered,
    remaining: student.creditsRemaining,
    total: student.creditsCompleted + student.creditsRegistered + student.creditsRemaining,
  };

  const upcomingDeadlines = [
    { title: 'Spring 2026 Registration Opens', date: 'Dec 15, 2025' },
    { title: 'Advising Appointment', date: 'Dec 10, 2025' },
    { title: 'Final Exams Begin', date: 'Dec 18, 2025' },
  ];

  const completionPercent = progressStats.total > 0 
    ? ((progressStats.completed + progressStats.registered) / progressStats.total) * 100 
    : 0;

  const completedCourses = student 
    ? Object.entries(student.courseStatuses).filter(([_, status]) => status === 'c').length
    : 0;
  const totalCourses = courses.length;
  const remainingCourses = totalCourses - completedCourses;
  const semestersLeft = Math.ceil(remainingCourses / 5);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">My Dashboard</h1>
        <p className="text-muted-foreground">Welcome back, {student?.name || user?.name}</p>
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
            {advisedCourses.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No advised courses yet. Contact your advisor for recommendations.
              </div>
            ) : (
              <div className="space-y-3">
                {advisedCourses.slice(0, 5).map((course) => (
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
            )}
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
              <div className="text-5xl font-bold text-primary">
                {semestersLeft <= 2 ? 'Spring' : semestersLeft <= 4 ? 'Fall' : 'Spring'} {2025 + Math.ceil(semestersLeft / 2)}
              </div>
              <div className="text-muted-foreground mt-2">Estimated Graduation</div>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-4 border-t">
              <div className="text-center">
                <div className="text-2xl font-bold">{semestersLeft}</div>
                <div className="text-sm text-muted-foreground">Semesters Left</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{remainingCourses}</div>
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
