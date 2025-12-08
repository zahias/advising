'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useAuth, Major } from '@/lib/auth/context';
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
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
  Loader2,
  Download
} from 'lucide-react';

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  type: string;
  semester: number | null;
  offered: boolean;
  prerequisites: string[];
  corequisites: string[];
  concurrent: string[];
  standingRequired: string | null;
  majorId: string;
}

interface CourseFormData {
  code: string;
  name: string;
  credits: number;
  type: string;
  semester: number | null;
  offered: boolean;
  prerequisites: string;
  corequisites: string;
  concurrent: string;
  standingRequired: string;
}

const emptyFormData: CourseFormData = {
  code: '',
  name: '',
  credits: 3,
  type: 'required',
  semester: null,
  offered: true,
  prerequisites: '',
  corequisites: '',
  concurrent: '',
  standingRequired: '',
};

export default function AdminCoursesPage() {
  const { majors, majorsLoading, currentMajor, majorVersion } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [majorFilter, setMajorFilter] = useState<string>('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [deletingCourse, setDeletingCourse] = useState<Course | null>(null);
  const [formData, setFormData] = useState<CourseFormData>(emptyFormData);
  const [selectedMajorId, setSelectedMajorId] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (currentMajor && majors.length > 0) {
      const matched = majors.find(m => m.code === currentMajor);
      if (matched) {
        setMajorFilter(matched.id);
        setSelectedMajorId(matched.id);
      }
    }
  }, [currentMajor, majors, majorVersion]);

  useEffect(() => {
    async function fetchCourses() {
      setLoading(true);
      try {
        const url = majorFilter && majorFilter !== 'all' 
          ? `/api/courses?majorId=${majorFilter}`
          : '/api/courses';
        const res = await fetch(url);
        const data = await res.json();
        setCourses(data);
      } catch (err) {
        console.error('Failed to fetch courses:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchCourses();
  }, [majorFilter, majorVersion]);

  const resetForm = () => {
    setFormData(emptyFormData);
    setError(null);
  };

  const handleAddCourse = async () => {
    const majorToUse = selectedMajorId || (majorFilter !== 'all' ? majorFilter : '');
    if (!formData.code || !formData.name || !majorToUse) {
      setError('Code, Name, and Major are required. Please select a major.');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const majorToUseForPost = selectedMajorId || (majorFilter !== 'all' ? majorFilter : '');
      const res = await fetch('/api/courses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          majorId: majorToUseForPost,
          code: formData.code,
          name: formData.name,
          credits: formData.credits,
          type: formData.type,
          semester: formData.semester,
          offered: formData.offered,
          prerequisites: formData.prerequisites.split(',').map(s => s.trim()).filter(Boolean),
          corequisites: formData.corequisites.split(',').map(s => s.trim()).filter(Boolean),
          concurrent: formData.concurrent.split(',').map(s => s.trim()).filter(Boolean),
          standingRequired: formData.standingRequired || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to add course');
      }

      const newCourse = await res.json();
      setCourses(prev => [...prev, newCourse]);
      setIsAddDialogOpen(false);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add course');
    } finally {
      setSaving(false);
    }
  };

  const handleEditCourse = async () => {
    if (!editingCourse || !formData.code || !formData.name) {
      setError('Code and Name are required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const res = await fetch('/api/courses', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: editingCourse.id,
          code: formData.code,
          name: formData.name,
          credits: formData.credits,
          type: formData.type,
          semester: formData.semester,
          offered: formData.offered,
          prerequisites: formData.prerequisites.split(',').map(s => s.trim()).filter(Boolean),
          corequisites: formData.corequisites.split(',').map(s => s.trim()).filter(Boolean),
          concurrent: formData.concurrent.split(',').map(s => s.trim()).filter(Boolean),
          standingRequired: formData.standingRequired || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to update course');
      }

      const updated = await res.json();
      setCourses(prev => prev.map(c => c.id === updated.id ? updated : c));
      setIsEditDialogOpen(false);
      setEditingCourse(null);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update course');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCourse = async () => {
    if (!deletingCourse) return;

    setSaving(true);
    try {
      const res = await fetch(`/api/courses?id=${deletingCourse.id}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to delete course');
      }

      setCourses(prev => prev.filter(c => c.id !== deletingCourse.id));
      setDeletingCourse(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete course');
    } finally {
      setSaving(false);
    }
  };

  const openEditDialog = (course: Course) => {
    setEditingCourse(course);
    setFormData({
      code: course.code,
      name: course.name,
      credits: course.credits,
      type: course.type,
      semester: course.semester,
      offered: course.offered,
      prerequisites: (course.prerequisites || []).join(', '),
      corequisites: (course.corequisites || []).join(', '),
      concurrent: (course.concurrent || []).join(', '),
      standingRequired: course.standingRequired || '',
    });
    setError(null);
    setIsEditDialogOpen(true);
  };

  const exportCSV = () => {
    const headers = ['Code', 'Name', 'Credits', 'Type', 'Semester', 'Offered', 'Prerequisites', 'Corequisites', 'Concurrent', 'Standing'];
    const rows = filteredCourses.map(c => [
      c.code,
      c.name,
      c.credits,
      c.type,
      c.semester || '',
      c.offered ? 'Yes' : 'No',
      (c.prerequisites || []).join(';'),
      (c.corequisites || []).join(';'),
      (c.concurrent || []).join(';'),
      c.standingRequired || '',
    ]);
    
    const csv = [headers.join(','), ...rows.map(r => r.map(v => `"${v}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `courses_${majorFilter === 'all' ? 'all' : majors.find(m => m.id === majorFilter)?.code || 'export'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredCourses = courses.filter(course => {
    const matchesSearch = course.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          course.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const getMajorCode = (majorId: string) => majors.find(m => m.id === majorId)?.code || 'Unknown';

  if (majorsLoading || loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Course Manager</h1>
          <p className="text-muted-foreground">Manage courses across all majors</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportCSV}>
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
          <Dialog open={isAddDialogOpen} onOpenChange={(open) => { setIsAddDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Course
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Add New Course</DialogTitle>
                <DialogDescription>Create a new course and set its prerequisites</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                {error && <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm">{error}</div>}
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Major *</Label>
                    <Select value={selectedMajorId} onValueChange={setSelectedMajorId}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select major" />
                      </SelectTrigger>
                      <SelectContent>
                        {majors.filter(m => m.isActive).map(m => (
                          <SelectItem key={m.id} value={m.id}>{m.code}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Course Code *</Label>
                    <Input 
                      placeholder="e.g., PBHL 401" 
                      value={formData.code}
                      onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Credits</Label>
                    <Input 
                      type="number" 
                      value={formData.credits}
                      onChange={(e) => setFormData({ ...formData, credits: Number(e.target.value) || 3 })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Course Name *</Label>
                  <Input 
                    placeholder="e.g., Advanced Epidemiology"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Type</Label>
                    <Select value={formData.type} onValueChange={(v) => setFormData({ ...formData, type: v })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="required">Required</SelectItem>
                        <SelectItem value="intensive">Intensive</SelectItem>
                        <SelectItem value="elective">Elective</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Semester</Label>
                    <Input 
                      type="number" 
                      placeholder="1-8"
                      value={formData.semester || ''}
                      onChange={(e) => setFormData({ ...formData, semester: e.target.value ? Number(e.target.value) : null })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Standing</Label>
                    <Input 
                      placeholder="e.g., Senior"
                      value={formData.standingRequired}
                      onChange={(e) => setFormData({ ...formData, standingRequired: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Prerequisites (comma separated)</Label>
                  <Input 
                    placeholder="e.g., PBHL 101, PBHL 201"
                    value={formData.prerequisites}
                    onChange={(e) => setFormData({ ...formData, prerequisites: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Corequisites</Label>
                    <Input 
                      placeholder="e.g., PBHL 301"
                      value={formData.corequisites}
                      onChange={(e) => setFormData({ ...formData, corequisites: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Concurrent</Label>
                    <Input 
                      placeholder="e.g., PBHL 302"
                      value={formData.concurrent}
                      onChange={(e) => setFormData({ ...formData, concurrent: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="offered" 
                    checked={formData.offered}
                    onCheckedChange={(checked) => setFormData({ ...formData, offered: !!checked })}
                  />
                  <Label htmlFor="offered">Currently Offered</Label>
                </div>
              </div>
              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => { setIsAddDialogOpen(false); resetForm(); }}>Cancel</Button>
                <Button onClick={handleAddCourse} disabled={saving}>
                  {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Add Course
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
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
            <Select value={majorFilter} onValueChange={(v) => {
              setMajorFilter(v);
              if (v !== 'all') setSelectedMajorId(v);
            }}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by major">
                  {majorFilter === 'all' ? 'All Majors' : majors.find(m => m.id === majorFilter)?.code || 'Select'}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Majors</SelectItem>
                {majors.filter(m => m.isActive).map(m => (
                  <SelectItem key={m.id} value={m.id}>{m.code} - {m.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {filteredCourses.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {courses.length === 0 ? 'No courses found. Add courses or import from Excel.' : 'No courses match your search.'}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Name</TableHead>
                  {majorFilter === 'all' && <TableHead>Major</TableHead>}
                  <TableHead className="text-center">Credits</TableHead>
                  <TableHead>Type</TableHead>
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
                    {majorFilter === 'all' && (
                      <TableCell>
                        <Badge variant="outline">{getMajorCode(course.majorId)}</Badge>
                      </TableCell>
                    )}
                    <TableCell className="text-center">{course.credits}</TableCell>
                    <TableCell>
                      <Badge variant={course.type === 'required' ? 'default' : 'secondary'}>
                        {course.type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {course.prerequisites && course.prerequisites.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {course.prerequisites.slice(0, 2).map(p => (
                            <Badge key={p} variant="outline" className="text-xs">{p}</Badge>
                          ))}
                          {course.prerequisites.length > 2 && (
                            <Badge variant="outline" className="text-xs">+{course.prerequisites.length - 2}</Badge>
                          )}
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
                        <Button variant="ghost" size="sm" onClick={() => openEditDialog(course)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-red-500 hover:text-red-700"
                          onClick={() => setDeletingCourse(course)}
                        >
                          <Trash2 className="h-4 w-4" />
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

      <Dialog open={isEditDialogOpen} onOpenChange={(open) => { setIsEditDialogOpen(open); if (!open) { setEditingCourse(null); resetForm(); } }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Course</DialogTitle>
            <DialogDescription>Update course details</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {error && <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm">{error}</div>}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Course Code *</Label>
                <Input 
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Credits</Label>
                <Input 
                  type="number" 
                  value={formData.credits}
                  onChange={(e) => setFormData({ ...formData, credits: Number(e.target.value) || 3 })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Course Name *</Label>
              <Input 
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={formData.type} onValueChange={(v) => setFormData({ ...formData, type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="required">Required</SelectItem>
                    <SelectItem value="intensive">Intensive</SelectItem>
                    <SelectItem value="elective">Elective</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Semester</Label>
                <Input 
                  type="number" 
                  value={formData.semester || ''}
                  onChange={(e) => setFormData({ ...formData, semester: e.target.value ? Number(e.target.value) : null })}
                />
              </div>
              <div className="space-y-2">
                <Label>Standing</Label>
                <Input 
                  value={formData.standingRequired}
                  onChange={(e) => setFormData({ ...formData, standingRequired: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Prerequisites (comma separated)</Label>
              <Input 
                value={formData.prerequisites}
                onChange={(e) => setFormData({ ...formData, prerequisites: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Corequisites</Label>
                <Input 
                  value={formData.corequisites}
                  onChange={(e) => setFormData({ ...formData, corequisites: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Concurrent</Label>
                <Input 
                  value={formData.concurrent}
                  onChange={(e) => setFormData({ ...formData, concurrent: e.target.value })}
                />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox 
                id="edit-offered" 
                checked={formData.offered}
                onCheckedChange={(checked) => setFormData({ ...formData, offered: !!checked })}
              />
              <Label htmlFor="edit-offered">Currently Offered</Label>
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => { setIsEditDialogOpen(false); setEditingCourse(null); resetForm(); }}>Cancel</Button>
            <Button onClick={handleEditCourse} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deletingCourse} onOpenChange={(open) => !open && setDeletingCourse(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Course?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete {deletingCourse?.code}? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteCourse} className="bg-red-600 hover:bg-red-700">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
