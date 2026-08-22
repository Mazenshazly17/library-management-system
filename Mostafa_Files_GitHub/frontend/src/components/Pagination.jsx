export function Pagination({ page, totalPages, total, onChange }) {
  const safeTotalPages = Math.max(totalPages || 1, 1);

  return (
    <div className="pagination">
      <span>Page {page} of {safeTotalPages} - {total || 0} result(s)</span>
      <div>
        <button className="secondary" type="button" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Previous
        </button>
        <button className="secondary" type="button" disabled={page >= safeTotalPages} onClick={() => onChange(page + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}
