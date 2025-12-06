'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/lib/auth/context';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
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
} from '@/components/ui/dialog';
import {
  GraduationCap,
  Search,
  BookOpen,
  Download,
  Plus,
  Pencil,
  Trash2,
  Save,
} from 'lucide-react';

interface Course {
  id: string;
  majorId: string;
  code: string;
  name: string;
  credits: number;
  type: string;
  semester?: number;
  offered?: boolean;
  prerequisites?: string[];
  corequisites?: string[];
  concurrent?: string[];
  standingRequired?: string;
  description?: string;
}

interface Major {
  id: string;
  code: string;
  name: string;
}

const COURSE_TYPES = ['required', 'core', 'elective', 'general', 'prerequisite'];
const STANDINGS = ['Freshman', 'Sophomore', 'Junior', 'Senior'];

export default function AdvisorCoursesPage() {
  const { currentMajor } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [majors, setMajors] = useState<Major[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    credits: 3,
    type: 'required',
    semester: '',
    prerequisites: '',
    corequisites: '',
    concurrent: '',
    standingRequired: '',
    description: '',
  });

  useEffect(() => {
    fetchData();
  }, [currentMajor]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [coursesRes, majorsRes] = await Promise.all([
        fetch(`/api/courses${currentMajor ? `?major=${currentMajor}` : ''}`),
        fetch('/api/majors'),
      ]);
      
      if (coursesRes.ok) {
        const data = await coursesRes.json();
        setCourses(data);
      }
      if (majorsRes.ok) {
        const data = await majorsRes.json();
        setMajors(data);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getCurrentMajorId = () => {
    const major = majors.find(m => m.code === currentMajor);
    return major?.id;
  };

  const courseTypes = [...new Set(courses.map(c => c.type || 'General'))];

  const filteredCourses = courses.filter(course => {
    const matchesSearch = 
      course.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      course.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'all' || course.type === filterType;
    return matchesSearch && matchesType;
  });

  const stats = {
    total: courses.length,
    withPrereqs: courses.filter(c => c.prerequisites && c.prerequisites.length > 0).length,
    withConcurrent: courses.filter(c => c.concurrent && c.concurrent.length > 0).length,
    withStanding: courses.filter(c => c.standingRequired).length,
  };

  const openAddDialog = () => {
    setEditingCourse(null);
    setFormData({
      code: '',
      name: '',
      credits: 3,
      type: 'required',
      semester: '',
      prerequisites: '',
      corequisites: '',
      concurrent: '',
      standingRequired: '',
      description: '',
    });
    setIsDialogOpen(true);
  };

  const openEditDialog = (course: Course) => {
    setEditingCourse(course);
    setFormData({
      code: course.code,
      name: course.name,
      credits: course.credits,
      type: course.type,
      semester: course.semester?.toString() || '',
      prerequisites: course.prerequisites?.join(', ') || '',
      corequisites: course.corequisites?.join(', ') || '',
      concurrent: course.concurrent?.join(', ') || '',
      standingRequired: course.standingRequired || '',
      description: course.description || '',
    });
    setIsDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const majorId = getCurrentMajorId();
      if (!majorId) {
        alert('Please select a major first');
        return;
      }

      const courseData = {
        majorId,
        code: formData.code,
        name: formData.name,
        credits: formData.credits,
        type: formData.type,
        semester: formData.semester ? parseInt(formData.semester) : null,
        prerequisites: formData.prerequisites ? formData.prerequisites.split(',').map(s => s.trim()).filter(Boolean) : [],
        corequisites: formData.corequisites ? formData.corequisites.split(',').map(s => s.trim()).filter(Boolean) : [],
        concurrent: formData.concurrent ? formData.concurrent.split(',').map(s => s.trim()).filter(Boolean) : [],
        standingRequired: formData.standingRequired || null,
        description: formData.description || null,
      };

      let res;
      if (editingCourse) {
        res = await fetch('/api/courses', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: editingCourse.id, ...courseData }),
        });
      } else {
        res = await fetch('/api/courses', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(courseData),
        });
      }

      if (res.ok) {
        setIsDialogOpen(false);
        fetchData();
      } else {
        const error = await res.json();
        alert(error.error || 'Failed to save course');
      }
    } catch (error) {
      console.error('Error saving course:', error);
      alert('Failed to save course');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (course: Course) => {
    if (!confirm(`Are you sure you want to delete ${course.code}?`)) return;

    try {
      const res = await fetch(`/api/courses?id=${course.id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchData();
      } else {
        alert('Failed to delete course');
      }
    } catch (error) {
      console.error('Error deleting course:', error);
      alert('Failed to delete course');
    }
  };

  const handleExport = () => {
    const csv = [
      ['Code', 'Name', 'Credits', 'Type', 'Semester', 'Prerequisites', 'Corequisites', 'Concurrent', 'Standing'].join(','),
      ...courses.map(c => [
        c.code,
        `"${c.name}"`,
        c.credits,
        c.type,
        c.semester || '',
        `"${c.prerequisites?.join('; ') || ''}"`,
        `"${c.corequisites?.join('; ') || ''}"`,
        `"${c.concurrent?.join('; ') || ''}"`,
        c.standingRequired || '',
      ].join(',')),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentMajor || 'all'}_courses.csv`;
    a.click();
  };

  if (!currentMajor) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <GraduationCap className="h-16 w-16 text-muted-foreground" />
        <h2 className="text-2xl font-bold">Select a Major</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Please select a major from the dropdown in the header to view and manage courses.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Courses</h1>
          <p className="text-muted-foreground">Manage course catalog for {currentMajor}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button onClick={openAddDialog}>
            <Plus className="h-4 w-4 mr-2" />
            Add Course
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Courses</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <BookOpen className="h-8 w-8 text-primary" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div>
              <p className="text-sm text-muted-foreground">With Prerequisites</p>
              <p className="text-2xl font-bold">{stats.withPrereqs}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div>
              <p className="text-sm text-muted-foreground">With Concurrent</p>
              <p className="text-2xl font-bold">{stats.withConcurrent}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div>
              <p className="text-sm text-muted-foreground">Standing Required</p>
              <p className="text-2xl font-bold">{stats.withStanding}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Course Catalog</CardTitle>
              <CardDescription>{filteredCourses.length} courses</CardDescription>
            </div>
            <div className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search courses..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  {courseTypes.map(type => (
                    <SelectItem key={type} value={type}>{type}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Loading courses...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Credits</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Prerequisites</TableHead>
                  <TableHead>Standing</TableHead>
                  <TableHead className="w-24">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCourses.map(course => (
                  <TableRow key={course.id}>
                    <TableCell className="font-medium">{course.code}</TableCell>
                    <TableCell>{course.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{course.credits}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{course.type || 'General'}</Badge>
                    </TableCell>
                    <TableCell className="max-w-[150px] truncate" title={course.prerequisites?.join(', ')}>
                      {course.prerequisites?.join(', ') || '-'}
                    </TableCell>
                    <TableCell>{course.standingRequired || '-'}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" onClick={() => openEditDialog(course)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(course)}>
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingCourse ? 'Edit Course' : 'Add Course'}</DialogTitle>
            <DialogDescription>
              {editingCourse ? 'Update course details below.' : 'Enter the details for the new course.'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Course Code *</Label>
                <Input
                  value={formData.code}
                  onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value }))}
                  placeholder="PBHL 101"
                />
              </div>
              <div className="space-y-2">
                <Label>Credits</Label>
                <Input
                  type="number"
                  value={formData.credits}
                  onChange={(e) => setFormData(prev => ({ ...prev, credits: parseInt(e.target.value) || 3 }))}
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Course Name *</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Introduction to Public Health"
              />
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={formData.type} onValueChange={(v) => setFormData(prev => ({ ...prev, type: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COURSE_TYPES.map(type => (
                      <SelectItem key={type} value={type}>{type}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Semester</Label>
                <Input
                  type="number"
                  value={formData.semester}
                  onChange={(e) => setFormData(prev => ({ ...prev, semester: e.target.value }))}
                  placeholder="1-8"
                />
              </div>
              <div className="space-y-2">
                <Label>Standing Required</Label>
                <Select 
                  value={formData.standingRequired || 'none'} 
                  onValueChange={(v) => setFormData(prev => ({ ...prev, standingRequired: v === 'none' ? '' : v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="None" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {STANDINGS.map(s => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Prerequisites</Label>
              <Input
                value={formData.prerequisites}
                onChange={(e) => setFormData(prev => ({ ...prev, prerequisites: e.target.value }))}
                placeholder="PBHL 101, PBHL 102 (comma separated)"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Corequisites</Label>
                <Input
                  value={formData.corequisites}
                  onChange={(e) => setFormData(prev => ({ ...prev, corequisites: e.target.value }))}
                  placeholder="Comma separated"
                />
              </div>
              <div className="space-y-2">
                <Label>Concurrent</Label>
                <Input
                  value={formData.concurrent}
                  onChange={(e) => setFormData(prev => ({ ...prev, concurrent: e.target.value }))}
                  placeholder="Comma separated"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Course description (optional)"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving || !formData.code || !formData.name}>
              {saving ? 'Saving...' : <><Save className="h-4 w-4 mr-2" /> Save</>}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
