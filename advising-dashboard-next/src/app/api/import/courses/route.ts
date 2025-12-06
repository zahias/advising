import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { courses, majors } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

interface CourseImportRow {
  'Course Code': string;
  'Title'?: string;
  'Name'?: string;
  'Credits'?: number;
  'Type'?: string;
  'Semester'?: number;
  'Offered'?: string | boolean;
  'Prerequisite'?: string;
  'Prerequisites'?: string;
  'Corequisite'?: string;
  'Corequisites'?: string;
  'Concurrent'?: string;
  'Standing'?: string;
  'Description'?: string;
}

function parseRequirements(str: string | undefined | null): string[] {
  if (!str || str === '') return [];
  return str.split(/[,;]/).map(p => p.trim()).filter(p => p.length > 0);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { majorId, data } = body as { majorId: string; data: CourseImportRow[] };
    
    if (!majorId || !data || !Array.isArray(data)) {
      return NextResponse.json({ error: 'majorId and data array are required' }, { status: 400 });
    }
    
    const majorResult = await db.select().from(majors).where(eq(majors.id, majorId));
    if (majorResult.length === 0) {
      return NextResponse.json({ error: 'Major not found' }, { status: 404 });
    }
    
    const results = { created: 0, updated: 0, errors: [] as string[] };
    
    for (const row of data) {
      try {
        const code = row['Course Code'];
        if (!code) {
          results.errors.push('Row missing Course Code');
          continue;
        }
        
        const name = row['Title'] || row['Name'] || code;
        const credits = row['Credits'] || 3;
        const type = row['Type']?.toLowerCase() || 'required';
        const semester = row['Semester'] || null;
        const offered = row['Offered'] === true || row['Offered'] === 'Yes' || row['Offered'] === 'TRUE' || row['Offered'] === 'true';
        const prerequisites = parseRequirements(row['Prerequisite'] || row['Prerequisites']);
        const corequisites = parseRequirements(row['Corequisite'] || row['Corequisites']);
        const concurrent = parseRequirements(row['Concurrent']);
        const standingRequired = row['Standing'] || null;
        const description = row['Description'] || null;
        
        const existing = await db.select().from(courses)
          .where(eq(courses.code, code))
          .limit(1);
        
        if (existing.length > 0 && existing[0].majorId === majorId) {
          await db.update(courses)
            .set({
              name,
              credits,
              type,
              semester,
              offered,
              prerequisites,
              corequisites,
              concurrent,
              standingRequired,
              description,
              updatedAt: new Date(),
            })
            .where(eq(courses.id, existing[0].id));
          results.updated++;
        } else {
          await db.insert(courses).values({
            majorId,
            code,
            name,
            credits,
            type,
            semester,
            offered,
            prerequisites,
            corequisites,
            concurrent,
            standingRequired,
            description,
          });
          results.created++;
        }
      } catch (err) {
        results.errors.push(`Error processing ${row['Course Code'] || 'unknown'}: ${err}`);
      }
    }
    
    return NextResponse.json(results);
  } catch (error) {
    console.error('Error importing courses:', error);
    return NextResponse.json({ error: 'Failed to import courses' }, { status: 500 });
  }
}
