export function Pagination({ page, totalPages, setPage }) {
  if (totalPages <= 1) return null;
  return (
    <div className="pagination">
      <button onClick={() => setPage((p) => p - 1)} disabled={page === 1}>
        Previous
      </button>
      <span>
        {page} / {totalPages}
      </span>
      <button
        onClick={() => setPage((p) => p + 1)}
        disabled={page === totalPages}
      >
        Next
      </button>
    </div>
  );
}
