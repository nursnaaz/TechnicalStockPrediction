import Badge from "@cloudscape-design/components/badge";
import SpaceBetween from "@cloudscape-design/components/space-between";
import type { IndicatorSignals } from "../types/scan";

interface SignalBadgesProps {
  signals: IndicatorSignals;
}

/**
 * Displays indicator signals as colored badges
 */
export default function SignalBadges({ signals }: SignalBadgesProps) {
  const signalList = [
    { key: "price_above_sma50", label: "SMA50", active: signals.price_above_sma50 },
    { key: "price_above_ema20", label: "EMA20", active: signals.price_above_ema20 },
    { key: "macd_above_signal", label: "MACD", active: signals.macd_above_signal },
    { key: "macd_histogram_positive", label: "MACD+", active: signals.macd_histogram_positive },
    { key: "volume_above_average", label: "Vol", active: signals.volume_above_average },
    { key: "relative_strength_positive", label: "RS", active: signals.relative_strength_positive },
  ];

  return (
    <SpaceBetween direction="horizontal" size="xs">
      {signalList.map((signal) => (
        <Badge key={signal.key} color={signal.active ? "green" : "grey"}>
          {signal.label}
        </Badge>
      ))}
    </SpaceBetween>
  );
}
