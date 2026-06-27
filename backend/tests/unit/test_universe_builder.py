"""
Unit Tests for Universe Builder

Tests for ticker validation and universe construction.
"""

import pytest
from core.universe_builder import UniverseBuilder


class TestValidateTicker:
    """Tests for the validate_ticker static method."""
    
    def test_valid_uppercase_ticker(self):
        """Test that valid uppercase tickers are accepted."""
        assert UniverseBuilder.validate_ticker("AAPL") is True
        assert UniverseBuilder.validate_ticker("MSFT") is True
        assert UniverseBuilder.validate_ticker("GOOGL") is True
    
    def test_valid_alphanumeric_ticker(self):
        """Test that alphanumeric tickers are accepted."""
        assert UniverseBuilder.validate_ticker("BRK") is True
        assert UniverseBuilder.validate_ticker("A") is True
        assert UniverseBuilder.validate_ticker("SPY500") is True
        assert UniverseBuilder.validate_ticker("QQQ3") is True
    
    def test_empty_ticker_rejected(self):
        """Test that empty ticker is rejected."""
        assert UniverseBuilder.validate_ticker("") is False
    
    def test_lowercase_ticker_rejected(self):
        """Test that lowercase tickers are rejected."""
        assert UniverseBuilder.validate_ticker("aapl") is False
        assert UniverseBuilder.validate_ticker("msft") is False
    
    def test_mixed_case_ticker_rejected(self):
        """Test that mixed case tickers are rejected."""
        assert UniverseBuilder.validate_ticker("AaPl") is False
        assert UniverseBuilder.validate_ticker("MsFt") is False
    
    def test_ticker_with_special_characters_rejected(self):
        """Test that tickers with special characters are rejected."""
        assert UniverseBuilder.validate_ticker("AAPL-B") is False
        assert UniverseBuilder.validate_ticker("BRK.B") is False
        assert UniverseBuilder.validate_ticker("SPY_500") is False
        assert UniverseBuilder.validate_ticker("MSFT@") is False
    
    def test_ticker_with_spaces_rejected(self):
        """Test that tickers with spaces are rejected."""
        assert UniverseBuilder.validate_ticker("A APL") is False
        assert UniverseBuilder.validate_ticker(" AAPL") is False
        assert UniverseBuilder.validate_ticker("AAPL ") is False
    
    def test_numeric_only_ticker_accepted(self):
        """Test that numeric-only tickers are accepted."""
        assert UniverseBuilder.validate_ticker("123") is True
        assert UniverseBuilder.validate_ticker("500") is True


class TestBuildUniverse:
    """Tests for the build_universe method."""
    
    def test_valid_tickers_preserved(self):
        """Test that valid tickers are preserved in output."""
        builder = UniverseBuilder()
        tickers = ["AAPL", "MSFT", "GOOGL"]
        result = builder.build_universe(tickers)
        
        assert result == ["AAPL", "MSFT", "GOOGL"]
        assert len(result) == 3
    
    def test_invalid_tickers_filtered_out(self):
        """Test that invalid tickers are filtered out with warnings logged."""
        builder = UniverseBuilder()
        tickers = ["AAPL", "aapl", "MSFT", "brk.b", "GOOGL"]
        result = builder.build_universe(tickers)
        
        # Only valid uppercase alphanumeric tickers should remain
        assert result == ["AAPL", "MSFT", "GOOGL"]
        assert len(result) == 3
    
    def test_empty_list_raises_value_error(self):
        """Test that ValueError is raised when input list is empty."""
        builder = UniverseBuilder()
        
        with pytest.raises(ValueError, match="Ticker list cannot be empty"):
            builder.build_universe([])
    
    def test_all_invalid_tickers_raises_value_error(self):
        """Test that ValueError is raised when all tickers are invalid."""
        builder = UniverseBuilder()
        invalid_tickers = ["aapl", "msft", "brk.b", "goog-l"]
        
        with pytest.raises(ValueError, match="All tickers are invalid"):
            builder.build_universe(invalid_tickers)
    
    def test_single_valid_ticker(self):
        """Test that single valid ticker works correctly."""
        builder = UniverseBuilder()
        result = builder.build_universe(["AAPL"])
        
        assert result == ["AAPL"]
        assert len(result) == 1
    
    def test_alphanumeric_validation_edge_cases(self):
        """Test alphanumeric validation with edge cases."""
        builder = UniverseBuilder()
        
        # Valid alphanumeric combinations
        tickers = ["ABC123", "A1B2C3", "XYZ", "123ABC"]
        result = builder.build_universe(tickers)
        assert result == ["ABC123", "A1B2C3", "XYZ", "123ABC"]
    
    def test_mixed_valid_and_invalid_tickers(self):
        """Test filtering with mix of valid and invalid tickers."""
        builder = UniverseBuilder()
        tickers = [
            "AAPL",      # valid
            "msft",      # invalid (lowercase)
            "GOOGL",     # valid
            "brk.b",     # invalid (special char)
            "TSLA",      # valid
            "",          # invalid (empty)
            "AMZN",      # valid
            "spy_500"    # invalid (special char and lowercase)
        ]
        result = builder.build_universe(tickers)
        
        assert result == ["AAPL", "GOOGL", "TSLA", "AMZN"]
        assert len(result) == 4
    
    def test_preserves_order_of_valid_tickers(self):
        """Test that the order of valid tickers is preserved."""
        builder = UniverseBuilder()
        tickers = ["TSLA", "AAPL", "MSFT", "GOOGL", "AMZN"]
        result = builder.build_universe(tickers)
        
        # Order should be preserved
        assert result == ["TSLA", "AAPL", "MSFT", "GOOGL", "AMZN"]
    
    def test_duplicate_valid_tickers(self):
        """Test behavior with duplicate valid tickers."""
        builder = UniverseBuilder()
        tickers = ["AAPL", "MSFT", "AAPL", "GOOGL", "MSFT"]
        result = builder.build_universe(tickers)
        
        # Duplicates should be preserved (filtering happens elsewhere)
        assert result == ["AAPL", "MSFT", "AAPL", "GOOGL", "MSFT"]
        assert len(result) == 5
    
    def test_whitespace_only_ticker_rejected(self):
        """Test that whitespace-only ticker is rejected."""
        builder = UniverseBuilder()
        tickers = ["AAPL", "   ", "MSFT"]
        result = builder.build_universe(tickers)
        
        assert result == ["AAPL", "MSFT"]
        assert len(result) == 2
