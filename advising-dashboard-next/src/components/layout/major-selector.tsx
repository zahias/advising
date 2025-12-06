'use client';

import { useAuth } from '@/lib/auth/context';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { GraduationCap } from 'lucide-react';

const majors = [
  { code: 'PBHL', name: 'Public Health' },
  { code: 'SPTH-New', name: 'Speech Therapy (New Curriculum)' },
  { code: 'SPTH-Old', name: 'Speech Therapy (Old Curriculum)' },
  { code: 'NURS', name: 'Nursing' },
];

export function MajorSelector() {
  const { currentMajor, setCurrentMajor } = useAuth();

  return (
    <div className="flex items-center gap-2">
      <GraduationCap className="h-4 w-4 text-muted-foreground" />
      <Select value={currentMajor || ''} onValueChange={setCurrentMajor}>
        <SelectTrigger className="w-[200px]">
          <SelectValue placeholder="Select Major" />
        </SelectTrigger>
        <SelectContent>
          {majors.map((major) => (
            <SelectItem key={major.code} value={major.code}>
              <div className="flex flex-col">
                <span className="font-medium">{major.code}</span>
                <span className="text-xs text-muted-foreground">{major.name}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
