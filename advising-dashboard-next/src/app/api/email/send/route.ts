import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { emailLogs, settings, students } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import nodemailer from 'nodemailer';

interface EmailSettings {
  smtpHost?: string;
  smtpPort?: number;
  smtpUser?: string;
  smtpPassword?: string;
  fromEmail?: string;
  fromName?: string;
}

async function getEmailSettings(): Promise<EmailSettings | null> {
  try {
    const result = await db.select().from(settings).where(eq(settings.key, 'email'));
    if (result.length > 0 && result[0].value) {
      return result[0].value as EmailSettings;
    }
    return null;
  } catch {
    return null;
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { studentId, recipientEmail, subject, body: emailBody, templateUsed, advisorId } = body;
    
    if (!recipientEmail || !subject || !emailBody) {
      return NextResponse.json({ error: 'recipientEmail, subject, and body are required' }, { status: 400 });
    }
    
    const emailSettings = await getEmailSettings();
    
    let sendStatus = 'pending';
    let errorMessage = '';
    
    if (emailSettings?.smtpHost && emailSettings?.smtpUser && emailSettings?.smtpPassword) {
      try {
        const transporter = nodemailer.createTransport({
          host: emailSettings.smtpHost,
          port: emailSettings.smtpPort || 587,
          secure: (emailSettings.smtpPort || 587) === 465,
          auth: {
            user: emailSettings.smtpUser,
            pass: emailSettings.smtpPassword,
          },
        });
        
        await transporter.sendMail({
          from: emailSettings.fromEmail 
            ? `"${emailSettings.fromName || 'Advising Dashboard'}" <${emailSettings.fromEmail}>`
            : emailSettings.smtpUser,
          to: recipientEmail,
          subject: subject,
          html: emailBody,
        });
        
        sendStatus = 'sent';
      } catch (sendError) {
        console.error('Error sending email:', sendError);
        sendStatus = 'failed';
        errorMessage = sendError instanceof Error ? sendError.message : 'Unknown error';
      }
    } else {
      sendStatus = 'queued';
      errorMessage = 'Email settings not configured - email saved for later sending';
    }
    
    const logResult = await db.insert(emailLogs).values({
      studentId: studentId || null,
      advisorId: advisorId || null,
      recipientEmail,
      subject,
      body: emailBody,
      templateUsed: templateUsed || null,
      status: sendStatus,
    }).returning();
    
    return NextResponse.json({
      success: sendStatus === 'sent',
      status: sendStatus,
      message: sendStatus === 'sent' 
        ? 'Email sent successfully' 
        : sendStatus === 'queued'
          ? 'Email queued - configure SMTP settings to send'
          : `Failed to send: ${errorMessage}`,
      log: logResult[0],
    });
  } catch (error) {
    console.error('Error in email send:', error);
    return NextResponse.json({ error: 'Failed to process email' }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const studentId = searchParams.get('studentId');
    const limit = parseInt(searchParams.get('limit') || '50');
    
    let result;
    if (studentId) {
      result = await db.select().from(emailLogs)
        .where(eq(emailLogs.studentId, studentId))
        .orderBy(emailLogs.sentAt)
        .limit(limit);
    } else {
      result = await db.select().from(emailLogs)
        .orderBy(emailLogs.sentAt)
        .limit(limit);
    }
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching email logs:', error);
    return NextResponse.json({ error: 'Failed to fetch email logs' }, { status: 500 });
  }
}
