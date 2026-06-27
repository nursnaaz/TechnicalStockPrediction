import StatusIndicator from "@cloudscape-design/components/status-indicator";
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import type { MarketRegime } from "../types/scan";

interface MarketRegimeBadgeProps {
  regime: MarketRegime;
}

/**
 * Displays the current market regime classification
 */
export default function MarketRegimeBadge({ regime }: MarketRegimeBadgeProps) {
  const getStatusType = (regime: MarketRegime) => {
    switch (regime) {
      case "bullish":
        return "success";
      case "bearish":
        return "error";
      case "neutral":
        return "info";
      default:
        return "info";
    }
  };

  const getLabel = (regime: MarketRegime) => {
    return regime.charAt(0).toUpperCase() + regime.slice(1);
  };

  return (
    <Container header={<Header variant="h2">Market Regime</Header>}>
      <StatusIndicator type={getStatusType(regime)}>
        {getLabel(regime)} Market
      </StatusIndicator>
    </Container>
  );
}
