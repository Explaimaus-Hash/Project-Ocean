export function LoadingOverlay({
  message = "Preparing globe",
}: {
  message?: string;
}) {
  return (
    <div className="scene-message" role="status">
      <span className="loader" aria-hidden="true" />
      <h2>{message}</h2>
      <p>Initializing the geographic workspace.</p>
    </div>
  );
}
