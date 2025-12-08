import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { students, majors, courses } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import * as XLSX from 'xlsx';

function normalizeColumnName(name: string): string {
  return name.toString().toLowerCase().trim().replace(/[^a-z0-9]/g, '');
}

function findColumn(headers: string[], variations: string[]): string | null {
  for (const header of headers) {
    const normalized = normalizeColumnName(header);
    for (const variation of variations) {
      if (normalized === normalizeColumnName(variation)) {
        return header;
      }
    }
  }
  return null;
}

function getStudentStanding(totalCredits: number): string {
  if (totalCredits >= 60) return 'Senior';
  if (totalCredits >= 30) return 'Junior';
  if (totalCredits >= 15) return 'Sophomore';
  return 'Freshman';
}

const META_COLUMNS = new Set([
  'id', 'name', 'email', 'student id', 'student name',
  'ofcreditscompleted', 'ofregistered', 'ofremaining', 
  'totalcredits', 'credits', 'standing', 'major',
  'numberofcreditscompleted', 'numberregistered', 'numberremaining',
]);

export async function POST(request: NextRequest) {
  try {
    const contentType = request.headers.get('content-type') || '';
    
    let majorId: string;
    let jsonData: Record<string, unknown>[];

    if (contentType.includes('multipart/form-data')) {
      const formData = await request.formData();
      const file = formData.get('file') as File | null;
      majorId = formData.get('majorId') as string;

      if (!file) {
        return NextResponse.json({ error: 'No file uploaded' }, { status: 400 });
      }

      if (!majorId) {
        return NextResponse.json({ error: 'majorId is required' }, { status: 400 });
      }

      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: 'array' });
      
      let allData: Record<string, unknown>[] = [];
      
      for (const sheetName of workbook.SheetNames) {
        const worksheet = workbook.Sheets[sheetName];
        const sheetData = XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, { defval: '' });
        
        if (sheetData.length > 0) {
          const headers = Object.keys(sheetData[0]);
          const hasId = findColumn(headers, ['ID', 'Student ID', 'StudentID']);
          const hasName = findColumn(headers, ['NAME', 'Name', 'Student Name', 'StudentName']);
          
          if (hasId && hasName) {
            allData = allData.concat(sheetData);
          }
        }
      }
      
      jsonData = allData;
    } else {
      const body = await request.json();
      majorId = body.majorId;
      jsonData = body.data;
      
      if (!majorId || !jsonData || !Array.isArray(jsonData)) {
        return NextResponse.json({ error: 'majorId and data array are required' }, { status: 400 });
      }
    }

    const majorRecord = await db.select().from(majors).where(eq(majors.id, majorId)).limit(1);
    if (majorRecord.length === 0) {
      return NextResponse.json({ error: 'Major not found' }, { status: 404 });
    }

    const coursesResult = await db.select().from(courses).where(eq(courses.majorId, majorId));
    const courseCodes = new Set(coursesResult.map(c => c.code));

    if (jsonData.length === 0) {
      return NextResponse.json({ error: 'No data found in file' }, { status: 400 });
    }

    const headers = Object.keys(jsonData[0]);
    
    const idCol = findColumn(headers, ['ID', 'Student ID', 'StudentID']);
    const nameCol = findColumn(headers, ['NAME', 'Name', 'Student Name', 'StudentName']);
    const emailCol = findColumn(headers, ['Email', 'E-mail', 'Email Address']);
    const creditsCompletedCol = findColumn(headers, ['# of Credits Completed', '# Credits Completed', 'Credits Completed', 'Completed Credits']);
    const creditsRegisteredCol = findColumn(headers, ['# Registered', '# Credits Registered', 'Registered Credits', 'Registered']);
    const creditsRemainingCol = findColumn(headers, ['# Remaining', '# Credits Remaining', 'Remaining Credits', 'Remaining']);

    if (!idCol) {
      return NextResponse.json({ 
        error: 'Missing required column: ID. Found columns: ' + headers.join(', ') 
      }, { status: 400 });
    }

    if (!nameCol) {
      return NextResponse.json({ 
        error: 'Missing required column: NAME. Found columns: ' + headers.join(', ') 
      }, { status: 400 });
    }

    const studentMap = new Map<string, {
      studentId: string;
      name: string;
      email: string | null;
      creditsCompleted: number;
      creditsRegistered: number;
      creditsRemaining: number;
      courseStatuses: Record<string, string>;
    }>();

    for (const row of jsonData) {
      const studentId = String(row[idCol] || '').trim();
      const name = String(row[nameCol] || '').trim();
      
      if (!studentId || !name) continue;

      const existing = studentMap.get(studentId);
      
      const email = emailCol ? String(row[emailCol] || '').trim() || null : null;
      const creditsCompleted = creditsCompletedCol ? Number(row[creditsCompletedCol]) || 0 : existing?.creditsCompleted || 0;
      const creditsRegistered = creditsRegisteredCol ? Number(row[creditsRegisteredCol]) || 0 : existing?.creditsRegistered || 0;
      const creditsRemaining = creditsRemainingCol ? Number(row[creditsRemainingCol]) || 0 : existing?.creditsRemaining || 0;

      const courseStatuses: Record<string, string> = existing?.courseStatuses || {};
      
      for (const [key, value] of Object.entries(row)) {
        if (key === idCol || key === nameCol || key === emailCol || 
            key === creditsCompletedCol || key === creditsRegisteredCol || key === creditsRemainingCol) {
          continue;
        }
        
        const normalizedKey = normalizeColumnName(key);
        if (META_COLUMNS.has(normalizedKey)) continue;
        
        if (value !== undefined && value !== null && value !== '') {
          const status = String(value).trim().toLowerCase();
          if (status && status !== '0' && status !== 'undefined' && status !== 'null') {
            if (courseCodes.has(key) || key.match(/^[A-Z]{2,4}\s?\d{3,4}/)) {
              courseStatuses[key] = status;
            }
          }
        }
      }

      studentMap.set(studentId, {
        studentId,
        name: existing?.name || name,
        email: email || existing?.email || null,
        creditsCompleted: Math.max(creditsCompleted, existing?.creditsCompleted || 0),
        creditsRegistered: Math.max(creditsRegistered, existing?.creditsRegistered || 0),
        creditsRemaining: Math.max(creditsRemaining, existing?.creditsRemaining || 0),
        courseStatuses,
      });
    }

    if (studentMap.size === 0) {
      return NextResponse.json({ error: 'No valid students found in file' }, { status: 400 });
    }

    await db.delete(students).where(eq(students.majorId, majorId));

    const studentsToInsert = Array.from(studentMap.values()).map(s => ({
      majorId,
      studentId: s.studentId,
      name: s.name,
      email: s.email,
      creditsCompleted: s.creditsCompleted,
      creditsRegistered: s.creditsRegistered,
      creditsRemaining: s.creditsRemaining,
      standing: getStudentStanding(s.creditsCompleted + s.creditsRegistered),
      courseStatuses: s.courseStatuses,
    }));

    const inserted = await db.insert(students).values(studentsToInsert).returning();

    return NextResponse.json({ 
      success: true, 
      count: inserted.length,
      message: `Imported ${inserted.length} students for ${majorRecord[0].code}`
    });
  } catch (error) {
    console.error('Error importing students:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Failed to import students' 
    }, { status: 500 });
  }
}
