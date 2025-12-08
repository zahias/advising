'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { useAuth, Major } from '@/lib/auth/context';
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
import { 
  Plus,
  Edit,
  Trash2,
  GraduationCap,
  Users,
  BookOpen,
  Loader2,
  Upload
} from 'lucide-react';

interface MajorFormData {
  code: string;
  name: string;
  description: string;
  isActive: boolean;
}

const emptyFormData: MajorFormData = {
  code: '',
  name: '',
  description: '',
  isActive: true,
};

export default function AdminMajorsPage() {
  const { majors, majorsLoading, refreshMajors, setCurrentMajor } = useAuth();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isConfigDialogOpen, setIsConfigDialogOpen] = useState(false);
  const [deleteDialogMajor, setDeleteDialogMajor] = useState<Major | null>(null);
  const [editingMajor, setEditingMajor] = useState<Major | null>(null);
  const [configuringMajor, setConfiguringMajor] = useState<Major | null>(null);
  const [formData, setFormData] = useState<MajorFormData>(emptyFormData);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setFormData(emptyFormData);
    setError(null);
  };

  const handleAddMajor = async () => {
    if (!formData.code || !formData.name) {
      setError('Code and Name are required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const res = await fetch('/api/majors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to add major');
      }

      await refreshMajors();
      setIsAddDialogOpen(false);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add major');
    } finally {
      setSaving(false);
    }
  };

  const handleEditMajor = async () => {
    if (!editingMajor) return;
    if (!formData.code || !formData.name) {
      setError('Code and Name are required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const res = await fetch('/api/majors', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: editingMajor.id, ...formData }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to update major');
      }

      await refreshMajors();
      setIsEditDialogOpen(false);
      setEditingMajor(null);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update major');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteMajor = async () => {
    if (!deleteDialogMajor) return;

    setSaving(true);
    setError(null);

    try {
      const res = await fetch(`/api/majors?id=${deleteDialogMajor.id}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to delete major');
      }

      await refreshMajors();
      setDeleteDialogMajor(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete major');
    } finally {
      setSaving(false);
    }
  };

  const openEditDialog = (major: Major) => {
    setEditingMajor(major);
    setFormData({
      code: major.code,
      name: major.name,
      description: major.description || '',
      isActive: major.isActive,
    });
    setError(null);
    setIsEditDialogOpen(true);
  };

  const openConfigDialog = (major: Major) => {
    setConfiguringMajor(major);
    setCurrentMajor(major.code);
    setIsConfigDialogOpen(true);
  };

  if (majorsLoading) {
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
          <h1 className="text-3xl font-bold">Major Manager</h1>
          <p className="text-muted-foreground">Configure academic programs and requirements</p>
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={(open) => { setIsAddDialogOpen(open); if (!open) resetForm(); }}>
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
              {error && (
                <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm">{error}</div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Major Code *</Label>
                  <Input 
                    placeholder="e.g., PBHL" 
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <div className="flex items-center gap-2 h-10">
                    <Switch 
                      checked={formData.isActive} 
                      onCheckedChange={(checked) => setFormData({ ...formData, isActive: checked })}
                    />
                    <span className="text-sm">{formData.isActive ? 'Active' : 'Inactive'}</span>
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Program Name *</Label>
                <Input 
                  placeholder="e.g., Public Health" 
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea 
                  placeholder="Program description..." 
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => { setIsAddDialogOpen(false); resetForm(); }}>Cancel</Button>
              <Button onClick={handleAddMajor} disabled={saving}>
                {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Add Major
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {majors.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <GraduationCap className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No Majors Yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Get started by adding your first academic program.
            </p>
            <Button onClick={() => setIsAddDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Major
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {majors.map(major => (
            <Card key={major.id} className="overflow-hidden">
              <div className="h-2 bg-primary" />
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-primary" />
                      {major.code}
                    </CardTitle>
                    <CardDescription className="mt-1">{major.name}</CardDescription>
                  </div>
                  <Badge variant={major.isActive ? 'default' : 'secondary'}>
                    {major.isActive ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  {major.description || 'No description provided.'}
                </p>
                
                <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                  <div className="text-center">
                    <div className="flex justify-center mb-1">
                      <BookOpen className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="text-lg font-bold">{major.courseCount || 0}</div>
                    <div className="text-xs text-muted-foreground">Courses</div>
                  </div>
                  <div className="text-center">
                    <div className="flex justify-center mb-1">
                      <Users className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="text-lg font-bold">{major.studentCount || 0}</div>
                    <div className="text-xs text-muted-foreground">Students</div>
                  </div>
                </div>

                <div className="flex gap-2 pt-4 border-t">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="flex-1"
                    onClick={() => openEditDialog(major)}
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="flex-1"
                    onClick={() => openConfigDialog(major)}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Import Data
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-red-500 hover:text-red-700"
                    onClick={() => setDeleteDialogMajor(major)}
                    disabled={(major.courseCount || 0) > 0 || (major.studentCount || 0) > 0}
                    title={(major.courseCount || 0) > 0 || (major.studentCount || 0) > 0 ? 'Remove courses and students first' : 'Delete major'}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={isEditDialogOpen} onOpenChange={(open) => { setIsEditDialogOpen(open); if (!open) { setEditingMajor(null); resetForm(); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Major</DialogTitle>
            <DialogDescription>
              Update the academic program details
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm">{error}</div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Major Code *</Label>
                <Input 
                  placeholder="e.g., PBHL" 
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                />
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <div className="flex items-center gap-2 h-10">
                  <Switch 
                    checked={formData.isActive} 
                    onCheckedChange={(checked) => setFormData({ ...formData, isActive: checked })}
                  />
                  <span className="text-sm">{formData.isActive ? 'Active' : 'Inactive'}</span>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Program Name *</Label>
              <Input 
                placeholder="e.g., Public Health" 
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea 
                placeholder="Program description..." 
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => { setIsEditDialogOpen(false); setEditingMajor(null); resetForm(); }}>Cancel</Button>
            <Button onClick={handleEditMajor} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={isConfigDialogOpen} onOpenChange={(open) => { setIsConfigDialogOpen(open); if (!open) setConfiguringMajor(null); }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Import Data for {configuringMajor?.code}</DialogTitle>
            <DialogDescription>
              Upload course catalog and student data for this major
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="border rounded-lg p-4 space-y-3">
              <h3 className="font-medium flex items-center gap-2">
                <BookOpen className="h-4 w-4" />
                Course Catalog
              </h3>
              <p className="text-sm text-muted-foreground">
                Upload an Excel file with course information. Required columns: Course Code, Offered.
              </p>
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                className="block w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-primary file:text-white file:cursor-pointer"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file || !configuringMajor) return;
                  
                  const formData = new FormData();
                  formData.append('file', file);
                  formData.append('majorId', configuringMajor.id);
                  
                  try {
                    const res = await fetch('/api/import/courses', {
                      method: 'POST',
                      body: formData,
                    });
                    
                    const data = await res.json();
                    if (res.ok) {
                      alert(`Successfully imported ${data.count} courses`);
                      refreshMajors();
                    } else {
                      alert(`Error: ${data.error}`);
                    }
                  } catch (err) {
                    alert('Failed to import courses');
                  }
                }}
              />
            </div>

            <div className="border rounded-lg p-4 space-y-3">
              <h3 className="font-medium flex items-center gap-2">
                <Users className="h-4 w-4" />
                Student Progress Report
              </h3>
              <p className="text-sm text-muted-foreground">
                Upload an Excel file with student data. Required columns: ID, NAME.
                Course columns will be read for progress status.
              </p>
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                className="block w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-primary file:text-white file:cursor-pointer"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file || !configuringMajor) return;
                  
                  const formData = new FormData();
                  formData.append('file', file);
                  formData.append('majorId', configuringMajor.id);
                  
                  try {
                    const res = await fetch('/api/import/students', {
                      method: 'POST',
                      body: formData,
                    });
                    
                    const data = await res.json();
                    if (res.ok) {
                      alert(`Successfully imported ${data.count} students`);
                      refreshMajors();
                    } else {
                      alert(`Error: ${data.error}`);
                    }
                  } catch (err) {
                    alert('Failed to import students');
                  }
                }}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button variant="outline" onClick={() => { setIsConfigDialogOpen(false); setConfiguringMajor(null); }}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteDialogMajor} onOpenChange={(open) => !open && setDeleteDialogMajor(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Major?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete {deleteDialogMajor?.code} ({deleteDialogMajor?.name})?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm">{error}</div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setDeleteDialogMajor(null); setError(null); }}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteMajor} className="bg-red-600 hover:bg-red-700" disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
