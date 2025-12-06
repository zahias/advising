import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { courses, majors } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const majorId = searchParams.get('majorId');
    const majorCode = searchParams.get('major');
    
    let result: (typeof courses.$inferSelect)[] = [];
    if (majorId) {
      result = await db.select().from(courses).where(eq(courses.majorId, majorId));
    } else if (majorCode) {
      const majorResult = await db.select().from(majors).where(eq(majors.code, majorCode));
      if (majorResult.length > 0) {
        result = await db.select().from(courses).where(eq(courses.majorId, majorResult[0].id));
      }
    } else {
      result = await db.select().from(courses);
    }
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching courses:', error);
    return NextResponse.json({ error: 'Failed to fetch courses' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const { majorId, code, name, credits, type, semester, offered, prerequisites, corequisites, concurrent, standingRequired, description } = body;
    
    if (!majorId || !code || !name) {
      return NextResponse.json({ error: 'majorId, code, and name are required' }, { status: 400 });
    }
    
    const result = await db.insert(courses).values({
      majorId,
      code,
      name,
      credits: credits || 3,
      type: type || 'required',
      semester: semester || null,
      offered: offered !== false,
      prerequisites: prerequisites || [],
      corequisites: corequisites || [],
      concurrent: concurrent || [],
      standingRequired: standingRequired || null,
      description: description || null,
    }).returning();
    
    return NextResponse.json(result[0], { status: 201 });
  } catch (error) {
    console.error('Error creating course:', error);
    return NextResponse.json({ error: 'Failed to create course' }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { id, code, name, credits, type, semester, offered, prerequisites, corequisites, concurrent, standingRequired, description } = body;
    
    if (!id) {
      return NextResponse.json({ error: 'Course ID is required' }, { status: 400 });
    }
    
    const updateData: Record<string, unknown> = { updatedAt: new Date() };
    if (code !== undefined) updateData.code = code;
    if (name !== undefined) updateData.name = name;
    if (credits !== undefined) updateData.credits = credits;
    if (type !== undefined) updateData.type = type;
    if (semester !== undefined) updateData.semester = semester;
    if (offered !== undefined) updateData.offered = offered;
    if (prerequisites !== undefined) updateData.prerequisites = prerequisites;
    if (corequisites !== undefined) updateData.corequisites = corequisites;
    if (concurrent !== undefined) updateData.concurrent = concurrent;
    if (standingRequired !== undefined) updateData.standingRequired = standingRequired;
    if (description !== undefined) updateData.description = description;
    
    const result = await db.update(courses)
      .set(updateData)
      .where(eq(courses.id, id))
      .returning();
    
    if (result.length === 0) {
      return NextResponse.json({ error: 'Course not found' }, { status: 404 });
    }
    
    return NextResponse.json(result[0]);
  } catch (error) {
    console.error('Error updating course:', error);
    return NextResponse.json({ error: 'Failed to update course' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    
    if (!id) {
      return NextResponse.json({ error: 'Course ID is required' }, { status: 400 });
    }
    
    await db.delete(courses).where(eq(courses.id, id));
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting course:', error);
    return NextResponse.json({ error: 'Failed to delete course' }, { status: 500 });
  }
}
