import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { advisingSessions, advisingPeriods, students } from '@/lib/db/schema';
import { eq, and, desc } from 'drizzle-orm';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const studentId = searchParams.get('studentId');
    const periodId = searchParams.get('periodId');
    
    let result;
    if (studentId && periodId) {
      result = await db.select()
        .from(advisingSessions)
        .where(and(
          eq(advisingSessions.studentId, studentId),
          eq(advisingSessions.periodId, periodId)
        ))
        .orderBy(desc(advisingSessions.updatedAt))
        .limit(1);
    } else if (studentId) {
      result = await db.select()
        .from(advisingSessions)
        .where(eq(advisingSessions.studentId, studentId))
        .orderBy(desc(advisingSessions.updatedAt));
    } else if (periodId) {
      result = await db.select()
        .from(advisingSessions)
        .where(eq(advisingSessions.periodId, periodId))
        .orderBy(desc(advisingSessions.updatedAt));
    } else {
      result = await db.select()
        .from(advisingSessions)
        .orderBy(desc(advisingSessions.updatedAt));
    }
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching sessions:', error);
    return NextResponse.json({ error: 'Failed to fetch sessions' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const { periodId, studentId, advisorId, advisedCourses, optionalCourses, repeatCourses, bypasses, note } = body;
    
    if (!periodId || !studentId) {
      return NextResponse.json({ error: 'periodId and studentId are required' }, { status: 400 });
    }
    
    const existing = await db.select()
      .from(advisingSessions)
      .where(and(
        eq(advisingSessions.studentId, studentId),
        eq(advisingSessions.periodId, periodId)
      ))
      .limit(1);
    
    if (existing.length > 0) {
      const result = await db.update(advisingSessions)
        .set({
          advisorId: advisorId || existing[0].advisorId,
          advisedCourses: advisedCourses || [],
          optionalCourses: optionalCourses || [],
          repeatCourses: repeatCourses || [],
          bypasses: bypasses || {},
          note: note || null,
          updatedAt: new Date(),
        })
        .where(eq(advisingSessions.id, existing[0].id))
        .returning();
      
      return NextResponse.json(result[0]);
    }
    
    const result = await db.insert(advisingSessions).values({
      periodId,
      studentId,
      advisorId: advisorId || null,
      advisedCourses: advisedCourses || [],
      optionalCourses: optionalCourses || [],
      repeatCourses: repeatCourses || [],
      bypasses: bypasses || {},
      note: note || null,
    }).returning();
    
    return NextResponse.json(result[0], { status: 201 });
  } catch (error) {
    console.error('Error creating/updating session:', error);
    return NextResponse.json({ error: 'Failed to create/update session' }, { status: 500 });
  }
}
