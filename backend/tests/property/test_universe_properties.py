"""
Property-Based Tests for Universe Builder

Tests mathematical properties and invariants for ticker validation and universe building.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from core.universe_builder import UniverseBuilder


# Strategy for valid ASCII uppercase alphanumeric tickers
valid_ticker_strategy = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
    min_size=1,
    max_size=10
)

# Strategy for invalid lowercase tickers
lowercase_ticker_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
    min_size=1,
    max_size=10
)


class TestTickerValidationProperties:
    """Property-based tests for ticker validation."""
    
    @settings(max_examples=20)
    @given(valid_ticker_strategy)
    def test_property_valid_alphanumeric_uppercase_tickers_accepted(self, ticker: str):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        
        Property: Any non-empty string containing only ASCII uppercase letters and digits
        should be accepted as a valid ticker.
        """
        assert UniverseBuilder.validate_ticker(ticker) is True
    
    @settings(max_examples=20)
    @given(lowercase_ticker_strategy)
    def test_property_lowercase_tickers_rejected(self, ticker: str):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.2**
        
        Property: Any string containing lowercase letters should be rejected.
        """
        assert UniverseBuilder.validate_ticker(ticker) is False
    
    @settings(max_examples=20)
    @given(st.text(alphabet=st.characters(blacklist_characters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"), min_size=1))
    def test_property_non_alphanumeric_rejected(self, ticker: str):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.2**
        
        Property: Any string containing characters other than ASCII uppercase letters
        and digits should be rejected.
        """
        assert UniverseBuilder.validate_ticker(ticker) is False
    
    @settings(max_examples=20)
    @given(st.text(max_size=0))
    def test_property_empty_ticker_rejected(self, ticker: str):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.1**
        
        Property: Empty strings should always be rejected.
        """
        assert UniverseBuilder.validate_ticker(ticker) is False


class TestUniverseBuildingProperties:
    """Property-based tests for universe building."""
    
    @settings(max_examples=20)
    @given(st.lists(valid_ticker_strategy, min_size=1))
    def test_property_all_valid_tickers_preserved(self, tickers: list):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.1, 2.2, 2.3**
        
        Property: When given a list of valid tickers, all should be preserved
        in the output universe.
        """
        builder = UniverseBuilder()
        result = builder.build_universe(tickers)
        
        # All tickers should be preserved
        assert len(result) == len(tickers)
        assert result == tickers
    
    @settings(max_examples=20)
    @given(st.lists(valid_ticker_strategy, min_size=1))
    def test_property_order_preserved(self, tickers: list):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.3**
        
        Property: The order of valid tickers in the input should be preserved
        in the output.
        """
        builder = UniverseBuilder()
        result = builder.build_universe(tickers)
        
        # Order should match input
        assert result == tickers
    
    @settings(max_examples=20)
    @given(st.lists(
        st.one_of(valid_ticker_strategy, lowercase_ticker_strategy),
        min_size=1
    ))
    def test_property_invalid_tickers_filtered(self, tickers: list):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.2, 2.3**
        
        Property: When given a mix of valid (uppercase alphanumeric) and
        invalid (lowercase) tickers, only valid ones appear in the output.
        """
        builder = UniverseBuilder()
        
        # Count expected valid tickers
        expected_valid = [t for t in tickers if UniverseBuilder.validate_ticker(t)]
        
        if not expected_valid:
            # All invalid - should raise ValueError
            with pytest.raises(ValueError, match="All tickers are invalid"):
                builder.build_universe(tickers)
        else:
            result = builder.build_universe(tickers)
            
            # Result should contain only valid tickers
            assert len(result) == len(expected_valid)
            assert result == expected_valid
            
            # All returned tickers should be valid
            for ticker in result:
                assert UniverseBuilder.validate_ticker(ticker)
    
    @settings(max_examples=20)
    @given(st.lists(lowercase_ticker_strategy, min_size=1))
    def test_property_all_invalid_raises_error(self, tickers: list):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.4**
        
        Property: When all tickers are invalid, ValueError should be raised.
        """
        builder = UniverseBuilder()
        with pytest.raises(ValueError, match="All tickers are invalid"):
            builder.build_universe(tickers)
    
    def test_property_empty_list_raises_error(self):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.4**
        
        Property: An empty ticker list should raise ValueError.
        """
        builder = UniverseBuilder()
        with pytest.raises(ValueError, match="Ticker list cannot be empty"):
            builder.build_universe([])
    
    @settings(max_examples=20)
    @given(st.lists(valid_ticker_strategy, min_size=1))
    def test_property_result_subset_invariant(self, tickers: list):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.2, 2.3**
        
        Property: The result should always be a subset (or equal to) of the input,
        preserving order.
        """
        builder = UniverseBuilder()
        result = builder.build_universe(tickers)
        
        # Result should be a subsequence of input (order preserved)
        # For all valid inputs, result equals input
        assert result == tickers
        
        # Length invariant: result length <= input length
        assert len(result) <= len(tickers)
    
    @settings(max_examples=20)
    @given(
        st.lists(valid_ticker_strategy, min_size=1),
        st.lists(lowercase_ticker_strategy, min_size=1)
    )
    def test_property_filtering_consistency(self, valid_tickers: list, invalid_tickers: list):
        """
        Property 4: Ticker Validation and Filtering
        **Validates: Requirements 2.2, 2.3**
        
        Property: Given a mix of valid and invalid tickers, the filtering
        should be consistent - only tickers that pass validate_ticker should
        appear in the result.
        """
        builder = UniverseBuilder()
        
        # Interleave valid and invalid tickers
        mixed_tickers = []
        for v, inv in zip(valid_tickers, invalid_tickers):
            mixed_tickers.append(v)
            mixed_tickers.append(inv)
        # Add any remaining from the longer list
        if len(valid_tickers) > len(invalid_tickers):
            mixed_tickers.extend(valid_tickers[len(invalid_tickers):])
        elif len(invalid_tickers) > len(valid_tickers):
            mixed_tickers.extend(invalid_tickers[len(valid_tickers):])
        
        result = builder.build_universe(mixed_tickers)
        
        # Result should contain only tickers that pass validation
        expected = [t for t in mixed_tickers if UniverseBuilder.validate_ticker(t)]
        assert result == expected
        
        # Double-check: all results should pass validation
        for ticker in result:
            assert UniverseBuilder.validate_ticker(ticker)
        
        # No invalid ticker should appear in result
        for inv in invalid_tickers:
            assert inv not in result
