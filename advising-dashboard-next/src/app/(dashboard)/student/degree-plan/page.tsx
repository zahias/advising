'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth/context';
import { 
  CheckCircle,
  Clock,
  Lock,
  BookOpen,
  ChevronRight,
  Download
} from 'lucide-react';

const degreePlan = [
  {
    semester: 'Year 1 - Fall',
    courses: [
      { code: 'PBHL 101', name: 'Introduction to Public Health', credits: 3, status: 'completed', grade: 'A' },
      { code: 'ENGL 101', name: 'English Composition I', credits: 3, status: 'completed', grade: 'B+' },
      { code: 'MATH 101', name: 'College Algebra', credits: 3, status: 'completed', grade: 'A-' },
      { code: 'BIOL 101', name: 'General Biology', credits: 4, status: 'completed', grade: 'B' },
    ]
  },
  {
    semester: 'Year 1 - Spring',
    courses: [
      { code: 'PBHL 102', name: 'Health and Society', credits: 3, status: 'completed', grade: 'A' },
      { code: 'ENGL 102', name: 'English Composition II', credits: 3, status: 'completed', grade: 'A-' },
      { code: 'MATH 201', name: 'Statistics', credits: 3, status: 'completed', grade: 'B+' },
      { code: 'CHEM 101', name: 'General Chemistry', credits: 4, status: 'completed', grade: 'B' },
    ]
  },
  {
    semester: 'Year 2 - Fall',
    courses: [
      { code: 'PBHL 201', name: 'Health Behavior', credits: 3, status: 'completed', grade: 'A' },
      { code: 'PBHL 202', name: 'Health Communication', credits: 3, status: 'completed', grade: 'A-' },
      { code: 'PBHL 210', name: 'Medical Terminology', credits: 3, status: 'completed', grade: 'B+' },
      { code: 'BIOL 201', name: 'Human Anatomy', credits: 4, status: 'completed', grade: 'B' },
    ]
  },
  {
    semester: 'Year 2 - Spring',
    courses: [
      { code: 'PBHL 250', name: 'Research Methods', credits: 3, status: 'registered', grade: null },
      { code: 'PBHL 220', name: 'Health Ethics', credits: 3, status: 'registered', grade: null },
      { code: 'BIOL 202', name: 'Human Physiology', credits: 4, status: 'registered', grade: null },
      { code: 'PSYC 101', name: 'General Psychology', credits: 3, status: 'registered', grade: null },
    ]
  },
  {
    semester: 'Year 3 - Fall',
    courses: [
      { code: 'PBHL 301', name: 'Epidemiology', credits: 3, status: 'available', grade: null },
      { code: 'PBHL 305', name: 'Biostatistics', credits: 3, status: 'available', grade: null },
      { code: 'PBHL 310', name: 'Environmental Health', credits: 3, status: 'locked', grade: null },
      { code: 'PBHL 315', name: 'Health Administration', credits: 3, status: 'available', grade: null },
    ]
  },
  {
    semester: 'Year 3 - Spring',
    courses: [
      { code: 'PBHL 320', name: 'Health Policy', credits: 3, status: 'locked', grade: null },
      { code: 'PBHL 350', name: 'Global Health', credits: 3, status: 'locked', grade: null },
      { code: 'PBHL 360', name: 'Health Economics', credits: 3, status: 'locked', grade: null },
      { code: 'PBHL 370', name: 'Community Health', credits: 3, status: 'locked', grade: null },
    ]
  },
  {
    semester: 'Year 4 - Fall',
    courses: [
      { code: 'PBHL 401', name: 'Capstone I', credits: 3, status: 'locked', grade: null },
      { code: 'PBHL 410', name: 'Program Evaluation', credits: 3, status: 'locked', grade: null },
      { code: 'PBHL 420', name: 'Health Promotion', credits: 3, status: 'locked', grade: null },
      { code: 'PBHL 4XX', name: 'Elective', credits: 3, status: 'locked', grade: null },
    ]
  },
  {
    semester: 'Year 4 - Spring',
    courses: [
      { code: 'PBHL 402', name: 'Capstone II', credits: 3, status: 'locked', grade: null },
      { code: 'PBHL 430', name: 'Public Health Leadership', credits: 3, status: 'locked', grade: null },
      { code: 'PBHL 4XX', name: 'Elective', credits: 3, status: 'locked', grade: null },
      { code: 'PBHL 4XX', name: 'Elective', credits: 3, status: 'locked', grade: null },
    ]
  },
];

export default function StudentDegreePlanPage() {
  const { user } = useAuth();

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'registered': return <Clock className="h-4 w-4 text-blue-500" />;
      case 'available': return <BookOpen className="h-4 w-4 text-orange-500" />;
      case 'locked': return <Lock className="h-4 w-4 text-gray-400" />;
      default: return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-50 border-green-200';
      case 'registered': return 'bg-blue-50 border-blue-200';
      case 'available': return 'bg-orange-50 border-orange-200';
      case 'locked': return 'bg-gray-50 border-gray-200 opacity-60';
      default: return 'bg-gray-50';
    }
  };

  const totalCredits = degreePlan.flatMap(s => s.courses).reduce((acc, c) => acc + c.credits, 0);
  const completedCredits = degreePlan.flatMap(s => s.courses).filter(c => c.status === 'completed').reduce((acc, c) => acc + c.credits, 0);
  const registeredCredits = degreePlan.flatMap(s => s.courses).filter(c => c.status === 'registered').reduce((acc, c) => acc + c.credits, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">Degree Plan</h1>
          <p className="text-muted-foreground">Bachelor of Science in Public Health</p>
        </div>
        <Button variant="outline">
          <Download className="h-4 w-4 mr-2" />
          Export Plan
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold">{totalCredits}</div>
              <div className="text-sm text-muted-foreground">Total Credits</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">{completedCredits}</div>
              <div className="text-sm text-muted-foreground">Completed</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">{registeredCredits}</div>
              <div className="text-sm text-muted-foreground">Registered</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-600">{totalCredits - completedCredits - registeredCredits}</div>
              <div className="text-sm text-muted-foreground">Remaining</div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <CheckCircle className="h-4 w-4 text-green-500" />
          <span>Completed</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-blue-500" />
          <span>Registered</span>
        </div>
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-orange-500" />
          <span>Available</span>
        </div>
        <div className="flex items-center gap-2">
          <Lock className="h-4 w-4 text-gray-400" />
          <span>Locked</span>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {degreePlan.map((semester, index) => (
          <Card key={index}>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">{semester.semester}</CardTitle>
              <CardDescription>
                {semester.courses.reduce((acc, c) => acc + c.credits, 0)} credits
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {semester.courses.map((course, i) => (
                  <div 
                    key={i}
                    className={`flex items-center justify-between p-3 rounded-lg border ${getStatusColor(course.status)}`}
                  >
                    <div className="flex items-center gap-3">
                      {getStatusIcon(course.status)}
                      <div>
                        <p className="font-medium text-sm">{course.code}</p>
                        <p className="text-xs text-muted-foreground">{course.name}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">{course.credits} cr</Badge>
                      {course.grade && (
                        <Badge className="bg-green-100 text-green-800 text-xs">{course.grade}</Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
