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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  GraduationCap,
  Mail,
  Send,
  Clock,
  CheckCircle,
  FileText,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

interface Student {
  id: string;
  studentId: string;
  name: string;
  email: string;
}

interface EmailLog {
  id: string;
  recipientEmail: string;
  subject: string;
  status: string;
  sentAt: string;
  studentId?: string;
}

export default function AdvisorEmailPage() {
  const { currentMajor, user } = useAuth();
  const [students, setStudents] = useState<Student[]>([]);
  const [emailLogs, setEmailLogs] = useState<EmailLog[]>([]);
  const [selectedStudents, setSelectedStudents] = useState<string[]>([]);
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    fetchStudents();
    fetchEmailHistory();
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

  const fetchEmailHistory = async () => {
    try {
      const res = await fetch('/api/email/send?limit=20');
      if (res.ok) {
        const data = await res.json();
        setEmailLogs(data);
      }
    } catch (error) {
      console.error('Error fetching email history:', error);
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
    setSendResult(null);
    
    const selectedStudentData = students.filter(s => selectedStudents.includes(s.id));
    let successCount = 0;
    let failCount = 0;
    
    for (const student of selectedStudentData) {
      if (!student.email) {
        failCount++;
        continue;
      }
      
      const personalizedMessage = message
        .replace(/{student_name}/g, student.name)
        .replace(/{student_id}/g, student.studentId)
        .replace(/{advisor_name}/g, user?.name || 'Advisor');
      
      try {
        const res = await fetch('/api/email/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            studentId: student.id,
            recipientEmail: student.email,
            subject: subject,
            body: `<div style="font-family: sans-serif;">${personalizedMessage.replace(/\n/g, '<br>')}</div>`,
          }),
        });
        
        const result = await res.json();
        if (result.success || result.status === 'queued') {
          successCount++;
        } else {
          failCount++;
        }
      } catch {
        failCount++;
      }
    }
    
    setSending(false);
    fetchEmailHistory();
    
    if (successCount > 0 && failCount === 0) {
      setSendResult({ success: true, message: `Successfully sent to ${successCount} student(s)` });
      setSubject('');
      setMessage('');
      setSelectedStudents([]);
    } else if (successCount > 0) {
      setSendResult({ success: true, message: `Sent to ${successCount}, failed for ${failCount} student(s)` });
    } else {
      setSendResult({ success: false, message: 'Failed to send emails. Please check SMTP settings.' });
    }
    
    setTimeout(() => setSendResult(null), 5000);
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
      body: 'Dear {student_name},\n\nThank you for meeting with me for advising. As discussed, please find your recommended courses in the student portal.\n\nRemember to register before the deadline.\n\nBest regards,\n{advisor_name}',
    },
  ];

  const useTemplate = (template: typeof templates[0]) => {
    setSubject(template.subject);
    setMessage(template.body);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'sent':
        return <Badge variant="default" className="bg-green-500"><CheckCircle className="h-3 w-3 mr-1" />Sent</Badge>;
      case 'queued':
        return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" />Queued</Badge>;
      case 'failed':
        return <Badge variant="destructive"><AlertCircle className="h-3 w-3 mr-1" />Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
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

      {sendResult && (
        <div className={`p-4 rounded-lg ${sendResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
          <div className="flex items-center gap-2">
            {sendResult.success ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : (
              <AlertCircle className="h-5 w-5 text-red-500" />
            )}
            <span className={sendResult.success ? 'text-green-700' : 'text-red-700'}>
              {sendResult.message}
            </span>
          </div>
        </div>
      )}

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
                    placeholder="Write your message here... Use {student_name} for personalization"
                    className="min-h-[200px]"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Available tokens: {'{student_name}'}, {'{student_id}'}, {'{advisor_name}'}
                  </p>
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
                      <><RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Sending...</>
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
                        <p className="text-xs text-muted-foreground truncate">
                          {student.email || 'No email'}
                        </p>
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
              {emailLogs.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No emails sent yet</p>
              ) : (
                <div className="space-y-3">
                  {emailLogs.map(log => (
                    <div key={log.id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium">{log.subject}</h4>
                        {getStatusBadge(log.status)}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        To: {log.recipientEmail} • {new Date(log.sentAt).toLocaleDateString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
