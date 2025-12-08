import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { majors, courses, students } from '@/lib/db/schema';
import { eq, sql } from 'drizzle-orm';

export async function GET() {
  try {
    const allMajors = await db.select().from(majors);
    
    const result = await Promise.all(allMajors.map(async (major) => {
      const [courseCount] = await db.select({ count: sql<number>`count(*)` }).from(courses).where(eq(courses.majorId, major.id));
      const [studentCount] = await db.select({ count: sql<number>`count(*)` }).from(students).where(eq(students.majorId, major.id));
      
      return {
        ...major,
        courseCount: Number(courseCount?.count || 0),
        studentCount: Number(studentCount?.count || 0),
      };
    }));
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching majors:', error);
    return NextResponse.json({ error: 'Failed to fetch majors' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const { code, name, description, isActive } = body;
    
    if (!code || !name) {
      return NextResponse.json({ error: 'code and name are required' }, { status: 400 });
    }
    
    const result = await db.insert(majors).values({
      code,
      name,
      description: description || null,
      isActive: isActive !== false,
    }).returning();
    
    return NextResponse.json(result[0], { status: 201 });
  } catch (error) {
    console.error('Error creating major:', error);
    return NextResponse.json({ error: 'Failed to create major' }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { id, code, name, description, isActive } = body;
    
    if (!id) {
      return NextResponse.json({ error: 'id is required' }, { status: 400 });
    }
    
    const updateData: Record<string, unknown> = {};
    if (code !== undefined) updateData.code = code;
    if (name !== undefined) updateData.name = name;
    if (description !== undefined) updateData.description = description;
    if (isActive !== undefined) updateData.isActive = isActive;
    
    const result = await db.update(majors)
      .set(updateData)
      .where(eq(majors.id, id))
      .returning();
    
    if (result.length === 0) {
      return NextResponse.json({ error: 'Major not found' }, { status: 404 });
    }
    
    return NextResponse.json(result[0]);
  } catch (error) {
    console.error('Error updating major:', error);
    return NextResponse.json({ error: 'Failed to update major' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    
    if (!id) {
      return NextResponse.json({ error: 'id is required' }, { status: 400 });
    }
    
    const [courseCount] = await db.select({ count: sql<number>`count(*)` }).from(courses).where(eq(courses.majorId, id));
    const [studentCount] = await db.select({ count: sql<number>`count(*)` }).from(students).where(eq(students.majorId, id));
    
    if (Number(courseCount?.count) > 0 || Number(studentCount?.count) > 0) {
      return NextResponse.json({ 
        error: 'Cannot delete major with existing courses or students. Remove them first.' 
      }, { status: 400 });
    }
    
    const result = await db.delete(majors).where(eq(majors.id, id)).returning();
    
    if (result.length === 0) {
      return NextResponse.json({ error: 'Major not found' }, { status: 404 });
    }
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting major:', error);
    return NextResponse.json({ error: 'Failed to delete major' }, { status: 500 });
  }
}
