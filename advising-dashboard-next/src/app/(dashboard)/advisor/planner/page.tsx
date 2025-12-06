'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
  Plus,
  X,
  Save,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  type: string;
  prerequisites?: string;
}

interface Student {
  id: string;
  studentId: string;
  name: string;
  credits: number;
  courseStatuses?: Record<string, string>;
}

interface PlannedSemester {
  name: string;
  courses: Course[];
}

export default function AdvisorPlannerPage() {
  const { currentMajor } = useAuth();
  const [students, setStudents] = useState<Student[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string>('');
  const [plannedSemesters, setPlannedSemesters] = useState<PlannedSemester[]>([
    { name: 'Spring 2026', courses: [] },
    { name: 'Summer 2026', courses: [] },
    { name: 'Fall 2026', courses: [] },
  ]);

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

  const getAvailableCourses = () => {
    const takenCodes = Object.entries(courseStatuses)
      .filter(([_, status]) => ['a', 'b', 'c', 'd', 'p', 's', 'r', 'cr'].includes((status || '').toLowerCase()))
      .map(([code]) => code);
    
    const plannedCodes = plannedSemesters.flatMap(s => s.courses.map(c => c.code));
    
    return courses.filter(c => 
      !takenCodes.includes(c.code) && !plannedCodes.includes(c.code)
    );
  };

  const addCourseToSemester = (semesterIndex: number, course: Course) => {
    setPlannedSemesters(prev => prev.map((sem, i) => 
      i === semesterIndex 
        ? { ...sem, courses: [...sem.courses, course] }
        : sem
    ));
  };

  const removeCourseFromSemester = (semesterIndex: number, courseId: string) => {
    setPlannedSemesters(prev => prev.map((sem, i) => 
      i === semesterIndex 
        ? { ...sem, courses: sem.courses.filter(c => c.id !== courseId) }
        : sem
    ));
  };

  const addSemester = () => {
    const lastSemester = plannedSemesters[plannedSemesters.length - 1]?.name || 'Fall 2025';
    const [season, year] = lastSemester.split(' ');
    let nextSeason = season === 'Spring' ? 'Summer' : season === 'Summer' ? 'Fall' : 'Spring';
    let nextYear = season === 'Fall' ? parseInt(year) + 1 : parseInt(year);
    
    setPlannedSemesters(prev => [...prev, { name: `${nextSeason} ${nextYear}`, courses: [] }]);
  };

  const getTotalCredits = (semester: PlannedSemester) => 
    semester.courses.reduce((sum, c) => sum + c.credits, 0);

  if (!currentMajor) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <GraduationCap className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-2xl font-bold">Select a Major</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Please select a major from the dropdown in the header to use the course planner.
        </p>
      </div>
    );
  }

  const availableCourses = getAvailableCourses();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Course Planner</h1>
          <p className="text-muted-foreground">Plan future semesters for students</p>
        </div>
        <Button>
          <Save className="h-4 w-4 mr-2" />
          Save Plan
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Student</CardTitle>
        </CardHeader>
        <CardContent>
          <Select value={selectedStudent} onValueChange={setSelectedStudent}>
            <SelectTrigger className="max-w-md">
              <SelectValue placeholder="Select a student" />
            </SelectTrigger>
            <SelectContent>
              {students.map(s => (
                <SelectItem key={s.id} value={s.id}>
                  {s.name} ({s.studentId}) - {s.credits} credits
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {student && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-4">
            {plannedSemesters.map((semester, semIndex) => (
              <Card key={semIndex}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{semester.name}</CardTitle>
                    <Badge variant="outline">
                      {getTotalCredits(semester)} credits
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {semester.courses.length === 0 ? (
                      <p className="text-sm text-muted-foreground italic">No courses planned</p>
                    ) : (
                      semester.courses.map(course => (
                        <div 
                          key={course.id}
                          className="flex items-center justify-between p-3 bg-muted rounded-lg"
                        >
                          <div>
                            <p className="font-medium">{course.code}</p>
                            <p className="text-sm text-muted-foreground">{course.name}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary">{course.credits} cr</Badge>
                            <Button 
                              variant="ghost" 
                              size="sm"
                              onClick={() => removeCourseFromSemester(semIndex, course.id)}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="mt-3">
                    <Select onValueChange={(courseId) => {
                      const course = courses.find(c => c.id === courseId);
                      if (course) addCourseToSemester(semIndex, course);
                    }}>
                      <SelectTrigger>
                        <SelectValue placeholder="Add a course..." />
                      </SelectTrigger>
                      <SelectContent>
                        {availableCourses.map(c => (
                          <SelectItem key={c.id} value={c.id}>
                            {c.code} - {c.name} ({c.credits} cr)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>
            ))}
            
            <Button variant="outline" onClick={addSemester} className="w-full">
              <Plus className="h-4 w-4 mr-2" />
              Add Semester
            </Button>
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Plan Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Planned Courses</span>
                  <span className="font-medium">
                    {plannedSemesters.reduce((sum, s) => sum + s.courses.length, 0)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Planned Credits</span>
                  <span className="font-medium">
                    {plannedSemesters.reduce((sum, s) => sum + getTotalCredits(s), 0)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Semesters</span>
                  <span className="font-medium">{plannedSemesters.length}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Available Courses</CardTitle>
                <CardDescription>{availableCourses.length} courses remaining</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="max-h-64 overflow-y-auto space-y-2">
                  {availableCourses.slice(0, 10).map(course => (
                    <div 
                      key={course.id}
                      className="p-2 bg-muted rounded text-sm"
                    >
                      <p className="font-medium">{course.code}</p>
                      <p className="text-muted-foreground truncate">{course.name}</p>
                    </div>
                  ))}
                  {availableCourses.length > 10 && (
                    <p className="text-sm text-muted-foreground text-center">
                      +{availableCourses.length - 10} more courses
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
