import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { advisingPeriods } from '@/lib/db/schema';
import { eq, and, desc } from 'drizzle-orm';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const majorId = searchParams.get('majorId');
    const activeOnly = searchParams.get('activeOnly') === 'true';
    
    let result;
    if (majorId && activeOnly) {
      result = await db.select()
        .from(advisingPeriods)
        .where(and(
          eq(advisingPeriods.majorId, majorId),
          eq(advisingPeriods.isActive, true)
        ))
        .orderBy(desc(advisingPeriods.createdAt));
    } else if (majorId) {
      result = await db.select()
        .from(advisingPeriods)
        .where(eq(advisingPeriods.majorId, majorId))
        .orderBy(desc(advisingPeriods.createdAt));
    } else {
      result = await db.select()
        .from(advisingPeriods)
        .orderBy(desc(advisingPeriods.createdAt));
    }
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching periods:', error);
    return NextResponse.json({ error: 'Failed to fetch periods' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const { majorId, semester, year, advisorName, isActive } = body;
    
    if (!majorId || !semester || !year) {
      return NextResponse.json({ error: 'majorId, semester, and year are required' }, { status: 400 });
    }
    
    if (isActive !== false) {
      await db.update(advisingPeriods)
        .set({ isActive: false })
        .where(eq(advisingPeriods.majorId, majorId));
    }
    
    const result = await db.insert(advisingPeriods).values({
      majorId,
      semester,
      year,
      advisorName: advisorName || null,
      isActive: isActive !== false,
    }).returning();
    
    return NextResponse.json(result[0], { status: 201 });
  } catch (error) {
    console.error('Error creating period:', error);
    return NextResponse.json({ error: 'Failed to create period' }, { status: 500 });
  }
}
