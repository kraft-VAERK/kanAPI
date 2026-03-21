import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { API } from "./dashboard/constants";
import { CaseDetailPage } from "./dashboard/CaseDetailPage";
import { CompanyAdminDashboard } from "./dashboard/CompanyAdminDashboard";
import { ProfileView } from "./dashboard/ProfileView";
import { SuperAdminDashboard } from "./dashboard/SuperAdminDashboard";
import { UserDashboard } from "./dashboard/UserDashboard";
import { UserProfileView } from "./dashboard/UserProfileView";

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [toast, setToast] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { caseId, userId } = useParams();

  useEffect(() => {
    fetch(`${API}/auth/me`, { credentials: "include" })
      .then(async (r) => {
        if (!r.ok) {
          navigate("/", { replace: true });
          return;
        }
        setUser(await r.json());
      })
      .catch(() => navigate("/", { replace: true }));
  }, [navigate]);

  // Pick up toast from router state and clear it
  useEffect(() => {
    if (location.state?.toast) {
      setToast(location.state.toast);
      // Clear state so refreshing doesn't re-show
      window.history.replaceState({}, "");
      const t = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(t);
    }
  }, [location.state?.toast]);

  async function handleLogout() {
    await fetch(`${API}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    navigate("/", { replace: true });
  }

  if (!user) return null;

  const isSuperAdmin = user.is_admin && !user.parent_id;
  const isCompanyAdmin = user.is_admin && !!user.parent_id;
  const isProfilePage = location.pathname === "/dashboard/profile";

  const header = (
    <header className="dashboard-header">
      <span>{user.username}</span>
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
        {toast && <span className="toast-success">{toast}</span>}
        <button onClick={() => navigate("/dashboard/profile")}>Profile</button>
        <button onClick={handleLogout}>Logout</button>
      </div>
    </header>
  );

  const isEditMode = caseId && location.pathname.endsWith("/edit");

  if (caseId)
    return (
      <>
        {header}
        <CaseDetailPage caseId={caseId} editMode={isEditMode} user={user} />
      </>
    );

  if (userId)
    return (
      <>
        {header}
        <UserProfileView
          userId={userId}
          viewerIsSuperAdmin={user.is_admin && !user.parent_id}
        />
      </>
    );

  if (isProfilePage)
    return (
      <>
        {header}
        <main className="dashboard-main">
          <div className="tabs">
            <button className="tab" onClick={() => navigate("/dashboard")}>
              ← Back
            </button>
            <button className="tab active">Profile</button>
          </div>
          <ProfileView user={user} />
        </main>
      </>
    );

  return (
    <>
      {header}
      {isSuperAdmin ? (
        <SuperAdminDashboard user={user} />
      ) : isCompanyAdmin ? (
        <CompanyAdminDashboard user={user} />
      ) : (
        <UserDashboard user={user} />
      )}
    </>
  );
}
