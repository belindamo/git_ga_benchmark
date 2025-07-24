# System Thinking: Optimizations for Inference Speed

## Question
What optimizations can I make to speed up inference of my DSPy calls?

## Correct Answer

Proven speed techniques:

1. **Caching**: Built-in with `cache` parameter to avoid redundant LM calls ([Issue #213](https://github.com/stanfordnlp/dspy/issues/213))

2. **Batching**: Use `n` parameter in `dspy.Predict(signature, n=5)` for parallel API calls ([Issue #991](https://github.com/stanfordnlp/dspy/issues/991))

3. **Multi-threading**: Set `num_threads` in evaluators - compilation drops from 60min single-thread to 6min with 10 threads

4. **Module freezing**: Set `._compiled = True` to skip re-optimization

### Past optimizations:
- Async support for I/O concurrency
- Connection pooling for LM clients

## Source Evidence with Links

- [DSPy FAQ](https://dspy.ai/faqs/): "compiling this program takes around 6 minutes...over 10 threads"
- [Issue #991](https://github.com/stanfordnlp/dspy/issues/991): Batching vs threading performance discussion
- [Issue #213](https://github.com/stanfordnlp/dspy/issues/213): Runtime cache control for avoiding redundant calls
- [Cheatsheet](https://dspy.ai/cheatsheet/) shows `num_threads=NUM_THREADS` in optimizers

## Key Points

1. **Caching**: Eliminates redundant LM calls with built-in cache parameter
2. **Batching**: Parallel API calls using n parameter for multiple predictions
3. **Multi-threading**: Dramatic speedup (60min → 6min with 10 threads)
4. **Module Freezing**: Skip re-optimization for compiled modules
5. **Proven Results**: All techniques have documented performance improvements 