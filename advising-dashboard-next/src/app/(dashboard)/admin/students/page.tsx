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
  Upload,
  Download,
  Edit,
  Trash2,
  FileSpreadsheet
} from 'lucide-react';

const sampleStudents = [
  { id: '12345', name: 'John Smith', email: 'jsmith@pu.edu', major: 'PBHL', credits: 45, standing: 'Sophomore', status: 'active' },
  { id: '12346', name: 'Sarah Johnson', email: 'sjohnson@pu.edu', major: 'PBHL', credits: 78, standing: 'Junior', status: 'active' },
  { id: '12347', name: 'Mike Williams', email: 'mwilliams@pu.edu', major: 'SPTH-New', credits: 92, standing: 'Senior', status: 'active' },
  { id: '12348', name: 'Emily Brown', email: 'ebrown@pu.edu', major: 'NURS', credits: 34, standing: 'Sophomore', status: 'active' },
  { id: '12349', name: 'David Lee', email: 'dlee@pu.edu', major: 'PBHL', credits: 67, standing: 'Junior', status: 'inactive' },
  { id: '12350', name: 'Lisa Chen', email: 'lchen@pu.edu', major: 'SPTH-New', credits: 88, standing: 'Senior', status: 'active' },
];

export default function AdminStudentsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [majorFilter, setMajorFilter] = useState<string>('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);

  const filteredStudents = sampleStudents.filter(student => {
    const matchesSearch = student.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          student.id.includes(searchQuery) ||
                          student.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesMajor = majorFilter === 'all' || student.major === majorFilter;
    return matchesSearch && matchesMajor;
  });

  const majors = ['all', ...new Set(sampleStudents.map(s => s.major))];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Student Manager</h1>
          <p className="text-muted-foreground">Manage students across all majors</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={isImportDialogOpen} onOpenChange={setIsImportDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Upload className="h-4 w-4 mr-2" />
                Import Excel
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Import Students from Excel</DialogTitle>
                <DialogDescription>
                  Upload an Excel file with student data to import
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="border-2 border-dashed rounded-lg p-8 text-center">
                  <FileSpreadsheet className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-sm text-muted-foreground mb-2">
                    Drag and drop your Excel file here, or click to browse
                  </p>
                  <Button variant="outline" size="sm">
                    Browse Files
                  </Button>
                </div>
                <div className="flex items-center gap-2">
                  <Label>Major:</Label>
                  <Select defaultValue="PBHL">
                    <SelectTrigger className="w-[180px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PBHL">PBHL</SelectItem>
                      <SelectItem value="SPTH-New">SPTH-New</SelectItem>
                      <SelectItem value="SPTH-Old">SPTH-Old</SelectItem>
                      <SelectItem value="NURS">NURS</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button className="w-full" onClick={() => setIsImportDialogOpen(false)}>
                  <Upload className="h-4 w-4 mr-2" />
                  Import Students
                </Button>
              </div>
            </DialogContent>
          </Dialog>

          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>

          <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Student
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add New Student</DialogTitle>
                <DialogDescription>
                  Manually add a student to the system
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Student ID</Label>
                    <Input placeholder="e.g., 12345" />
                  </div>
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
                </div>
                <div className="space-y-2">
                  <Label>Full Name</Label>
                  <Input placeholder="e.g., John Smith" />
                </div>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input type="email" placeholder="e.g., jsmith@pu.edu" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Credits Completed</Label>
                    <Input type="number" placeholder="0" />
                  </div>
                  <div className="space-y-2">
                    <Label>Standing</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="Select standing" />
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
                <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>Cancel</Button>
                <Button onClick={() => setIsAddDialogOpen(false)}>Add Student</Button>
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
                <TableHead>ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Major</TableHead>
                <TableHead className="text-center">Credits</TableHead>
                <TableHead>Standing</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredStudents.map((student) => (
                <TableRow key={student.id}>
                  <TableCell className="font-medium">{student.id}</TableCell>
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
                  <TableCell className="text-muted-foreground">{student.email}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{student.major}</Badge>
                  </TableCell>
                  <TableCell className="text-center">{student.credits}</TableCell>
                  <TableCell>{student.standing}</TableCell>
                  <TableCell>
                    <Badge variant={student.status === 'active' ? 'default' : 'secondary'}>
                      {student.status}
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
