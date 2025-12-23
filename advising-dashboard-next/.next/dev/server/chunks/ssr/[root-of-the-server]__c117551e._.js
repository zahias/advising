module.exports = [
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[project]/advising-dashboard-next/src/lib/auth/context.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "AuthProvider",
    ()=>AuthProvider,
    "useAuth",
    ()=>useAuth
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/advising-dashboard-next/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/advising-dashboard-next/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
'use client';
;
;
const AuthContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["createContext"])(undefined);
function AuthProvider({ children }) {
    const [user, setUser] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [currentRole, setCurrentRole] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])('admin');
    const [currentMajor, setCurrentMajor] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [currentStudentId, setCurrentStudentId] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [majors, setMajors] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])([]);
    const [majorsLoading, setMajorsLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(true);
    const [majorVersion, setMajorVersion] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(0);
    const fetchMajors = (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useCallback"])(async ()=>{
        try {
            setMajorsLoading(true);
            const res = await fetch('/api/majors');
            if (res.ok) {
                const data = await res.json();
                setMajors(data);
            }
        } catch (error) {
            console.error('Failed to fetch majors:', error);
        } finally{
            setMajorsLoading(false);
        }
    }, []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        const savedUser = localStorage.getItem('advisingUser');
        const savedRole = localStorage.getItem('advisingRole');
        const savedMajor = localStorage.getItem('advisingMajor');
        const savedStudentId = localStorage.getItem('advisingStudentId');
        if (savedUser) {
            setUser(JSON.parse(savedUser));
        }
        if (savedRole) {
            setCurrentRole(savedRole);
        }
        if (savedMajor) {
            setCurrentMajor(savedMajor);
        }
        if (savedStudentId) {
            setCurrentStudentId(savedStudentId);
        }
        fetchMajors();
    }, [
        fetchMajors
    ]);
    const currentMajorId = majors.find((m)=>m.code === currentMajor)?.id || null;
    const login = (role, name)=>{
        const newUser = {
            id: crypto.randomUUID(),
            name,
            email: `${name.toLowerCase().replace(/\s+/g, '.')}@university.edu`,
            role
        };
        setUser(newUser);
        setCurrentRole(role);
        localStorage.setItem('advisingUser', JSON.stringify(newUser));
        localStorage.setItem('advisingRole', role);
    };
    const logout = ()=>{
        setUser(null);
        setCurrentRole('admin');
        setCurrentMajor(null);
        setCurrentStudentId(null);
        localStorage.removeItem('advisingUser');
        localStorage.removeItem('advisingRole');
        localStorage.removeItem('advisingMajor');
        localStorage.removeItem('advisingStudentId');
    };
    const handleSetCurrentRole = (role)=>{
        setCurrentRole(role);
        localStorage.setItem('advisingRole', role);
    };
    const handleSetCurrentMajor = (majorCode)=>{
        setCurrentMajor(majorCode);
        setMajorVersion((v)=>v + 1);
        if (majorCode) {
            localStorage.setItem('advisingMajor', majorCode);
        } else {
            localStorage.removeItem('advisingMajor');
        }
    };
    const handleSetCurrentStudentId = (studentId)=>{
        setCurrentStudentId(studentId);
        if (studentId) {
            localStorage.setItem('advisingStudentId', studentId);
        } else {
            localStorage.removeItem('advisingStudentId');
        }
    };
    const refreshMajors = async ()=>{
        await fetchMajors();
        setMajorVersion((v)=>v + 1);
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(AuthContext.Provider, {
        value: {
            user,
            currentRole,
            currentMajor,
            currentMajorId,
            currentStudentId,
            majors,
            majorsLoading,
            majorVersion,
            setCurrentRole: handleSetCurrentRole,
            setCurrentMajor: handleSetCurrentMajor,
            setCurrentStudentId: handleSetCurrentStudentId,
            login,
            logout,
            refreshMajors,
            isAdmin: currentRole === 'admin',
            isAdvisor: currentRole === 'advisor',
            isStudent: currentRole === 'student'
        },
        children: children
    }, void 0, false, {
        fileName: "[project]/advising-dashboard-next/src/lib/auth/context.tsx",
        lineNumber: 148,
        columnNumber: 5
    }, this);
}
function useAuth() {
    const context = (0, __TURBOPACK__imported__module__$5b$project$5d2f$advising$2d$dashboard$2d$next$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useContext"])(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
}),
"[project]/advising-dashboard-next/node_modules/next/dist/server/route-modules/app-page/module.compiled.js [app-ssr] (ecmascript)", ((__turbopack_context__, module, exports) => {
"use strict";

if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
;
else {
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    else {
        if ("TURBOPACK compile-time truthy", 1) {
            if ("TURBOPACK compile-time truthy", 1) {
                module.exports = __turbopack_context__.r("[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)");
            } else //TURBOPACK unreachable
            ;
        } else //TURBOPACK unreachable
        ;
    }
} //# sourceMappingURL=module.compiled.js.map
}),
"[project]/advising-dashboard-next/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)", ((__turbopack_context__, module, exports) => {
"use strict";

module.exports = __turbopack_context__.r("[project]/advising-dashboard-next/node_modules/next/dist/server/route-modules/app-page/module.compiled.js [app-ssr] (ecmascript)").vendored['react-ssr'].ReactJsxDevRuntime; //# sourceMappingURL=react-jsx-dev-runtime.js.map
}),
"[project]/advising-dashboard-next/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)", ((__turbopack_context__, module, exports) => {
"use strict";

module.exports = __turbopack_context__.r("[project]/advising-dashboard-next/node_modules/next/dist/server/route-modules/app-page/module.compiled.js [app-ssr] (ecmascript)").vendored['react-ssr'].React; //# sourceMappingURL=react.js.map
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__c117551e._.js.map