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
  const [activeTab, setActiveTab] = useState("cases");
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditPage, setAuditPage] = useState(1);
  const [auditLoaded, setAuditLoaded] = useState(false);
  const [changelog, setChangelog] = useState([]);
  const [changelogLoaded, setChangelogLoaded] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const stateUser = location.state?.user;
    if (stateUser && stateUser.username === userId) {
      setU(stateUser);
      setForm({
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
        email: updated.email,
        full_name: updated.full_name || "",
        is_active: updated.is_active,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
      // refresh changelog so new entries appear immediately
      setChangelogLoaded(false);
      fetch(`${API}/user/${userId}/changelog`, { credentials: "include" })
        .then((r) => (r.ok ? r.json() : []))
        .then((data) => { setChangelog(data); setChangelogLoaded(true); });
    } catch {
      setSaveError("Network error.");
    } finally {
      setSaving(false);
    }
  }

  function loadChangelog() {
    if (changelogLoaded) return;
    fetch(`${API}/user/${userId}/changelog`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        setChangelog(data);
        setChangelogLoaded(true);
      });
  }

  function loadAudit() {
    if (auditLoaded) return;
    fetch(`${API}/audit/logs?user=${encodeURIComponent(userId)}&limit=200`, {
      credentials: "include",
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        setAuditLogs(data);
        setAuditLoaded(true);
      });
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
    (form.email !== u.email ||
      (form.full_name || null) !== u.full_name ||
      form.is_active !== u.is_active);

  const totalPages = Math.max(1, Math.ceil(cases.length / PAGE_SIZE));
  const pageSlice = cases.slice((casesPage - 1) * PAGE_SIZE, casesPage * PAGE_SIZE);

  const auditTotalPages = Math.max(1, Math.ceil(auditLogs.length / PAGE_SIZE));
  const auditPageSlice = auditLogs.slice((auditPage - 1) * PAGE_SIZE, auditPage * PAGE_SIZE);

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
                <span className="customer-info-value">{u.username}</span>
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
            <button
              className={`tab${activeTab === "cases" ? " active" : ""}`}
              onClick={() => setActiveTab("cases")}
            >
              Cases{cases.length > 0 ? ` (${cases.length})` : ""}
            </button>
            {viewerIsSuperAdmin && (
              <button
                className={`tab${activeTab === "activity" ? " active" : ""}`}
                onClick={() => { setActiveTab("activity"); loadAudit(); }}
              >
                Activity
              </button>
            )}
          </div>

          {activeTab === "cases" && (
            cases.length === 0 ? (
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
            )
          )}

          {viewerIsSuperAdmin && (
            <div style={{ marginTop: "2rem" }}>
              <div className="section-heading" style={{ cursor: "pointer" }} onClick={() => { loadChangelog(); }}>
                <h3 style={{ margin: 0, fontSize: "1rem" }}>Profile Changelog</h3>
                {!changelogLoaded && (
                  <button className="btn" style={{ fontSize: "0.8em" }} onClick={(e) => { e.stopPropagation(); loadChangelog(); }}>
                    Load
                  </button>
                )}
                {changelogLoaded && (
                  <span className="customer-hero-tag" style={{ marginLeft: "auto" }}>
                    {changelog.length} {changelog.length === 1 ? "change" : "changes"}
                  </span>
                )}
              </div>
              {changelogLoaded && (
                changelog.length === 0 ? (
                  <p className="no-cases" style={{ marginTop: "0.5rem" }}>No changes recorded.</p>
                ) : (
                  <table style={{ marginTop: "0.5rem" }}>
                    <thead>
                      <tr>
                        <th>When</th>
                        <th>Changed by</th>
                        <th>Field</th>
                        <th>Before</th>
                        <th>After</th>
                      </tr>
                    </thead>
                    <tbody>
                      {changelog.map((c) => (
                        <tr key={c.id}>
                          <td style={{ whiteSpace: "nowrap", color: "var(--text-muted)", fontSize: "0.85em" }}>
                            {new Date(c.changed_at).toLocaleString()}
                          </td>
                          <td style={{ fontSize: "0.85em" }}>{c.changed_by || "—"}</td>
                          <td style={{ fontWeight: 600 }}>{c.field}</td>
                          <td style={{ color: "var(--error)", fontFamily: "monospace", fontSize: "0.85em" }}>
                            {c.old_value ?? "—"}
                          </td>
                          <td style={{ color: "var(--success)", fontFamily: "monospace", fontSize: "0.85em" }}>
                            {c.new_value ?? "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )
              )}
            </div>
          )}

          {activeTab === "activity" && (
            !auditLoaded ? (
              <p className="no-cases">Loading…</p>
            ) : auditLogs.length === 0 ? (
              <p className="no-cases">No activity recorded for this user.</p>
            ) : (
              <>
                <table>
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Method</th>
                      <th>Path</th>
                      <th>Status</th>
                      <th>Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditPageSlice.map((e, i) => (
                      <tr key={i}>
                        <td style={{ whiteSpace: "nowrap", color: "var(--text-muted)", fontSize: "0.85em" }}>
                          {e.timestamp}
                        </td>
                        <td style={{ fontWeight: 600 }}>{e.method}</td>
                        <td style={{ fontFamily: "monospace", fontSize: "0.85em", wordBreak: "break-all" }}>
                          {e.path}
                        </td>
                        <td style={{ fontWeight: 600, color: e.status_code < 400 ? "var(--success)" : "var(--error)" }}>
                          {e.status_code}
                        </td>
                        <td style={{ color: "var(--text-muted)", fontSize: "0.85em" }}>
                          {e.duration_ms.toFixed(0)}ms
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <Pagination
                  page={auditPage}
                  totalPages={auditTotalPages}
                  setPage={setAuditPage}
                />
              </>
            )
          )}
        </>
      )}
    </main>
  );
}
