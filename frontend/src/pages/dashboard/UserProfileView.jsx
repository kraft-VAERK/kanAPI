import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { API, PAGE_SIZE } from "./constants";
import { CasesTable } from "./CasesTable";
import { Pagination } from "./Pagination";

export function UserProfileView({ userId, viewerIsSuperAdmin }) {
  const [u, setU] = useState(null);
  const [cases, setCases] = useState([]);
  const [casesPage, setCasesPage] = useState(1);
  const [error, setError] = useState(null);
  const [deleteState, setDeleteState] = useState(null); // null | 'confirm' | 'deleting'
  const [deleteError, setDeleteError] = useState(null);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const stateUser = location.state?.user;
    if (stateUser && stateUser.username === userId) {
      setU(stateUser);
      setForm({
        username: stateUser.username,
        email: stateUser.email,
        full_name: stateUser.full_name || "",
        is_active: stateUser.is_active,
      });
    } else {
      fetch(`${API}/user/${userId}`, { credentials: "include" })
        .then(async (r) => {
          if (!r.ok) {
            setError("User not found.");
            return;
          }
          const data = await r.json();
          setU(data);
          setForm({
            username: data.username,
            email: data.email,
            full_name: data.full_name || "",
            is_active: data.is_active,
          });
        })
        .catch(() => setError("Failed to load user."));
    }
    fetch(`${API}/user/${userId}/cases`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setCases);
  }, [userId]);

  async function handleDelete() {
    setDeleteState("deleting");
    setDeleteError(null);
    try {
      const res = await fetch(`${API}/user/${userId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setDeleteError(data.detail || "Failed to delete user.");
        setDeleteState(null);
        return;
      }
      navigate(-1);
    } catch {
      setDeleteError("Network error.");
      setDeleteState(null);
    }
  }

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      const body = {
        username: form.username,
        email: form.email,
        full_name: form.full_name || null,
        is_active: form.is_active,
      };
      const res = await fetch(`${API}/user/${userId}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setSaveError(data.detail || "Failed to save.");
        return;
      }
      const updated = await res.json();
      setU(updated);
      setForm({
        username: updated.username,
        email: updated.email,
        full_name: updated.full_name || "",
        is_active: updated.is_active,
      });
      setSaveSuccess(true);
    } catch {
      setSaveError("Network error.");
    } finally {
      setSaving(false);
    }
  }

  const role = u
    ? u.is_admin
      ? u.parent_id
        ? "Company admin"
        : "Super admin"
      : "User"
    : "…";
  const initials = u
    ? (u.full_name || u.username).slice(0, 2).toUpperCase()
    : "?";
  const dirty =
    form &&
    u &&
    (form.username !== u.username ||
      form.email !== u.email ||
      (form.full_name || null) !== u.full_name ||
      form.is_active !== u.is_active);

  return (
    <main className="dashboard-main">
      <div className="section-heading">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <h2>User Profile</h2>
        {u &&
          (deleteState === "confirm" ? (
            <div className="delete-confirm">
              <span>Delete this user?</span>
              <button className="back-btn" onClick={() => setDeleteState(null)}>
                Cancel
              </button>
              <button className="delete-btn" onClick={handleDelete}>
                Confirm
              </button>
            </div>
          ) : (
            <button
              className="delete-btn"
              onClick={() => setDeleteState("confirm")}
            >
              Delete
            </button>
          ))}
      </div>
      {deleteError && (
        <p className="form-error" style={{ marginBottom: "1rem" }}>
          {deleteError}
        </p>
      )}
      {error ? (
        <p className="no-cases">{error}</p>
      ) : !u || !form ? (
        <p className="no-cases">Loading…</p>
      ) : (
        <>
          <div className="profile-card">
            <div className="profile-header">
              <div className="profile-avatar">{initials}</div>
              <div className="profile-header-info">
                <span className="profile-header-name">
                  {u.full_name || u.username}
                </span>
                <span className="profile-header-role">{role}</span>
              </div>
            </div>
            <div className="profile-fields">
              <div className="profile-field">
                <label>ID</label>
                {viewerIsSuperAdmin ? (
                  <input
                    value={form.username}
                    onChange={(e) => {
                      setForm((f) => ({ ...f, username: e.target.value }));
                      setSaveSuccess(false);
                    }}
                  />
                ) : (
                  <div className="profile-field-static">{u.username}</div>
                )}
              </div>
              <div className="profile-field">
                <label>Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => {
                    setForm((f) => ({ ...f, email: e.target.value }));
                    setSaveSuccess(false);
                  }}
                />
              </div>
              <div className="profile-field">
                <label>Full name</label>
                <input
                  value={form.full_name}
                  onChange={(e) => {
                    setForm((f) => ({ ...f, full_name: e.target.value }));
                    setSaveSuccess(false);
                  }}
                />
              </div>
              <div className="profile-field">
                <label>Status</label>
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => {
                      setForm((f) => ({ ...f, is_active: e.target.checked }));
                      setSaveSuccess(false);
                    }}
                  />
                  {form.is_active ? "Active" : "Inactive"}
                </label>
              </div>
            </div>
            {(dirty || saveError || saveSuccess) && (
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
                {saveError && <span className="form-error">{saveError}</span>}
                {saveSuccess && (
                  <span className="profile-success">Changes saved.</span>
                )}
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
              <p className="no-cases">No cases assigned to this user.</p>
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
                  totalPages={Math.max(
                    1,
                    Math.ceil(cases.length / PAGE_SIZE),
                  )}
                  setPage={setCasesPage}
                />
              </>
            )}
          </section>
        </>
      )}
    </main>
  );
}
