import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { majors } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export async function GET() {
  try {
    const result = await db.select().from(majors);
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
