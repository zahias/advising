'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth/context';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  GraduationCap,
  Calendar,
  TrendingUp,
  Clock,
  CheckCircle,
} from 'lucide-react';

interface Student {
  id: string;
  studentId: string;
  name: string;
  credits: number;
  standing: string;
  courseStatuses?: Record<string, string>;
}

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
}

export default function AdvisorProjectionsPage() {
  const { currentMajor } = useAuth();
  const [students, setStudents] = useState<Student[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string>('');
  const [coursesPerSemester, setCoursesPerSemester] = useState<number>(5);

  useEffect(() => {
    fetchData();
  }, [currentMajor]);

  const fetchData = async () => {
    try {
      const [studentsRes, coursesRes] = await Promise.all([
        fetch(`/api/students${currentMajor ? `?major=${currentMajor}` : ''}`),
        fetch(`/api/courses${currentMajor ? `?major=${currentMajor}` : ''}`),
      ]);
      
      if (studentsRes.ok) setStudents(await studentsRes.json());
      if (coursesRes.ok) setCourses(await coursesRes.json());
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const student = students.find(s => s.id === selectedStudent);
  const courseStatuses = student?.courseStatuses || {};

  const completedCourses = Object.entries(courseStatuses).filter(([_, status]) => 
    ['a', 'b', 'c', 'd', 'p', 's'].includes((status || '').toLowerCase())
  ).length;

  const registeredCourses = Object.entries(courseStatuses).filter(([_, status]) => 
    ['r', 'cr'].includes((status || '').toLowerCase())
  ).length;

  const remainingCourses = courses.length - completedCourses - registeredCourses;
  const semestersRemaining = Math.ceil(remainingCourses / coursesPerSemester);

  const getSemesterName = (offset: number) => {
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();
    
    let semester = currentMonth < 5 ? 'Spring' : currentMonth < 8 ? 'Summer' : 'Fall';
    let year = currentYear;
    
    for (let i = 0; i < offset; i++) {
      if (semester === 'Spring') { semester = 'Summer'; }
      else if (semester === 'Summer') { semester = 'Fall'; }
      else { semester = 'Spring'; year++; }
    }
    
    return `${semester} ${year}`;
  };

  const projectedTimeline = Array.from({ length: Math.min(semestersRemaining, 8) }, (_, i) => ({
    semester: getSemesterName(i + 1),
    courses: Math.min(coursesPerSemester, remainingCourses - (i * coursesPerSemester)),
  })).filter(s => s.courses > 0);

  if (!currentMajor) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <GraduationCap className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-2xl font-bold">Select a Major</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Please select a major from the dropdown in the header to view graduation projections.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Graduation Projections</h1>
        <p className="text-muted-foreground">Estimate graduation timeline based on course load</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Projection Settings</CardTitle>
          <CardDescription>Configure student and course load</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Select Student</label>
              <Select value={selectedStudent} onValueChange={setSelectedStudent}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a student" />
                </SelectTrigger>
                <SelectContent>
                  {students.map(s => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name} ({s.studentId})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Courses Per Semester</label>
              <Select 
                value={coursesPerSemester.toString()} 
                onValueChange={(v) => setCoursesPerSemester(parseInt(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[3, 4, 5, 6, 7].map(n => (
                    <SelectItem key={n} value={n.toString()}>
                      {n} courses/semester
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {student && (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Courses</p>
                    <p className="text-2xl font-bold">{courses.length}</p>
                  </div>
                  <GraduationCap className="h-8 w-8 text-primary" />
                </div>
              </CardContent>
            </Card>
            <Card className="bg-green-50">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-green-700">Completed</p>
                    <p className="text-2xl font-bold text-green-800">{completedCourses}</p>
                  </div>
                  <CheckCircle className="h-8 w-8 text-green-500" />
                </div>
              </CardContent>
            </Card>
            <Card className="bg-blue-50">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-blue-700">Registered</p>
                    <p className="text-2xl font-bold text-blue-800">{registeredCourses}</p>
                  </div>
                  <Clock className="h-8 w-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>
            <Card className="bg-orange-50">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-orange-700">Remaining</p>
                    <p className="text-2xl font-bold text-orange-800">{remainingCourses}</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-orange-500" />
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Projected Timeline
              </CardTitle>
              <CardDescription>
                Estimated graduation: {getSemesterName(semestersRemaining)} ({semestersRemaining} semesters remaining)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {projectedTimeline.map((item, index) => (
                  <div key={index} className="flex items-center gap-4">
                    <div className="w-32 font-medium">{item.semester}</div>
                    <div className="flex-1">
                      <div className="h-8 bg-primary/20 rounded-lg overflow-hidden">
                        <div 
                          className="h-full bg-primary rounded-lg flex items-center justify-center text-white text-sm font-medium"
                          style={{ width: `${(item.courses / coursesPerSemester) * 100}%` }}
                        >
                          {item.courses} courses
                        </div>
                      </div>
                    </div>
                    {index === projectedTimeline.length - 1 && (
                      <Badge className="bg-green-500">Graduation</Badge>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Progress Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">Overall Progress</span>
                    <span className="text-sm text-muted-foreground">
                      {Math.round((completedCourses / courses.length) * 100)}%
                    </span>
                  </div>
                  <div className="h-4 bg-gray-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-green-500 rounded-full"
                      style={{ width: `${(completedCourses / courses.length) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2 pt-4">
                  <div className="p-4 bg-muted rounded-lg">
                    <p className="text-sm text-muted-foreground">Current Standing</p>
                    <p className="text-lg font-bold">{student.standing}</p>
                  </div>
                  <div className="p-4 bg-muted rounded-lg">
                    <p className="text-sm text-muted-foreground">Credits Earned</p>
                    <p className="text-lg font-bold">{student.credits}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
