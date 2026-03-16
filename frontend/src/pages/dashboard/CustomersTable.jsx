export function CustomersTable({ customers, onSelect }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Cases</th>
        </tr>
      </thead>
      <tbody>
        {customers.map(({ name, count }) => (
          <tr key={name} className="clickable" onClick={() => onSelect(name)}>
            <td>{name}</td>
            <td>{count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
