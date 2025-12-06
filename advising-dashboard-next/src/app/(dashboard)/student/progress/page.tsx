'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth/context';
import { 
  CheckCircle,
  Clock,
  XCircle,
  BookOpen
} from 'lucide-react';

const sampleCourseProgress = [
  { code: 'PBHL 101', name: 'Introduction to Public Health', credits: 3, status: 'completed', grade: 'A', semester: 'Fall 2023' },
  { code: 'PBHL 201', name: 'Health Behavior', credits: 3, status: 'completed', grade: 'B+', semester: 'Spring 2024' },
  { code: 'PBHL 202', name: 'Health Communication', credits: 3, status: 'completed', grade: 'A-', semester: 'Spring 2024' },
  { code: 'PBHL 301', name: 'Epidemiology', credits: 3, status: 'registered', grade: null, semester: 'Fall 2024' },
  { code: 'PBHL 305', name: 'Biostatistics', credits: 3, status: 'registered', grade: null, semester: 'Fall 2024' },
  { code: 'PBHL 320', name: 'Health Policy', credits: 3, status: 'remaining', grade: null, semester: null },
  { code: 'PBHL 350', name: 'Global Health', credits: 3, status: 'remaining', grade: null, semester: null },
  { code: 'PBHL 401', name: 'Capstone I', credits: 3, status: 'remaining', grade: null, semester: null },
  { code: 'PBHL 402', name: 'Capstone II', credits: 3, status: 'remaining', grade: null, semester: null },
];

export default function StudentProgressPage() {
  const { user } = useAuth();

  const completedCourses = sampleCourseProgress.filter(c => c.status === 'completed');
  const registeredCourses = sampleCourseProgress.filter(c => c.status === 'registered');
  const remainingCourses = sampleCourseProgress.filter(c => c.status === 'remaining');

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'registered': return <Clock className="h-5 w-5 text-blue-500" />;
      case 'remaining': return <XCircle className="h-5 w-5 text-gray-400" />;
      default: return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed': return <Badge className="bg-green-100 text-green-800">Completed</Badge>;
      case 'registered': return <Badge className="bg-blue-100 text-blue-800">Registered</Badge>;
      case 'remaining': return <Badge variant="outline">Remaining</Badge>;
      default: return null;
    }
  };

  const CourseList = ({ courses, title, icon: Icon }: { courses: typeof sampleCourseProgress; title: string; icon: React.ElementType }) => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
        <CardDescription>
          {courses.length} courses • {courses.reduce((acc, c) => acc + c.credits, 0)} credits
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {courses.map(course => (
            <div 
              key={course.code}
              className="flex items-center justify-between p-3 rounded-lg border"
            >
              <div className="flex items-center gap-3">
                {getStatusIcon(course.status)}
                <div>
                  <p className="font-medium">{course.code}</p>
                  <p className="text-sm text-muted-foreground">{course.name}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="outline">{course.credits} cr</Badge>
                {course.grade && (
                  <Badge className="bg-primary/10 text-primary">{course.grade}</Badge>
                )}
                {course.semester && (
                  <span className="text-sm text-muted-foreground">{course.semester}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">My Progress</h1>
        <p className="text-muted-foreground">Track your academic journey</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Completed</p>
                <p className="text-2xl font-bold">{completedCourses.length} courses</p>
                <p className="text-sm text-muted-foreground">
                  {completedCourses.reduce((acc, c) => acc + c.credits, 0)} credits
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Clock className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Registered</p>
                <p className="text-2xl font-bold">{registeredCourses.length} courses</p>
                <p className="text-sm text-muted-foreground">
                  {registeredCourses.reduce((acc, c) => acc + c.credits, 0)} credits
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gray-100 rounded-lg">
                <BookOpen className="h-6 w-6 text-gray-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Remaining</p>
                <p className="text-2xl font-bold">{remainingCourses.length} courses</p>
                <p className="text-sm text-muted-foreground">
                  {remainingCourses.reduce((acc, c) => acc + c.credits, 0)} credits
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-6">
        <CourseList courses={completedCourses} title="Completed Courses" icon={CheckCircle} />
        <CourseList courses={registeredCourses} title="Currently Registered" icon={Clock} />
        <CourseList courses={remainingCourses} title="Remaining Courses" icon={BookOpen} />
      </div>
    </div>
  );
}
