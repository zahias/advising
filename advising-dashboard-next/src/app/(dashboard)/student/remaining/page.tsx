'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/auth/context';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  BookOpen,
  Search,
  Clock,
  AlertCircle,
  CheckCircle,
  GraduationCap,
} from 'lucide-react';

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  type: string;
  prerequisites?: string;
  concurrent?: string;
  standing?: string;
}

interface Student {
  id: string;
  studentId: string;
  majorId: string;
  name: string;
  email?: string;
  credits: number;
  creditsCompleted: number;
  standing: string;
  courseStatuses?: Record<string, string>;
}

export default function StudentRemainingPage() {
  const { user, currentStudentId } = useAuth();
  const [student, setStudent] = useState<Student | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [user, currentStudentId]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const studentsRes = await fetch('/api/students');
      if (!studentsRes.ok) throw new Error('Failed to fetch students');
      
      const studentsData = await studentsRes.json();
      
      let matchedStudent = null;
      
      if (currentStudentId) {
        matchedStudent = studentsData.find((s: Student) => s.id === currentStudentId);
      }
      
      if (!matchedStudent && user?.email) {
        matchedStudent = studentsData.find((s: Student) => 
          s.email?.toLowerCase() === user.email?.toLowerCase()
        );
      }
      
      if (!matchedStudent) {
        setError('No student record found for your account. Please contact your advisor.');
        setLoading(false);
        return;
      }
      
      setStudent(matchedStudent);
      
      const coursesRes = await fetch(`/api/courses?majorId=${matchedStudent.majorId || ''}`);
      if (coursesRes.ok) {
        const coursesData = await coursesRes.json();
        setCourses(coursesData);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      setError('Failed to load your course information. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto" />
          <p className="text-muted-foreground">Loading your remaining courses...</p>
        </div>
      </div>
    );
  }

  if (error || !student) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <AlertCircle className="h-16 w-16 text-red-500" />
        <h2 className="text-2xl font-bold">Unable to Load Data</h2>
        <p className="text-muted-foreground text-center max-w-md">
          {error || 'No student record found for your account.'}
        </p>
      </div>
    );
  }

  const courseStatuses = student.courseStatuses || {};

  const getCourseStatus = (courseCode: string) => {
    const status = courseStatuses[courseCode];
    if (!status || status === '' || status === 'nan') return 'remaining';
    if (['a', 'b', 'c', 'd', 'p', 's'].includes(status.toLowerCase())) return 'completed';
    if (['r', 'cr'].includes(status.toLowerCase())) return 'registered';
    return 'remaining';
  };

  const remainingCourses = courses.filter(c => getCourseStatus(c.code) === 'remaining');
  const courseTypes = [...new Set(remainingCourses.map(c => c.type || 'General'))];

  const filteredCourses = remainingCourses.filter(course => {
    const matchesSearch = 
      course.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      course.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'all' || course.type === filterType;
    return matchesSearch && matchesType;
  });

  const totalRemainingCredits = remainingCourses.reduce((sum, c) => sum + c.credits, 0);

  const coursesByType = courseTypes.reduce((acc, type) => {
    acc[type] = filteredCourses.filter(c => (c.type || 'General') === type);
    return acc;
  }, {} as Record<string, Course[]>);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Remaining Courses</h1>
        <p className="text-muted-foreground">Courses you still need to complete for graduation</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Remaining Courses</p>
                <p className="text-2xl font-bold">{remainingCourses.length}</p>
              </div>
              <BookOpen className="h-8 w-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Remaining Credits</p>
                <p className="text-2xl font-bold">{totalRemainingCredits}</p>
              </div>
              <Clock className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Est. Semesters</p>
                <p className="text-2xl font-bold">{Math.ceil(remainingCourses.length / 5)}</p>
              </div>
              <GraduationCap className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Courses to Complete</CardTitle>
              <CardDescription>{filteredCourses.length} courses remaining</CardDescription>
            </div>
            <div className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search courses..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  {courseTypes.map(type => (
                    <SelectItem key={type} value={type}>{type}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {courseTypes.map(type => (
              coursesByType[type]?.length > 0 && (
                <div key={type}>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    {type}
                    <Badge variant="secondary">{coursesByType[type].length}</Badge>
                  </h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    {coursesByType[type].map(course => (
                      <div 
                        key={course.id}
                        className="p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-medium">{course.code}</p>
                            <p className="text-sm text-muted-foreground">{course.name}</p>
                          </div>
                          <Badge variant="outline">{course.credits} cr</Badge>
                        </div>
                        {(course.prerequisites || course.standing) && (
                          <div className="mt-2 space-y-1">
                            {course.prerequisites && (
                              <p className="text-xs text-muted-foreground">
                                <span className="font-medium">Prerequisites:</span> {course.prerequisites}
                              </p>
                            )}
                            {course.standing && (
                              <p className="text-xs text-muted-foreground">
                                <span className="font-medium">Standing:</span> {course.standing}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Legend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-orange-100 border border-orange-300" />
              <span className="text-sm">Remaining (not yet taken)</span>
            </div>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-yellow-500" />
              <span className="text-sm">Has prerequisites</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
