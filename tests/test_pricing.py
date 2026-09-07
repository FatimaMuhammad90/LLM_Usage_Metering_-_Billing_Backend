# tests/test_pricing.py
import pytest
from src.pricing import calculate_ai_cost, PRICING

def test_cached_tokens_are_cheaper():
    # 1000 standard tokens = 1000 * 100 = 100,000
    standard_cost = calculate_ai_cost(1000, 0, 0, 0)
    
    # 1000 cached tokens = 1000 * 50 = 50,000
    cached_cost = calculate_ai_cost(1000, 1000, 0, 0)
    
    assert standard_cost == 100000, f"Expected 100000, got {standard_cost}"
    assert cached_cost == 50000, f"Expected 50000, got {cached_cost}"
    assert cached_cost < standard_cost, "Cached tokens should be cheaper!"


def test_reasoning_tokens_count_as_output():
    # 1000 output tokens = 1000 * 300 = 300,000
    output_only = calculate_ai_cost(0, 0, 1000, 0)
    
    # 1000 reasoning tokens = 1000 * 300 = 300,000 (same as output)
    reasoning_only = calculate_ai_cost(0, 0, 0, 1000)
    
    # 500 output + 500 reasoning = 1000 * 300 = 300,000
    combined = calculate_ai_cost(0, 0, 500, 500)
    
    assert output_only == 300000, f"Expected 300000, got {output_only}"
    assert reasoning_only == 300000, f"Expected 300000, got {reasoning_only}"
    assert combined == 300000, f"Expected 300000, got {combined}"


def test_mixed_tokens_calculation():
    # 1000 input: 400 standard, 300 cached, 200 output, 100 reasoning
    cost = calculate_ai_cost(1000, 300, 200, 100)
    
    # Expected:
    # Standard input: (1000-300) * 100 = 700 * 100 = 70,000
    # Cached input: 300 * 50 = 15,000
    # Total output: (200+100) * 300 = 300 * 300 = 90,000
    # Total: 70,000 + 15,000 + 90,000 = 175,000
    
    expected = 175000
    assert cost == expected, f"Expected {expected}, got {cost}"


def test_pricing_constants_pinned():
    assert PRICING["input"]["standard"] == 100, "Standard input price changed!"
    assert PRICING["input"]["cached"] == 50, "Cached input price changed!"
    assert PRICING["output"] == 300, "Output price changed!"


def test_no_negative_costs():
    cost = calculate_ai_cost(0, 0, 0, 0)
    assert cost == 0, f"Expected 0, got {cost}"
    
    # Edge case: more cached than total input
    cost = calculate_ai_cost(100, 1000, 0, 0)
    assert cost >= 0, "Negative cost!"