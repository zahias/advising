'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
  Download,
  Edit,
  Trash2,
  Loader2,
  Users
} from 'lucide-react';

interface Student {
  id: string;
  studentId: string;
  name: string;
  email: string | null;
  standing: string | null;
  creditsCompleted: number;
  creditsRegistered: number;
  creditsRemaining: number;
  majorId: string;
}

interface StudentFormData {
  studentId: string;
  name: string;
  email: string;
  creditsCompleted: number;
  standing: string;
}

const emptyFormData: StudentFormData = {
  studentId: '',
  name: '',
  email: '',
  creditsCompleted: 0,
  standing: 'Freshman',
};

export default function AdminStudentsPage() {
  const { majors, majorsLoading, currentMajor, majorVersion } = useAuth();
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [majorFilter, setMajorFilter] = useState<string>('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingStudent, setEditingStudent] = useState<Student | null>(null);
  const [deletingStudent, setDeletingStudent] = useState<Student | null>(null);
  const [formData, setFormData] = useState<StudentFormData>(emptyFormData);
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
    async function fetchStudents() {
      setLoading(true);
      try {
        const url = majorFilter && majorFilter !== 'all' 
          ? `/api/students?majorId=${majorFilter}`
          : '/api/students';
        const res = await fetch(url);
        const data = await res.json();
        setStudents(data);
      } catch (err) {
        console.error('Failed to fetch students:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchStudents();
  }, [majorFilter, majorVersion]);

  const resetForm = () => {
    setFormData(emptyFormData);
    setError(null);
  };

  const handleAddStudent = async () => {
    const majorToUse = selectedMajorId || (majorFilter !== 'all' ? majorFilter : '');
    if (!formData.studentId || !formData.name || !majorToUse) {
      setError('Student ID, Name, and Major are required. Please select a major.');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const majorToUseForPost = selectedMajorId || (majorFilter !== 'all' ? majorFilter : '');
      const res = await fetch('/api/students', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          majorId: majorToUseForPost,
          studentId: formData.studentId,
          name: formData.name,
          email: formData.email || null,
          creditsCompleted: formData.creditsCompleted,
          standing: formData.standing,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to add student');
      }

      const newStudent = await res.json();
      setStudents(prev => [...prev, newStudent]);
      setIsAddDialogOpen(false);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add student');
    } finally {
      setSaving(false);
    }
  };

  const handleEditStudent = async () => {
    if (!editingStudent || !formData.studentId || !formData.name) {
      setError('Student ID and Name are required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const res = await fetch('/api/students', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: editingStudent.id,
          studentId: formData.studentId,
          name: formData.name,
          email: formData.email || null,
          creditsCompleted: formData.creditsCompleted,
          standing: formData.standing,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to update student');
      }

      const updated = await res.json();
      setStudents(prev => prev.map(s => s.id === updated.id ? updated : s));
      setIsEditDialogOpen(false);
      setEditingStudent(null);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update student');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteStudent = async () => {
    if (!deletingStudent) return;

    setSaving(true);
    try {
      const res = await fetch(`/api/students?id=${deletingStudent.id}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to delete student');
      }

      setStudents(prev => prev.filter(s => s.id !== deletingStudent.id));
      setDeletingStudent(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete student');
    } finally {
      setSaving(false);
    }
  };

  const openEditDialog = (student: Student) => {
    setEditingStudent(student);
    setFormData({
      studentId: student.studentId,
      name: student.name,
      email: student.email || '',
      creditsCompleted: student.creditsCompleted,
      standing: student.standing || 'Freshman',
    });
    setError(null);
    setIsEditDialogOpen(true);
  };

  const exportCSV = () => {
    const headers = ['Student ID', 'Name', 'Email', 'Credits Completed', 'Credits Registered', 'Credits Remaining', 'Standing'];
    const rows = filteredStudents.map(s => [
      s.studentId,
      s.name,
      s.email || '',
      s.creditsCompleted,
      s.creditsRegistered,
      s.creditsRemaining,
      s.standing || '',
    ]);
    
    const csv = [headers.join(','), ...rows.map(r => r.map(v => `"${v}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `students_${majorFilter === 'all' ? 'all' : majors.find(m => m.id === majorFilter)?.code || 'export'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredStudents = students.filter(student => {
    const matchesSearch = student.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          student.studentId.includes(searchQuery) ||
                          (student.email || '').toLowerCase().includes(searchQuery.toLowerCase());
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
          <h1 className="text-3xl font-bold">Student Manager</h1>
          <p className="text-muted-foreground">Manage students across all majors</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportCSV}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Dialog open={isAddDialogOpen} onOpenChange={(open) => { setIsAddDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Student
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add New Student</DialogTitle>
                <DialogDescription>Manually add a student to the system</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                {error && <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm">{error}</div>}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Student ID *</Label>
                    <Input 
                      placeholder="e.g., 12345"
                      value={formData.studentId}
                      onChange={(e) => setFormData({ ...formData, studentId: e.target.value })}
                    />
                  </div>
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
                </div>
                <div className="space-y-2">
                  <Label>Full Name *</Label>
                  <Input 
                    placeholder="e.g., John Smith"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input 
                    type="email" 
                    placeholder="e.g., jsmith@pu.edu"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Credits Completed</Label>
                    <Input 
                      type="number" 
                      value={formData.creditsCompleted}
                      onChange={(e) => setFormData({ ...formData, creditsCompleted: Number(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Standing</Label>
                    <Select value={formData.standing} onValueChange={(v) => setFormData({ ...formData, standing: v })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Freshman">Freshman</SelectItem>
                        <SelectItem value="Sophomore">Sophomore</SelectItem>
                        <SelectItem value="Junior">Junior</SelectItem>
                        <SelectItem value="Senior">Senior</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => { setIsAddDialogOpen(false); resetForm(); }}>Cancel</Button>
                <Button onClick={handleAddStudent} disabled={saving}>
                  {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Add Student
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
                placeholder="Search by name, ID, or email..."
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
          {filteredStudents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Users className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No Students Found</h3>
              <p className="text-muted-foreground text-center">
                {students.length === 0 ? 'Import students from Excel or add them manually.' : 'No students match your search.'}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  {majorFilter === 'all' && <TableHead>Major</TableHead>}
                  <TableHead className="text-center">Credits</TableHead>
                  <TableHead>Standing</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredStudents.map((student) => (
                  <TableRow key={student.id}>
                    <TableCell className="font-medium">{student.studentId}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="text-xs font-medium text-primary">
                            {student.name.split(' ').map(n => n[0]).join('')}
                          </span>
                        </div>
                        {student.name}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{student.email || '-'}</TableCell>
                    {majorFilter === 'all' && (
                      <TableCell>
                        <Badge variant="outline">{getMajorCode(student.majorId)}</Badge>
                      </TableCell>
                    )}
                    <TableCell className="text-center">
                      {student.creditsCompleted + student.creditsRegistered}
                    </TableCell>
                    <TableCell>{student.standing || '-'}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="sm" onClick={() => openEditDialog(student)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-red-500 hover:text-red-700"
                          onClick={() => setDeletingStudent(student)}
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

      <Dialog open={isEditDialogOpen} onOpenChange={(open) => { setIsEditDialogOpen(open); if (!open) { setEditingStudent(null); resetForm(); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Student</DialogTitle>
            <DialogDescription>Update student details</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {error && <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm">{error}</div>}
            <div className="space-y-2">
              <Label>Student ID *</Label>
              <Input 
                value={formData.studentId}
                onChange={(e) => setFormData({ ...formData, studentId: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Full Name *</Label>
              <Input 
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input 
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Credits Completed</Label>
                <Input 
                  type="number" 
                  value={formData.creditsCompleted}
                  onChange={(e) => setFormData({ ...formData, creditsCompleted: Number(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Standing</Label>
                <Select value={formData.standing} onValueChange={(v) => setFormData({ ...formData, standing: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Freshman">Freshman</SelectItem>
                    <SelectItem value="Sophomore">Sophomore</SelectItem>
                    <SelectItem value="Junior">Junior</SelectItem>
                    <SelectItem value="Senior">Senior</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => { setIsEditDialogOpen(false); setEditingStudent(null); resetForm(); }}>Cancel</Button>
            <Button onClick={handleEditStudent} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deletingStudent} onOpenChange={(open) => !open && setDeletingStudent(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Student?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete {deletingStudent?.name}? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteStudent} className="bg-red-600 hover:bg-red-700">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
