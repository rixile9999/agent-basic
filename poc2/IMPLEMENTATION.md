# POC 2 Implementation Complete

## Overview

POC 2 extends the POC 1 framework to the **crypto trading domain**, testing whether NL→DSL→Function Call provides better accuracy and efficiency for financial commands.

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| `config.py` | ✅ Complete | DashScope API config |
| `models.py` | ✅ Complete | Dataclasses for types |
| `dataset/functions.py` | ✅ Complete | 9 trading functions |
| `dataset/queries.py` | ✅ Complete | 100 NL queries (s33/m33/c34) |
| `dsl/schemas/narrow.json` | ✅ Complete | Function-name matching |
| `dsl/schemas/medium.json` | ✅ Complete | Verb-based DSL |
| `dsl/schemas/wide.json` | ✅ Complete | Intent-based DSL |
| `dsl/parser.py` | ✅ Complete | Deterministic parsers |
| `dsl/fuzzy_parser.py` | ✅ Complete | Grammar extension layer |
| `dsl/grammar_extensions.json` | ✅ Complete | 50+ alias rules |
| `methods/method_a.py` | ✅ Complete | Direct FC |
| `methods/method_b.py` | ✅ Complete | NL→DSL→FC |
| `eval/metrics.py` | ✅ Complete | EM, arg match, aggregation |
| `eval/runner.py` | ✅ Complete | Async experiment runner |
| **`main.py`** | ✅ **Complete** | CLI entry point |
| **`test_parsers.py`** | ✅ **Complete** | Parser validation |

## Key Differences from POC 1

### Domain Change
| POC 1 | POC 2 |
|-------|-------|
| Smart Home (8 functions) | Crypto Trading (9 functions) |
| Light, temperature, scene | Place order, cancel, alert |
| Simple state values | Numeric prices, quantities |
| Korean/English room names | Korean/English coin names |

### Function Specifications

```python
place_order(ticker, side, qty, order_type, price?)
cancel_order(order_id?, ticker?, side?, order_type?)
get_price(ticker)
get_balance(asset?)
get_portfolio()
set_alert(ticker, condition, threshold)
set_conditional_order(trigger_ticker, trigger_condition, trigger_price,
                      action_ticker, action_side, action_qty, action_order_type)
get_market_info(ticker)
get_order_history(ticker?, limit)
```

### Parser Enhancements

1. **Ticker normalization**: 20+ Korean/English coin name aliases
   - "비트코인" → "BTC", "이더리움" → "ETH"
   
2. **Condition normalization**: 30+ trigger condition aliases
   - "이상", "넘으면", "돌파" → "gte"
   - "이하", "내려오면", "떨어지면" → "lte"

3. **Order type aliases**: Korean trading terms
   - "시장가", "즉시" → "market"
   - "지정가" → "limit"
   - "손절" → "stop_loss", "익절" → "take_profit"

4. **Grammar extension layer**: Fallback parsing with automatic alias application

## Test Results

**Parser Tests**: 21/21 passed ✓

```
=== Medium DSL Tests ===
7/7 passed - All verb-based mappings work correctly

=== Wide DSL Tests ===
9/9 passed - Intent-based parsing works

=== Fuzzy Parser Tests ===
5/5 passed - Korean aliases applied automatically
```

## Usage

### Run Parser Tests
```bash
python poc2/test_parsers.py
```

### Run Smoke Test (10 queries)
```bash
export DASHSCOPE_API_KEY=your_key
python -m poc2.main --smoke
```

### Run Full Experiment (100 queries)
```bash
python -m poc2.main
# ~900 API calls (3 models × 3 methods × 100 queries)
```

### Run Specific Configuration
```bash
# Method A only (direct FC)
python -m poc2.main --method a

# Method B with medium DSL only
python -m poc2.main --method b --width medium

# Specific models
python -m poc2.main --model qwen-turbo --model qwen-plus
```

## Query Dataset Structure

### Simple (33 queries)
- `get_price`: s01-s10 (10 queries)
- `place_order` market: s11-s17 (7 queries)
- `get_balance`: s18-s22 (5 queries)
- `get_portfolio`: s23-s25 (3 queries)
- `get_order_history`: s26-s28 (3 queries)
- `get_market_info`: s29-s30 (2 queries)
- `cancel_order` by ID: s31-s32 (2 queries)
- Additional: s33 (1 query)

### Medium (33 queries)
- Limit orders with specific prices
- Alert configurations
- Simple conditional orders (same coin)
- Partial cancellations

### Complex (34 queries)
- Cross-asset conditional orders
- Complex cancellation filters
- Portfolio-level queries
- Multi-condition triggers

## Expected Outcomes

Based on POC 1 results:

| Metric | Method A (Direct) | Method B (DSL) |
|--------|------------------|----------------|
| **Accuracy (EM%)** | 60-65% | 35-45% |
| **Avg Tokens** | ~1300 | ~350 |
| **Token Savings** | - | ~73% reduction |
| **Error Rate** | <1% | 5-10% (before grammar) |

**Hypothesis**: Crypto domain has more precise terminology than smart home, which may improve DSL accuracy.

## Next Steps

1. **Run smoke test** to verify end-to-end flow
2. **Run full experiment** to collect baseline data
3. **Analyze errors** and update grammar extensions
4. **Iterate** on grammar rules to reduce error rate
5. **Compare** with POC 1 results to validate domain differences

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `poc2/main.py` | Created | CLI entry point |
| `poc2/test_parsers.py` | Created | Parser validation |
| `poc2/dsl/grammar_extensions.json` | Populated | 50+ alias rules |
| `poc2/IMPLEMENTATION.md` | Created | This document |

## Implementation Notes

### Design Decisions

1. **Flat structure for conditional orders**: Unlike nested JSON, we use flat fields (`trigger_ticker`, `action_ticker`) for simpler parsing.

2. **Korean terminology**: All Korean trading terms are supported (비트코인, 시장가, 지정가, etc.).

3. **Numeric tolerance**: Price matching allows 0.1% tolerance for floating-point variations.

4. **Grammar-first approach**: The `grammar_extensions.json` allows iterative improvement without code changes.

### Known Limitations

1. **Cross-asset detection**: Wide DSL relies on `target_asset` field presence to distinguish alerts from conditional orders.

2. **Cancel order ambiguity**: "BTC 주문 취소" could mean cancel all BTC orders or a specific order.

3. **Trigger parsing**: Wide DSL trigger string parsing ("BTC >= 60000") is regex-based and may fail on unusual formats.

### Future Enhancements

1. **Add narrow DSL tests** to test suite
2. **Implement trigger string parser** with more robust regex
3. **Add validation layer** for DSL schemas before parsing
4. **Create error analysis script** similar to POC 1
