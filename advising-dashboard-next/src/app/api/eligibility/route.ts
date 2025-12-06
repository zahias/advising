import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { courses, students, advisingSessions, advisingPeriods } from '@/lib/db/schema';
import { eq, and, desc } from 'drizzle-orm';
import { 
  checkEligibility, 
  getAllCoursesWithEligibility,
  getStudentStanding,
  type Course as EligibilityCourse,
  type Student as EligibilityStudent
} from '@/lib/eligibility';

function dbCourseToEligibilityCourse(dbCourse: typeof courses.$inferSelect): EligibilityCourse {
  return {
    id: dbCourse.id,
    code: dbCourse.code,
    name: dbCourse.name,
    credits: dbCourse.credits,
    type: dbCourse.type as 'required' | 'intensive' | 'elective',
    semester: dbCourse.semester ?? undefined,
    offered: dbCourse.offered,
    prerequisites: (dbCourse.prerequisites as string[]) || [],
    corequisites: (dbCourse.corequisites as string[]) || [],
    concurrent: (dbCourse.concurrent as string[]) || [],
    standingRequired: dbCourse.standingRequired ?? undefined,
    description: dbCourse.description ?? undefined,
  };
}

function dbStudentToEligibilityStudent(dbStudent: typeof students.$inferSelect): EligibilityStudent {
  const totalCredits = (dbStudent.creditsCompleted || 0) + (dbStudent.creditsRegistered || 0);
  return {
    id: dbStudent.id,
    studentId: dbStudent.studentId,
    name: dbStudent.name,
    email: dbStudent.email ?? undefined,
    standing: dbStudent.standing || getStudentStanding(totalCredits),
    creditsCompleted: dbStudent.creditsCompleted || 0,
    creditsRegistered: dbStudent.creditsRegistered || 0,
    creditsRemaining: dbStudent.creditsRemaining || 0,
    courseStatuses: (dbStudent.courseStatuses as Record<string, string>) || {},
  };
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const studentId = searchParams.get('studentId');
    const majorId = searchParams.get('majorId');
    const periodId = searchParams.get('periodId');
    
    if (!studentId || !majorId) {
      return NextResponse.json({ error: 'studentId and majorId are required' }, { status: 400 });
    }
    
    const studentResult = await db.select().from(students).where(eq(students.id, studentId));
    if (studentResult.length === 0) {
      return NextResponse.json({ error: 'Student not found' }, { status: 404 });
    }
    
    const coursesResult = await db.select().from(courses).where(eq(courses.majorId, majorId));
    
    let session = null;
    if (periodId) {
      const sessionResult = await db.select()
        .from(advisingSessions)
        .where(and(
          eq(advisingSessions.studentId, studentId),
          eq(advisingSessions.periodId, periodId)
        ))
        .orderBy(desc(advisingSessions.updatedAt))
        .limit(1);
      
      if (sessionResult.length > 0) {
        session = sessionResult[0];
      }
    }
    
    const student = dbStudentToEligibilityStudent(studentResult[0]);
    const courseList = coursesResult.map(dbCourseToEligibilityCourse);
    
    const advisedCourses = session?.advisedCourses as string[] || [];
    const optionalCourses = session?.optionalCourses as string[] || [];
    const repeatCourses = session?.repeatCourses as string[] || [];
    const bypasses = session?.bypasses as Record<string, { note: string; advisor: string }> || {};
    
    const allAdvised = [...advisedCourses, ...optionalCourses, ...repeatCourses];
    
    const eligibilityResults = getAllCoursesWithEligibility(
      student,
      courseList,
      allAdvised,
      { bypasses }
    );
    
    return NextResponse.json({
      student,
      courses: eligibilityResults,
      session: session ? {
        id: session.id,
        advisedCourses,
        optionalCourses,
        repeatCourses,
        bypasses,
        note: session.note,
      } : null,
    });
  } catch (error) {
    console.error('Error checking eligibility:', error);
    return NextResponse.json({ error: 'Failed to check eligibility' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { studentId, courseCode, majorId, advisedCourses = [], bypasses = {} } = body;
    
    if (!studentId || !courseCode || !majorId) {
      return NextResponse.json({ error: 'studentId, courseCode, and majorId are required' }, { status: 400 });
    }
    
    const studentResult = await db.select().from(students).where(eq(students.id, studentId));
    if (studentResult.length === 0) {
      return NextResponse.json({ error: 'Student not found' }, { status: 404 });
    }
    
    const coursesResult = await db.select().from(courses).where(eq(courses.majorId, majorId));
    
    const student = dbStudentToEligibilityStudent(studentResult[0]);
    const courseList = coursesResult.map(dbCourseToEligibilityCourse);
    
    const result = checkEligibility(
      student,
      courseCode,
      advisedCourses,
      courseList,
      { bypasses }
    );
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error checking single course eligibility:', error);
    return NextResponse.json({ error: 'Failed to check eligibility' }, { status: 500 });
  }
}
