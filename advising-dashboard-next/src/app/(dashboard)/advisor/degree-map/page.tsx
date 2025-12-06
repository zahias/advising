'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
  CheckCircle,
  Clock,
  BookOpen,
} from 'lucide-react';

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  type: string;
  semester?: number;
}

interface Student {
  id: string;
  studentId: string;
  name: string;
  credits: number;
  courseStatuses?: Record<string, string>;
}

export default function AdvisorDegreeMapPage() {
  const { currentMajor } = useAuth();
  const [students, setStudents] = useState<Student[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [currentMajor]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [studentsRes, coursesRes] = await Promise.all([
        fetch(`/api/students${currentMajor ? `?major=${currentMajor}` : ''}`),
        fetch(`/api/courses${currentMajor ? `?major=${currentMajor}` : ''}`),
      ]);
      
      if (studentsRes.ok) setStudents(await studentsRes.json());
      if (coursesRes.ok) setCourses(await coursesRes.json());
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const student = students.find(s => s.id === selectedStudent);
  const courseStatuses = student?.courseStatuses || {};

  const getCourseStatus = (courseCode: string) => {
    const status = courseStatuses[courseCode];
    if (!status || status === '' || status === 'nan') return 'remaining';
    if (['a', 'b', 'c', 'd', 'p', 's'].includes(status.toLowerCase())) return 'completed';
    if (['r', 'cr'].includes(status.toLowerCase())) return 'registered';
    if (['f', 'w', 'i', 'wp', 'wf'].includes(status.toLowerCase())) return 'failed';
    return 'remaining';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 border-green-300 text-green-800';
      case 'registered': return 'bg-blue-100 border-blue-300 text-blue-800';
      case 'failed': return 'bg-red-100 border-red-300 text-red-800';
      default: return 'bg-gray-100 border-gray-300 text-gray-800';
    }
  };

  const courseTypes = [...new Set(courses.map(c => c.type || 'General'))];
  const coursesByType = courseTypes.reduce((acc, type) => {
    acc[type] = courses.filter(c => (c.type || 'General') === type);
    return acc;
  }, {} as Record<string, Course[]>);

  if (!currentMajor) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <GraduationCap className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-2xl font-bold">Select a Major</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Please select a major from the dropdown in the header to view the degree map.
        </p>
      </div>
    );
  }

  const stats = student ? {
    completed: Object.entries(courseStatuses).filter(([_, s]) => 
      ['a', 'b', 'c', 'd', 'p', 's'].includes((s || '').toLowerCase())
    ).length,
    registered: Object.entries(courseStatuses).filter(([_, s]) => 
      ['r', 'cr'].includes((s || '').toLowerCase())
    ).length,
    remaining: courses.length - Object.entries(courseStatuses).filter(([_, s]) => 
      ['a', 'b', 'c', 'd', 'p', 's', 'r', 'cr'].includes((s || '').toLowerCase())
    ).length,
  } : { completed: 0, registered: 0, remaining: courses.length };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Degree Map</h1>
        <p className="text-muted-foreground">Visual overview of degree requirements and progress</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Student</CardTitle>
          <CardDescription>View degree progress for a specific student</CardDescription>
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
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="bg-green-50 border-green-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-green-700">Completed</p>
                  <p className="text-2xl font-bold text-green-800">{stats.completed}</p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-blue-700">Registered</p>
                  <p className="text-2xl font-bold text-blue-800">{stats.registered}</p>
                </div>
                <Clock className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gray-50 border-gray-200">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-700">Remaining</p>
                  <p className="text-2xl font-bold text-gray-800">{stats.remaining}</p>
                </div>
                <BookOpen className="h-8 w-8 text-gray-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="space-y-6">
        {courseTypes.map(type => (
          <Card key={type}>
            <CardHeader>
              <CardTitle>{type}</CardTitle>
              <CardDescription>{coursesByType[type].length} courses</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                {coursesByType[type].map(course => {
                  const status = selectedStudent ? getCourseStatus(course.code) : 'remaining';
                  return (
                    <div
                      key={course.id}
                      className={`p-3 rounded-lg border ${getStatusColor(status)}`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{course.code}</p>
                          <p className="text-xs truncate max-w-[180px]">{course.name}</p>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {course.credits} cr
                        </Badge>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-green-100 border border-green-300" />
              <span className="text-sm">Completed</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-blue-100 border border-blue-300" />
              <span className="text-sm">Registered</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-red-100 border border-red-300" />
              <span className="text-sm">Failed/Withdrawn</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-gray-100 border border-gray-300" />
              <span className="text-sm">Remaining</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
