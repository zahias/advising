'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Search,
  BookOpen,
  GraduationCap,
  RefreshCw,
} from 'lucide-react';

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  type: string;
  prerequisites?: string;
  concurrent?: string;
  corequisites?: string;
  standing?: string;
}

interface Student {
  id: string;
  studentId: string;
  majorId: string;
  name: string;
  email: string;
  credits: number;
  creditsCompleted: number;
  standing: string;
  courseStatuses?: Record<string, string>;
}

interface EligibilityResult {
  course: {
    id: string;
    code: string;
    name: string;
    credits: number;
  };
  eligibility: {
    status: string;
    reason: string;
    missingPrerequisites: string[];
    missingConcurrent: string[];
    missingCorequisites: string[];
    standingIssue: boolean;
    hasBypass: boolean;
  };
}

export default function AdvisorEligibilityPage() {
  const { currentMajor } = useAuth();
  const [students, setStudents] = useState<Student[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string>('');
  const [eligibilityResults, setEligibilityResults] = useState<EligibilityResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState<string>('all');

  useEffect(() => {
    fetchStudents();
    fetchCourses();
  }, [currentMajor]);

  const fetchStudents = async () => {
    try {
      const res = await fetch(`/api/students${currentMajor ? `?major=${currentMajor}` : ''}`);
      if (res.ok) {
        const data = await res.json();
        setStudents(data);
      }
    } catch (error) {
      console.error('Error fetching students:', error);
    }
  };

  const fetchCourses = async () => {
    try {
      const res = await fetch(`/api/courses${currentMajor ? `?major=${currentMajor}` : ''}`);
      if (res.ok) {
        const data = await res.json();
        setCourses(data);
      }
    } catch (error) {
      console.error('Error fetching courses:', error);
    }
  };

  const checkEligibility = async () => {
    if (!selectedStudent) return;
    
    const majorId = students.find(s => s.id === selectedStudent)?.majorId;
    if (!majorId) return;
    
    setLoading(true);
    try {
      const res = await fetch(`/api/eligibility?studentId=${selectedStudent}&majorId=${majorId}`);
      
      if (res.ok) {
        const data = await res.json();
        setEligibilityResults(data.courses || []);
      }
    } catch (error) {
      console.error('Error checking eligibility:', error);
    } finally {
      setLoading(false);
    }
  };

  const student = students.find(s => s.id === selectedStudent);

  const getCategory = (status: string) => {
    const lower = status.toLowerCase();
    if (lower === 'completed') return 'completed';
    if (lower === 'registered') return 'registered';
    if (lower.includes('eligible') && !lower.includes('ineligible')) return 'eligible';
    if (lower.includes('condition') || lower.includes('bypass')) return 'with-conditions';
    if (lower === 'ineligible' || lower.includes('ineligible')) return 'ineligible';
    return 'eligible';
  };

  const filteredResults = eligibilityResults.filter(result => {
    const matchesSearch = result.course.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          result.course.name.toLowerCase().includes(searchTerm.toLowerCase());
    const category = getCategory(result.eligibility.status);
    const matchesFilter = filterCategory === 'all' || category === filterCategory;
    return matchesSearch && matchesFilter;
  });

  const categoryCounts = {
    eligible: eligibilityResults.filter(r => getCategory(r.eligibility.status) === 'eligible').length,
    'with-conditions': eligibilityResults.filter(r => getCategory(r.eligibility.status) === 'with-conditions').length,
    ineligible: eligibilityResults.filter(r => getCategory(r.eligibility.status) === 'ineligible').length,
    completed: eligibilityResults.filter(r => getCategory(r.eligibility.status) === 'completed').length,
    registered: eligibilityResults.filter(r => getCategory(r.eligibility.status) === 'registered').length,
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'eligible': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'with-conditions': return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'ineligible': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'completed': return <CheckCircle className="h-4 w-4 text-blue-500" />;
      case 'registered': return <Clock className="h-4 w-4 text-purple-500" />;
      default: return null;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'eligible': return 'bg-green-50 border-green-200';
      case 'with-conditions': return 'bg-yellow-50 border-yellow-200';
      case 'ineligible': return 'bg-red-50 border-red-200';
      case 'completed': return 'bg-blue-50 border-blue-200';
      case 'registered': return 'bg-purple-50 border-purple-200';
      default: return 'bg-gray-50 border-gray-200';
    }
  };

  if (!currentMajor) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <GraduationCap className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-2xl font-bold">Select a Major</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Please select a major from the dropdown in the header to check course eligibility.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Course Eligibility</h1>
        <p className="text-muted-foreground">Check which courses a student is eligible to take</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Student</CardTitle>
          <CardDescription>Choose a student to view their course eligibility</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <Select value={selectedStudent} onValueChange={setSelectedStudent}>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="Select a student" />
              </SelectTrigger>
              <SelectContent>
                {students.map(s => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.name} ({s.studentId}) - {s.creditsCompleted || s.credits || 0} credits
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={checkEligibility} disabled={!selectedStudent || loading}>
              {loading ? (
                <><RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Checking...</>
              ) : (
                <><Search className="h-4 w-4 mr-2" /> Check Eligibility</>
              )}
            </Button>
          </div>

          {student && (
            <div className="flex items-center gap-4 p-4 bg-muted rounded-lg">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                <span className="text-lg font-bold text-primary">
                  {student.name.split(' ').map(n => n[0]).join('')}
                </span>
              </div>
              <div>
                <p className="font-medium">{student.name}</p>
                <p className="text-sm text-muted-foreground">
                  {student.studentId} • {student.credits} credits • {student.standing}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {eligibilityResults.length > 0 && (
        <>
          <div className="grid gap-4 md:grid-cols-5">
            <Card className="bg-green-50 border-green-200">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-green-700">Eligible</p>
                    <p className="text-2xl font-bold text-green-800">{categoryCounts.eligible}</p>
                  </div>
                  <CheckCircle className="h-8 w-8 text-green-500" />
                </div>
              </CardContent>
            </Card>
            <Card className="bg-yellow-50 border-yellow-200">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-yellow-700">With Conditions</p>
                    <p className="text-2xl font-bold text-yellow-800">{categoryCounts['with-conditions']}</p>
                  </div>
                  <AlertCircle className="h-8 w-8 text-yellow-500" />
                </div>
              </CardContent>
            </Card>
            <Card className="bg-red-50 border-red-200">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-red-700">Ineligible</p>
                    <p className="text-2xl font-bold text-red-800">{categoryCounts.ineligible}</p>
                  </div>
                  <XCircle className="h-8 w-8 text-red-500" />
                </div>
              </CardContent>
            </Card>
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-blue-700">Completed</p>
                    <p className="text-2xl font-bold text-blue-800">{categoryCounts.completed}</p>
                  </div>
                  <CheckCircle className="h-8 w-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>
            <Card className="bg-purple-50 border-purple-200">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-purple-700">Registered</p>
                    <p className="text-2xl font-bold text-purple-800">{categoryCounts.registered}</p>
                  </div>
                  <Clock className="h-8 w-8 text-purple-500" />
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Eligibility Results</CardTitle>
                  <CardDescription>{eligibilityResults.length} courses analyzed</CardDescription>
                </div>
                <div className="flex gap-2">
                  <Input
                    placeholder="Search courses..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                  <Select value={filterCategory} onValueChange={setFilterCategory}>
                    <SelectTrigger className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Categories</SelectItem>
                      <SelectItem value="eligible">Eligible</SelectItem>
                      <SelectItem value="with-conditions">With Conditions</SelectItem>
                      <SelectItem value="ineligible">Ineligible</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="registered">Registered</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {filteredResults.map((result) => {
                  const category = getCategory(result.eligibility.status);
                  const hasIssues = result.eligibility.missingPrerequisites.length > 0 ||
                                    result.eligibility.missingConcurrent.length > 0 ||
                                    result.eligibility.missingCorequisites.length > 0 ||
                                    result.eligibility.standingIssue;
                  return (
                    <div
                      key={result.course.id}
                      className={`p-4 rounded-lg border ${getCategoryColor(category)}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          {getCategoryIcon(category)}
                          <div>
                            <p className="font-medium">{result.course.code}</p>
                            <p className="text-sm text-muted-foreground">{result.course.name}</p>
                          </div>
                        </div>
                        <Badge variant="outline" className="capitalize">
                          {result.eligibility.status}
                        </Badge>
                      </div>
                      {(hasIssues || result.eligibility.reason) && (
                        <div className="mt-3 pl-7 space-y-1">
                          {result.eligibility.reason && (
                            <p className="text-sm text-muted-foreground">• {result.eligibility.reason}</p>
                          )}
                          {result.eligibility.missingPrerequisites.length > 0 && (
                            <p className="text-sm text-red-600">
                              • Missing prerequisites: {result.eligibility.missingPrerequisites.join(', ')}
                            </p>
                          )}
                          {result.eligibility.missingConcurrent.length > 0 && (
                            <p className="text-sm text-orange-600">
                              • Must take concurrently: {result.eligibility.missingConcurrent.join(', ')}
                            </p>
                          )}
                          {result.eligibility.missingCorequisites.length > 0 && (
                            <p className="text-sm text-orange-600">
                              • Missing corequisites: {result.eligibility.missingCorequisites.join(', ')}
                            </p>
                          )}
                          {result.eligibility.standingIssue && (
                            <p className="text-sm text-red-600">• Does not meet standing requirement</p>
                          )}
                          {result.eligibility.hasBypass && (
                            <p className="text-sm text-green-600">• Has advisor bypass</p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
