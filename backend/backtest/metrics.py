"""
Backtest Metrics Calculator

Calculates performance metrics from backtest results.
"""

from typing import List, Dict
import statistics


class BacktestMetrics:
    """Calculate and aggregate backtesting metrics."""
    
    @staticmethod
    def calculate_aggregate_metrics(trades: List[Dict]) -> Dict:
        """
        Calculate aggregate metrics from a list of trade results.
        
        Args:
            trades: List of trade dictionaries from backtest
            
        Returns:
            Dictionary with aggregate metrics
        """
        if not trades:
            return {
                "total_trades": 0,
                "error": "No trades to analyze"
            }
        
        # Filter out trades without analysis
        analyzed_trades = [
            t for t in trades 
            if t.get("status") == "analyzed"
        ]
        
        if not analyzed_trades:
            return {
                "total_trades": len(trades),
                "analyzed_trades": 0,
                "error": "No successfully analyzed trades"
            }
        
        # Calculate basic metrics
        total_trades = len(analyzed_trades)
        winners = [t for t in analyzed_trades if t["is_winner"]]
        losers = [t for t in analyzed_trades if not t["is_winner"]]
        
        win_count = len(winners)
        loss_count = len(losers)
        
        win_rate = (win_count / total_trades) if total_trades > 0 else 0
        
        # Target hit rates
        target_1_hits = len([t for t in analyzed_trades if t["hit_target_1"]])
        target_2_hits = len([t for t in analyzed_trades if t["hit_target_2"]])
        stop_hits = len([t for t in analyzed_trades if t["hit_stop"]])
        
        target_1_rate = (target_1_hits / total_trades) if total_trades > 0 else 0
        target_2_rate = (target_2_hits / total_trades) if total_trades > 0 else 0
        stop_rate = (stop_hits / total_trades) if total_trades > 0 else 0
        
        # Confusion Matrix (score >= 70 = predicted bullish, max_gain >= 5% = actually went up)
        tp = len([t for t in analyzed_trades if t.get("classification") == "true_positive"])
        fp = len([t for t in analyzed_trades if t.get("classification") == "false_positive"])
        fn = len([t for t in analyzed_trades if t.get("classification") == "false_negative"])
        tn = len([t for t in analyzed_trades if t.get("classification") == "true_negative"])
        
        accuracy = ((tp + tn) / total_trades) if total_trades > 0 else 0
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0
        f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
        
        # Return metrics
        returns = [t["return_pct"] for t in analyzed_trades]
        avg_return = statistics.mean(returns) if returns else 0
        
        winner_returns = [t["return_pct"] for t in winners]
        loser_returns = [t["return_pct"] for t in losers]
        
        avg_winner = statistics.mean(winner_returns) if winner_returns else 0
        avg_loser = statistics.mean(loser_returns) if loser_returns else 0
        
        # Reward-to-risk ratio
        reward_risk = abs(avg_winner / avg_loser) if avg_loser != 0 else 0
        
        # Expectancy: (Win% × Avg Win) - (Loss% × Avg Loss)
        win_pct = win_rate
        loss_pct = 1 - win_rate
        expectancy = (win_pct * avg_winner) - (loss_pct * abs(avg_loser))
        
        # Max gain/loss
        max_gains = [t["max_gain_pct"] for t in analyzed_trades]
        max_losses = [t["max_loss_pct"] for t in analyzed_trades]
        
        best_trade = max(max_gains) if max_gains else 0
        worst_trade = min(max_losses) if max_losses else 0
        
        # Score-based analysis
        score_buckets = BacktestMetrics._analyze_by_score(analyzed_trades)
        
        return {
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": round(win_rate, 3),
            "avg_return": round(avg_return, 2),
            "avg_winner": round(avg_winner, 2),
            "avg_loser": round(avg_loser, 2),
            "reward_risk_ratio": round(reward_risk, 2),
            "expectancy": round(expectancy, 2),
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "target_1_hit_count": target_1_hits,
            "target_1_hit_rate": round(target_1_rate, 3),
            "target_2_hit_count": target_2_hits,
            "target_2_hit_rate": round(target_2_rate, 3),
            "stop_hit_count": stop_hits,
            "stop_hit_rate": round(stop_rate, 3),
            "confusion_matrix": {
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "true_negative": tn
            },
            "accuracy": round(accuracy, 3),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1_score, 3),
            "by_score_bucket": score_buckets
        }
    
    @staticmethod
    def _analyze_by_score(trades: List[Dict]) -> Dict:
        """
        Analyze performance by score buckets.
        
        Args:
            trades: List of trade results
            
        Returns:
            Dict with metrics per score bucket
        """
        buckets = {
            "80-100": [],
            "70-79": [],
            "60-69": [],
            "50-59": [],
            "0-49": []
        }
        
        # Categorize trades
        for trade in trades:
            score = trade.get("score", 0)
            if score >= 80:
                buckets["80-100"].append(trade)
            elif score >= 70:
                buckets["70-79"].append(trade)
            elif score >= 60:
                buckets["60-69"].append(trade)
            elif score >= 50:
                buckets["50-59"].append(trade)
            else:
                buckets["0-49"].append(trade)
        
        # Calculate metrics per bucket
        result = {}
        for bucket_name, bucket_trades in buckets.items():
            if not bucket_trades:
                result[bucket_name] = {
                    "count": 0,
                    "win_rate": 0,
                    "avg_return": 0
                }
                continue
            
            winners = [t for t in bucket_trades if t["is_winner"]]
            returns = [t["return_pct"] for t in bucket_trades]
            
            result[bucket_name] = {
                "count": len(bucket_trades),
                "win_rate": round(len(winners) / len(bucket_trades), 3),
                "avg_return": round(statistics.mean(returns), 2)
            }
        
        return result
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted return).
        
        Args:
            returns: List of return percentages
            risk_free_rate: Annual risk-free rate (default 2%)
            
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        # Convert to decimal
        returns_decimal = [r / 100 for r in returns]
        
        mean_return = statistics.mean(returns_decimal)
        std_return = statistics.stdev(returns_decimal)
        
        if std_return == 0:
            return 0.0
        
        # Annualize (assuming monthly returns)
        annual_return = mean_return * 12
        annual_std = std_return * (12 ** 0.5)
        
        sharpe = (annual_return - risk_free_rate) / annual_std
        
        return round(sharpe, 2)
    
    @staticmethod
    def calculate_max_drawdown(trades: List[Dict]) -> float:
        """
        Calculate maximum drawdown from a series of trades.
        
        Args:
            trades: List of trade results (should be chronological)
            
        Returns:
            Maximum drawdown percentage
        """
        if not trades:
            return 0.0
        
        # Build equity curve (assuming $10,000 starting capital)
        capital = 10000
        equity_curve = [capital]
        
        for trade in trades:
            if trade.get("status") != "analyzed":
                continue
            
            return_pct = trade.get("return_pct", 0)
            capital = capital * (1 + return_pct / 100)
            equity_curve.append(capital)
        
        # Calculate drawdowns
        peak = equity_curve[0]
        max_dd = 0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = ((value - peak) / peak) * 100
            if dd < max_dd:
                max_dd = dd
        
        return round(max_dd, 2)
