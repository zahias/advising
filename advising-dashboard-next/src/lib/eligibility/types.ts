export interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  type: 'required' | 'intensive' | 'elective';
  semester?: number;
  offered: boolean;
  prerequisites: string[];
  corequisites: string[];
  concurrent: string[];
  standingRequired?: string;
  description?: string;
}

export interface Student {
  id: string;
  studentId: string;
  name: string;
  email?: string;
  standing?: string;
  creditsCompleted: number;
  creditsRegistered: number;
  creditsRemaining: number;
  courseStatuses: Record<string, string>;
}

export interface Bypass {
  courseCode: string;
  advisorName: string;
  note: string;
  createdAt: string;
}

export interface AdvisingSession {
  id: string;
  periodId: string;
  studentId: string;
  advisorId?: string;
  advisedCourses: string[];
  optionalCourses: string[];
  repeatCourses: string[];
  bypasses: Record<string, { note: string; advisor: string }>;
  note?: string;
}

export type EligibilityStatus = 
  | 'Eligible'
  | 'Completed'
  | 'Registered'
  | 'Not Eligible'
  | 'Advised'
  | 'Optional';

export interface EligibilityResult {
  status: EligibilityStatus;
  reason: string;
  missingPrerequisites: string[];
  missingConcurrent: string[];
  missingCorequisites: string[];
  standingIssue: boolean;
  hasBypass: boolean;
  bypassInfo?: { note: string; advisor: string };
}

export interface MutualConcurrentPair {
  courseA: string;
  courseB: string;
}
