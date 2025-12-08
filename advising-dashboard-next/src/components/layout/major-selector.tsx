'use client';

import { useAuth } from '@/lib/auth/context';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { GraduationCap, Loader2 } from 'lucide-react';

export function MajorSelector() {
  const { currentMajor, setCurrentMajor, majors, majorsLoading } = useAuth();

  if (majorsLoading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading majors...</span>
      </div>
    );
  }

  const activeMajors = majors.filter(m => m.isActive);

  return (
    <div className="flex items-center gap-2">
      <GraduationCap className="h-4 w-4 text-muted-foreground" />
      <Select value={currentMajor || ''} onValueChange={setCurrentMajor}>
        <SelectTrigger className="w-[220px]">
          <SelectValue placeholder="Select Major" />
        </SelectTrigger>
        <SelectContent>
          {activeMajors.length === 0 ? (
            <div className="p-2 text-sm text-muted-foreground">No majors found</div>
          ) : (
            activeMajors.map((major) => (
              <SelectItem key={major.code} value={major.code}>
                <div className="flex flex-col">
                  <span className="font-medium">{major.code}</span>
                  <span className="text-xs text-muted-foreground">{major.name}</span>
                </div>
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>
    </div>
  );
}
