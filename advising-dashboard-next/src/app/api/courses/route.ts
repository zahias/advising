import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { courses, majors } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const majorId = searchParams.get('majorId');
    
    let result;
    if (majorId) {
      result = await db.select().from(courses).where(eq(courses.majorId, majorId));
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
