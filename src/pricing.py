PRICING = {
    "input": {
        "standard": 100,
        "cached": 50,
    },
    "output": 300,
}

def calculate_ai_cost(input_tokens: int,cached_input_tokens: int,output_tokens: int,reasoning_tokens: int):
    
    regular_input_tokens = input_tokens - cached_input_tokens

    input_cost = regular_input_tokens * PRICING["input"]["standard"]
    cached_cost = cached_input_tokens * PRICING["input"]["cached"]

    total_output_tokens = output_tokens + reasoning_tokens
    output_cost = total_output_tokens * PRICING["output"]

    return input_cost + cached_cost + output_cost