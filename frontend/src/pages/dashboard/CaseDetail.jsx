export function CaseDetail({ c }) {
  const fields = [
    ["Customer", c.customer],
    [
      "Status",
      <span key="status" className={`status-badge status-badge--${c.status}`}>
        {c.status.replace("_", " ")}
      </span>,
    ],
    ["Responsible", c.responsible_person],
    ["Created", new Date(c.created_at).toLocaleDateString()],
    [
      "Updated",
      c.updated_at ? new Date(c.updated_at).toLocaleDateString() : "—",
    ],
  ];
  return (
    <div className="case-detail">
      {fields.map(([label, value]) => (
        <div key={label} className="case-detail-row">
          <span className="case-detail-label">{label}</span>
          <span className="case-detail-value">{value}</span>
        </div>
      ))}
    </div>
  );
}
