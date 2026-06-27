import Spinner from "@cloudscape-design/components/spinner";
import Box from "@cloudscape-design/components/box";

interface LoadingIndicatorProps {
  message?: string;
}

/**
 * Loading indicator component displayed during scan execution
 */
export default function LoadingIndicator({ message = "Scanning stocks..." }: LoadingIndicatorProps) {
  return (
    <Box textAlign="center" padding="l">
      <Spinner size="large" />
      <Box variant="p" padding={{ top: "s" }}>
        {message}
      </Box>
    </Box>
  );
}
