'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
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
  Mail,
  Calendar,
  Database,
  Shield,
  Save,
  RefreshCw,
  CheckCircle,
  Upload,
  AlertCircle,
} from 'lucide-react';

export default function AdminSettingsPage() {
  const [periods, setPeriods] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'success' | 'error' | null>(null);
  const [seedStatus, setSeedStatus] = useState<string | null>(null);

  const [emailSettings, setEmailSettings] = useState({
    smtpHost: 'smtp.office365.com',
    smtpPort: '587',
    smtpUser: '',
    smtpPassword: '',
    fromEmail: '',
    fromName: 'Academic Advising',
    enabled: true,
  });

  const [advisingSettings, setAdvisingSettings] = useState({
    currentPeriodId: '',
    autoSendConfirmation: true,
    requireSignature: false,
    allowSelfAdvising: false,
    maxCoursesPerSession: '6',
  });

  const [securitySettings, setSecuritySettings] = useState({
    sessionTimeout: '30',
    requireRoleSelection: true,
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [periodsRes, settingsRes] = await Promise.all([
        fetch('/api/periods'),
        fetch('/api/settings'),
      ]);
      
      if (periodsRes.ok) {
        const periodsData = await periodsRes.json();
        setPeriods(periodsData);
        if (periodsData.length > 0) {
          const activePeriod = periodsData.find((p: any) => p.isActive) || periodsData[0];
          setAdvisingSettings(prev => ({ ...prev, currentPeriodId: activePeriod.id }));
        }
      }
      
      if (settingsRes.ok) {
        const settingsData = await settingsRes.json();
        for (const setting of settingsData) {
          if (setting.key === 'email' && setting.value) {
            setEmailSettings(prev => ({ ...prev, ...setting.value }));
          } else if (setting.key === 'advising' && setting.value) {
            setAdvisingSettings(prev => ({ ...prev, ...setting.value }));
          } else if (setting.key === 'security' && setting.value) {
            setSecuritySettings(prev => ({ ...prev, ...setting.value }));
          }
        }
      }
    } catch (error) {
      console.error('Error fetching data:', error);
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
    setSaveStatus(null);
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          settings: [
            { key: 'email', value: emailSettings, category: 'email' },
            { key: 'advising', value: advisingSettings, category: 'advising' },
            { key: 'security', value: securitySettings, category: 'security' },
          ],
        }),
      });
      
      if (res.ok) {
        setSaveStatus('success');
        setTimeout(() => setSaveStatus(null), 3000);
      } else {
        setSaveStatus('error');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  };
  
  const handleTestEmail = async () => {
    try {
      const res = await fetch('/api/email/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipientEmail: emailSettings.fromEmail || emailSettings.smtpUser,
          subject: 'Test Email from Advising Dashboard',
          body: '<p>This is a test email from the Advising Dashboard. If you received this, your email settings are configured correctly.</p>',
        }),
      });
      
      const data = await res.json();
      if (data.success) {
        alert('Test email sent successfully!');
      } else {
        alert(`Email status: ${data.status} - ${data.message}`);
      }
    } catch (error) {
      alert('Failed to send test email. Please check your settings.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground">Configure system-wide settings and preferences</p>
        </div>
        <Button onClick={handleSave} disabled={saving} variant={saveStatus === 'success' ? 'default' : saveStatus === 'error' ? 'destructive' : 'default'}>
          {saving ? (
            <><RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Saving...</>
          ) : saveStatus === 'success' ? (
            <><CheckCircle className="h-4 w-4 mr-2" /> Saved!</>
          ) : saveStatus === 'error' ? (
            <><AlertCircle className="h-4 w-4 mr-2" /> Error - Try Again</>
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
                    placeholder="smtp.office365.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label>SMTP Port</Label>
                  <Input 
                    value={emailSettings.smtpPort}
                    onChange={(e) => setEmailSettings(prev => ({ ...prev, smtpPort: e.target.value }))}
                    placeholder="587"
                  />
                </div>
                <div className="space-y-2">
                  <Label>SMTP Username</Label>
                  <Input 
                    type="email"
                    placeholder="advising@university.edu"
                    value={emailSettings.smtpUser}
                    onChange={(e) => setEmailSettings(prev => ({ ...prev, smtpUser: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>SMTP Password</Label>
                  <Input 
                    type="password"
                    placeholder="••••••••"
                    value={emailSettings.smtpPassword}
                    onChange={(e) => setEmailSettings(prev => ({ ...prev, smtpPassword: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>From Email Address</Label>
                  <Input 
                    type="email"
                    placeholder="advising@university.edu"
                    value={emailSettings.fromEmail}
                    onChange={(e) => setEmailSettings(prev => ({ ...prev, fromEmail: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>From Name</Label>
                  <Input 
                    value={emailSettings.fromName}
                    onChange={(e) => setEmailSettings(prev => ({ ...prev, fromName: e.target.value }))}
                    placeholder="Academic Advising"
                  />
                </div>
              </div>

              <Button variant="outline" onClick={handleTestEmail}>
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
                  <Input 
                    type="number" 
                    className="w-24" 
                    value={securitySettings.sessionTimeout}
                    onChange={(e) => setSecuritySettings(prev => ({ ...prev, sessionTimeout: e.target.value }))}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Require Role Selection</Label>
                    <p className="text-sm text-muted-foreground">Users must select role on each login</p>
                  </div>
                  <Switch 
                    checked={securitySettings.requireRoleSelection}
                    onCheckedChange={(checked) => setSecuritySettings(prev => ({ ...prev, requireRoleSelection: checked }))}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
