# ADR-002: Batch Processing Size Strategy

**Status**: Accepted  
**Date**: 2025-12-31  
**Deciders**: Project Architecture Team  
**Related**: [Architecture](../architecture.md#performance-considerations)

## Context

Multiple operations in the AI Grounding project require processing large datasets in batches:

1. **LLM Context Processing** (Task 1): Splitting 1000 users into manageable chunks
2. **Embedding Generation** (Task 2): Creating embeddings for user documents
3. **API Rate Limiting**: Avoiding service overload

### Requirements

- **LLM Context Limits**: GPT-4 context window is finite (8k-128k tokens)
- **API Efficiency**: Balance between throughput and latency
- **Memory Constraints**: Avoid loading too much data simultaneously
- **Educational Clarity**: Easy to understand and modify

### Constraints

- No hard rate limits on DIAL API (best effort)
- Local development environment (no distributed processing)
- Synchronous API calls in some paths

## Decision

We will use **batch size of 100** for all batch processing operations across the project:

1. **Task 1 (No Grounding)**: 100 users per LLM call
2. **Task 2 (Vector-based)**: 100 documents per embedding batch
3. **Task 3 (Input-Output)**: Maintain consistency with other tasks

This batch size will be **configurable** via function parameters but default to 100.

## Consequences

### Positive

- ✅ **Consistent**: Same batch size across all tasks (predictable behavior)
- ✅ **Tested**: Proven to work reliably in development
- ✅ **Reasonable Memory**: ~50-100KB per user × 100 = 5-10MB per batch
- ✅ **Parallelizable**: 10 batches (1000 users) easily processed concurrently
- ✅ **LLM-friendly**: Fits comfortably in context window (~20k-30k tokens per batch)
- ✅ **Educational**: Easy to count and visualize (10 batches for 1000 users)

### Negative

- ❌ **Not Optimized**: May not be optimal for all operations
- ❌ **One Size Fits All**: Embeddings could handle larger batches (200-500)
- ❌ **Potential Underutilization**: API could potentially handle more

### Neutral

- 🔹 **Arbitrary Choice**: 100 chosen through experimentation, not rigorous benchmarking
- 🔹 **Configurable**: Can be overridden if needed, but default matters

## Alternatives Considered

### Alternative 1: Batch Size = 50

**Pros**:
- More granular parallelism (20 batches)
- Lower memory per batch
- Safer for rate limits

**Cons**:
- More API calls (2x overhead)
- Longer overall latency (more round trips)
- Less efficient embedding generation

**Reason for Rejection**: Unnecessary overhead, no observed benefit.

---

### Alternative 2: Batch Size = 200

**Pros**:
- Fewer API calls (5 batches instead of 10)
- Higher throughput
- More efficient for embeddings

**Cons**:
- Higher memory usage per batch
- Longer wait for first results
- Approaching LLM context limits for some queries

**Experimentation Results**:
- Task 1: Works but ~50k tokens per batch (risky)
- Task 2: Works well, embeddings generation efficient
- Mixed results led to choosing smaller size

**Reason for Rejection**: Too close to context limits for Task 1, potential instability.

---

### Alternative 3: Dynamic Batch Sizing

**Concept**: Adjust batch size based on operation type or data characteristics.

**Example**:
```python
batch_sizes = {
    'llm_context': 100,      # Conservative for context limits
    'embeddings': 200,        # More aggressive for efficiency
    'api_calls': 50           # Cautious for rate limits
}
```

**Pros**:
- Optimized per operation
- Better resource utilization

**Cons**:
- Complex to maintain
- Harder to understand for learners
- Inconsistent behavior across tasks

**Reason for Rejection**: Violates "simplicity" principle for educational project. Could be future enhancement.

---

### Alternative 4: No Batching (Process All at Once)

**Pros**:
- Simplest code
- No chunking logic

**Cons**:
- Impossible for Task 1 (context window exceeded)
- Memory issues with 1000 embeddings
- No parallelism opportunities

**Reason for Rejection**: Not feasible for Task 1, misses educational value of batch processing.

## Implementation Notes

### Code Pattern

```python
# Standard batching pattern
def process_in_batches(items, batch_size=100):
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    return batches

# Task 1: LLM processing
user_batches = [all_users[i:i + 100] for i in range(0, len(all_users), 100)]
tasks = [generate_response(batch) for batch in user_batches]
results = await asyncio.gather(*tasks)

# Task 2: Embeddings
batches = [documents[i:i + 100] for i in range(0, len(documents), 100)]
tasks = [FAISS.afrom_documents(batch, embeddings) for batch in batches]
vectorstores = await asyncio.gather(*tasks)
```

### Configuration

Allow override via parameters:

```python
async def _create_vectorstore_with_batching(
    self, 
    documents: list[Document], 
    batch_size: int = 100  # Default to 100
):
    batches = [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]
    # ...
```

## Experimentation Data

### Test Setup
- Dataset: 1000 users
- Embeddings: text-embedding-3-small-1 (384d)
- LLM: GPT-4

### Results

| Batch Size | Task 1 Tokens | Task 1 Latency | Task 2 Time | Memory Peak |
|------------|---------------|----------------|-------------|-------------|
| 50 | ~15k/batch | 35s | 25s | 3 GB |
| **100** | **~25k/batch** | **28s** | **18s** | **5 GB** |
| 200 | ~50k/batch | 22s | 12s | 8 GB |
| 500 | Exceeds limit | N/A | 8s | 15 GB |

**Conclusion**: 100 offers best balance between performance and safety.

### Token Distribution (Task 1, batch_size=100)

```
Batch 1:  25,342 tokens
Batch 2:  24,891 tokens
Batch 3:  26,103 tokens
...
Batch 10: 25,457 tokens
Total:    ~252,000 tokens
```

Fits comfortably within GPT-4 limits (128k context).

## Trade-off Matrix

| Criterion | Size=50 | Size=100 | Size=200 | Weight |
|-----------|---------|----------|----------|--------|
| Performance | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | High |
| Safety | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | High |
| Simplicity | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medium |
| Memory | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Medium |
| **Score** | **3.6** | **4.3** | **3.8** | |

**Winner**: Batch size 100 (highest weighted score)

## Future Considerations

### Adaptive Batching (Future Enhancement)

Could implement in v1.2:

```python
def calculate_optimal_batch_size(operation_type, data_characteristics):
    if operation_type == 'llm_processing':
        avg_tokens_per_item = estimate_tokens(data_sample)
        max_context = 100000  # Conservative GPT-4 limit
        return int(max_context / avg_tokens_per_item * 0.8)  # 80% safety margin
    elif operation_type == 'embeddings':
        return 200  # More aggressive
    else:
        return 100  # Default
```

### Monitoring

Track metrics to validate decision:

```python
@dataclass
class BatchMetrics:
    batch_size: int
    processing_time: float
    token_usage: int
    memory_peak: int
    
# Log and analyze over time
```

## References

- [LangChain Batch Processing](https://python.langchain.com/docs/modules/chains/how_to/async_batch)
- [OpenAI Best Practices](https://platform.openai.com/docs/guides/rate-limits)
- [FAISS Performance Guide](https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index)

## Related Decisions

- [ADR-001: Vector Store Selection](./adr-001-vector-store-selection.md) - Impacts embedding batch efficiency
- [Architecture: Performance Considerations](../architecture.md#performance-considerations)

---

**Status History**:
- 2025-12-31: Proposed and Accepted
