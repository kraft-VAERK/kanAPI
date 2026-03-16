const STATUSES = ["open", "pending", "in_progress", "closed"];

export function CaseDetail({ c, onStatusChange }) {
  const fields = [
    ["ID", c.id],
    ["Customer", c.customer],
    ["Responsible", c.responsible_person],
    ["Created", new Date(c.created_at).toLocaleDateString()],
    [
      "Updated",
      c.updated_at ? new Date(c.updated_at).toLocaleDateString() : "—",
    ],
  ];
  return (
    <div className="case-detail">
      <div className="case-detail-row">
        <span className="case-detail-label">Status</span>
        {onStatusChange ? (
          <select
            className="case-detail-value"
            value={c.status}
            onChange={(e) => onStatusChange(e.target.value)}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        ) : (
          <span className="case-detail-value">{c.status}</span>
        )}
      </div>
      {fields.map(([label, value]) => (
        <div key={label} className="case-detail-row">
          <span className="case-detail-label">{label}</span>
          <span className="case-detail-value">{value}</span>
        </div>
      ))}
    </div>
  );
}
