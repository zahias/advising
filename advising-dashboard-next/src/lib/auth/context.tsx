'use client';

import { createContext, useContext, useState, ReactNode, useEffect } from 'react';

export type UserRole = 'admin' | 'advisor' | 'student';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

export interface AuthContextType {
  user: User | null;
  currentRole: UserRole;
  currentMajor: string | null;
  currentStudentId: string | null;
  setCurrentRole: (role: UserRole) => void;
  setCurrentMajor: (majorCode: string | null) => void;
  setCurrentStudentId: (studentId: string | null) => void;
  login: (role: UserRole, name: string) => void;
  logout: () => void;
  isAdmin: boolean;
  isAdvisor: boolean;
  isStudent: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [currentRole, setCurrentRole] = useState<UserRole>('admin');
  const [currentMajor, setCurrentMajor] = useState<string | null>(null);
  const [currentStudentId, setCurrentStudentId] = useState<string | null>(null);

  useEffect(() => {
    const savedUser = localStorage.getItem('advisingUser');
    const savedRole = localStorage.getItem('advisingRole') as UserRole | null;
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
  }, []);

  const login = (role: UserRole, name: string) => {
    const newUser: User = {
      id: crypto.randomUUID(),
      name,
      email: `${name.toLowerCase().replace(/\s+/g, '.')}@university.edu`,
      role,
    };
    setUser(newUser);
    setCurrentRole(role);
    localStorage.setItem('advisingUser', JSON.stringify(newUser));
    localStorage.setItem('advisingRole', role);
  };

  const logout = () => {
    setUser(null);
    setCurrentRole('admin');
    setCurrentMajor(null);
    setCurrentStudentId(null);
    localStorage.removeItem('advisingUser');
    localStorage.removeItem('advisingRole');
    localStorage.removeItem('advisingMajor');
    localStorage.removeItem('advisingStudentId');
  };

  const handleSetCurrentRole = (role: UserRole) => {
    setCurrentRole(role);
    localStorage.setItem('advisingRole', role);
  };

  const handleSetCurrentMajor = (majorCode: string | null) => {
    setCurrentMajor(majorCode);
    if (majorCode) {
      localStorage.setItem('advisingMajor', majorCode);
    } else {
      localStorage.removeItem('advisingMajor');
    }
  };

  const handleSetCurrentStudentId = (studentId: string | null) => {
    setCurrentStudentId(studentId);
    if (studentId) {
      localStorage.setItem('advisingStudentId', studentId);
    } else {
      localStorage.removeItem('advisingStudentId');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        currentRole,
        currentMajor,
        currentStudentId,
        setCurrentRole: handleSetCurrentRole,
        setCurrentMajor: handleSetCurrentMajor,
        setCurrentStudentId: handleSetCurrentStudentId,
        login,
        logout,
        isAdmin: currentRole === 'admin',
        isAdvisor: currentRole === 'advisor',
        isStudent: currentRole === 'student',
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
