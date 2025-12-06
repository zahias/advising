import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { advisingPlans, students, majors } from '@/lib/db/schema';
import { eq, and } from 'drizzle-orm';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const studentId = searchParams.get('studentId');
    const periodId = searchParams.get('periodId');
    
    let result;
    if (studentId && periodId) {
      result = await db.select().from(advisingPlans)
        .where(and(
          eq(advisingPlans.studentId, studentId),
          eq(advisingPlans.periodId, periodId)
        ))
        .orderBy(advisingPlans.termSequence);
    } else if (studentId) {
      result = await db.select().from(advisingPlans)
        .where(eq(advisingPlans.studentId, studentId))
        .orderBy(advisingPlans.termSequence);
    } else {
      result = await db.select().from(advisingPlans).orderBy(advisingPlans.termSequence);
    }
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching plans:', error);
    return NextResponse.json({ error: 'Failed to fetch plans' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { studentId, periodId, termName, termSequence, plannedCourses, notes } = body;
    
    if (!studentId || !termName || termSequence === undefined) {
      return NextResponse.json({ error: 'studentId, termName, and termSequence are required' }, { status: 400 });
    }
    
    const result = await db.insert(advisingPlans).values({
      studentId,
      periodId: periodId || null,
      termName,
      termSequence,
      plannedCourses: plannedCourses || [],
      notes: notes || null,
    }).returning();
    
    return NextResponse.json(result[0], { status: 201 });
  } catch (error) {
    console.error('Error creating plan:', error);
    return NextResponse.json({ error: 'Failed to create plan' }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { id, plannedCourses, notes, termName } = body;
    
    if (!id) {
      return NextResponse.json({ error: 'Plan ID is required' }, { status: 400 });
    }
    
    const updateData: Record<string, unknown> = { updatedAt: new Date() };
    if (plannedCourses !== undefined) updateData.plannedCourses = plannedCourses;
    if (notes !== undefined) updateData.notes = notes;
    if (termName !== undefined) updateData.termName = termName;
    
    const result = await db.update(advisingPlans)
      .set(updateData)
      .where(eq(advisingPlans.id, id))
      .returning();
    
    if (result.length === 0) {
      return NextResponse.json({ error: 'Plan not found' }, { status: 404 });
    }
    
    return NextResponse.json(result[0]);
  } catch (error) {
    console.error('Error updating plan:', error);
    return NextResponse.json({ error: 'Failed to update plan' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    
    if (!id) {
      return NextResponse.json({ error: 'Plan ID is required' }, { status: 400 });
    }
    
    await db.delete(advisingPlans).where(eq(advisingPlans.id, id));
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting plan:', error);
    return NextResponse.json({ error: 'Failed to delete plan' }, { status: 500 });
  }
}
