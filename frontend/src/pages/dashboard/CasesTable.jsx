export function CasesTable({ cases, onCaseClick, onCustomerClick }) {
  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Customer</th>
          <th>Responsible</th>
          <th>Status</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {cases.map((c) => (
          <tr key={c.id}>
            <td className="id">
              {onCaseClick ? (
                <button
                  className="link-btn id-link"
                  onClick={() => onCaseClick(c)}
                >
                  {c.id}
                </button>
              ) : (
                c.id
              )}
            </td>
            <td>
              {onCustomerClick ? (
                <button
                  className="link-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCustomerClick(c.customer);
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
          </tr>
        ))}
      </tbody>
    </table>
  );
}
