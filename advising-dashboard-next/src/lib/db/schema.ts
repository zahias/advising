import { pgTable, text, integer, timestamp, boolean, json, uuid, varchar } from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: varchar('email', { length: 255 }).notNull().unique(),
  name: varchar('name', { length: 255 }).notNull(),
  role: varchar('role', { length: 50 }).notNull().default('student'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const majors = pgTable('majors', {
  id: uuid('id').primaryKey().defaultRandom(),
  code: varchar('code', { length: 50 }).notNull().unique(),
  name: varchar('name', { length: 255 }).notNull(),
  description: text('description'),
  isActive: boolean('is_active').default(true).notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const advisorMajors = pgTable('advisor_majors', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  majorId: uuid('major_id').notNull().references(() => majors.id, { onDelete: 'cascade' }),
});

export const courses = pgTable('courses', {
  id: uuid('id').primaryKey().defaultRandom(),
  majorId: uuid('major_id').notNull().references(() => majors.id, { onDelete: 'cascade' }),
  code: varchar('code', { length: 50 }).notNull(),
  name: varchar('name', { length: 255 }).notNull(),
  credits: integer('credits').notNull().default(3),
  type: varchar('type', { length: 50 }).notNull().default('required'),
  semester: integer('semester'),
  offered: boolean('offered').default(true).notNull(),
  prerequisites: json('prerequisites').$type<string[]>().default([]),
  corequisites: json('corequisites').$type<string[]>().default([]),
  concurrent: json('concurrent').$type<string[]>().default([]),
  standingRequired: varchar('standing_required', { length: 50 }),
  description: text('description'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const students = pgTable('students', {
  id: uuid('id').primaryKey().defaultRandom(),
  studentId: varchar('student_id', { length: 50 }).notNull(),
  majorId: uuid('major_id').notNull().references(() => majors.id, { onDelete: 'cascade' }),
  userId: uuid('user_id').references(() => users.id),
  name: varchar('name', { length: 255 }).notNull(),
  email: varchar('email', { length: 255 }),
  standing: varchar('standing', { length: 50 }),
  creditsCompleted: integer('credits_completed').default(0),
  creditsRegistered: integer('credits_registered').default(0),
  creditsRemaining: integer('credits_remaining').default(0),
  courseStatuses: json('course_statuses').$type<Record<string, string>>().default({}),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const advisingPeriods = pgTable('advising_periods', {
  id: uuid('id').primaryKey().defaultRandom(),
  majorId: uuid('major_id').notNull().references(() => majors.id, { onDelete: 'cascade' }),
  semester: varchar('semester', { length: 20 }).notNull(),
  year: integer('year').notNull(),
  advisorName: varchar('advisor_name', { length: 255 }),
  isActive: boolean('is_active').default(true).notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

export const advisingSessions = pgTable('advising_sessions', {
  id: uuid('id').primaryKey().defaultRandom(),
  periodId: uuid('period_id').notNull().references(() => advisingPeriods.id, { onDelete: 'cascade' }),
  studentId: uuid('student_id').notNull().references(() => students.id, { onDelete: 'cascade' }),
  advisorId: uuid('advisor_id').references(() => users.id),
  advisedCourses: json('advised_courses').$type<string[]>().default([]),
  optionalCourses: json('optional_courses').$type<string[]>().default([]),
  repeatCourses: json('repeat_courses').$type<string[]>().default([]),
  bypasses: json('bypasses').$type<Record<string, { note: string; advisor: string }>>().default({}),
  note: text('note'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const usersRelations = relations(users, ({ many }) => ({
  advisorMajors: many(advisorMajors),
  advisingSessions: many(advisingSessions),
}));

export const majorsRelations = relations(majors, ({ many }) => ({
  courses: many(courses),
  students: many(students),
  advisorMajors: many(advisorMajors),
  advisingPeriods: many(advisingPeriods),
}));

export const coursesRelations = relations(courses, ({ one }) => ({
  major: one(majors, {
    fields: [courses.majorId],
    references: [majors.id],
  }),
}));

export const studentsRelations = relations(students, ({ one, many }) => ({
  major: one(majors, {
    fields: [students.majorId],
    references: [majors.id],
  }),
  user: one(users, {
    fields: [students.userId],
    references: [users.id],
  }),
  advisingSessions: many(advisingSessions),
}));

export const advisingSessionsRelations = relations(advisingSessions, ({ one }) => ({
  period: one(advisingPeriods, {
    fields: [advisingSessions.periodId],
    references: [advisingPeriods.id],
  }),
  student: one(students, {
    fields: [advisingSessions.studentId],
    references: [students.id],
  }),
  advisor: one(users, {
    fields: [advisingSessions.advisorId],
    references: [users.id],
  }),
}));
