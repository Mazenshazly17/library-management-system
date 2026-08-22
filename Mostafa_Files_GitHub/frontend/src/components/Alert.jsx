export function Alert({ type = 'info', children, onClose }) {
  if (!children) return null;

  return (
    <div className={`alert ${type}`}>
      <span>{children}</span>
      {onClose && (
        <button type="button" onClick={onClose} aria-label="Close alert">
          x
        </button>
      )}
    </div>
  );
}
