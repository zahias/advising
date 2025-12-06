import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { students, majors, courses } from '@/lib/db/schema';
import { eq, and } from 'drizzle-orm';

interface StudentImportRow {
  ID: string | number;
  NAME: string;
  Email?: string;
  '# of Credits Completed'?: number;
  '# Registered'?: number;
  '# Remaining'?: number;
  'Total Credits'?: number;
  [key: string]: string | number | undefined;
}

function getStudentStanding(totalCredits: number): string {
  if (totalCredits >= 60) return 'Senior';
  if (totalCredits >= 30) return 'Junior';
  if (totalCredits >= 15) return 'Sophomore';
  return 'Freshman';
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { majorId, data } = body as { majorId: string; data: StudentImportRow[] };
    
    if (!majorId || !data || !Array.isArray(data)) {
      return NextResponse.json({ error: 'majorId and data array are required' }, { status: 400 });
    }
    
    const majorResult = await db.select().from(majors).where(eq(majors.id, majorId));
    if (majorResult.length === 0) {
      return NextResponse.json({ error: 'Major not found' }, { status: 404 });
    }
    
    const coursesResult = await db.select().from(courses).where(eq(courses.majorId, majorId));
    const courseCodes = new Set(coursesResult.map(c => c.code));
    
    const results = { created: 0, updated: 0, errors: [] as string[] };
    
    const baseColumns = ['ID', 'NAME', 'Email', '# of Credits Completed', '# Registered', '# Remaining', 'Total Credits'];
    
    for (const row of data) {
      try {
        const studentId = String(row.ID);
        const name = row.NAME;
        
        if (!studentId || !name) {
          results.errors.push('Row missing ID or NAME');
          continue;
        }
        
        const creditsCompleted = row['# of Credits Completed'] || 0;
        const creditsRegistered = row['# Registered'] || 0;
        const creditsRemaining = row['# Remaining'] || 0;
        const totalCredits = row['Total Credits'] || (creditsCompleted + creditsRegistered);
        const email = row.Email || null;
        
        const courseStatuses: Record<string, string> = {};
        for (const [key, value] of Object.entries(row)) {
          if (!baseColumns.includes(key) && value !== undefined && value !== null && value !== '') {
            if (courseCodes.has(key) || key.match(/^[A-Z]{2,4}\s?\d{3}/)) {
              courseStatuses[key] = String(value).toLowerCase();
            }
          }
        }
        
        const standing = getStudentStanding(totalCredits);
        
        const existing = await db.select().from(students)
          .where(and(
            eq(students.studentId, studentId),
            eq(students.majorId, majorId)
          ))
          .limit(1);
        
        if (existing.length > 0) {
          await db.update(students)
            .set({
              name,
              email,
              standing,
              creditsCompleted,
              creditsRegistered,
              creditsRemaining,
              courseStatuses,
              updatedAt: new Date(),
            })
            .where(eq(students.id, existing[0].id));
          results.updated++;
        } else {
          await db.insert(students).values({
            majorId,
            studentId,
            name,
            email,
            standing,
            creditsCompleted,
            creditsRegistered,
            creditsRemaining,
            courseStatuses,
          });
          results.created++;
        }
      } catch (err) {
        results.errors.push(`Error processing ${row.NAME || 'unknown'}: ${err}`);
      }
    }
    
    return NextResponse.json(results);
  } catch (error) {
    console.error('Error importing students:', error);
    return NextResponse.json({ error: 'Failed to import students' }, { status: 500 });
  }
}
