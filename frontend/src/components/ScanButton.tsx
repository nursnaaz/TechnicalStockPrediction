import Button from "@cloudscape-design/components/button";

interface ScanButtonProps {
  onClick: () => void;
  loading: boolean;
}

/**
 * Button component to trigger a stock scan
 */
export default function ScanButton({ onClick, loading }: ScanButtonProps) {
  return (
    <Button
      variant="primary"
      onClick={onClick}
      loading={loading}
      disabled={loading}
    >
      Run Scan
    </Button>
  );
}
