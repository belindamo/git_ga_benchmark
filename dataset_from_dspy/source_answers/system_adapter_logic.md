# System Thinking: Adapter Logic and Token Waste

## Question
I am confused why there are multiple adapters and worry about wasting tokens. What is the logic between how the adapters interact with each other?

## Correct Answer

DSPy uses fallback logic: ChatAdapter tries first, if parsing fails it automatically falls back to JSONAdapter ([#1932](https://github.com/stanfordnlp/dspy/issues/1932)). 

This wastes tokens because ChatAdapter often fails on structured outputs, triggering expensive retry with JSONAdapter. 

### Solution to avoid waste:
Set `dspy.configure(adapter=dspy.JSONAdapter())` as default. 

Note: No XML adapter exists despite requests.

## Source Evidence with Links

- Fallback mechanism in `dspy/adapters/base.py` exception handling
- [Issue #1932](https://github.com/stanfordnlp/dspy/issues/1932): "ChatAdapter always fails wasting the LLM call (at least 2 calls are done for each prompt)"
- Default configuration in `dspy/predict/predict.py`

## Key Points

1. **Fallback Design**: ChatAdapter attempts first, JSONAdapter as backup
2. **Token Waste**: ChatAdapter failures trigger expensive retries 
3. **Root Cause**: ChatAdapter struggles with structured outputs
4. **Optimization**: Configure JSONAdapter as default to avoid fallback
5. **Limitation**: No XML adapter available despite user requests 