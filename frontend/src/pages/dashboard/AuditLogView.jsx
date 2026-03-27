import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { API, PAGE_SIZE } from "./constants";
import { Pagination } from "./Pagination";

const METHOD_COLORS = {
  GET:    { color: "var(--text-secondary)" },
  POST:   { color: "#2563eb" },
  PATCH:  { color: "#d97706" },
  DELETE: { color: "var(--error)" },
};

function statusStyle(code) {
  if (code >= 200 && code < 300) return { color: "var(--success)" };
  if (code >= 400) return { color: "var(--error)" };
  return { color: "var(--text-secondary)" };
}

export function AuditLogView() {
  const [logs, setLogs] = useState([]);
  const [page, setPage] = useState(1);
  const [filterUser, setFilterUser] = useState("");
  const [filterMethod, setFilterMethod] = useState("");
  const [debouncedUser, setDebouncedUser] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const t = setTimeout(() => setDebouncedUser(filterUser), 300);
    return () => clearTimeout(t);
  }, [filterUser]);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ limit: "500" });
    if (debouncedUser) params.set("user", debouncedUser);
    fetch(`${API}/audit/logs?${params}`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setLogs)
      .finally(() => setLoading(false));
  }, [debouncedUser]);

  useEffect(() => {
    setPage(1);
  }, [debouncedUser, filterMethod]);

  const visible = filterMethod
    ? logs.filter((l) => l.method === filterMethod)
    : logs;

  const totalPages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const pageSlice = visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <main className="dashboard-main">
      <div className="section-heading">
        <button className="back-btn" onClick={() => navigate("/dashboard")}>
          ← Companies
        </button>
        <h2>Audit Log</h2>
        <span className="customer-hero-tag" style={{ marginLeft: "auto" }}>
          {visible.length} entries
        </span>
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <input
          className="search-input"
          placeholder="Filter by username…"
          value={filterUser}
          onChange={(e) => setFilterUser(e.target.value)}
          style={{ flex: "1", minWidth: "160px" }}
        />
        <select
          className="status-select"
          value={filterMethod}
          onChange={(e) => setFilterMethod(e.target.value)}
        >
          <option value="">All methods</option>
          <option value="GET">GET</option>
          <option value="POST">POST</option>
          <option value="PATCH">PATCH</option>
          <option value="DELETE">DELETE</option>
        </select>
      </div>

      {loading ? (
        <p className="no-cases">Loading…</p>
      ) : visible.length === 0 ? (
        <p className="no-cases">No audit entries found.</p>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>User</th>
                <th>IP</th>
                <th>Method</th>
                <th>Path</th>
                <th>Status</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {pageSlice.map((e, i) => (
                <tr key={i}>
                  <td style={{ whiteSpace: "nowrap", color: "var(--text-muted)", fontSize: "0.85em" }}>
                    {e.timestamp}
                  </td>
                  <td>
                    <button
                      className="link-btn"
                      onClick={() => navigate(`/user/${e.username}`)}
                    >
                      {e.username}
                    </button>
                  </td>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.85em" }}>{e.ip}</td>
                  <td>
                    <span style={{ fontWeight: 600, ...METHOD_COLORS[e.method] }}>
                      {e.method}
                    </span>
                  </td>
                  <td style={{ fontFamily: "monospace", fontSize: "0.85em", wordBreak: "break-all" }}>
                    {e.path}
                  </td>
                  <td>
                    <span style={{ fontWeight: 600, ...statusStyle(e.status_code) }}>
                      {e.status_code}
                    </span>
                  </td>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.85em", whiteSpace: "nowrap" }}>
                    {e.duration_ms.toFixed(0)}ms
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} totalPages={totalPages} setPage={setPage} />
        </>
      )}
    </main>
  );
}
