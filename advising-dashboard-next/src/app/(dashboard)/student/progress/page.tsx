'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth/context';
import { 
  CheckCircle,
  Clock,
  XCircle,
  BookOpen,
  AlertCircle,
  Loader2
} from 'lucide-react';

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

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  type: string;
  semester?: number;
  prerequisites: string[];
}

export default function StudentProgressPage() {
  const { user, currentMajor, currentStudentId, setCurrentStudentId } = useAuth();
  const [loading, setLoading] = useState(true);
  const [student, setStudent] = useState<Student | null>(null);
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
        }
      } catch (err) {
        console.error('Failed to fetch data:', err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [currentMajor]);

  const getStatusInfo = (code: string) => {
    if (!student) return { status: 'remaining', label: 'Not Started', icon: AlertCircle, color: 'gray' };
    
    const status = student.courseStatuses[code];
    switch (status?.toLowerCase()) {
      case 'c':
        return { status: 'completed', label: 'Completed', icon: CheckCircle, color: 'green' };
      case 'r':
      case 'cr':
        return { status: 'registered', label: 'Registered', icon: Clock, color: 'blue' };
      case 'f':
        return { status: 'failed', label: 'Failed', icon: XCircle, color: 'red' };
      case 'nc':
        return { status: 'not-completed', label: 'Not Completed', icon: XCircle, color: 'orange' };
      default:
        return { status: 'remaining', label: 'Remaining', icon: AlertCircle, color: 'gray' };
    }
  };

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

  const completedCourses = courses.filter(c => getStatusInfo(c.code).status === 'completed');
  const registeredCourses = courses.filter(c => getStatusInfo(c.code).status === 'registered');
  const remainingCourses = courses.filter(c => 
    getStatusInfo(c.code).status === 'remaining' || 
    getStatusInfo(c.code).status === 'failed' ||
    getStatusInfo(c.code).status === 'not-completed'
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'registered': return <Clock className="h-5 w-5 text-blue-500" />;
      case 'failed': return <XCircle className="h-5 w-5 text-red-500" />;
      default: return <AlertCircle className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed': return <Badge className="bg-green-100 text-green-800">Completed</Badge>;
      case 'registered': return <Badge className="bg-blue-100 text-blue-800">Registered</Badge>;
      case 'failed': return <Badge className="bg-red-100 text-red-800">Failed</Badge>;
      default: return <Badge variant="outline">Remaining</Badge>;
    }
  };

  const CourseList = ({ courses: courseList, title, icon: Icon }: { courses: Course[]; title: string; icon: React.ElementType }) => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
        <CardDescription>
          {courseList.length} courses - {courseList.reduce((acc, c) => acc + c.credits, 0)} credits
        </CardDescription>
      </CardHeader>
      <CardContent>
        {courseList.length === 0 ? (
          <p className="text-center py-4 text-muted-foreground">No courses in this category</p>
        ) : (
          <div className="space-y-3">
            {courseList.map(course => {
              const statusInfo = getStatusInfo(course.code);
              return (
                <div 
                  key={course.code}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    {getStatusIcon(statusInfo.status)}
                    <div>
                      <p className="font-medium">{course.code}</p>
                      <p className="text-sm text-muted-foreground">{course.name}</p>
                      {course.prerequisites.length > 0 && (
                        <p className="text-xs text-muted-foreground">
                          Prereqs: {course.prerequisites.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="outline">{course.credits} cr</Badge>
                    <Badge variant="outline">{course.type}</Badge>
                    {getStatusBadge(statusInfo.status)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">My Progress</h1>
        <p className="text-muted-foreground">
          {student?.name} - {student?.standing} - {currentMajor}
        </p>
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
