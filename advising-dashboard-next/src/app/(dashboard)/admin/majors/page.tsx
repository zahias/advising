'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { 
  Plus,
  Edit,
  Trash2,
  GraduationCap,
  Users,
  BookOpen,
  Settings
} from 'lucide-react';

const sampleMajors = [
  { 
    id: '1', 
    code: 'PBHL', 
    name: 'Public Health', 
    description: 'Bachelor of Science in Public Health',
    totalCredits: 120,
    courses: 42,
    students: 234,
    advisors: 3,
    status: 'active',
    color: '#3B82F6'
  },
  { 
    id: '2', 
    code: 'SPTH-New', 
    name: 'Speech Therapy (New Curriculum)', 
    description: 'Bachelor of Science in Speech-Language Pathology',
    totalCredits: 125,
    courses: 48,
    students: 156,
    advisors: 2,
    status: 'active',
    color: '#10B981'
  },
  { 
    id: '3', 
    code: 'SPTH-Old', 
    name: 'Speech Therapy (Old Curriculum)', 
    description: 'Bachelor of Science in Speech-Language Pathology (Legacy)',
    totalCredits: 122,
    courses: 45,
    students: 89,
    advisors: 2,
    status: 'legacy',
    color: '#F59E0B'
  },
  { 
    id: '4', 
    code: 'NURS', 
    name: 'Nursing', 
    description: 'Bachelor of Science in Nursing',
    totalCredits: 128,
    courses: 52,
    students: 368,
    advisors: 4,
    status: 'active',
    color: '#EF4444'
  },
];

export default function AdminMajorsPage() {
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Major Manager</h1>
          <p className="text-muted-foreground">Configure academic programs and requirements</p>
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Major
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Major</DialogTitle>
              <DialogDescription>
                Create a new academic program
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Major Code</Label>
                  <Input placeholder="e.g., PBHL" />
                </div>
                <div className="space-y-2">
                  <Label>Total Credits</Label>
                  <Input type="number" placeholder="120" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Program Name</Label>
                <Input placeholder="e.g., Public Health" />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea placeholder="Program description..." />
              </div>
              <div className="space-y-2">
                <Label>Theme Color</Label>
                <div className="flex gap-2">
                  {['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'].map(color => (
                    <button
                      key={color}
                      className="w-8 h-8 rounded-full border-2 border-white shadow"
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>Cancel</Button>
              <Button onClick={() => setIsAddDialogOpen(false)}>Add Major</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {sampleMajors.map(major => (
          <Card key={major.id} className="overflow-hidden">
            <div className="h-2" style={{ backgroundColor: major.color }} />
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <span 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: major.color }}
                    />
                    {major.code}
                  </CardTitle>
                  <CardDescription className="mt-1">{major.name}</CardDescription>
                </div>
                <Badge variant={major.status === 'active' ? 'default' : 'secondary'}>
                  {major.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">{major.description}</p>
              
              <div className="grid grid-cols-4 gap-4 pt-4 border-t">
                <div className="text-center">
                  <div className="flex justify-center mb-1">
                    <GraduationCap className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="text-lg font-bold">{major.totalCredits}</div>
                  <div className="text-xs text-muted-foreground">Credits</div>
                </div>
                <div className="text-center">
                  <div className="flex justify-center mb-1">
                    <BookOpen className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="text-lg font-bold">{major.courses}</div>
                  <div className="text-xs text-muted-foreground">Courses</div>
                </div>
                <div className="text-center">
                  <div className="flex justify-center mb-1">
                    <Users className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="text-lg font-bold">{major.students}</div>
                  <div className="text-xs text-muted-foreground">Students</div>
                </div>
                <div className="text-center">
                  <div className="flex justify-center mb-1">
                    <Users className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="text-lg font-bold">{major.advisors}</div>
                  <div className="text-xs text-muted-foreground">Advisors</div>
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t">
                <Button variant="outline" size="sm" className="flex-1">
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </Button>
                <Button variant="outline" size="sm" className="flex-1">
                  <Settings className="h-4 w-4 mr-2" />
                  Configure
                </Button>
                <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
