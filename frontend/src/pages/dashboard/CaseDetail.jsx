export function CaseDetail({ c }) {
  const fields = [
    ["ID", c.id],
    ["Customer", c.customer],
    ["Responsible", c.responsible_person],
    ["Status", c.status],
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
