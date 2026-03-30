import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { API } from "./constants";
import { ActivityTimeline } from "./ActivityTimeline";
import { CaseDetail } from "./CaseDetail";
import { CaseEditForm } from "./CaseEditForm";
import { DocumentsTable } from "./DocumentsTable";

export function CaseDetailPage({ caseId, editMode, user }) {
  const location = useLocation();
  const [c, setC] = useState(location.state?.case || null);
  const [docs, setDocs] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loadingCase, setLoadingCase] = useState(!location.state?.case);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingActivity, setLoadingActivity] = useState(true);
  const [deleteState, setDeleteState] = useState(null);
  const [deleteError, setDeleteError] = useState(null);
  const [archiving, setArchiving] = useState(false);
  const [archiveError, setArchiveError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [mdViewer, setMdViewer] = useState(null); // { filename, content }
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${API}/case/${caseId}`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        setC(data);
        setLoadingCase(false);
      });
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

  function reloadActivity() {
    fetch(`${API}/case/${caseId}/activity`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setActivity);
  }

  async function deleteDocument(filename) {
    await fetch(`${API}/case/${caseId}/documents/${filename}`, {
      method: "DELETE",
      credentials: "include",
    });
    setDocs((prev) => prev.filter((d) => d.name !== filename));
  }

  async function view(filename) {
    const res = await fetch(`${API}/case/${caseId}/documents/${filename}`, {
      credentials: "include",
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
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

  async function viewMarkdown(pdfFilename) {
    const mdFilename = pdfFilename.replace(/\.pdf$/i, ".md");
    const res = await fetch(`${API}/case/${caseId}/documents/${mdFilename}`, {
      credentials: "include",
    });
    if (res.ok) {
      const text = await res.text();
      setMdViewer({ filename: mdFilename, content: text });
    }
  }

  async function uploadDocument(file) {
    setUploading(true);
    setUploadError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API}/case/${caseId}/documents`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setUploadError(data.detail || "Upload failed.");
        return;
      }
      const updated = await fetch(`${API}/case/${caseId}/documents`, { credentials: "include" });
      setDocs(updated.ok ? await updated.json() : docs);
      reloadActivity();
    } catch {
      setUploadError("Network error.");
    } finally {
      setUploading(false);
    }
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
        setC((prev) => ({ ...prev, archived: !archiving_to }));
        return;
      }
      setC(await res.json());
    } catch {
      setArchiveError("Network error.");
      setC((prev) => ({ ...prev, archived: !archiving_to }));
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

  const canEdit =
    user?.is_admin ||
    c.responsible_user_id === user?.username ||
    c.responsible_person === user?.full_name ||
    c.responsible_person === user?.username;

  return (
    <main className="dashboard-main">
      <div className="section-heading">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <h2>Case</h2>
        {canEdit && (
          <>
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
          </>
        )}
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

      <div className="tabs">
        <button
          className={`tab${!editMode ? " active" : ""}`}
          onClick={() => navigate(`/case/${caseId}`, { replace: true })}
        >
          Detail
        </button>
        {canEdit && (
          <button
            className={`tab${editMode ? " active" : ""}`}
            onClick={() => navigate(`/case/${caseId}/edit`, { replace: true })}
          >
            Edit
          </button>
        )}
      </div>

      {!editMode && (
        <>
          <section className="detail-section">
            <h3 className="detail-section-title">Information</h3>
            <CaseDetail c={c} />
          </section>

          <section className="detail-section">
            <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "0.75rem" }}>
              <h3 className="detail-section-title" style={{ margin: 0 }}>Documents</h3>
              {canEdit && (
                <>
                  <input
                    id="pdf-upload"
                    type="file"
                    accept="application/pdf"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      if (e.target.files[0]) uploadDocument(e.target.files[0]);
                      e.target.value = "";
                    }}
                  />
                  <label
                    htmlFor="pdf-upload"
                    className="btn btn-filled"
                    style={{ cursor: uploading ? "not-allowed" : "pointer" }}
                  >
                    {uploading ? "Uploading…" : "Upload PDF"}
                  </label>
                </>
              )}
            </div>
            {uploadError && <p className="form-error">{uploadError}</p>}
            {loadingDocs ? (
              <p className="no-cases">Loading…</p>
            ) : docs.length === 0 ? (
              <p className="no-cases">No documents attached.</p>
            ) : (
              <DocumentsTable docs={docs} onView={view} onDownload={download} onDelete={deleteDocument} onViewMarkdown={viewMarkdown} />
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
        </>
      )}

      {editMode && canEdit && (
        <section className="detail-section">
          <h3 className="detail-section-title">Edit Case</h3>
          <CaseEditForm
            c={c}
            caseId={caseId}
            isAdmin={!!user?.is_admin}
            onSaved={(updated) => {
              setC(updated);
              reloadActivity();
            }}
          />
        </section>
      )}
      {mdViewer && (
        <div className="modal-overlay" onClick={() => setMdViewer(null)}>
          <div className="modal md-viewer-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{mdViewer.filename}</span>
              <button className="btn" onClick={() => setMdViewer(null)}>Close</button>
            </div>
            <pre className="md-viewer-content">{mdViewer.content}</pre>
          </div>
        </div>
      )}
    </main>
  );
}
