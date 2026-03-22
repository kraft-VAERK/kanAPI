import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { API, PAGE_SIZE } from "./constants";
import { CasesTable } from "./CasesTable";
import { Pagination } from "./Pagination";

export function ProfileView({ user }) {
  const [username, setUsername] = useState(user.username);
  const [email, setEmail] = useState(user.email);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [cases, setCases] = useState([]);
  const [casesPage, setCasesPage] = useState(1);
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${API}/user/${user.username}/cases`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setCases);
  }, [user.username]);

  const dirty = username !== user.username || email !== user.email;
  const role = user.is_admin
    ? user.parent_id
      ? "Company admin"
      : "Super admin"
    : "User";
  const initials = (user.full_name || user.username).slice(0, 2).toUpperCase();

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const res = await fetch(`${API}/user/${user.username}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Failed to save.");
        return;
      }
      if (username !== user.username) {
        await fetch(`${API}/auth/logout`, { method: "POST", credentials: "include" });
        navigate("/", { replace: true });
        return;
      }
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch {
      setError("Network error.");
    } finally {
      setSaving(false);
    }
  }

  const totalPages = Math.max(1, Math.ceil(cases.length / PAGE_SIZE));
  const pageSlice = cases.slice((casesPage - 1) * PAGE_SIZE, casesPage * PAGE_SIZE);

  return (
    <>
      <div className="section-heading">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
      </div>

      <div className="customer-hero">
        <div className="customer-hero-avatar">{initials}</div>
        <h2 className="customer-hero-name">{user.full_name || user.username}</h2>
        <span className="customer-hero-tag">{role}</span>

        <div className="customer-stats">
          <div className="customer-stat">
            <span className="customer-stat-value">{cases.length}</span>
            <span className="customer-stat-label">Cases</span>
          </div>
          <div className="customer-stat">
            <span className="customer-stat-value">
              {user.is_active ? "Active" : "Inactive"}
            </span>
            <span className="customer-stat-label">Status</span>
          </div>
        </div>
      </div>

      <div className="customer-info-grid">
        <div className="customer-info-card">
          <span className="customer-info-icon">@</span>
          <div className="customer-info-content">
            <span className="customer-info-label">Username</span>
            <input
              className="profile-inline-input"
              value={username}
              onChange={(e) => { setUsername(e.target.value); setSuccess(false); }}
            />
          </div>
        </div>
        <div className="customer-info-card">
          <span className="customer-info-icon">✉</span>
          <div className="customer-info-content">
            <span className="customer-info-label">Email</span>
            <input
              className="profile-inline-input"
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setSuccess(false); }}
            />
          </div>
        </div>
        <InfoCard icon="☺" label="Full Name" value={user.full_name} />
        <InfoCard icon="⚑" label="Parent" value={user.parent_id || "—"} />
      </div>

      {(dirty || error || success) && (
        <div className="profile-save-row">
          {dirty && (
            <button
              className="profile-save-btn"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Saving…" : "Save changes"}
            </button>
          )}
          {error && <span className="form-error">{error}</span>}
          {success && <span className="profile-success">Changes saved.</span>}
        </div>
      )}

      <div className="tabs" style={{ marginTop: "1.5rem" }}>
        <button className="tab active">
          Cases{cases.length > 0 ? ` (${cases.length})` : ""}
        </button>
      </div>

      {cases.length === 0 ? (
        <p className="no-cases">No cases assigned to you.</p>
      ) : (
        <>
          <CasesTable
            cases={pageSlice}
            onCaseClick={(c) =>
              navigate(`/case/${c.id}`, { state: { case: c } })
            }
          />
          <Pagination
            page={casesPage}
            totalPages={totalPages}
            setPage={setCasesPage}
          />
        </>
      )}
    </>
  );
}

function InfoCard({ icon, label, value }) {
  return (
    <div className="customer-info-card">
      <span className="customer-info-icon">{icon}</span>
      <div className="customer-info-content">
        <span className="customer-info-label">{label}</span>
        <span className="customer-info-value">{value || "—"}</span>
      </div>
    </div>
  );
}
