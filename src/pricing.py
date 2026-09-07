
from typing import Dict, Any

PRICING = {
    "input": {
        "standard": 100, 
        "cached": 50,    
    },
    "output": 300,        
}

def calculate_ai_cost( input_tokens: int, cached_input_tokens: int, output_tokens: int, reasoning_tokens: int) -> int:

    regular_input_tokens = max(0, input_tokens - cached_input_tokens)
    
    # Calculate input costs
    input_cost = regular_input_tokens * PRICING["input"]["standard"]
    cached_cost = cached_input_tokens * PRICING["input"]["cached"]
    
    # Output: reasoning tokens are output tokens!
    total_output_tokens = output_tokens + reasoning_tokens
    output_cost = total_output_tokens * PRICING["output"]
    
    # Total cost
    total_cost = input_cost + cached_cost + output_cost
    return total_cost