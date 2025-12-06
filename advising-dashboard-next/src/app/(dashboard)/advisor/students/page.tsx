'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
  Search,
  Filter,
  CheckCircle,
  Clock,
  ArrowUpDown,
  ChevronRight,
  Download
} from 'lucide-react';
import Link from 'next/link';

const sampleStudents = [
  { id: '12345', name: 'John Smith', credits: 45, remaining: 75, standing: 'Sophomore', status: 'advised', lastAdvised: '2024-12-04' },
  { id: '12346', name: 'Sarah Johnson', credits: 78, remaining: 42, standing: 'Junior', status: 'pending', lastAdvised: null },
  { id: '12347', name: 'Mike Williams', credits: 92, remaining: 28, standing: 'Senior', status: 'advised', lastAdvised: '2024-11-28' },
  { id: '12348', name: 'Emily Brown', credits: 34, remaining: 86, standing: 'Sophomore', status: 'pending', lastAdvised: null },
  { id: '12349', name: 'David Lee', credits: 67, remaining: 53, standing: 'Junior', status: 'advised', lastAdvised: '2024-12-01' },
  { id: '12350', name: 'Lisa Chen', credits: 88, remaining: 32, standing: 'Senior', status: 'advised', lastAdvised: '2024-12-03' },
  { id: '12351', name: 'James Taylor', credits: 85, remaining: 35, standing: 'Senior', status: 'pending', lastAdvised: null },
  { id: '12352', name: 'Anna Martinez', credits: 56, remaining: 64, standing: 'Junior', status: 'advised', lastAdvised: '2024-11-30' },
];

export default function AdvisorStudentsPage() {
  const { currentMajor } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'advised' | 'pending'>('all');

  if (!currentMajor) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="text-6xl">🎓</div>
        <h2 className="text-2xl font-bold">Select a Major</h2>
        <p className="text-muted-foreground">Please select a major from the header dropdown.</p>
      </div>
    );
  }

  const filteredStudents = sampleStudents.filter(student => {
    const matchesSearch = student.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          student.id.includes(searchQuery);
    const matchesStatus = statusFilter === 'all' || student.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const stats = {
    total: sampleStudents.length,
    advised: sampleStudents.filter(s => s.status === 'advised').length,
    pending: sampleStudents.filter(s => s.status === 'pending').length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Students</h1>
          <p className="text-muted-foreground">{currentMajor} • {stats.total} students</p>
        </div>
        <Button variant="outline">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="cursor-pointer hover:bg-gray-50" onClick={() => setStatusFilter('all')}>
          <CardContent className="pt-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-muted-foreground">Total Students</p>
                <p className="text-3xl font-bold">{stats.total}</p>
              </div>
              <Badge variant={statusFilter === 'all' ? 'default' : 'outline'}>All</Badge>
            </div>
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:bg-gray-50" onClick={() => setStatusFilter('advised')}>
          <CardContent className="pt-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-muted-foreground">Advised</p>
                <p className="text-3xl font-bold text-green-600">{stats.advised}</p>
              </div>
              <Badge variant={statusFilter === 'advised' ? 'default' : 'outline'} className="bg-green-100 text-green-800">
                <CheckCircle className="h-3 w-3 mr-1" />
                Advised
              </Badge>
            </div>
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:bg-gray-50" onClick={() => setStatusFilter('pending')}>
          <CardContent className="pt-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-3xl font-bold text-orange-600">{stats.pending}</p>
              </div>
              <Badge variant={statusFilter === 'pending' ? 'default' : 'outline'} className="bg-orange-100 text-orange-800">
                <Clock className="h-3 w-3 mr-1" />
                Pending
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Standing</TableHead>
                <TableHead className="text-center">Credits</TableHead>
                <TableHead className="text-center">Remaining</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Advised</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredStudents.map((student) => (
                <TableRow key={student.id} className="cursor-pointer hover:bg-gray-50">
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
                  <TableCell>{student.standing}</TableCell>
                  <TableCell className="text-center">{student.credits}</TableCell>
                  <TableCell className="text-center">{student.remaining}</TableCell>
                  <TableCell>
                    <Badge variant={student.status === 'advised' ? 'default' : 'secondary'}>
                      {student.status === 'advised' ? (
                        <><CheckCircle className="h-3 w-3 mr-1" /> Advised</>
                      ) : (
                        <><Clock className="h-3 w-3 mr-1" /> Pending</>
                      )}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {student.lastAdvised || 'Never'}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/advisor/session?student=${student.id}`}>
                        <ChevronRight className="h-4 w-4" />
                      </Link>
                    </Button>
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
