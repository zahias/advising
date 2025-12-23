module.exports = [
"[externals]/next/dist/compiled/next-server/app-route-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-route-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/@opentelemetry/api [external] (next/dist/compiled/@opentelemetry/api, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/@opentelemetry/api", () => require("next/dist/compiled/@opentelemetry/api"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/after-task-async-storage.external.js [external] (next/dist/server/app-render/after-task-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/after-task-async-storage.external.js", () => require("next/dist/server/app-render/after-task-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/os [external] (os, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("os", () => require("os"));

module.exports = mod;
}),
"[externals]/fs [external] (fs, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("fs", () => require("fs"));

module.exports = mod;
}),
"[externals]/net [external] (net, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("net", () => require("net"));

module.exports = mod;
}),
"[externals]/tls [external] (tls, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("tls", () => require("tls"));

module.exports = mod;
}),
"[externals]/crypto [external] (crypto, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("crypto", () => require("crypto"));

module.exports = mod;
}),
"[externals]/stream [external] (stream, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("stream", () => require("stream"));

module.exports = mod;
}),
"[externals]/perf_hooks [external] (perf_hooks, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("perf_hooks", () => require("perf_hooks"));

module.exports = mod;
}),
"[project]/src/lib/db/schema.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "advisingPeriods",
    ()=>advisingPeriods,
    "advisingSessions",
    ()=>advisingSessions,
    "advisingSessionsRelations",
    ()=>advisingSessionsRelations,
    "advisorMajors",
    ()=>advisorMajors,
    "courses",
    ()=>courses,
    "coursesRelations",
    ()=>coursesRelations,
    "majors",
    ()=>majors,
    "majorsRelations",
    ()=>majorsRelations,
    "students",
    ()=>students,
    "studentsRelations",
    ()=>studentsRelations,
    "users",
    ()=>users,
    "usersRelations",
    ()=>usersRelations
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$table$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/pg-core/table.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$text$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/pg-core/columns/text.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$integer$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/pg-core/columns/integer.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/pg-core/columns/timestamp.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$boolean$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/pg-core/columns/boolean.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$json$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/pg-core/columns/json.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/pg-core/columns/uuid.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/pg-core/columns/varchar.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$relations$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/relations.js [app-route] (ecmascript)");
;
;
const users = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$table$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["pgTable"])('users', {
    id: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('id').primaryKey().defaultRandom(),
    email: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('email', {
        length: 255
    }).notNull().unique(),
    name: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('name', {
        length: 255
    }).notNull(),
    role: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('role', {
        length: 50
    }).notNull().default('student'),
    createdAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('created_at').defaultNow().notNull(),
    updatedAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('updated_at').defaultNow().notNull()
});
const majors = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$table$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["pgTable"])('majors', {
    id: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('id').primaryKey().defaultRandom(),
    code: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('code', {
        length: 50
    }).notNull().unique(),
    name: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('name', {
        length: 255
    }).notNull(),
    description: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$text$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["text"])('description'),
    isActive: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$boolean$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["boolean"])('is_active').default(true).notNull(),
    createdAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('created_at').defaultNow().notNull(),
    updatedAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('updated_at').defaultNow().notNull()
});
const advisorMajors = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$table$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["pgTable"])('advisor_majors', {
    id: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('id').primaryKey().defaultRandom(),
    userId: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('user_id').notNull().references(()=>users.id, {
        onDelete: 'cascade'
    }),
    majorId: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('major_id').notNull().references(()=>majors.id, {
        onDelete: 'cascade'
    })
});
const courses = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$table$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["pgTable"])('courses', {
    id: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('id').primaryKey().defaultRandom(),
    majorId: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('major_id').notNull().references(()=>majors.id, {
        onDelete: 'cascade'
    }),
    code: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('code', {
        length: 50
    }).notNull(),
    name: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('name', {
        length: 255
    }).notNull(),
    credits: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$integer$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["integer"])('credits').notNull().default(3),
    type: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('type', {
        length: 50
    }).notNull().default('required'),
    semester: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$integer$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["integer"])('semester'),
    offered: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$boolean$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["boolean"])('offered').default(true).notNull(),
    prerequisites: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$json$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["json"])('prerequisites').$type().default([]),
    corequisites: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$json$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["json"])('corequisites').$type().default([]),
    concurrent: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$json$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["json"])('concurrent').$type().default([]),
    standingRequired: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('standing_required', {
        length: 50
    }),
    description: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$text$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["text"])('description'),
    createdAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('created_at').defaultNow().notNull(),
    updatedAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('updated_at').defaultNow().notNull()
});
const students = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$table$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["pgTable"])('students', {
    id: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('id').primaryKey().defaultRandom(),
    studentId: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('student_id', {
        length: 50
    }).notNull(),
    majorId: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('major_id').notNull().references(()=>majors.id, {
        onDelete: 'cascade'
    }),
    userId: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('user_id').references(()=>users.id),
    name: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('name', {
        length: 255
    }).notNull(),
    email: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('email', {
        length: 255
    }),
    standing: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('standing', {
        length: 50
    }),
    creditsCompleted: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$integer$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["integer"])('credits_completed').default(0),
    creditsRegistered: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$integer$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["integer"])('credits_registered').default(0),
    creditsRemaining: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$integer$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["integer"])('credits_remaining').default(0),
    courseStatuses: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$json$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["json"])('course_statuses').$type().default({}),
    createdAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('created_at').defaultNow().notNull(),
    updatedAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('updated_at').defaultNow().notNull()
});
const advisingPeriods = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$table$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["pgTable"])('advising_periods', {
    id: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('id').primaryKey().defaultRandom(),
    majorId: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('major_id').notNull().references(()=>majors.id, {
        onDelete: 'cascade'
    }),
    semester: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('semester', {
        length: 20
    }).notNull(),
    year: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$integer$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["integer"])('year').notNull(),
    advisorName: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$varchar$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["varchar"])('advisor_name', {
        length: 255
    }),
    isActive: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$boolean$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["boolean"])('is_active').default(true).notNull(),
    createdAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('created_at').defaultNow().notNull()
});
const advisingSessions = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$table$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["pgTable"])('advising_sessions', {
    id: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('id').primaryKey().defaultRandom(),
    periodId: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('period_id').notNull().references(()=>advisingPeriods.id, {
        onDelete: 'cascade'
    }),
    studentId: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('student_id').notNull().references(()=>students.id, {
        onDelete: 'cascade'
    }),
    advisorId: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$uuid$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["uuid"])('advisor_id').references(()=>users.id),
    advisedCourses: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$json$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["json"])('advised_courses').$type().default([]),
    optionalCourses: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$json$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["json"])('optional_courses').$type().default([]),
    repeatCourses: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$json$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["json"])('repeat_courses').$type().default([]),
    bypasses: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$json$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["json"])('bypasses').$type().default({}),
    note: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$text$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["text"])('note'),
    createdAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('created_at').defaultNow().notNull(),
    updatedAt: (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$pg$2d$core$2f$columns$2f$timestamp$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["timestamp"])('updated_at').defaultNow().notNull()
});
const usersRelations = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$relations$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["relations"])(users, ({ many })=>({
        advisorMajors: many(advisorMajors),
        advisingSessions: many(advisingSessions)
    }));
const majorsRelations = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$relations$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["relations"])(majors, ({ many })=>({
        courses: many(courses),
        students: many(students),
        advisorMajors: many(advisorMajors),
        advisingPeriods: many(advisingPeriods)
    }));
const coursesRelations = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$relations$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["relations"])(courses, ({ one })=>({
        major: one(majors, {
            fields: [
                courses.majorId
            ],
            references: [
                majors.id
            ]
        })
    }));
const studentsRelations = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$relations$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["relations"])(students, ({ one, many })=>({
        major: one(majors, {
            fields: [
                students.majorId
            ],
            references: [
                majors.id
            ]
        }),
        user: one(users, {
            fields: [
                students.userId
            ],
            references: [
                users.id
            ]
        }),
        advisingSessions: many(advisingSessions)
    }));
const advisingSessionsRelations = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$relations$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["relations"])(advisingSessions, ({ one })=>({
        period: one(advisingPeriods, {
            fields: [
                advisingSessions.periodId
            ],
            references: [
                advisingPeriods.id
            ]
        }),
        student: one(students, {
            fields: [
                advisingSessions.studentId
            ],
            references: [
                students.id
            ]
        }),
        advisor: one(users, {
            fields: [
                advisingSessions.advisorId
            ],
            references: [
                users.id
            ]
        })
    }));
}),
"[project]/src/lib/db/index.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "db",
    ()=>db
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$postgres$2d$js$2f$driver$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/postgres-js/driver.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$postgres$2f$src$2f$index$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/postgres/src/index.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/db/schema.ts [app-route] (ecmascript)");
;
;
;
const connectionString = process.env.DATABASE_URL;
const client = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$postgres$2f$src$2f$index$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["default"])(connectionString);
const db = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$postgres$2d$js$2f$driver$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["drizzle"])(client, {
    schema: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__
});
}),
"[project]/src/lib/eligibility/types.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([]);
;
}),
"[project]/src/lib/eligibility/index.ts [app-route] (ecmascript) <locals>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "calculateCurriculumYears",
    ()=>calculateCurriculumYears,
    "checkCourseCompleted",
    ()=>checkCourseCompleted,
    "checkCourseFailed",
    ()=>checkCourseFailed,
    "checkCourseNotCompleted",
    ()=>checkCourseNotCompleted,
    "checkCourseRegistered",
    ()=>checkCourseRegistered,
    "checkEligibility",
    ()=>checkEligibility,
    "getAllCoursesWithEligibility",
    ()=>getAllCoursesWithEligibility,
    "getCorequisiteAndConcurrentCourses",
    ()=>getCorequisiteAndConcurrentCourses,
    "getCoursesNeedingRepeat",
    ()=>getCoursesNeedingRepeat,
    "getEligibleCourses",
    ()=>getEligibleCourses,
    "getMutualConcurrentPairs",
    ()=>getMutualConcurrentPairs,
    "getStudentStanding",
    ()=>getStudentStanding,
    "isCourseOffered",
    ()=>isCourseOffered,
    "parseRequirements",
    ()=>parseRequirements
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$eligibility$2f$types$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/eligibility/types.ts [app-route] (ecmascript)");
;
function getStudentStanding(totalCredits) {
    if (totalCredits >= 60) return 'Senior';
    if (totalCredits >= 30) return 'Junior';
    if (totalCredits >= 15) return 'Sophomore';
    return 'Freshman';
}
function checkCourseCompleted(student, courseCode) {
    const status = student.courseStatuses[courseCode];
    return status?.toLowerCase() === 'c';
}
function checkCourseRegistered(student, courseCode) {
    const status = student.courseStatuses[courseCode];
    if (!status || status === '' || status.toLowerCase() === 'nan') {
        return courseCode in student.courseStatuses;
    }
    const s = status.toLowerCase();
    return s === 'r' || s === 'cr';
}
function checkCourseFailed(student, courseCode) {
    const status = student.courseStatuses[courseCode];
    return status?.toLowerCase() === 'f';
}
function checkCourseNotCompleted(student, courseCode) {
    const status = student.courseStatuses[courseCode];
    return status?.toLowerCase() === 'nc';
}
function parseRequirements(requirementStr) {
    if (!requirementStr || requirementStr === '') return [];
    const parts = requirementStr.split(/[,;]|\band\b/i).map((p)=>p.trim()).filter((p)=>p.length > 0);
    return parts;
}
function isCourseOffered(course) {
    return course.offered === true;
}
function getMutualConcurrentPairs(courses) {
    const pairs = [];
    const seen = new Set();
    for (const courseA of courses){
        for (const concurrentCode of courseA.concurrent){
            const courseB = courses.find((c)=>c.code === concurrentCode);
            if (!courseB) continue;
            if (courseB.concurrent.includes(courseA.code)) {
                const pairKey = [
                    courseA.code,
                    courseB.code
                ].sort().join('|');
                if (!seen.has(pairKey)) {
                    seen.add(pairKey);
                    pairs.push({
                        courseA: courseA.code,
                        courseB: courseB.code
                    });
                }
            }
        }
    }
    return pairs;
}
function getCorequisiteAndConcurrentCourses(courses) {
    const result = new Set();
    for (const course of courses){
        if (course.corequisites.length > 0 || course.concurrent.length > 0) {
            result.add(course.code);
        }
    }
    return Array.from(result);
}
function checkStandingRequirement(student, standingRequired) {
    if (!standingRequired) {
        return {
            met: true,
            reason: ''
        };
    }
    const totalCredits = student.creditsCompleted + student.creditsRegistered;
    const studentStanding = getStudentStanding(totalCredits);
    const standingOrder = [
        'Freshman',
        'Sophomore',
        'Junior',
        'Senior'
    ];
    const reqLower = standingRequired.toLowerCase();
    let requiredIndex = -1;
    if (reqLower.includes('senior')) {
        requiredIndex = standingOrder.indexOf('Senior');
    } else if (reqLower.includes('junior')) {
        requiredIndex = standingOrder.indexOf('Junior');
    } else if (reqLower.includes('sophomore')) {
        requiredIndex = standingOrder.indexOf('Sophomore');
    }
    if (requiredIndex === -1) {
        return {
            met: true,
            reason: ''
        };
    }
    const studentIndex = standingOrder.indexOf(studentStanding);
    if (studentIndex >= requiredIndex) {
        return {
            met: true,
            reason: ''
        };
    }
    return {
        met: false,
        reason: `Requires ${standingOrder[requiredIndex]} standing (currently ${studentStanding})`
    };
}
function checkEligibility(student, courseCode, advisedCourses, courses, options = {}) {
    const { ignoreOffered = false, bypasses = {}, simulateCourses = [] } = options;
    const course = courses.find((c)=>c.code === courseCode);
    if (!course) {
        return {
            status: 'Not Eligible',
            reason: 'Course not found in catalog',
            missingPrerequisites: [],
            missingConcurrent: [],
            missingCorequisites: [],
            standingIssue: false,
            hasBypass: false
        };
    }
    if (checkCourseCompleted(student, courseCode)) {
        return {
            status: 'Completed',
            reason: 'Course already completed',
            missingPrerequisites: [],
            missingConcurrent: [],
            missingCorequisites: [],
            standingIssue: false,
            hasBypass: false
        };
    }
    if (checkCourseRegistered(student, courseCode)) {
        return {
            status: 'Registered',
            reason: 'Currently registered for this course',
            missingPrerequisites: [],
            missingConcurrent: [],
            missingCorequisites: [],
            standingIssue: false,
            hasBypass: false
        };
    }
    if (advisedCourses.includes(courseCode)) {
        return {
            status: 'Advised',
            reason: 'Course has been advised',
            missingPrerequisites: [],
            missingConcurrent: [],
            missingCorequisites: [],
            standingIssue: false,
            hasBypass: false
        };
    }
    if (bypasses[courseCode]) {
        return {
            status: 'Eligible',
            reason: `Bypass granted: ${bypasses[courseCode].note}`,
            missingPrerequisites: [],
            missingConcurrent: [],
            missingCorequisites: [],
            standingIssue: false,
            hasBypass: true,
            bypassInfo: bypasses[courseCode]
        };
    }
    if (!ignoreOffered && !isCourseOffered(course)) {
        return {
            status: 'Not Eligible',
            reason: 'Course is not offered this semester',
            missingPrerequisites: [],
            missingConcurrent: [],
            missingCorequisites: [],
            standingIssue: false,
            hasBypass: false
        };
    }
    const issues = [];
    const missingPrerequisites = [];
    const missingConcurrent = [];
    const missingCorequisites = [];
    let standingIssue = false;
    const standingCheck = checkStandingRequirement(student, course.standingRequired);
    if (!standingCheck.met) {
        issues.push(standingCheck.reason);
        standingIssue = true;
    }
    const mutualPairs = getMutualConcurrentPairs(courses);
    const isMutualPairMember = mutualPairs.some((pair)=>pair.courseA === courseCode || pair.courseB === courseCode);
    const effectiveAdvised = [
        ...advisedCourses,
        ...simulateCourses
    ];
    for (const prereqCode of course.prerequisites){
        if (prereqCode.toLowerCase().includes('standing')) {
            continue;
        }
        const prereqCompleted = checkCourseCompleted(student, prereqCode);
        const prereqRegistered = checkCourseRegistered(student, prereqCode);
        const prereqAdvised = effectiveAdvised.includes(prereqCode);
        const prereqBypassed = bypasses[prereqCode] !== undefined;
        if (prereqCompleted) {
            continue;
        }
        if (prereqRegistered) {
            continue;
        }
        if (prereqBypassed) {
            continue;
        }
        if (!prereqAdvised) {
            missingPrerequisites.push(prereqCode);
        }
    }
    for (const concurrentCode of course.concurrent){
        if (isMutualPairMember) {
            const isPairPartner = mutualPairs.some((pair)=>pair.courseA === courseCode && pair.courseB === concurrentCode || pair.courseB === courseCode && pair.courseA === concurrentCode);
            if (isPairPartner) {
                continue;
            }
        }
        const concurrentCompleted = checkCourseCompleted(student, concurrentCode);
        const concurrentRegistered = checkCourseRegistered(student, concurrentCode);
        const concurrentAdvised = effectiveAdvised.includes(concurrentCode);
        const concurrentBypassed = bypasses[concurrentCode] !== undefined;
        if (concurrentCompleted || concurrentRegistered || concurrentAdvised || concurrentBypassed) {
            continue;
        }
        missingConcurrent.push(concurrentCode);
    }
    for (const coreqCode of course.corequisites){
        const coreqCompleted = checkCourseCompleted(student, coreqCode);
        const coreqRegistered = checkCourseRegistered(student, coreqCode);
        const coreqAdvised = effectiveAdvised.includes(coreqCode);
        const coreqBypassed = bypasses[coreqCode] !== undefined;
        if (coreqCompleted || coreqRegistered || coreqAdvised || coreqBypassed) {
            continue;
        }
        missingCorequisites.push(coreqCode);
    }
    if (missingPrerequisites.length > 0) {
        issues.push(`Missing prerequisites: ${missingPrerequisites.join(', ')}`);
    }
    if (missingConcurrent.length > 0) {
        issues.push(`Missing concurrent courses: ${missingConcurrent.join(', ')}`);
    }
    if (missingCorequisites.length > 0) {
        issues.push(`Missing corequisites: ${missingCorequisites.join(', ')}`);
    }
    if (issues.length === 0) {
        return {
            status: 'Eligible',
            reason: 'All requirements met',
            missingPrerequisites: [],
            missingConcurrent: [],
            missingCorequisites: [],
            standingIssue: false,
            hasBypass: false
        };
    }
    return {
        status: 'Not Eligible',
        reason: issues.join('; '),
        missingPrerequisites,
        missingConcurrent,
        missingCorequisites,
        standingIssue,
        hasBypass: false
    };
}
function getEligibleCourses(student, courses, advisedCourses = [], options = {}) {
    const { bypasses = {}, excludeCodes = [] } = options;
    const results = [];
    for (const course of courses){
        if (excludeCodes.includes(course.code)) {
            continue;
        }
        const eligibility = checkEligibility(student, course.code, advisedCourses, courses, {
            bypasses
        });
        if (eligibility.status === 'Eligible') {
            results.push({
                course,
                eligibility
            });
        }
    }
    return results;
}
function getAllCoursesWithEligibility(student, courses, advisedCourses = [], options = {}) {
    const { bypasses = {}, excludeCodes = [] } = options;
    return courses.filter((course)=>!excludeCodes.includes(course.code)).map((course)=>({
            course,
            eligibility: checkEligibility(student, course.code, advisedCourses, courses, {
                bypasses
            })
        }));
}
function calculateCurriculumYears(courses) {
    const courseYears = {};
    const prereqMap = {};
    const standingReqs = {};
    for (const course of courses){
        const coursePrereqs = [];
        let standingReq;
        for (const prereq of course.prerequisites){
            if (prereq.toLowerCase().includes('standing')) {
                standingReq = prereq;
            } else {
                coursePrereqs.push(prereq);
            }
        }
        prereqMap[course.code] = coursePrereqs;
        standingReqs[course.code] = standingReq;
    }
    function getCourseYear(courseCode, visited = new Set()) {
        if (courseYears[courseCode] !== undefined) {
            return courseYears[courseCode];
        }
        if (visited.has(courseCode)) {
            return 1;
        }
        visited.add(courseCode);
        const prereqs = prereqMap[courseCode] || [];
        const standingReq = standingReqs[courseCode];
        let maxPrereqYear = 0;
        for (const prereqCode of prereqs){
            if (prereqMap[prereqCode] !== undefined) {
                const prereqYear = getCourseYear(prereqCode, new Set(visited));
                maxPrereqYear = Math.max(maxPrereqYear, prereqYear);
            }
        }
        let standingYear = 1;
        if (standingReq) {
            if (standingReq.toLowerCase().includes('senior')) {
                standingYear = 3;
            } else if (standingReq.toLowerCase().includes('junior')) {
                standingYear = 2;
            }
        }
        const courseYear = Math.max(maxPrereqYear + 1, standingYear);
        courseYears[courseCode] = courseYear;
        return courseYear;
    }
    for (const courseCode of Object.keys(prereqMap)){
        getCourseYear(courseCode);
    }
    return courseYears;
}
function getCoursesNeedingRepeat(student, courses) {
    return courses.filter((course)=>checkCourseFailed(student, course.code));
}
}),
"[project]/src/app/api/eligibility/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "GET",
    ()=>GET,
    "POST",
    ()=>POST
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/server.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/db/index.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/db/schema.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$sql$2f$expressions$2f$conditions$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/sql/expressions/conditions.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$sql$2f$expressions$2f$select$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/drizzle-orm/sql/expressions/select.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$eligibility$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/src/lib/eligibility/index.ts [app-route] (ecmascript) <locals>");
;
;
;
;
;
function dbCourseToEligibilityCourse(dbCourse) {
    return {
        id: dbCourse.id,
        code: dbCourse.code,
        name: dbCourse.name,
        credits: dbCourse.credits,
        type: dbCourse.type,
        semester: dbCourse.semester ?? undefined,
        offered: dbCourse.offered,
        prerequisites: dbCourse.prerequisites || [],
        corequisites: dbCourse.corequisites || [],
        concurrent: dbCourse.concurrent || [],
        standingRequired: dbCourse.standingRequired ?? undefined,
        description: dbCourse.description ?? undefined
    };
}
function dbStudentToEligibilityStudent(dbStudent) {
    const totalCredits = (dbStudent.creditsCompleted || 0) + (dbStudent.creditsRegistered || 0);
    return {
        id: dbStudent.id,
        studentId: dbStudent.studentId,
        name: dbStudent.name,
        email: dbStudent.email ?? undefined,
        standing: dbStudent.standing || (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$eligibility$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getStudentStanding"])(totalCredits),
        creditsCompleted: dbStudent.creditsCompleted || 0,
        creditsRegistered: dbStudent.creditsRegistered || 0,
        creditsRemaining: dbStudent.creditsRemaining || 0,
        courseStatuses: dbStudent.courseStatuses || {}
    };
}
async function GET(request) {
    try {
        const { searchParams } = new URL(request.url);
        const studentId = searchParams.get('studentId');
        const majorId = searchParams.get('majorId');
        const periodId = searchParams.get('periodId');
        if (!studentId || !majorId) {
            return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
                error: 'studentId and majorId are required'
            }, {
                status: 400
            });
        }
        const studentResult = await __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["db"].select().from(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["students"]).where((0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$sql$2f$expressions$2f$conditions$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["eq"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["students"].id, studentId));
        if (studentResult.length === 0) {
            return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
                error: 'Student not found'
            }, {
                status: 404
            });
        }
        const coursesResult = await __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["db"].select().from(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["courses"]).where((0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$sql$2f$expressions$2f$conditions$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["eq"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["courses"].majorId, majorId));
        let session = null;
        if (periodId) {
            const sessionResult = await __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["db"].select().from(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["advisingSessions"]).where((0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$sql$2f$expressions$2f$conditions$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["and"])((0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$sql$2f$expressions$2f$conditions$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["eq"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["advisingSessions"].studentId, studentId), (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$sql$2f$expressions$2f$conditions$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["eq"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["advisingSessions"].periodId, periodId))).orderBy((0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$sql$2f$expressions$2f$select$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["desc"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["advisingSessions"].updatedAt)).limit(1);
            if (sessionResult.length > 0) {
                session = sessionResult[0];
            }
        }
        const student = dbStudentToEligibilityStudent(studentResult[0]);
        const courseList = coursesResult.map(dbCourseToEligibilityCourse);
        const advisedCourses = session?.advisedCourses || [];
        const optionalCourses = session?.optionalCourses || [];
        const repeatCourses = session?.repeatCourses || [];
        const bypasses = session?.bypasses || {};
        const allAdvised = [
            ...advisedCourses,
            ...optionalCourses,
            ...repeatCourses
        ];
        const eligibilityResults = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$eligibility$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAllCoursesWithEligibility"])(student, courseList, allAdvised, {
            bypasses
        });
        return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            student,
            courses: eligibilityResults,
            session: session ? {
                id: session.id,
                advisedCourses,
                optionalCourses,
                repeatCourses,
                bypasses,
                note: session.note
            } : null
        });
    } catch (error) {
        console.error('Error checking eligibility:', error);
        return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: 'Failed to check eligibility'
        }, {
            status: 500
        });
    }
}
async function POST(request) {
    try {
        const body = await request.json();
        const { studentId, courseCode, majorId, advisedCourses = [], bypasses = {} } = body;
        if (!studentId || !courseCode || !majorId) {
            return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
                error: 'studentId, courseCode, and majorId are required'
            }, {
                status: 400
            });
        }
        const studentResult = await __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["db"].select().from(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["students"]).where((0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$sql$2f$expressions$2f$conditions$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["eq"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["students"].id, studentId));
        if (studentResult.length === 0) {
            return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
                error: 'Student not found'
            }, {
                status: 404
            });
        }
        const coursesResult = await __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["db"].select().from(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["courses"]).where((0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$drizzle$2d$orm$2f$sql$2f$expressions$2f$conditions$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["eq"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2f$schema$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["courses"].majorId, majorId));
        const student = dbStudentToEligibilityStudent(studentResult[0]);
        const courseList = coursesResult.map(dbCourseToEligibilityCourse);
        const result = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$eligibility$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["checkEligibility"])(student, courseCode, advisedCourses, courseList, {
            bypasses
        });
        return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json(result);
    } catch (error) {
        console.error('Error checking single course eligibility:', error);
        return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: 'Failed to check eligibility'
        }, {
            status: 500
        });
    }
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__aafbdef6._.js.map