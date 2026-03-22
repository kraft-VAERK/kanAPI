export function CasesTable({ cases, onCaseClick, onCustomerClick }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Customer</th>
          <th>Responsible</th>
          <th>Status</th>
          <th>Created</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {cases.map((c) => (
          <tr key={c.id}>
            <td>
              {onCustomerClick ? (
                <button
                  className="link-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCustomerClick(c.customer, c.company_id);
                  }}
                >
                  {c.customer}
                </button>
              ) : (
                c.customer
              )}
            </td>
            <td>{c.responsible_person}</td>
            <td>{c.status}</td>
            <td>{new Date(c.created_at).toLocaleDateString()}</td>
            <td>
              {onCaseClick && (
                <button
                  className="arrow-btn"
                  onClick={() => onCaseClick(c)}
                  aria-label="View case"
                >
                  &#8250;
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
