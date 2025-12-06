import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { emailTemplates } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const category = searchParams.get('category');
    const activeOnly = searchParams.get('activeOnly') === 'true';
    
    let result;
    if (category && activeOnly) {
      result = await db.select().from(emailTemplates)
        .where(eq(emailTemplates.category, category));
      result = result.filter(t => t.isActive);
    } else if (category) {
      result = await db.select().from(emailTemplates)
        .where(eq(emailTemplates.category, category));
    } else if (activeOnly) {
      result = await db.select().from(emailTemplates)
        .where(eq(emailTemplates.isActive, true));
    } else {
      result = await db.select().from(emailTemplates);
    }
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching email templates:', error);
    return NextResponse.json({ error: 'Failed to fetch templates' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, subject, body: templateBody, category } = body;
    
    if (!name || !subject || !templateBody) {
      return NextResponse.json({ error: 'Name, subject, and body are required' }, { status: 400 });
    }
    
    const result = await db.insert(emailTemplates).values({
      name,
      subject,
      body: templateBody,
      category: category || 'general',
    }).returning();
    
    return NextResponse.json(result[0], { status: 201 });
  } catch (error) {
    console.error('Error creating email template:', error);
    return NextResponse.json({ error: 'Failed to create template' }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { id, name, subject, body: templateBody, category, isActive } = body;
    
    if (!id) {
      return NextResponse.json({ error: 'Template ID is required' }, { status: 400 });
    }
    
    const updateData: Record<string, unknown> = { updatedAt: new Date() };
    if (name !== undefined) updateData.name = name;
    if (subject !== undefined) updateData.subject = subject;
    if (templateBody !== undefined) updateData.body = templateBody;
    if (category !== undefined) updateData.category = category;
    if (isActive !== undefined) updateData.isActive = isActive;
    
    const result = await db.update(emailTemplates)
      .set(updateData)
      .where(eq(emailTemplates.id, id))
      .returning();
    
    if (result.length === 0) {
      return NextResponse.json({ error: 'Template not found' }, { status: 404 });
    }
    
    return NextResponse.json(result[0]);
  } catch (error) {
    console.error('Error updating email template:', error);
    return NextResponse.json({ error: 'Failed to update template' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    
    if (!id) {
      return NextResponse.json({ error: 'Template ID is required' }, { status: 400 });
    }
    
    await db.delete(emailTemplates).where(eq(emailTemplates.id, id));
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting email template:', error);
    return NextResponse.json({ error: 'Failed to delete template' }, { status: 500 });
  }
}
