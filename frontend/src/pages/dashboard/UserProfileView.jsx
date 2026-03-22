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
  const [deleteState, setDeleteState] = useState(null);
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
      setTimeout(() => setSaveSuccess(false), 3000);
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

  const totalPages = Math.max(1, Math.ceil(cases.length / PAGE_SIZE));
  const pageSlice = cases.slice((casesPage - 1) * PAGE_SIZE, casesPage * PAGE_SIZE);

  return (
    <main className="dashboard-main">
      <div className="section-heading">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
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
          <div className="customer-hero">
            <div className="customer-hero-avatar">{initials}</div>
            <h2 className="customer-hero-name">{u.full_name || u.username}</h2>
            <span className="customer-hero-tag">{role}</span>

            <div className="customer-stats">
              <div className="customer-stat">
                <span className="customer-stat-value">{cases.length}</span>
                <span className="customer-stat-label">Cases</span>
              </div>
              <div className="customer-stat">
                <span className="customer-stat-value">
                  {u.is_active ? "Active" : "Inactive"}
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
                {viewerIsSuperAdmin ? (
                  <input
                    className="profile-inline-input"
                    value={form.username}
                    onChange={(e) => {
                      setForm((f) => ({ ...f, username: e.target.value }));
                      setSaveSuccess(false);
                    }}
                  />
                ) : (
                  <span className="customer-info-value">{u.username}</span>
                )}
              </div>
            </div>
            <div className="customer-info-card">
              <span className="customer-info-icon">✉</span>
              <div className="customer-info-content">
                <span className="customer-info-label">Email</span>
                <input
                  className="profile-inline-input"
                  type="email"
                  value={form.email}
                  onChange={(e) => {
                    setForm((f) => ({ ...f, email: e.target.value }));
                    setSaveSuccess(false);
                  }}
                />
              </div>
            </div>
            <div className="customer-info-card">
              <span className="customer-info-icon">☺</span>
              <div className="customer-info-content">
                <span className="customer-info-label">Full Name</span>
                <input
                  className="profile-inline-input"
                  value={form.full_name}
                  onChange={(e) => {
                    setForm((f) => ({ ...f, full_name: e.target.value }));
                    setSaveSuccess(false);
                  }}
                />
              </div>
            </div>
            <div className="customer-info-card">
              <span className="customer-info-icon">⏻</span>
              <div className="customer-info-content">
                <span className="customer-info-label">Status</span>
                <label className="profile-inline-toggle">
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

          <div className="tabs" style={{ marginTop: "1.5rem" }}>
            <button className="tab active">
              Cases{cases.length > 0 ? ` (${cases.length})` : ""}
            </button>
          </div>

          {cases.length === 0 ? (
            <p className="no-cases">No cases assigned to this user.</p>
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
      )}
    </main>
  );
}
