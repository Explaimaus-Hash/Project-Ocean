export function ErrorState({
  title = "Globe unavailable",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="scene-message" role="alert">
      <h2>{title}</h2>
      <p>{message}</p>
      {onRetry && <button onClick={onRetry}>Retry globe</button>}
    </div>
  );
}
