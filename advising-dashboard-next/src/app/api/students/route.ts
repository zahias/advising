import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { students, majors } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const majorId = searchParams.get('majorId');
    const majorCode = searchParams.get('major');
    
    let result: (typeof students.$inferSelect)[] = [];
    if (majorId) {
      result = await db.select().from(students).where(eq(students.majorId, majorId));
    } else if (majorCode) {
      const majorResult = await db.select().from(majors).where(eq(majors.code, majorCode));
      if (majorResult.length > 0) {
        result = await db.select().from(students).where(eq(students.majorId, majorResult[0].id));
      }
    } else {
      result = await db.select().from(students);
    }
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching students:', error);
    return NextResponse.json({ error: 'Failed to fetch students' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const { majorId, studentId, name, email, standing, creditsCompleted, creditsRegistered, creditsRemaining, courseStatuses } = body;
    
    if (!majorId || !studentId || !name) {
      return NextResponse.json({ error: 'majorId, studentId, and name are required' }, { status: 400 });
    }
    
    const result = await db.insert(students).values({
      majorId,
      studentId,
      name,
      email: email || null,
      standing: standing || null,
      creditsCompleted: creditsCompleted || 0,
      creditsRegistered: creditsRegistered || 0,
      creditsRemaining: creditsRemaining || 0,
      courseStatuses: courseStatuses || {},
    }).returning();
    
    return NextResponse.json(result[0], { status: 201 });
  } catch (error) {
    console.error('Error creating student:', error);
    return NextResponse.json({ error: 'Failed to create student' }, { status: 500 });
  }
}
