'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth/context';
import { 
  CheckCircle,
  Calendar,
  User,
  FileText,
  Download,
  Mail
} from 'lucide-react';

const advisingHistory = [
  {
    date: '2024-12-04',
    advisor: 'Dr. Robert Johnson',
    semester: 'Spring 2025',
    courses: [
      { code: 'PBHL 301', name: 'Epidemiology', credits: 3 },
      { code: 'PBHL 305', name: 'Biostatistics', credits: 3 },
      { code: 'PBHL 320', name: 'Health Policy', credits: 3 },
    ],
    notes: 'Student is on track for Spring 2027 graduation. Recommended completing Epidemiology before Environmental Health.',
    status: 'current'
  },
  {
    date: '2024-08-15',
    advisor: 'Dr. Robert Johnson',
    semester: 'Fall 2024',
    courses: [
      { code: 'PBHL 201', name: 'Health Behavior', credits: 3 },
      { code: 'PBHL 202', name: 'Health Communication', credits: 3 },
      { code: 'PBHL 250', name: 'Research Methods', credits: 3 },
    ],
    notes: 'Focus on core requirements this semester. Consider summer internship for practical experience.',
    status: 'completed'
  },
  {
    date: '2024-04-10',
    advisor: 'Dr. Jane Smith',
    semester: 'Summer 2024',
    courses: [
      { code: 'PBHL 290', name: 'Internship', credits: 3 },
    ],
    notes: 'Approved internship at local health department. Student to submit hours log by end of summer.',
    status: 'completed'
  },
];

export default function StudentAdvisedPage() {
  const { user } = useAuth();

  const currentAdvising = advisingHistory.find(a => a.status === 'current');
  const pastAdvising = advisingHistory.filter(a => a.status === 'completed');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Advised Courses</h1>
        <p className="text-muted-foreground">View your advising history and recommendations</p>
      </div>

      {currentAdvising && (
        <Card className="border-primary">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-primary">
                  <CheckCircle className="h-5 w-5" />
                  Current Advising - {currentAdvising.semester}
                </CardTitle>
                <CardDescription className="mt-1">
                  Advised on {currentAdvising.date} by {currentAdvising.advisor}
                </CardDescription>
              </div>
              <Badge className="bg-primary">Current</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              {currentAdvising.courses.map(course => (
                <div 
                  key={course.code}
                  className="flex items-center justify-between p-3 rounded-lg bg-primary/5 border border-primary/20"
                >
                  <div>
                    <p className="font-medium">{course.code}</p>
                    <p className="text-sm text-muted-foreground">{course.name}</p>
                  </div>
                  <Badge variant="outline">{course.credits} credits</Badge>
                </div>
              ))}
            </div>

            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-start gap-2">
                <FileText className="h-4 w-4 mt-0.5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Advisor Notes</p>
                  <p className="text-sm text-muted-foreground">{currentAdvising.notes}</p>
                </div>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Download PDF
              </Button>
              <Button variant="outline" size="sm">
                <Mail className="h-4 w-4 mr-2" />
                Email to Self
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div>
        <h2 className="text-xl font-semibold mb-4">Past Advising Sessions</h2>
        <div className="space-y-4">
          {pastAdvising.map((session, index) => (
            <Card key={index}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{session.semester}</CardTitle>
                    <CardDescription className="flex items-center gap-4 mt-1">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {session.date}
                      </span>
                      <span className="flex items-center gap-1">
                        <User className="h-3 w-3" />
                        {session.advisor}
                      </span>
                    </CardDescription>
                  </div>
                  <Badge variant="secondary">Completed</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2 mb-4">
                  {session.courses.map(course => (
                    <Badge key={course.code} variant="outline">
                      {course.code} ({course.credits} cr)
                    </Badge>
                  ))}
                </div>
                <p className="text-sm text-muted-foreground">{session.notes}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
