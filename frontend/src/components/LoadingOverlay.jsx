export default function LoadingOverlay({ message }) {
  return (
    <div className="loading-overlay">
      <div className="loading-overlay__spinner" />
      <p className="loading-overlay__message">{message}</p>
    </div>
  );
}
