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

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { id, studentId, name, email, standing, creditsCompleted, creditsRegistered, creditsRemaining, courseStatuses } = body;
    
    if (!id) {
      return NextResponse.json({ error: 'id is required' }, { status: 400 });
    }
    
    const updateData: Record<string, unknown> = { updatedAt: new Date() };
    if (studentId !== undefined) updateData.studentId = studentId;
    if (name !== undefined) updateData.name = name;
    if (email !== undefined) updateData.email = email;
    if (standing !== undefined) updateData.standing = standing;
    if (creditsCompleted !== undefined) updateData.creditsCompleted = creditsCompleted;
    if (creditsRegistered !== undefined) updateData.creditsRegistered = creditsRegistered;
    if (creditsRemaining !== undefined) updateData.creditsRemaining = creditsRemaining;
    if (courseStatuses !== undefined) updateData.courseStatuses = courseStatuses;
    
    const result = await db.update(students)
      .set(updateData)
      .where(eq(students.id, id))
      .returning();
    
    if (result.length === 0) {
      return NextResponse.json({ error: 'Student not found' }, { status: 404 });
    }
    
    return NextResponse.json(result[0]);
  } catch (error) {
    console.error('Error updating student:', error);
    return NextResponse.json({ error: 'Failed to update student' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    
    if (!id) {
      return NextResponse.json({ error: 'id is required' }, { status: 400 });
    }
    
    const result = await db.delete(students).where(eq(students.id, id)).returning();
    
    if (result.length === 0) {
      return NextResponse.json({ error: 'Student not found' }, { status: 404 });
    }
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting student:', error);
    return NextResponse.json({ error: 'Failed to delete student' }, { status: 500 });
  }
}
