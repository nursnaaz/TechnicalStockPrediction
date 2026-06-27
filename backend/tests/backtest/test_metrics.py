"""
Tests for BacktestMetrics calculations.
"""

import pytest
from backtest.metrics import BacktestMetrics


class TestAggregateMetrics:
    """Tests for aggregate metric calculation."""
    
    def test_empty_trades(self):
        """Empty trades list returns error."""
        result = BacktestMetrics.calculate_aggregate_metrics([])
        assert result["total_trades"] == 0
        assert "error" in result
    
    def test_no_analyzed_trades(self):
        """Trades without 'analyzed' status return error."""
        trades = [
            {"ticker": "AAPL", "status": "insufficient_data"},
            {"ticker": "MSFT", "status": "no_forward_data"},
        ]
        result = BacktestMetrics.calculate_aggregate_metrics(trades)
        assert result["analyzed_trades"] == 0
        assert "error" in result
    
    def test_all_winners(self):
        """All winning trades produce 100% win rate."""
        trades = [
            {
                "ticker": "AAPL", "status": "analyzed",
                "is_winner": True, "return_pct": 5.0,
                "max_gain_pct": 8.0, "max_loss_pct": -2.0,
                "hit_target_1": False, "hit_target_2": False,
                "hit_stop": False, "score": 85
            },
            {
                "ticker": "MSFT", "status": "analyzed",
                "is_winner": True, "return_pct": 12.0,
                "max_gain_pct": 15.0, "max_loss_pct": -1.0,
                "hit_target_1": True, "hit_target_2": False,
                "hit_stop": False, "score": 90
            },
        ]
        result = BacktestMetrics.calculate_aggregate_metrics(trades)
        assert result["win_rate"] == 1.0
        assert result["win_count"] == 2
        assert result["loss_count"] == 0
        assert result["avg_return"] == 8.5
        assert result["target_1_hit_count"] == 1
    
    def test_all_losers(self):
        """All losing trades produce 0% win rate."""
        trades = [
            {
                "ticker": "AAPL", "status": "analyzed",
                "is_winner": False, "return_pct": -5.0,
                "max_gain_pct": 2.0, "max_loss_pct": -8.0,
                "hit_target_1": False, "hit_target_2": False,
                "hit_stop": True, "score": 40
            },
        ]
        result = BacktestMetrics.calculate_aggregate_metrics(trades)
        assert result["win_rate"] == 0.0
        assert result["loss_count"] == 1
        assert result["stop_hit_count"] == 1
    
    def test_mixed_results(self):
        """Mix of winners and losers calculates correctly."""
        trades = [
            {
                "ticker": "AAPL", "status": "analyzed",
                "is_winner": True, "return_pct": 10.0,
                "max_gain_pct": 12.0, "max_loss_pct": -3.0,
                "hit_target_1": True, "hit_target_2": False,
                "hit_stop": False, "score": 75
            },
            {
                "ticker": "MSFT", "status": "analyzed",
                "is_winner": False, "return_pct": -5.0,
                "max_gain_pct": 2.0, "max_loss_pct": -7.0,
                "hit_target_1": False, "hit_target_2": False,
                "hit_stop": True, "score": 60
            },
            {
                "ticker": "GOOGL", "status": "analyzed",
                "is_winner": True, "return_pct": 8.0,
                "max_gain_pct": 10.0, "max_loss_pct": -2.0,
                "hit_target_1": True, "hit_target_2": False,
                "hit_stop": False, "score": 80
            },
        ]
        result = BacktestMetrics.calculate_aggregate_metrics(trades)
        assert result["total_trades"] == 3
        assert result["win_count"] == 2
        assert result["loss_count"] == 1
        assert abs(result["win_rate"] - 0.667) < 0.01
        assert result["target_1_hit_count"] == 2
        assert result["stop_hit_count"] == 1
    
    def test_score_bucket_analysis(self):
        """Score buckets correctly categorize trades."""
        trades = [
            {"ticker": "A", "status": "analyzed", "is_winner": True, "return_pct": 10.0,
             "max_gain_pct": 12.0, "max_loss_pct": -1.0, "hit_target_1": True,
             "hit_target_2": False, "hit_stop": False, "score": 85},
            {"ticker": "B", "status": "analyzed", "is_winner": True, "return_pct": 8.0,
             "max_gain_pct": 10.0, "max_loss_pct": -2.0, "hit_target_1": True,
             "hit_target_2": False, "hit_stop": False, "score": 92},
            {"ticker": "C", "status": "analyzed", "is_winner": False, "return_pct": -3.0,
             "max_gain_pct": 2.0, "max_loss_pct": -5.0, "hit_target_1": False,
             "hit_target_2": False, "hit_stop": False, "score": 45},
        ]
        result = BacktestMetrics.calculate_aggregate_metrics(trades)
        buckets = result["by_score_bucket"]
        
        assert buckets["80-100"]["count"] == 2
        assert buckets["80-100"]["win_rate"] == 1.0
        assert buckets["0-49"]["count"] == 1
        assert buckets["0-49"]["win_rate"] == 0.0


class TestSharpeRatio:
    """Tests for Sharpe ratio calculation."""
    
    def test_empty_returns(self):
        """Empty returns list gives 0."""
        assert BacktestMetrics.calculate_sharpe_ratio([]) == 0.0
    
    def test_single_return(self):
        """Single return gives 0 (need >= 2 for stdev)."""
        assert BacktestMetrics.calculate_sharpe_ratio([5.0]) == 0.0
    
    def test_constant_returns(self):
        """Zero stdev (constant returns) gives 0."""
        assert BacktestMetrics.calculate_sharpe_ratio([5.0, 5.0, 5.0]) == 0.0
    
    def test_positive_sharpe(self):
        """Consistently positive returns give positive Sharpe."""
        returns = [3.0, 4.0, 5.0, 2.0, 6.0, 3.5]
        sharpe = BacktestMetrics.calculate_sharpe_ratio(returns)
        assert sharpe > 0


class TestMaxDrawdown:
    """Tests for max drawdown calculation."""
    
    def test_empty_trades(self):
        """Empty trades give 0 drawdown."""
        assert BacktestMetrics.calculate_max_drawdown([]) == 0.0
    
    def test_all_winners_no_drawdown(self):
        """All winners have minimal/no drawdown."""
        trades = [
            {"status": "analyzed", "return_pct": 5.0},
            {"status": "analyzed", "return_pct": 3.0},
            {"status": "analyzed", "return_pct": 7.0},
        ]
        dd = BacktestMetrics.calculate_max_drawdown(trades)
        assert dd == 0.0  # No drawdown when all positive
    
    def test_drawdown_from_losers(self):
        """Losing trades create drawdown."""
        trades = [
            {"status": "analyzed", "return_pct": 10.0},
            {"status": "analyzed", "return_pct": -15.0},
            {"status": "analyzed", "return_pct": -5.0},
        ]
        dd = BacktestMetrics.calculate_max_drawdown(trades)
        assert dd < 0  # Drawdown is negative
