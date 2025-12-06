'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { 
  Search,
  Plus,
  Edit,
  Trash2,
  BookOpen,
  Filter
} from 'lucide-react';

const sampleCourses = [
  { id: '1', code: 'PBHL 101', name: 'Introduction to Public Health', credits: 3, type: 'Required', semester: 1, offered: true, prereqs: [], major: 'PBHL' },
  { id: '2', code: 'PBHL 201', name: 'Health Behavior', credits: 3, type: 'Required', semester: 2, offered: true, prereqs: ['PBHL 101'], major: 'PBHL' },
  { id: '3', code: 'PBHL 301', name: 'Epidemiology', credits: 3, type: 'Required', semester: 3, offered: true, prereqs: ['PBHL 101', 'PBHL 201'], major: 'PBHL' },
  { id: '4', code: 'PBHL 305', name: 'Biostatistics', credits: 3, type: 'Required', semester: 3, offered: true, prereqs: ['MATH 201'], major: 'PBHL' },
  { id: '5', code: 'PBHL 320', name: 'Health Policy', credits: 3, type: 'Required', semester: 4, offered: false, prereqs: ['PBHL 201'], major: 'PBHL' },
  { id: '6', code: 'PBHL 350', name: 'Global Health', credits: 3, type: 'Intensive', semester: 5, offered: true, prereqs: ['PBHL 301'], major: 'PBHL' },
  { id: '7', code: 'SPTH 101', name: 'Introduction to Speech Therapy', credits: 3, type: 'Required', semester: 1, offered: true, prereqs: [], major: 'SPTH-New' },
  { id: '8', code: 'NURS 101', name: 'Fundamentals of Nursing', credits: 4, type: 'Required', semester: 1, offered: true, prereqs: [], major: 'NURS' },
];

export default function AdminCoursesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [majorFilter, setMajorFilter] = useState<string>('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

  const filteredCourses = sampleCourses.filter(course => {
    const matchesSearch = course.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          course.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesMajor = majorFilter === 'all' || course.major === majorFilter;
    return matchesSearch && matchesMajor;
  });

  const majors = ['all', ...new Set(sampleCourses.map(c => c.major))];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Course Manager</h1>
          <p className="text-muted-foreground">Manage courses across all majors</p>
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Course
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Add New Course</DialogTitle>
              <DialogDescription>
                Create a new course and set its prerequisites
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Course Code</Label>
                  <Input placeholder="e.g., PBHL 401" />
                </div>
                <div className="space-y-2">
                  <Label>Credits</Label>
                  <Input type="number" placeholder="3" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Course Name</Label>
                <Input placeholder="e.g., Advanced Epidemiology" />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Major</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select major" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PBHL">PBHL</SelectItem>
                      <SelectItem value="SPTH-New">SPTH-New</SelectItem>
                      <SelectItem value="SPTH-Old">SPTH-Old</SelectItem>
                      <SelectItem value="NURS">NURS</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Required">Required</SelectItem>
                      <SelectItem value="Intensive">Intensive</SelectItem>
                      <SelectItem value="Elective">Elective</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Semester</Label>
                  <Input type="number" placeholder="1-8" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Prerequisites (comma separated)</Label>
                <Input placeholder="e.g., PBHL 101, PBHL 201" />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea placeholder="Course description..." />
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox id="offered" defaultChecked />
                <Label htmlFor="offered">Currently Offered</Label>
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>Cancel</Button>
              <Button onClick={() => setIsAddDialogOpen(false)}>Add Course</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search courses..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={majorFilter} onValueChange={setMajorFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by major" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Majors</SelectItem>
                {majors.filter(m => m !== 'all').map(major => (
                  <SelectItem key={major} value={major}>{major}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Major</TableHead>
                <TableHead className="text-center">Credits</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-center">Semester</TableHead>
                <TableHead>Prerequisites</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCourses.map((course) => (
                <TableRow key={course.id}>
                  <TableCell className="font-medium">{course.code}</TableCell>
                  <TableCell>{course.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{course.major}</Badge>
                  </TableCell>
                  <TableCell className="text-center">{course.credits}</TableCell>
                  <TableCell>
                    <Badge variant={course.type === 'Required' ? 'default' : 'secondary'}>
                      {course.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">{course.semester}</TableCell>
                  <TableCell>
                    {course.prereqs.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {course.prereqs.map(p => (
                          <Badge key={p} variant="outline" className="text-xs">{p}</Badge>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-sm">None</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={course.offered ? 'default' : 'secondary'} className={course.offered ? 'bg-green-100 text-green-800' : ''}>
                      {course.offered ? 'Offered' : 'Not Offered'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
