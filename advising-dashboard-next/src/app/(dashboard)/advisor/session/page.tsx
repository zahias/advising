'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { 
  User,
  BookOpen,
  CheckCircle,
  XCircle,
  AlertCircle,
  Save,
  Mail,
  Download,
  Clock,
  RefreshCw,
  Shield,
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
}

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  type: string;
  prerequisites: string[];
  corequisites: string[];
  concurrent: string[];
  standingRequired?: string;
  offered: boolean;
}

interface EligibilityResult {
  status: string;
  reason: string;
  missingPrerequisites: string[];
  missingConcurrent: string[];
  missingCorequisites: string[];
  standingIssue: boolean;
  hasBypass: boolean;
  bypassInfo?: { note: string; advisor: string };
}

interface CourseWithEligibility {
  course: Course;
  eligibility: EligibilityResult;
}

interface Major {
  id: string;
  code: string;
  name: string;
}

interface Period {
  id: string;
  semester: string;
  year: number;
  advisorName?: string;
  isActive: boolean;
}

interface Session {
  id: string;
  advisedCourses: string[];
  optionalCourses: string[];
  repeatCourses: string[];
  bypasses: Record<string, { note: string; advisor: string }>;
  note?: string;
}

export default function AdvisorSessionPage() {
  const { currentMajor, user } = useAuth();
  
  const [majors, setMajors] = useState<Major[]>([]);
  const [selectedMajorId, setSelectedMajorId] = useState<string>('');
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<string>('');
  const [periods, setPeriods] = useState<Period[]>([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>('');
  const [coursesWithEligibility, setCoursesWithEligibility] = useState<CourseWithEligibility[]>([]);
  const [session, setSession] = useState<Session | null>(null);
  
  const [advisedCourses, setAdvisedCourses] = useState<string[]>([]);
  const [optionalCourses, setOptionalCourses] = useState<string[]>([]);
  const [repeatCourses, setRepeatCourses] = useState<string[]>([]);
  const [bypasses, setBypasses] = useState<Record<string, { note: string; advisor: string }>>({});
  const [advisorNote, setAdvisorNote] = useState('');
  
  const [bypassCourseCode, setBypassCourseCode] = useState('');
  const [bypassNote, setBypassNote] = useState('');
  const [bypassDialogOpen, setBypassDialogOpen] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchMajors() {
      try {
        const res = await fetch('/api/majors');
        const data = await res.json();
        setMajors(data);
        if (data.length > 0 && !selectedMajorId) {
          const matched = data.find((m: Major) => m.code === currentMajor);
          if (matched) {
            setSelectedMajorId(matched.id);
          }
        }
      } catch (err) {
        console.error('Failed to fetch majors:', err);
      }
    }
    fetchMajors();
  }, [currentMajor, selectedMajorId]);

  useEffect(() => {
    async function fetchStudentsAndPeriods() {
      if (!selectedMajorId) return;
      
      try {
        const [studentsRes, periodsRes] = await Promise.all([
          fetch(`/api/students?majorId=${selectedMajorId}`),
          fetch(`/api/periods?majorId=${selectedMajorId}`)
        ]);
        
        const studentsData = await studentsRes.json();
        const periodsData = await periodsRes.json();
        
        setStudents(studentsData);
        setPeriods(periodsData);
        
        const activePeriod = periodsData.find((p: Period) => p.isActive);
        if (activePeriod) {
          setSelectedPeriodId(activePeriod.id);
        }
      } catch (err) {
        console.error('Failed to fetch students/periods:', err);
      }
    }
    fetchStudentsAndPeriods();
  }, [selectedMajorId]);

  const fetchEligibility = useCallback(async () => {
    if (!selectedStudentId || !selectedMajorId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const url = new URL('/api/eligibility', window.location.origin);
      url.searchParams.set('studentId', selectedStudentId);
      url.searchParams.set('majorId', selectedMajorId);
      if (selectedPeriodId) {
        url.searchParams.set('periodId', selectedPeriodId);
      }
      
      const res = await fetch(url.toString());
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || 'Failed to fetch eligibility');
      }
      
      setCoursesWithEligibility(data.courses || []);
      
      if (data.session) {
        setSession(data.session);
        setAdvisedCourses(data.session.advisedCourses || []);
        setOptionalCourses(data.session.optionalCourses || []);
        setRepeatCourses(data.session.repeatCourses || []);
        setBypasses(data.session.bypasses || {});
        setAdvisorNote(data.session.note || '');
      } else {
        setSession(null);
        setAdvisedCourses([]);
        setOptionalCourses([]);
        setRepeatCourses([]);
        setBypasses({});
        setAdvisorNote('');
      }
    } catch (err) {
      console.error('Failed to fetch eligibility:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch eligibility');
    } finally {
      setLoading(false);
    }
  }, [selectedStudentId, selectedMajorId, selectedPeriodId]);

  useEffect(() => {
    fetchEligibility();
  }, [fetchEligibility]);

  const saveSession = async () => {
    if (!selectedStudentId || !selectedPeriodId) {
      setError('Please select a student and advising period');
      return;
    }
    
    setSaving(true);
    setError(null);
    
    try {
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          periodId: selectedPeriodId,
          studentId: selectedStudentId,
          advisorId: user?.id,
          advisedCourses,
          optionalCourses,
          repeatCourses,
          bypasses,
          note: advisorNote,
        }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || 'Failed to save session');
      }
      
      setSession(data);
      await fetchEligibility();
    } catch (err) {
      console.error('Failed to save session:', err);
      setError(err instanceof Error ? err.message : 'Failed to save session');
    } finally {
      setSaving(false);
    }
  };

  const toggleCourse = (code: string, type: 'advised' | 'optional' | 'repeat') => {
    const setters = {
      advised: setAdvisedCourses,
      optional: setOptionalCourses,
      repeat: setRepeatCourses,
    };
    
    const others = {
      advised: [optionalCourses, repeatCourses, setOptionalCourses, setRepeatCourses] as const,
      optional: [advisedCourses, repeatCourses, setAdvisedCourses, setRepeatCourses] as const,
      repeat: [advisedCourses, optionalCourses, setAdvisedCourses, setOptionalCourses] as const,
    };
    
    const [other1, other2, setOther1, setOther2] = others[type];
    
    if (other1.includes(code)) {
      setOther1(prev => prev.filter(c => c !== code));
    }
    if (other2.includes(code)) {
      setOther2(prev => prev.filter(c => c !== code));
    }
    
    setters[type](prev => 
      prev.includes(code) 
        ? prev.filter(c => c !== code)
        : [...prev, code]
    );
  };

  const addBypass = () => {
    if (!bypassCourseCode || !bypassNote) return;
    
    setBypasses(prev => ({
      ...prev,
      [bypassCourseCode]: {
        note: bypassNote,
        advisor: user?.name || 'Advisor',
      },
    }));
    
    setBypassCourseCode('');
    setBypassNote('');
    setBypassDialogOpen(false);
  };

  const removeBypass = (code: string) => {
    setBypasses(prev => {
      const updated = { ...prev };
      delete updated[code];
      return updated;
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Eligible': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'Not Eligible': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'Completed': return <CheckCircle className="h-4 w-4 text-blue-500" />;
      case 'Registered': return <Clock className="h-4 w-4 text-purple-500" />;
      case 'Advised': return <CheckCircle className="h-4 w-4 text-yellow-500" />;
      default: return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string, hasBypass: boolean) => {
    if (hasBypass) {
      return <Badge className="bg-orange-100 text-orange-800">Bypass</Badge>;
    }
    switch (status) {
      case 'Eligible': return <Badge className="bg-green-100 text-green-800">Eligible</Badge>;
      case 'Not Eligible': return <Badge className="bg-red-100 text-red-800">Not Eligible</Badge>;
      case 'Completed': return <Badge className="bg-blue-100 text-blue-800">Completed</Badge>;
      case 'Registered': return <Badge className="bg-purple-100 text-purple-800">Registered</Badge>;
      case 'Advised': return <Badge className="bg-yellow-100 text-yellow-800">Advised</Badge>;
      default: return <Badge variant="outline">Unknown</Badge>;
    }
  };

  const selectedStudent = students.find(s => s.id === selectedStudentId);
  const selectedPeriod = periods.find(p => p.id === selectedPeriodId);
  
  const allSelectedCourses = [...advisedCourses, ...optionalCourses, ...repeatCourses];
  const totalCredits = allSelectedCourses.reduce((acc, code) => {
    const course = coursesWithEligibility.find(c => c.course.code === code);
    return acc + (course?.course.credits || 0);
  }, 0);

  const eligibleCourses = coursesWithEligibility.filter(c => 
    c.eligibility.status === 'Eligible' || c.eligibility.hasBypass
  );
  const completedCourses = coursesWithEligibility.filter(c => c.eligibility.status === 'Completed');
  const registeredCourses = coursesWithEligibility.filter(c => c.eligibility.status === 'Registered');
  const notEligibleCourses = coursesWithEligibility.filter(c => 
    c.eligibility.status === 'Not Eligible' && !c.eligibility.hasBypass
  );

  if (!currentMajor) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="text-6xl">🎓</div>
        <h2 className="text-2xl font-bold">Select a Major</h2>
        <p className="text-muted-foreground">Please select a major from the header dropdown.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Advising Session</h1>
          <p className="text-muted-foreground">{currentMajor} - Create or edit advising recommendations</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchEligibility} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Select Student
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Advising Period</Label>
              <Select value={selectedPeriodId} onValueChange={setSelectedPeriodId}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose period..." />
                </SelectTrigger>
                <SelectContent>
                  {periods.map(p => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.semester} {p.year} {p.isActive && '(Active)'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Student</Label>
              <Select value={selectedStudentId} onValueChange={setSelectedStudentId}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a student..." />
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

            {selectedStudent && (
              <div className="p-4 bg-gray-50 rounded-lg space-y-2">
                <p className="font-medium text-lg">{selectedStudent.name}</p>
                <p className="text-sm text-muted-foreground">ID: {selectedStudent.studentId}</p>
                <div className="flex gap-2 pt-2 flex-wrap">
                  <Badge>{selectedStudent.standing || 'Unknown'}</Badge>
                  <Badge variant="outline">{selectedStudent.creditsCompleted + selectedStudent.creditsRegistered} credits</Badge>
                  <Badge variant="outline">{selectedStudent.creditsRemaining} remaining</Badge>
                </div>
              </div>
            )}

            {selectedStudent && (
              <Dialog open={bypassDialogOpen} onOpenChange={setBypassDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="w-full">
                    <Shield className="h-4 w-4 mr-2" />
                    Grant Bypass
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Grant Requisite Bypass</DialogTitle>
                    <DialogDescription>
                      Allow student to take a course without meeting prerequisites
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>Course Code</Label>
                      <Select value={bypassCourseCode} onValueChange={setBypassCourseCode}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select course..." />
                        </SelectTrigger>
                        <SelectContent>
                          {notEligibleCourses.map(({ course }) => (
                            <SelectItem key={course.code} value={course.code}>
                              {course.code} - {course.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Bypass Reason</Label>
                      <Textarea
                        placeholder="Explain why this bypass is being granted..."
                        value={bypassNote}
                        onChange={(e) => setBypassNote(e.target.value)}
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setBypassDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={addBypass} disabled={!bypassCourseCode || !bypassNote}>
                      Grant Bypass
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            )}

            {Object.keys(bypasses).length > 0 && (
              <div className="space-y-2">
                <Label>Active Bypasses</Label>
                <div className="space-y-2">
                  {Object.entries(bypasses).map(([code, info]) => (
                    <div key={code} className="flex items-center justify-between p-2 bg-orange-50 rounded border border-orange-200">
                      <div>
                        <p className="font-medium text-sm">{code}</p>
                        <p className="text-xs text-muted-foreground">{info.note}</p>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => removeBypass(code)}>
                        ×
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Course Eligibility
            </CardTitle>
            <CardDescription>
              Select courses to recommend - check Advised for required, Optional for suggestions
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!selectedStudentId ? (
              <div className="text-center py-8 text-muted-foreground">
                Select a student to view eligible courses
              </div>
            ) : loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="space-y-6">
                {eligibleCourses.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-medium text-green-700">Eligible Courses ({eligibleCourses.length})</h3>
                    <div className="space-y-2">
                      {eligibleCourses.map(({ course, eligibility }) => (
                        <CourseRow
                          key={course.code}
                          course={course}
                          eligibility={eligibility}
                          isAdvised={advisedCourses.includes(course.code)}
                          isOptional={optionalCourses.includes(course.code)}
                          isRepeat={repeatCourses.includes(course.code)}
                          onToggle={toggleCourse}
                          getStatusIcon={getStatusIcon}
                          getStatusBadge={getStatusBadge}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {registeredCourses.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-medium text-purple-700">Currently Registered ({registeredCourses.length})</h3>
                    <div className="space-y-2">
                      {registeredCourses.map(({ course, eligibility }) => (
                        <CourseRow
                          key={course.code}
                          course={course}
                          eligibility={eligibility}
                          isAdvised={false}
                          isOptional={false}
                          isRepeat={false}
                          onToggle={() => {}}
                          getStatusIcon={getStatusIcon}
                          getStatusBadge={getStatusBadge}
                          disabled
                        />
                      ))}
                    </div>
                  </div>
                )}

                {notEligibleCourses.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-medium text-red-700">Not Eligible ({notEligibleCourses.length})</h3>
                    <div className="space-y-2">
                      {notEligibleCourses.map(({ course, eligibility }) => (
                        <CourseRow
                          key={course.code}
                          course={course}
                          eligibility={eligibility}
                          isAdvised={false}
                          isOptional={false}
                          isRepeat={false}
                          onToggle={() => {}}
                          getStatusIcon={getStatusIcon}
                          getStatusBadge={getStatusBadge}
                          disabled
                          showReason
                        />
                      ))}
                    </div>
                  </div>
                )}

                {completedCourses.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-medium text-blue-700">Completed ({completedCourses.length})</h3>
                    <div className="space-y-2">
                      {completedCourses.map(({ course, eligibility }) => (
                        <CourseRow
                          key={course.code}
                          course={course}
                          eligibility={eligibility}
                          isAdvised={false}
                          isOptional={false}
                          isRepeat={false}
                          onToggle={() => {}}
                          getStatusIcon={getStatusIcon}
                          getStatusBadge={getStatusBadge}
                          disabled
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {selectedStudentId && (
        <Card>
          <CardHeader>
            <CardTitle>Advising Summary</CardTitle>
            <CardDescription>
              {allSelectedCourses.length} courses selected - {totalCredits} total credits
              {selectedPeriod && ` - ${selectedPeriod.semester} ${selectedPeriod.year}`}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {advisedCourses.length > 0 && (
              <div>
                <Label className="text-green-700">Advised Courses</Label>
                <div className="flex flex-wrap gap-2 mt-1">
                  {advisedCourses.map(code => (
                    <Badge key={code} className="bg-green-100 text-green-800 text-sm py-1 px-3">
                      {code}
                      <button 
                        className="ml-2 hover:text-red-500"
                        onClick={() => toggleCourse(code, 'advised')}
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {optionalCourses.length > 0 && (
              <div>
                <Label className="text-blue-700">Optional Courses</Label>
                <div className="flex flex-wrap gap-2 mt-1">
                  {optionalCourses.map(code => (
                    <Badge key={code} className="bg-blue-100 text-blue-800 text-sm py-1 px-3">
                      {code}
                      <button 
                        className="ml-2 hover:text-red-500"
                        onClick={() => toggleCourse(code, 'optional')}
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {repeatCourses.length > 0 && (
              <div>
                <Label className="text-orange-700">Repeat Courses</Label>
                <div className="flex flex-wrap gap-2 mt-1">
                  {repeatCourses.map(code => (
                    <Badge key={code} className="bg-orange-100 text-orange-800 text-sm py-1 px-3">
                      {code}
                      <button 
                        className="ml-2 hover:text-red-500"
                        onClick={() => toggleCourse(code, 'repeat')}
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label>Advisor Notes</Label>
              <Textarea
                placeholder="Add notes for this advising session..."
                value={advisorNote}
                onChange={(e) => setAdvisorNote(e.target.value)}
                rows={4}
              />
            </div>

            <div className="flex gap-3 pt-4">
              <Button className="flex-1" onClick={saveSession} disabled={saving}>
                {saving ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-2" />
                )}
                Save Session
              </Button>
              <Button variant="outline" disabled>
                <Mail className="h-4 w-4 mr-2" />
                Email Student
              </Button>
              <Button variant="outline" disabled>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface CourseRowProps {
  course: Course;
  eligibility: EligibilityResult;
  isAdvised: boolean;
  isOptional: boolean;
  isRepeat: boolean;
  onToggle: (code: string, type: 'advised' | 'optional' | 'repeat') => void;
  getStatusIcon: (status: string) => React.ReactNode;
  getStatusBadge: (status: string, hasBypass: boolean) => React.ReactNode;
  disabled?: boolean;
  showReason?: boolean;
}

function CourseRow({
  course,
  eligibility,
  isAdvised,
  isOptional,
  isRepeat,
  onToggle,
  getStatusIcon,
  getStatusBadge,
  disabled = false,
  showReason = false,
}: CourseRowProps) {
  const isSelected = isAdvised || isOptional || isRepeat;
  
  return (
    <div 
      className={`flex items-start justify-between p-4 rounded-lg border transition-colors ${
        disabled 
          ? 'bg-gray-50'
          : isSelected
            ? 'bg-green-50 border-green-200'
            : 'hover:bg-gray-50'
      }`}
    >
      <div className="flex items-start gap-4">
        {!disabled && (
          <div className="flex flex-col gap-1 pt-1">
            <label className="flex items-center gap-1 text-xs cursor-pointer">
              <Checkbox 
                checked={isAdvised}
                onCheckedChange={() => onToggle(course.code, 'advised')}
              />
              <span>Advised</span>
            </label>
            <label className="flex items-center gap-1 text-xs cursor-pointer">
              <Checkbox 
                checked={isOptional}
                onCheckedChange={() => onToggle(course.code, 'optional')}
              />
              <span>Optional</span>
            </label>
          </div>
        )}
        {getStatusIcon(eligibility.status)}
        <div>
          <p className="font-medium">{course.code}</p>
          <p className="text-sm text-muted-foreground">{course.name}</p>
          {course.prerequisites.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Prereqs: {course.prerequisites.join(', ')}
            </p>
          )}
          {showReason && eligibility.reason && (
            <p className="text-xs text-red-600 mt-1">{eligibility.reason}</p>
          )}
          {eligibility.hasBypass && eligibility.bypassInfo && (
            <p className="text-xs text-orange-600 mt-1">
              Bypass: {eligibility.bypassInfo.note}
            </p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant="outline">{course.credits} cr</Badge>
        <Badge variant="outline">{course.type}</Badge>
        {getStatusBadge(eligibility.status, eligibility.hasBypass)}
      </div>
    </div>
  );
}
