'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  GraduationCap,
  Mail,
  Send,
  Users,
  Clock,
  CheckCircle,
  FileText,
} from 'lucide-react';

interface Student {
  id: string;
  studentId: string;
  name: string;
  email: string;
}

export default function AdvisorEmailPage() {
  const { currentMajor, user } = useAuth();
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudents, setSelectedStudents] = useState<string[]>([]);
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchStudents();
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

  const toggleStudent = (studentId: string) => {
    setSelectedStudents(prev => 
      prev.includes(studentId) 
        ? prev.filter(id => id !== studentId)
        : [...prev, studentId]
    );
  };

  const selectAll = () => {
    if (selectedStudents.length === students.length) {
      setSelectedStudents([]);
    } else {
      setSelectedStudents(students.map(s => s.id));
    }
  };

  const handleSend = async () => {
    if (!subject || !message || selectedStudents.length === 0) return;
    
    setSending(true);
    await new Promise(resolve => setTimeout(resolve, 1500));
    setSending(false);
    
    setSubject('');
    setMessage('');
    setSelectedStudents([]);
  };

  const templates = [
    {
      name: 'Advising Reminder',
      subject: 'Advising Appointment Reminder',
      body: 'Dear {student_name},\n\nThis is a reminder that you have an upcoming advising appointment. Please make sure to review your degree progress before our meeting.\n\nBest regards,\n{advisor_name}',
    },
    {
      name: 'Registration Open',
      subject: 'Course Registration Now Open',
      body: 'Dear {student_name},\n\nCourse registration for the upcoming semester is now open. Based on our advising session, please register for your approved courses as soon as possible.\n\nIf you have any questions, please contact me.\n\nBest regards,\n{advisor_name}',
    },
    {
      name: 'Session Follow-up',
      subject: 'Advising Session Follow-up',
      body: 'Dear {student_name},\n\nThank you for meeting with me for advising. As discussed, please find your recommended courses attached.\n\nRemember to register before the deadline.\n\nBest regards,\n{advisor_name}',
    },
  ];

  const useTemplate = (template: typeof templates[0]) => {
    setSubject(template.subject);
    setMessage(template.body.replace('{advisor_name}', user?.name || 'Advisor'));
  };

  if (!currentMajor) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <GraduationCap className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-2xl font-bold">Select a Major</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Please select a major from the dropdown in the header to send emails.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Email Students</h1>
        <p className="text-muted-foreground">Send emails to students in {currentMajor}</p>
      </div>

      <Tabs defaultValue="compose" className="space-y-6">
        <TabsList>
          <TabsTrigger value="compose">
            <Mail className="h-4 w-4 mr-2" />
            Compose
          </TabsTrigger>
          <TabsTrigger value="templates">
            <FileText className="h-4 w-4 mr-2" />
            Templates
          </TabsTrigger>
          <TabsTrigger value="history">
            <Clock className="h-4 w-4 mr-2" />
            History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="compose" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Compose Email</CardTitle>
                <CardDescription>Write and send emails to selected students</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Subject</Label>
                  <Input 
                    placeholder="Email subject..."
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Message</Label>
                  <Textarea 
                    placeholder="Write your message here..."
                    className="min-h-[200px]"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                  />
                </div>
                <div className="flex items-center justify-between pt-4">
                  <p className="text-sm text-muted-foreground">
                    {selectedStudents.length} recipient(s) selected
                  </p>
                  <Button 
                    onClick={handleSend}
                    disabled={!subject || !message || selectedStudents.length === 0 || sending}
                  >
                    {sending ? (
                      <>Sending...</>
                    ) : (
                      <><Send className="h-4 w-4 mr-2" /> Send Email</>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Recipients</CardTitle>
                    <CardDescription>{students.length} students</CardDescription>
                  </div>
                  <Button variant="outline" size="sm" onClick={selectAll}>
                    {selectedStudents.length === students.length ? 'Deselect All' : 'Select All'}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="max-h-[400px] overflow-y-auto space-y-2">
                  {students.map(student => (
                    <div 
                      key={student.id}
                      className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer hover:bg-muted ${
                        selectedStudents.includes(student.id) ? 'bg-primary/10' : ''
                      }`}
                      onClick={() => toggleStudent(student.id)}
                    >
                      <Checkbox 
                        checked={selectedStudents.includes(student.id)}
                        onCheckedChange={() => toggleStudent(student.id)}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{student.name}</p>
                        <p className="text-xs text-muted-foreground truncate">{student.email}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="templates">
          <div className="grid gap-4 md:grid-cols-3">
            {templates.map((template, i) => (
              <Card key={i}>
                <CardHeader>
                  <CardTitle className="text-lg">{template.name}</CardTitle>
                  <CardDescription>{template.subject}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
                    {template.body}
                  </p>
                  <Button 
                    variant="outline" 
                    className="w-full"
                    onClick={() => useTemplate(template)}
                  >
                    Use Template
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle>Email History</CardTitle>
              <CardDescription>Previously sent emails</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">Registration Open</h4>
                    <Badge variant="secondary">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Sent
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">Sent to 45 students • Dec 1, 2025</p>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">Advising Reminder</h4>
                    <Badge variant="secondary">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Sent
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">Sent to 12 students • Nov 28, 2025</p>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">Session Follow-up</h4>
                    <Badge variant="secondary">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Sent
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">Sent to 8 students • Nov 25, 2025</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
