import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { settings } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const category = searchParams.get('category');
    const key = searchParams.get('key');
    
    let result;
    if (key) {
      result = await db.select().from(settings).where(eq(settings.key, key));
      return NextResponse.json(result[0] || null);
    } else if (category) {
      result = await db.select().from(settings).where(eq(settings.category, category));
    } else {
      result = await db.select().from(settings);
    }
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching settings:', error);
    return NextResponse.json({ error: 'Failed to fetch settings' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { key, value, category } = body;
    
    if (!key) {
      return NextResponse.json({ error: 'Key is required' }, { status: 400 });
    }
    
    const existing = await db.select().from(settings).where(eq(settings.key, key));
    
    if (existing.length > 0) {
      const result = await db.update(settings)
        .set({ value, category: category || existing[0].category, updatedAt: new Date() })
        .where(eq(settings.key, key))
        .returning();
      return NextResponse.json(result[0]);
    } else {
      const result = await db.insert(settings).values({
        key,
        value: value || {},
        category: category || 'general',
      }).returning();
      return NextResponse.json(result[0], { status: 201 });
    }
  } catch (error) {
    console.error('Error saving setting:', error);
    return NextResponse.json({ error: 'Failed to save setting' }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const settingsToSave = body.settings;
    
    if (!settingsToSave || !Array.isArray(settingsToSave)) {
      return NextResponse.json({ error: 'Settings array is required' }, { status: 400 });
    }
    
    const results = [];
    for (const setting of settingsToSave) {
      const { key, value, category } = setting;
      if (!key) continue;
      
      const existing = await db.select().from(settings).where(eq(settings.key, key));
      
      if (existing.length > 0) {
        const result = await db.update(settings)
          .set({ value, category: category || existing[0].category, updatedAt: new Date() })
          .where(eq(settings.key, key))
          .returning();
        results.push(result[0]);
      } else {
        const result = await db.insert(settings).values({
          key,
          value: value || {},
          category: category || 'general',
        }).returning();
        results.push(result[0]);
      }
    }
    
    return NextResponse.json(results);
  } catch (error) {
    console.error('Error saving settings:', error);
    return NextResponse.json({ error: 'Failed to save settings' }, { status: 500 });
  }
}
