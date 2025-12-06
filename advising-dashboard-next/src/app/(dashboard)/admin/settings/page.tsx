'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Settings,
  Mail,
  Calendar,
  Database,
  Shield,
  Bell,
  Save,
  RefreshCw,
  CheckCircle,
  Upload,
} from 'lucide-react';

export default function AdminSettingsPage() {
  const [periods, setPeriods] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [seedStatus, setSeedStatus] = useState<string | null>(null);

  const [emailSettings, setEmailSettings] = useState({
    smtpHost: 'smtp.office365.com',
    smtpPort: '587',
    senderEmail: '',
    senderName: 'Academic Advising',
    enabled: true,
  });

  const [advisingSettings, setAdvisingSettings] = useState({
    currentPeriodId: '',
    autoSendConfirmation: true,
    requireSignature: false,
    allowSelfAdvising: false,
    maxCoursesPerSession: '6',
  });

  useEffect(() => {
    fetchPeriods();
  }, []);

  const fetchPeriods = async () => {
    try {
      const res = await fetch('/api/periods');
      if (res.ok) {
        const data = await res.json();
        setPeriods(data);
        if (data.length > 0) {
          const activePeriod = data.find((p: any) => p.isActive) || data[0];
          setAdvisingSettings(prev => ({ ...prev, currentPeriodId: activePeriod.id }));
        }
      }
    } catch (error) {
      console.error('Error fetching periods:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSeedDatabase = async () => {
    setSeedStatus('seeding');
    try {
      const res = await fetch('/api/seed', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setSeedStatus('success');
        setTimeout(() => setSeedStatus(null), 3000);
        fetchPeriods();
      } else {
        setSeedStatus('error');
        console.error('Seed error:', data.error);
      }
    } catch (error) {
      setSeedStatus('error');
      console.error('Seed error:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setSaving(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground">Configure system-wide settings and preferences</p>
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <><RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Saving...</>
          ) : (
            <><Save className="h-4 w-4 mr-2" /> Save Changes</>
          )}
        </Button>
      </div>

      <Tabs defaultValue="advising" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="advising">
            <Calendar className="h-4 w-4 mr-2" />
            Advising
          </TabsTrigger>
          <TabsTrigger value="email">
            <Mail className="h-4 w-4 mr-2" />
            Email
          </TabsTrigger>
          <TabsTrigger value="database">
            <Database className="h-4 w-4 mr-2" />
            Database
          </TabsTrigger>
          <TabsTrigger value="security">
            <Shield className="h-4 w-4 mr-2" />
            Security
          </TabsTrigger>
        </TabsList>

        <TabsContent value="advising" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Advising Period</CardTitle>
              <CardDescription>Configure the current advising period and session settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Current Advising Period</Label>
                  <Select 
                    value={advisingSettings.currentPeriodId} 
                    onValueChange={(value) => setAdvisingSettings(prev => ({ ...prev, currentPeriodId: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select period" />
                    </SelectTrigger>
                    <SelectContent>
                      {periods.map(period => (
                        <SelectItem key={period.id} value={period.id}>
                          {period.name} {period.isActive && <Badge className="ml-2">Active</Badge>}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Max Courses Per Session</Label>
                  <Input 
                    type="number" 
                    value={advisingSettings.maxCoursesPerSession}
                    onChange={(e) => setAdvisingSettings(prev => ({ ...prev, maxCoursesPerSession: e.target.value }))}
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Auto-send Confirmation Email</Label>
                    <p className="text-sm text-muted-foreground">Send email to students after advising session</p>
                  </div>
                  <Switch 
                    checked={advisingSettings.autoSendConfirmation}
                    onCheckedChange={(checked) => setAdvisingSettings(prev => ({ ...prev, autoSendConfirmation: checked }))}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Require Student Signature</Label>
                    <p className="text-sm text-muted-foreground">Students must sign off on advising plan</p>
                  </div>
                  <Switch 
                    checked={advisingSettings.requireSignature}
                    onCheckedChange={(checked) => setAdvisingSettings(prev => ({ ...prev, requireSignature: checked }))}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Allow Self-Advising</Label>
                    <p className="text-sm text-muted-foreground">Students can create their own advising sessions</p>
                  </div>
                  <Switch 
                    checked={advisingSettings.allowSelfAdvising}
                    onCheckedChange={(checked) => setAdvisingSettings(prev => ({ ...prev, allowSelfAdvising: checked }))}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="email" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Email Configuration</CardTitle>
              <CardDescription>Configure SMTP settings for sending emails</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                <div>
                  <Label>Email Notifications</Label>
                  <p className="text-sm text-muted-foreground">Enable or disable all email notifications</p>
                </div>
                <Switch 
                  checked={emailSettings.enabled}
                  onCheckedChange={(checked) => setEmailSettings(prev => ({ ...prev, enabled: checked }))}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>SMTP Host</Label>
                  <Input 
                    value={emailSettings.smtpHost}
                    onChange={(e) => setEmailSettings(prev => ({ ...prev, smtpHost: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>SMTP Port</Label>
                  <Input 
                    value={emailSettings.smtpPort}
                    onChange={(e) => setEmailSettings(prev => ({ ...prev, smtpPort: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Sender Email</Label>
                  <Input 
                    type="email"
                    placeholder="advising@university.edu"
                    value={emailSettings.senderEmail}
                    onChange={(e) => setEmailSettings(prev => ({ ...prev, senderEmail: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Sender Name</Label>
                  <Input 
                    value={emailSettings.senderName}
                    onChange={(e) => setEmailSettings(prev => ({ ...prev, senderName: e.target.value }))}
                  />
                </div>
              </div>

              <Button variant="outline">
                <Mail className="h-4 w-4 mr-2" />
                Send Test Email
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="database" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Database Management</CardTitle>
              <CardDescription>Manage database operations and sample data</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="p-4 border rounded-lg space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">Seed Sample Data</h3>
                    <p className="text-sm text-muted-foreground">
                      Populate database with sample majors, courses, students, and advising periods for testing
                    </p>
                  </div>
                  <Button 
                    variant="outline" 
                    onClick={handleSeedDatabase}
                    disabled={seedStatus === 'seeding'}
                  >
                    {seedStatus === 'seeding' ? (
                      <><RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Seeding...</>
                    ) : seedStatus === 'success' ? (
                      <><CheckCircle className="h-4 w-4 mr-2 text-green-500" /> Done!</>
                    ) : (
                      <><Database className="h-4 w-4 mr-2" /> Seed Database</>
                    )}
                  </Button>
                </div>
              </div>

              <div className="p-4 border rounded-lg space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">Import Data</h3>
                    <p className="text-sm text-muted-foreground">
                      Import courses or student progress from Excel files
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      <Upload className="h-4 w-4 mr-2" />
                      Import Courses
                    </Button>
                    <Button variant="outline" size="sm">
                      <Upload className="h-4 w-4 mr-2" />
                      Import Students
                    </Button>
                  </div>
                </div>
              </div>

              <div className="p-4 border border-red-200 bg-red-50 rounded-lg space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-red-800">Danger Zone</h3>
                    <p className="text-sm text-red-600">
                      Clear all data from the database. This action cannot be undone.
                    </p>
                  </div>
                  <Button variant="destructive" size="sm">
                    Clear Database
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>Configure authentication and access controls</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="p-4 bg-muted rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="h-5 w-5 text-blue-500" />
                  <h3 className="font-medium">Microsoft 365 SSO</h3>
                  <Badge variant="secondary">Coming Soon</Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Single Sign-On with Microsoft 365 is pending IT approval. Currently using demo authentication.
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Session Timeout</Label>
                    <p className="text-sm text-muted-foreground">Auto-logout after inactivity (minutes)</p>
                  </div>
                  <Input type="number" className="w-24" defaultValue="30" />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Require Role Selection</Label>
                    <p className="text-sm text-muted-foreground">Users must select role on each login</p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
