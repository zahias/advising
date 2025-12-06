'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { useAuth } from '@/lib/auth/context';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { 
  User,
  BookOpen,
  CheckCircle,
  XCircle,
  AlertCircle,
  Save,
  Mail,
  Download,
  Clock
} from 'lucide-react';

const sampleCourses = [
  { code: 'PBHL 301', name: 'Epidemiology', credits: 3, type: 'Required', status: 'eligible', prereqs: 'PBHL 101' },
  { code: 'PBHL 305', name: 'Biostatistics', credits: 3, type: 'Required', status: 'eligible', prereqs: 'MATH 201' },
  { code: 'PBHL 320', name: 'Health Policy', credits: 3, type: 'Required', status: 'eligible', prereqs: 'PBHL 201' },
  { code: 'PBHL 310', name: 'Environmental Health', credits: 3, type: 'Required', status: 'not-eligible', prereqs: 'PBHL 301' },
  { code: 'PBHL 401', name: 'Capstone I', credits: 3, type: 'Required', status: 'not-eligible', prereqs: 'Senior standing' },
  { code: 'PBHL 350', name: 'Global Health', credits: 3, type: 'Intensive', status: 'eligible', prereqs: 'PBHL 201' },
  { code: 'PBHL 355', name: 'Community Health', credits: 3, type: 'Intensive', status: 'completed', prereqs: 'None' },
];

const sampleStudents = [
  { id: '12345', name: 'John Smith' },
  { id: '12346', name: 'Sarah Johnson' },
  { id: '12347', name: 'Mike Williams' },
  { id: '12348', name: 'Emily Brown' },
];

export default function AdvisorSessionPage() {
  const { currentMajor } = useAuth();
  const [selectedStudent, setSelectedStudent] = useState<string>('');
  const [selectedCourses, setSelectedCourses] = useState<string[]>([]);
  const [advisorNote, setAdvisorNote] = useState('');

  if (!currentMajor) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="text-6xl">🎓</div>
        <h2 className="text-2xl font-bold">Select a Major</h2>
        <p className="text-muted-foreground">Please select a major from the header dropdown.</p>
      </div>
    );
  }

  const student = sampleStudents.find(s => s.id === selectedStudent);
  const eligibleCourses = sampleCourses.filter(c => c.status === 'eligible');

  const toggleCourse = (code: string) => {
    setSelectedCourses(prev => 
      prev.includes(code) 
        ? prev.filter(c => c !== code)
        : [...prev, code]
    );
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'eligible': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'not-eligible': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'completed': return <CheckCircle className="h-4 w-4 text-blue-500" />;
      default: return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'eligible': return <Badge className="bg-green-100 text-green-800">Eligible</Badge>;
      case 'not-eligible': return <Badge className="bg-red-100 text-red-800">Not Eligible</Badge>;
      case 'completed': return <Badge className="bg-blue-100 text-blue-800">Completed</Badge>;
      default: return <Badge variant="outline">Unknown</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Advising Session</h1>
        <p className="text-muted-foreground">{currentMajor} • Create or edit advising recommendations</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Select Student
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Select value={selectedStudent} onValueChange={setSelectedStudent}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a student..." />
              </SelectTrigger>
              <SelectContent>
                {sampleStudents.map(s => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.name} ({s.id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {student && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-2">
                <p className="font-medium text-lg">{student.name}</p>
                <p className="text-sm text-muted-foreground">ID: {student.id}</p>
                <div className="flex gap-2 pt-2">
                  <Badge>Junior</Badge>
                  <Badge variant="outline">78 credits</Badge>
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
              Select courses to recommend for this student
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!selectedStudent ? (
              <div className="text-center py-8 text-muted-foreground">
                Select a student to view eligible courses
              </div>
            ) : (
              <div className="space-y-3">
                {sampleCourses.map(course => (
                  <div 
                    key={course.code}
                    className={`flex items-center justify-between p-4 rounded-lg border transition-colors ${
                      course.status === 'eligible' 
                        ? 'hover:bg-green-50 cursor-pointer' 
                        : course.status === 'completed'
                          ? 'bg-blue-50'
                          : 'bg-gray-50'
                    }`}
                    onClick={() => course.status === 'eligible' && toggleCourse(course.code)}
                  >
                    <div className="flex items-center gap-4">
                      {course.status === 'eligible' && (
                        <Checkbox 
                          checked={selectedCourses.includes(course.code)}
                          onCheckedChange={() => toggleCourse(course.code)}
                        />
                      )}
                      {getStatusIcon(course.status)}
                      <div>
                        <p className="font-medium">{course.code}</p>
                        <p className="text-sm text-muted-foreground">{course.name}</p>
                        <p className="text-xs text-muted-foreground">Prereqs: {course.prereqs}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="outline">{course.credits} cr</Badge>
                      <Badge variant="outline">{course.type}</Badge>
                      {getStatusBadge(course.status)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {selectedStudent && (
        <Card>
          <CardHeader>
            <CardTitle>Advising Summary</CardTitle>
            <CardDescription>
              {selectedCourses.length} courses selected • {selectedCourses.reduce((acc, code) => {
                const course = sampleCourses.find(c => c.code === code);
                return acc + (course?.credits || 0);
              }, 0)} total credits
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedCourses.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {selectedCourses.map(code => (
                  <Badge key={code} variant="secondary" className="text-sm py-1 px-3">
                    {code}
                    <button 
                      className="ml-2 hover:text-red-500"
                      onClick={() => toggleCourse(code)}
                    >
                      ×
                    </button>
                  </Badge>
                ))}
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">Advisor Notes</label>
              <Textarea
                placeholder="Add notes for this advising session..."
                value={advisorNote}
                onChange={(e) => setAdvisorNote(e.target.value)}
                rows={4}
              />
            </div>

            <div className="flex gap-3 pt-4">
              <Button className="flex-1">
                <Save className="h-4 w-4 mr-2" />
                Save Session
              </Button>
              <Button variant="outline">
                <Mail className="h-4 w-4 mr-2" />
                Email Student
              </Button>
              <Button variant="outline">
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
