# Project Context: Agent Basic

## Project Overview

This is a **Python research project** focused on developing a **reflexive language model** system for efficient natural language to function call pipelines. The project explores an alternative approach to large language models by implementing a **NL → DSL → Function Call** architecture aimed at maximizing efficiency and reducing costs.

### Core Research Concept

The project investigates whether using an intermediate **Domain-Specific Language (DSL)** layer between natural language and function calls provides better accuracy and efficiency compared to direct **NL → Function Call** mapping. The research is driven by the vision of creating a "vibe operation system" where language models act as NL→DSL transformers for automated operations.

### Key Research Questions

1. Does NL→DSL→FunctionCall provide better accuracy than NL→FunctionCall directly?
2. Can DSL schemas be automatically generated from function specifications?
3. Can models be efficiently fine-tuned for DSL generation tasks?

## Project Structure

```
agent-basic/
├── poc1/                          # Proof of Concept 1 - Smart Home NL→DSL→Function
│   ├── config.py                  # Experiment configuration
│   ├── models.py                  # Common type definitions (renamed from types.py)
│   ├── main.py                    # CLI entry point for experiments
│   ├── analyze_failures.py        # Failure analysis script
│   ├── FAILURE_ANALYSIS.md        # Detailed failure analysis report
│   ├── dataset/
│   │   ├── functions.py           # Home automation function specs (8 functions)
│   │   └── queries.py             # NL query dataset with ground truth
│   ├── dsl/
│   │   ├── schemas/               # DSL schema definitions (narrow/medium/wide)
│   │   └── parser.py              # Deterministic DSL→Function parsers (hardened)
│   ├── methods/
│   │   ├── method_a.py            # Direct NL→Function approach
│   │   └── method_b.py            # NL→DSL→Function approach
│   ├── eval/
│   │   ├── metrics.py             # Evaluation metrics (EM, argument match, etc.)
│   │   └── runner.py              # Experiment runner
│   └── results/                   # Experiment output (JSON + MD reports)
├── poc2/                          # Proof of Concept 2 - Crypto Trading NL→DSL→Function
│   ├── config.py                  # DashScope API config
│   ├── models.py                  # Type definitions
│   ├── main.py                    # CLI entry point (IMPLEMENTED)
│   ├── test_parsers.py            # Parser validation tests
│   ├── IMPLEMENTATION.md          # POC 2 implementation guide
│   ├── dataset/
│   │   ├── functions.py           # Crypto trading function specs (9 functions)
│   │   └── queries.py             # 100 NL queries (s33/m33/c34)
│   ├── dsl/
│   │   ├── schemas/               # narrow/medium/wide JSON schemas
│   │   ├── parser.py              # Deterministic parsers with ticker/condition maps
│   │   ├── fuzzy_parser.py        # Grammar extension fallback layer
│   │   └── grammar_extensions.json # 50+ alias rules (Korean/English)
│   ├── methods/
│   │   ├── method_a.py            # Direct FC via tool_calling
│   │   └── method_b.py            # NL→DSL→FC via json_schema
│   ├── eval/
│   │   ├── metrics.py             # EM with 0.1% price tolerance
│   │   └── runner.py              # Async experiment runner
│   └── results/                   # Experiment output
├── dashscope_client.py            # DashScope API client for MAF framework
├── devui-main.py                  # DevUI server with multiple agents
├── nurse_schedule_restorer.py     # Nurse schedule image restoration pipeline
└── research_plan.md               # Research vision and business plan
```

## Technologies & Dependencies

- **Python 3.10+** with async/await patterns
- **DashScope API** - Alibaba Cloud LLM API (qwen-vl-ocr, qwen3.6-plus, qwen-turbo, etc.)
- **OpenAI-compatible client** - For models supporting OpenAI API format
- **agent_framework** - Microsoft Agent Framework (MAF) for agent architecture
- **python-dotenv** - Environment variable management

## Building and Running

### Prerequisites

1. Set environment variables:
   ```bash
   export DASHSCOPE_API_KEY=your_api_key
   export OPENAI_API_KEY=your_api_key
   export OPENAI_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
   ```

### Running POC 1 Experiments

```bash
# Full experiment (all models × all methods)
python -m poc1.main

# Quick smoke test
python -m poc1.main --smoke

# Specific model only
python -m poc1.main --model qwen-turbo --model qwen-plus

# Method A only (direct NL→Function)
python -m poc1.main --method a

# Method B only (NL→DSL→Function) with specific DSL width
python -m poc1.main --method b --width medium
```

### Running DevUI Server

```bash
python devui-main.py
# Opens http://localhost:8080
```

The DevUI provides three agents:
- **DemoAgent** - General-purpose assistant using qwen3.6-plus
- **OCRAgent** - Image text extraction using qwen-vl-ocr
- **NurseScheduleAgent** - Nurse schedule image restoration pipeline

## Development Conventions

### Code Style

- **Type hints** - Extensive use of Python type annotations
- **Dataclasses** - For structured data representation
- **Async-first** - All I/O operations use async/await
- **Korean comments** - Internal documentation uses Korean

### Testing Practices

- Experiments use **exact match (EM)** rate as primary metric
- **Argument match ratio** for partial credit evaluation
- Results saved as JSON in `poc1/results/`

### Key Architectural Patterns

1. **Two-Method Comparison**:
   - **Method A**: Direct NL → Function Call
   - **Method B**: NL → DSL → Function Call (with narrow/medium/wide DSL variants)

2. **DSL Width Variants**:
   - **Narrow**: `{"function": "<name>", "args": {...}}`
   - **Medium**: `{"verb": ..., "target": ..., "location": ..., "params": {...}}`
   - **Wide**: `{"intent": ..., "subject": ..., "modifiers": [...]}`

3. **Nurse Schedule Pipeline** (2-stage):
   - **Step 1**: qwen-vl-ocr with `table_parsing` → HTML tables (parallel)
   - **Step 2**: qwen3.6-plus → OCR correction + table merging + change report

## Key Files Reference

| File | Purpose |
|------|---------|
| `poc1/config.py` | Experiment configuration, API settings, model list |
| `poc1/models.py` | Dataclasses: FunctionSpec, NLQuery, MethodResult, EvalResult |
| `poc1/dsl/parser.py` | Deterministic DSL→Function parsers (hardened with safe type conversion) |
| `poc1/dataset/functions.py` | 8 home automation function specifications |
| `poc1/dataset/queries.py` | 100 NL queries (simple/medium/complex) with ground truth |
| `poc1/FAILURE_ANALYSIS.md` | Detailed error analysis and parser hardening report |
| `poc2/config.py` | POC 2 experiment configuration |
| `poc2/main.py` | POC 2 CLI entry point |
| `poc2/test_parsers.py` | POC 2 parser validation tests (21 tests) |
| `poc2/dsl/parser.py` | Crypto DSL parsers with 50+ ticker/condition aliases |
| `poc2/dsl/grammar_extensions.json` | Fallback grammar rules for fuzzy parsing |
| `poc2/dataset/functions.py` | 9 crypto trading functions |
| `poc2/dataset/queries.py` | 100 crypto trading NL queries |
| `poc2/IMPLEMENTATION.md` | POC 2 implementation guide and usage |
| `devui-main.py` | Multi-agent DevUI server configuration |
| `nurse_schedule_restorer.py` | Image-to-table restoration pipeline |
| `research_plan.md` | Research vision, business considerations, POC plans |

## POC 1 Results Summary

### Latest Experiment (results_20260410_125622)
- **Total API calls**: 900
- **Models tested**: qwen-turbo, qwen-plus, qwen-max
- **Methods**: Direct FC (A), DSL medium/wide (B)

### Key Findings
| Metric | Method A (Direct) | Method B (DSL) |
|--------|------------------|----------------|
| **Accuracy (EM%)** | 61.0% | 37.5% |
| **Avg Tokens** | 1319 | 367 |
| **Token Savings** | - | ~72% reduction |
| **Error Rate** | 0.7% | 7.8% |

### Parser Hardening (April 2026)
- **Issue**: 49 errors (5.4%) from string-to-float conversion failures
- **Fix**: Added `_VALUE_STATE_MAP` and `_safe_float()` for robust type conversion
- **Test coverage**: 11/11 parser tests passing
- **Expected improvement**: 75-85% error reduction

### Research Conclusion
- **Accuracy**: Direct FC outperforms DSL by ~23 percentage points
- **Cost**: DSL provides 72% token reduction (3-4x cost savings)
- **Recommendation**: Hybrid approach or fine-tuned small model for DSL

## POC 2 Implementation Status

### Domain: Crypto Trading (9 functions)
- `place_order` - Market/limit buy/sell orders
- `cancel_order` - Cancel by ID or filters
- `get_price` - Current price lookup
- `get_balance` - Balance inquiry
- `get_portfolio` - Full portfolio view
- `set_alert` - Price alerts
- `set_conditional_order` - Conditional/cross-asset orders
- `get_market_info` - Market data (24h volume, etc.)
- `get_order_history` - Order history

### Parser Features
- **20+ ticker aliases**: 비트코인→BTC, 이더리움→ETH, etc.
- **30+ condition aliases**: 이상/넘으면→gte, 이하/내려오면→lte
- **Order type aliases**: 시장가→market, 지정가→limit, 손절→stop_loss

### Test Results
- **Parser tests**: 21/21 passed ✓
- **Ready for experiment**: Yes

### Running POC 2
```bash
# Parser tests
python poc2/test_parsers.py

# Smoke test (10 queries)
python -m poc2.main --smoke

# Full experiment (100 queries, ~900 API calls)
python -m poc2.main
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DASHSCOPE_API_KEY` | DashScope API key |
| `OPENAI_API_KEY` | OpenAI-compatible API key (can use DashScope) |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint URL |

## Models Used

- **qwen-vl-ocr** - OCR with table_parsing capability
- **qwen3.6-plus** - LLM for text correction and merging
- **qwen-turbo, qwen-plus, qwen-max** - POC1 experiment models
