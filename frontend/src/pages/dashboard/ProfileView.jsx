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
        // Session JWT still holds the old username — must re-login.
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

  return (
    <>
      <div className="profile-card">
        <div className="profile-header">
          <div className="profile-avatar">{initials}</div>
          <div className="profile-header-info">
            <span className="profile-header-name">
              {user.full_name || user.username}
            </span>
            <span className="profile-header-role">{role}</span>
          </div>
        </div>

        <div className="profile-fields">
          <div className="profile-field">
            <label>Username</label>
            <input
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setSuccess(false);
              }}
            />
          </div>
          <div className="profile-field">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setSuccess(false);
              }}
            />
          </div>
          <div className="profile-field">
            <label>Full name</label>
            <div className="profile-field-static">{user.full_name || "—"}</div>
          </div>
          <div className="profile-field">
            <label>Status</label>
            <div className="profile-badge">
              {user.is_active ? "Active" : "Inactive"}
            </div>
          </div>
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
      </div>

      <section className="detail-section">
        <h3 className="detail-section-title">
          Cases{" "}
          {cases.length > 0 && (
            <span className="detail-count">({cases.length})</span>
          )}
        </h3>
        {cases.length === 0 ? (
          <p className="no-cases">No cases assigned to you.</p>
        ) : (
          <>
            <CasesTable
              cases={cases.slice(
                (casesPage - 1) * PAGE_SIZE,
                casesPage * PAGE_SIZE,
              )}
              onCaseClick={(c) =>
                navigate(`/case/${c.id}`, { state: { case: c } })
              }
            />
            <Pagination
              page={casesPage}
              totalPages={Math.max(1, Math.ceil(cases.length / PAGE_SIZE))}
              setPage={setCasesPage}
            />
          </>
        )}
      </section>
    </>
  );
}
