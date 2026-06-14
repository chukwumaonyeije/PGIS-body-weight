interface ErrorMessageProps {
  message: string;
  className?: string;
}

export default function ErrorMessage({ message, className = "" }: ErrorMessageProps) {
  return (
    <div
      role="alert"
      className={`bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg ${className}`}
    >
      {message}
    </div>
  );
}
