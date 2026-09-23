"use client";

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { AuthTokenResponse, ParticipantRole } from "@multilingual/contracts";

export interface AdminUser {
  userId: string;
  tenantId: string;
  email: string;
  displayName: string;
  role: ParticipantRole;
}

export interface OrganizationInfo {
  id: string;
  name: string;
  slug: string;
}

interface AdminAuthContextType {
  user: AdminUser;
  organization: OrganizationInfo;
  token: string;
  isAdmin: boolean;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  setUserRole: (role: ParticipantRole) => void;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const DEFAULT_USER: AdminUser = {
  userId: "usr_admin_001",
  tenantId: "org_acme_enterprise",
  email: "admin@acme-enterprise.org",
  displayName: "Devon Vance (Admin)",
  role: ParticipantRole.HOST,
};

const DEFAULT_ORG: OrganizationInfo = {
  id: "org_acme_enterprise",
  name: "Acme Global Enterprise",
  slug: "acme-enterprise",
};

const AdminAuthContext = createContext<AdminAuthContextType>({
  user: DEFAULT_USER,
  organization: DEFAULT_ORG,
  token: "",
  isAdmin: true,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  setUserRole: () => {},
  login: async () => false,
  logout: () => {},
});

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AdminUser>(DEFAULT_USER);
  const [organization, setOrganization] = useState<OrganizationInfo>(DEFAULT_ORG);
  const [token, setToken] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Restore stored token and session on client hydration
  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedToken = localStorage.getItem("admin_token");
      const storedUser = localStorage.getItem("admin_user");
      const storedOrg = localStorage.getItem("admin_org");

      if (storedToken) {
        setToken(storedToken);
      }
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch {
          // ignore corrupted storage
        }
      }
      if (storedOrg) {
        try {
          setOrganization(JSON.parse(storedOrg));
        } catch {
          // ignore corrupted storage
        }
      }

      // If no token exists, provision a valid dev bearer token from backend auth endpoint
      if (!storedToken) {
        fetch(`${API_BASE_URL}/api/v1/auth/token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: DEFAULT_USER.userId,
            tenant_id: DEFAULT_USER.tenantId,
            email: DEFAULT_USER.email,
            role: ParticipantRole.HOST,
          }),
        })
          .then(async (res) => {
            if (res.ok) {
              const data: AuthTokenResponse = await res.json();
              setToken(data.access_token);
              localStorage.setItem("admin_token", data.access_token);
            }
          })
          .catch((err) => {
            console.warn("Failed to auto-provision initial admin token:", err);
          });
      }
    }
  }, []);

  const isAdmin = user.role === ParticipantRole.HOST;
  const isAuthenticated = Boolean(token && token.length > 0);

  const setUserRole = (newRole: ParticipantRole) => {
    setUser((prev) => {
      const updated = { ...prev, role: newRole };
      if (typeof window !== "undefined") {
        localStorage.setItem("admin_user", JSON.stringify(updated));
      }
      return updated;
    });
  };

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        let msg = `Authentication failed (${res.status})`;
        try {
          const body = await res.json();
          if (body?.detail) msg = body.detail;
        } catch {
          // non-JSON
        }
        setError(msg);
        return false;
      }

      const data: AuthTokenResponse = await res.json();
      setToken(data.access_token);

      const updatedUser: AdminUser = {
        userId: data.user_id,
        tenantId: data.tenant_id,
        email,
        displayName: email.split("@")[0],
        role: ParticipantRole.HOST,
      };
      setUser(updatedUser);

      if (typeof window !== "undefined") {
        localStorage.setItem("admin_token", data.access_token);
        localStorage.setItem("admin_user", JSON.stringify(updatedUser));
      }
      return true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to authentication server";
      setError(msg);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setToken("");
    setUser(DEFAULT_USER);
    if (typeof window !== "undefined") {
      localStorage.removeItem("admin_token");
      localStorage.removeItem("admin_user");
      localStorage.removeItem("admin_org");
    }
  }, []);

  return (
    <AdminAuthContext.Provider
      value={{
        user,
        organization,
        token,
        isAdmin,
        isAuthenticated,
        isLoading,
        error,
        setUserRole,
        login,
        logout,
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}

