import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { majors } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const result = await db.select().from(majors).where(eq(majors.id, id));
    
    if (result.length === 0) {
      return NextResponse.json({ error: 'Major not found' }, { status: 404 });
    }
    
    return NextResponse.json(result[0]);
  } catch (error) {
    console.error('Error fetching major:', error);
    return NextResponse.json({ error: 'Failed to fetch major' }, { status: 500 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    
    const result = await db.update(majors)
      .set({
        ...body,
        updatedAt: new Date(),
      })
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

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const result = await db.delete(majors).where(eq(majors.id, id)).returning();
    
    if (result.length === 0) {
      return NextResponse.json({ error: 'Major not found' }, { status: 404 });
    }
    
    return NextResponse.json({ message: 'Major deleted successfully' });
  } catch (error) {
    console.error('Error deleting major:', error);
    return NextResponse.json({ error: 'Failed to delete major' }, { status: 500 });
  }
}
