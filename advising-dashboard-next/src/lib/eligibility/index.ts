import type { 
  Course, 
  Student, 
  EligibilityResult, 
  EligibilityStatus,
  MutualConcurrentPair 
} from './types';

export * from './types';

export function getStudentStanding(totalCredits: number): string {
  if (totalCredits >= 60) return 'Senior';
  if (totalCredits >= 30) return 'Junior';
  if (totalCredits >= 15) return 'Sophomore';
  return 'Freshman';
}

export function checkCourseCompleted(student: Student, courseCode: string): boolean {
  const status = student.courseStatuses[courseCode];
  return status?.toLowerCase() === 'c';
}

export function checkCourseRegistered(student: Student, courseCode: string): boolean {
  const status = student.courseStatuses[courseCode];
  if (!status || status === '' || status.toLowerCase() === 'nan') {
    return courseCode in student.courseStatuses;
  }
  const s = status.toLowerCase();
  return s === 'r' || s === 'cr';
}

export function checkCourseFailed(student: Student, courseCode: string): boolean {
  const status = student.courseStatuses[courseCode];
  return status?.toLowerCase() === 'f';
}

export function checkCourseNotCompleted(student: Student, courseCode: string): boolean {
  const status = student.courseStatuses[courseCode];
  return status?.toLowerCase() === 'nc';
}

export function parseRequirements(requirementStr: string | undefined | null): string[] {
  if (!requirementStr || requirementStr === '') return [];
  
  const parts = requirementStr
    .split(/[,;]|\band\b/i)
    .map(p => p.trim())
    .filter(p => p.length > 0);
  
  return parts;
}

export function isCourseOffered(course: Course): boolean {
  return course.offered === true;
}

export function getMutualConcurrentPairs(courses: Course[]): MutualConcurrentPair[] {
  const pairs: MutualConcurrentPair[] = [];
  const seen = new Set<string>();
  
  for (const courseA of courses) {
    for (const concurrentCode of courseA.concurrent) {
      const courseB = courses.find(c => c.code === concurrentCode);
      if (!courseB) continue;
      
      if (courseB.concurrent.includes(courseA.code)) {
        const pairKey = [courseA.code, courseB.code].sort().join('|');
        if (!seen.has(pairKey)) {
          seen.add(pairKey);
          pairs.push({
            courseA: courseA.code,
            courseB: courseB.code,
          });
        }
      }
    }
  }
  
  return pairs;
}

export function getCorequisiteAndConcurrentCourses(courses: Course[]): string[] {
  const result = new Set<string>();
  
  for (const course of courses) {
    if (course.corequisites.length > 0 || course.concurrent.length > 0) {
      result.add(course.code);
    }
  }
  
  return Array.from(result);
}

function checkStandingRequirement(
  student: Student,
  standingRequired: string | undefined
): { met: boolean; reason: string } {
  if (!standingRequired) {
    return { met: true, reason: '' };
  }
  
  const totalCredits = student.creditsCompleted + student.creditsRegistered;
  const studentStanding = getStudentStanding(totalCredits);
  
  const standingOrder = ['Freshman', 'Sophomore', 'Junior', 'Senior'];
  const reqLower = standingRequired.toLowerCase();
  
  let requiredIndex = -1;
  if (reqLower.includes('senior')) {
    requiredIndex = standingOrder.indexOf('Senior');
  } else if (reqLower.includes('junior')) {
    requiredIndex = standingOrder.indexOf('Junior');
  } else if (reqLower.includes('sophomore')) {
    requiredIndex = standingOrder.indexOf('Sophomore');
  }
  
  if (requiredIndex === -1) {
    return { met: true, reason: '' };
  }
  
  const studentIndex = standingOrder.indexOf(studentStanding);
  
  if (studentIndex >= requiredIndex) {
    return { met: true, reason: '' };
  }
  
  return { 
    met: false, 
    reason: `Requires ${standingOrder[requiredIndex]} standing (currently ${studentStanding})` 
  };
}

export function checkEligibility(
  student: Student,
  courseCode: string,
  advisedCourses: string[],
  courses: Course[],
  options: {
    ignoreOffered?: boolean;
    bypasses?: Record<string, { note: string; advisor: string }>;
    simulateCourses?: string[];
  } = {}
): EligibilityResult {
  const {
    ignoreOffered = false,
    bypasses = {},
    simulateCourses = [],
  } = options;
  
  const course = courses.find(c => c.code === courseCode);
  
  if (!course) {
    return {
      status: 'Not Eligible',
      reason: 'Course not found in catalog',
      missingPrerequisites: [],
      missingConcurrent: [],
      missingCorequisites: [],
      standingIssue: false,
      hasBypass: false,
    };
  }
  
  if (checkCourseCompleted(student, courseCode)) {
    return {
      status: 'Completed',
      reason: 'Course already completed',
      missingPrerequisites: [],
      missingConcurrent: [],
      missingCorequisites: [],
      standingIssue: false,
      hasBypass: false,
    };
  }
  
  if (checkCourseRegistered(student, courseCode)) {
    return {
      status: 'Registered',
      reason: 'Currently registered for this course',
      missingPrerequisites: [],
      missingConcurrent: [],
      missingCorequisites: [],
      standingIssue: false,
      hasBypass: false,
    };
  }
  
  if (advisedCourses.includes(courseCode)) {
    return {
      status: 'Advised',
      reason: 'Course has been advised',
      missingPrerequisites: [],
      missingConcurrent: [],
      missingCorequisites: [],
      standingIssue: false,
      hasBypass: false,
    };
  }
  
  if (bypasses[courseCode]) {
    return {
      status: 'Eligible',
      reason: `Bypass granted: ${bypasses[courseCode].note}`,
      missingPrerequisites: [],
      missingConcurrent: [],
      missingCorequisites: [],
      standingIssue: false,
      hasBypass: true,
      bypassInfo: bypasses[courseCode],
    };
  }
  
  if (!ignoreOffered && !isCourseOffered(course)) {
    return {
      status: 'Not Eligible',
      reason: 'Course is not offered this semester',
      missingPrerequisites: [],
      missingConcurrent: [],
      missingCorequisites: [],
      standingIssue: false,
      hasBypass: false,
    };
  }
  
  const issues: string[] = [];
  const missingPrerequisites: string[] = [];
  const missingConcurrent: string[] = [];
  const missingCorequisites: string[] = [];
  let standingIssue = false;
  
  const standingCheck = checkStandingRequirement(student, course.standingRequired);
  if (!standingCheck.met) {
    issues.push(standingCheck.reason);
    standingIssue = true;
  }
  
  const mutualPairs = getMutualConcurrentPairs(courses);
  const isMutualPairMember = mutualPairs.some(
    pair => pair.courseA === courseCode || pair.courseB === courseCode
  );
  
  const effectiveAdvised = [...advisedCourses, ...simulateCourses];
  
  for (const prereqCode of course.prerequisites) {
    if (prereqCode.toLowerCase().includes('standing')) {
      continue;
    }
    
    const prereqCompleted = checkCourseCompleted(student, prereqCode);
    const prereqRegistered = checkCourseRegistered(student, prereqCode);
    const prereqAdvised = effectiveAdvised.includes(prereqCode);
    const prereqBypassed = bypasses[prereqCode] !== undefined;
    
    if (prereqCompleted) {
      continue;
    }
    
    if (prereqRegistered) {
      continue;
    }
    
    if (prereqBypassed) {
      continue;
    }
    
    if (!prereqAdvised) {
      missingPrerequisites.push(prereqCode);
    }
  }
  
  for (const concurrentCode of course.concurrent) {
    if (isMutualPairMember) {
      const isPairPartner = mutualPairs.some(
        pair => 
          (pair.courseA === courseCode && pair.courseB === concurrentCode) ||
          (pair.courseB === courseCode && pair.courseA === concurrentCode)
      );
      if (isPairPartner) {
        continue;
      }
    }
    
    const concurrentCompleted = checkCourseCompleted(student, concurrentCode);
    const concurrentRegistered = checkCourseRegistered(student, concurrentCode);
    const concurrentAdvised = effectiveAdvised.includes(concurrentCode);
    const concurrentBypassed = bypasses[concurrentCode] !== undefined;
    
    if (concurrentCompleted || concurrentRegistered || concurrentAdvised || concurrentBypassed) {
      continue;
    }
    
    missingConcurrent.push(concurrentCode);
  }
  
  for (const coreqCode of course.corequisites) {
    const coreqCompleted = checkCourseCompleted(student, coreqCode);
    const coreqRegistered = checkCourseRegistered(student, coreqCode);
    const coreqAdvised = effectiveAdvised.includes(coreqCode);
    const coreqBypassed = bypasses[coreqCode] !== undefined;
    
    if (coreqCompleted || coreqRegistered || coreqAdvised || coreqBypassed) {
      continue;
    }
    
    missingCorequisites.push(coreqCode);
  }
  
  if (missingPrerequisites.length > 0) {
    issues.push(`Missing prerequisites: ${missingPrerequisites.join(', ')}`);
  }
  
  if (missingConcurrent.length > 0) {
    issues.push(`Missing concurrent courses: ${missingConcurrent.join(', ')}`);
  }
  
  if (missingCorequisites.length > 0) {
    issues.push(`Missing corequisites: ${missingCorequisites.join(', ')}`);
  }
  
  if (issues.length === 0) {
    return {
      status: 'Eligible',
      reason: 'All requirements met',
      missingPrerequisites: [],
      missingConcurrent: [],
      missingCorequisites: [],
      standingIssue: false,
      hasBypass: false,
    };
  }
  
  return {
    status: 'Not Eligible',
    reason: issues.join('; '),
    missingPrerequisites,
    missingConcurrent,
    missingCorequisites,
    standingIssue,
    hasBypass: false,
  };
}

export function getEligibleCourses(
  student: Student,
  courses: Course[],
  advisedCourses: string[] = [],
  options: {
    bypasses?: Record<string, { note: string; advisor: string }>;
    excludeCodes?: string[];
  } = {}
): { course: Course; eligibility: EligibilityResult }[] {
  const { bypasses = {}, excludeCodes = [] } = options;
  
  const results: { course: Course; eligibility: EligibilityResult }[] = [];
  
  for (const course of courses) {
    if (excludeCodes.includes(course.code)) {
      continue;
    }
    
    const eligibility = checkEligibility(
      student,
      course.code,
      advisedCourses,
      courses,
      { bypasses }
    );
    
    if (eligibility.status === 'Eligible') {
      results.push({ course, eligibility });
    }
  }
  
  return results;
}

export function getAllCoursesWithEligibility(
  student: Student,
  courses: Course[],
  advisedCourses: string[] = [],
  options: {
    bypasses?: Record<string, { note: string; advisor: string }>;
    excludeCodes?: string[];
  } = {}
): { course: Course; eligibility: EligibilityResult }[] {
  const { bypasses = {}, excludeCodes = [] } = options;
  
  return courses
    .filter(course => !excludeCodes.includes(course.code))
    .map(course => ({
      course,
      eligibility: checkEligibility(
        student,
        course.code,
        advisedCourses,
        courses,
        { bypasses }
      ),
    }));
}

export function calculateCurriculumYears(courses: Course[]): Record<string, number> {
  const courseYears: Record<string, number> = {};
  const prereqMap: Record<string, string[]> = {};
  const standingReqs: Record<string, string | undefined> = {};
  
  for (const course of courses) {
    const coursePrereqs: string[] = [];
    let standingReq: string | undefined;
    
    for (const prereq of course.prerequisites) {
      if (prereq.toLowerCase().includes('standing')) {
        standingReq = prereq;
      } else {
        coursePrereqs.push(prereq);
      }
    }
    
    prereqMap[course.code] = coursePrereqs;
    standingReqs[course.code] = standingReq;
  }
  
  function getCourseYear(courseCode: string, visited: Set<string> = new Set()): number {
    if (courseYears[courseCode] !== undefined) {
      return courseYears[courseCode];
    }
    
    if (visited.has(courseCode)) {
      return 1;
    }
    
    visited.add(courseCode);
    
    const prereqs = prereqMap[courseCode] || [];
    const standingReq = standingReqs[courseCode];
    
    let maxPrereqYear = 0;
    for (const prereqCode of prereqs) {
      if (prereqMap[prereqCode] !== undefined) {
        const prereqYear = getCourseYear(prereqCode, new Set(visited));
        maxPrereqYear = Math.max(maxPrereqYear, prereqYear);
      }
    }
    
    let standingYear = 1;
    if (standingReq) {
      if (standingReq.toLowerCase().includes('senior')) {
        standingYear = 3;
      } else if (standingReq.toLowerCase().includes('junior')) {
        standingYear = 2;
      }
    }
    
    const courseYear = Math.max(maxPrereqYear + 1, standingYear);
    courseYears[courseCode] = courseYear;
    return courseYear;
  }
  
  for (const courseCode of Object.keys(prereqMap)) {
    getCourseYear(courseCode);
  }
  
  return courseYears;
}

export function getCoursesNeedingRepeat(student: Student, courses: Course[]): Course[] {
  return courses.filter(course => checkCourseFailed(student, course.code));
}
