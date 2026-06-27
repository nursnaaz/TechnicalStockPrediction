import Alert from "@cloudscape-design/components/alert";

interface ErrorMessageProps {
  message: string;
  onDismiss?: () => void;
}

/**
 * Error message component for displaying scan failures or validation errors
 */
export default function ErrorMessage({ message, onDismiss }: ErrorMessageProps) {
  return (
    <Alert
      type="error"
      dismissible={!!onDismiss}
      onDismiss={onDismiss}
    >
      {message}
    </Alert>
  );
}
