import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { API } from "./constants";
import { ActivityTimeline } from "./ActivityTimeline";
import { CaseDetail } from "./CaseDetail";
import { DocumentsTable } from "./DocumentsTable";

export function CaseDetailPage({ caseId }) {
  const location = useLocation();
  const [c, setC] = useState(location.state?.case || null);
  const [docs, setDocs] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loadingCase, setLoadingCase] = useState(!location.state?.case);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingActivity, setLoadingActivity] = useState(true);
  const [deleteState, setDeleteState] = useState(null); // null | 'confirm' | 'deleting'
  const [deleteError, setDeleteError] = useState(null);
  const [archiving, setArchiving] = useState(false);
  const [archiveError, setArchiveError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!location.state?.case) {
      fetch(`${API}/case/${caseId}`, { credentials: "include" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          setC(data);
          setLoadingCase(false);
        });
    }
    fetch(`${API}/case/${caseId}/documents`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => {
        setDocs(d);
        setLoadingDocs(false);
      });
    fetch(`${API}/case/${caseId}/activity`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((a) => {
        setActivity(a);
        setLoadingActivity(false);
      });
  }, [caseId]);

  async function handleStatusChange(status) {
    const res = await fetch(`${API}/case/${caseId}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (res.ok) setC(await res.json());
  }

  async function deleteDocument(filename) {
    await fetch(`${API}/case/${caseId}/documents/${filename}`, {
      method: "DELETE",
      credentials: "include",
    });
    setDocs((prev) => prev.filter((d) => d.name !== filename));
  }

  async function download(filename) {
    const res = await fetch(`${API}/case/${caseId}/documents/${filename}`, {
      credentials: "include",
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleDelete() {
    setDeleteState("deleting");
    setDeleteError(null);
    try {
      const res = await fetch(`${API}/case/${caseId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setDeleteError(data.detail || "Failed to delete case.");
        setDeleteState(null);
        return;
      }
      navigate(-1);
    } catch {
      setDeleteError("Network error.");
      setDeleteState(null);
    }
  }

  async function handleArchive() {
    const archiving_to = !c.archived;
    setArchiving(true);
    setArchiveError(null);
    // Optimistically flip the button so it responds immediately
    setC((prev) => ({ ...prev, archived: archiving_to, ...(archiving_to && { status: "closed" }) }));
    try {
      const res = await fetch(`${API}/case/${caseId}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ archived: archiving_to, ...(archiving_to && { status: "closed" }) }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setArchiveError(data.detail || "Failed to update case.");
        setC((prev) => ({ ...prev, archived: !archiving_to })); // revert
        return;
      }
      setC(await res.json());
    } catch {
      setArchiveError("Network error.");
      setC((prev) => ({ ...prev, archived: !archiving_to })); // revert
    } finally {
      setArchiving(false);
    }
  }

  if (loadingCase)
    return (
      <main className="dashboard-main">
        <p className="no-cases">Loading…</p>
      </main>
    );
  if (!c)
    return (
      <main className="dashboard-main">
        <p className="no-cases">Case not found.</p>
      </main>
    );

  return (
    <main className="dashboard-main">
      <div className="section-heading">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <h2>Case</h2>
        {deleteState === "confirm" ? (
          <div className="delete-confirm">
            <span>Delete this case?</span>
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
        )}
        <button
          className="archive-btn"
          onClick={handleArchive}
          disabled={archiving}
        >
          {c.archived ? "Unarchive" : "Archive"}
        </button>
      </div>
      {archiveError && (
        <p className="form-error" style={{ marginBottom: "1rem" }}>
          {archiveError}
        </p>
      )}
      {deleteError && (
        <p className="form-error" style={{ marginBottom: "1rem" }}>
          {deleteError}
        </p>
      )}

      <section className="detail-section">
        <h3 className="detail-section-title">Information</h3>
        <CaseDetail c={c} onStatusChange={handleStatusChange} />
      </section>

      <section className="detail-section">
        <h3 className="detail-section-title">Documents</h3>
        {loadingDocs ? (
          <p className="no-cases">Loading…</p>
        ) : docs.length === 0 ? (
          <p className="no-cases">No documents attached.</p>
        ) : (
          <DocumentsTable docs={docs} onDownload={download} onDelete={deleteDocument} />
        )}
      </section>

      <section className="detail-section">
        <h3 className="detail-section-title">Activity</h3>
        {loadingActivity ? (
          <p className="no-cases">Loading…</p>
        ) : activity.length === 0 ? (
          <p className="no-cases">No activity recorded.</p>
        ) : (
          <ActivityTimeline entries={activity} />
        )}
      </section>
    </main>
  );
}
