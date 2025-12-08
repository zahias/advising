import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { courses, majors } from '@/lib/db/schema';
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

function parseRequirements(str: string | undefined | null): string[] {
  if (!str || str === '' || str === 'undefined' || str === 'null') return [];
  return String(str).split(/[,;]/).map(p => p.trim()).filter(p => p.length > 0);
}

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
      
      const sheetName = workbook.SheetNames[0];
      const worksheet = workbook.Sheets[sheetName];
      jsonData = XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, { defval: '' });
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

    if (jsonData.length === 0) {
      return NextResponse.json({ error: 'No data found in file' }, { status: 400 });
    }

    const headers = Object.keys(jsonData[0]);
    
    const codeCol = findColumn(headers, ['Course Code', 'CourseCode', 'Code', 'Course']);
    const offeredCol = findColumn(headers, ['Offered', 'Semester', 'Term', 'Offering']);
    const nameCol = findColumn(headers, ['Course Name', 'CourseName', 'Name', 'Title', 'Course Title']);
    const creditsCol = findColumn(headers, ['Credits', 'Credit', 'Credit Hours', 'CreditHours', 'Cr']);
    const prereqCol = findColumn(headers, ['Prerequisites', 'Prereq', 'Pre-requisite', 'Prerequisite']);
    const coreqCol = findColumn(headers, ['Corequisites', 'Coreq', 'Co-requisite', 'Corequisite']);
    const concurrentCol = findColumn(headers, ['Concurrent', 'Concurrent Enrollment', 'ConcurrentEnrollment']);
    const typeCol = findColumn(headers, ['Type', 'Course Type', 'CourseType', 'Category']);
    const standingCol = findColumn(headers, ['Standing', 'Required Standing', 'RequiredStanding', 'Level']);
    const semesterCol = findColumn(headers, ['Semester Number', 'SemesterNumber', 'Sem', 'Semester Num']);

    if (!codeCol) {
      return NextResponse.json({ 
        error: 'Missing required column: Course Code. Found columns: ' + headers.join(', ') 
      }, { status: 400 });
    }

    const coursesToInsert: Array<{
      majorId: string;
      code: string;
      name: string;
      credits: number;
      prerequisites: string[];
      corequisites: string[];
      concurrent: string[];
      type: string;
      standingRequired: string | null;
      offered: boolean;
      semester: number | null;
    }> = [];

    for (const row of jsonData) {
      const code = String(row[codeCol] || '').trim();
      if (!code) continue;

      const credits = creditsCol ? Number(row[creditsCol]) || 3 : 3;
      const name = nameCol ? String(row[nameCol] || '').trim() || code : code;
      const prerequisites = prereqCol ? parseRequirements(String(row[prereqCol])) : [];
      const corequisites = coreqCol ? parseRequirements(String(row[coreqCol])) : [];
      const concurrent = concurrentCol ? parseRequirements(String(row[concurrentCol])) : [];
      const type = typeCol ? String(row[typeCol] || 'required').trim().toLowerCase() : 'required';
      const standingRequired = standingCol ? String(row[standingCol] || '').trim() || null : null;
      
      let offered = true;
      if (offeredCol) {
        const offeredVal = row[offeredCol];
        offered = offeredVal === true || 
                  offeredVal === 'Yes' || 
                  offeredVal === 'TRUE' || 
                  offeredVal === 'true' ||
                  offeredVal === 'Y' ||
                  offeredVal === 1 ||
                  offeredVal === '1';
      }
      
      const semester = semesterCol ? Number(row[semesterCol]) || null : null;

      coursesToInsert.push({
        majorId,
        code,
        name,
        credits,
        prerequisites,
        corequisites,
        concurrent,
        type,
        standingRequired,
        offered,
        semester,
      });
    }

    if (coursesToInsert.length === 0) {
      return NextResponse.json({ error: 'No valid courses found in file' }, { status: 400 });
    }

    await db.delete(courses).where(eq(courses.majorId, majorId));

    const inserted = await db.insert(courses).values(coursesToInsert).returning();

    return NextResponse.json({ 
      success: true, 
      count: inserted.length,
      message: `Imported ${inserted.length} courses for ${majorRecord[0].code}`
    });
  } catch (error) {
    console.error('Error importing courses:', error);
    return NextResponse.json({ 
      error: error instanceof Error ? error.message : 'Failed to import courses' 
    }, { status: 500 });
  }
}
