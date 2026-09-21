"use client";

import { createContext, useContext, useState, ReactNode } from "react";
import { ParticipantRole } from "@multilingual/contracts";

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
  setUserRole: (role: ParticipantRole) => void;
}

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
  token: "mock_admin_bearer_token",
  isAdmin: true,
  setUserRole: () => {},
});

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AdminUser>(DEFAULT_USER);
  const [organization] = useState<OrganizationInfo>(DEFAULT_ORG);
  const token = "mock_admin_bearer_token";

  const isAdmin = user.role === ParticipantRole.HOST;

  const setUserRole = (newRole: ParticipantRole) => {
    setUser((prev) => ({
      ...prev,
      role: newRole,
    }));
  };

  return (
    <AdminAuthContext.Provider
      value={{
        user,
        organization,
        token,
        isAdmin,
        setUserRole,
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}
