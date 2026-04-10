"""
POC 2 Quick Test — DSL Parser Test (no API calls)
"""
import sys
sys.path.insert(0, '.')

from poc2.dsl.parser import parse_dsl, parse_wide, parse_medium, parse_narrow
from poc2.dsl.fuzzy_parser import parse_dsl_fuzzy

print("=" * 60)
print("POC 2 DSL Parser Quick Test")
print("=" * 60)

# ── Medium DSL Tests ──────────────────────────────────────────────────────────
print("\n=== Medium DSL Tests ===\n")

medium_tests = [
    # (dsl, expected_function, expected_args_subset)
    ({"verb": "buy", "asset": "BTC", "qty": 0.1, "price_type": "market"},
     "place_order", {"ticker": "BTC", "side": "buy", "qty": 0.1}),
    
    ({"verb": "sell", "asset": "ETH", "qty": 1.0, "price_type": "limit", "price": 3000},
     "place_order", {"ticker": "ETH", "side": "sell", "qty": 1.0, "price": 3000}),
    
    ({"verb": "get_price", "asset": "BTC"},
     "get_price", {"ticker": "BTC"}),
    
    ({"verb": "get_balance", "asset": "ETH"},
     "get_balance", {"asset": "ETH"}),
    
    ({"verb": "set_alert", "asset": "BTC", "trigger_condition": "gte", "trigger_price": 60000},
     "set_alert", {"ticker": "BTC", "condition": "gte", "threshold": 60000}),
    
    ({"verb": "set_condition", "asset": "BTC", "trigger_condition": "gte", "trigger_price": 60000,
      "action_asset": "ETH", "action_side": "sell", "action_qty": 1},
     "set_conditional_order", {"trigger_ticker": "BTC", "trigger_condition": "gte"}),
    
    ({"verb": "cancel", "asset": "BTC", "side_filter": "buy", "order_type_filter": "limit"},
     "cancel_order", {"ticker": "BTC", "side": "buy", "order_type": "limit"}),
]

passed = 0
failed = 0
for dsl, expected_fn, expected_args in medium_tests:
    try:
        result = parse_medium(dsl)
        if result.name == expected_fn:
            match = all(result.arguments.get(k) == v for k, v in expected_args.items())
            if match:
                print(f"✓ {dsl['verb']:15} → {result.name:20} (args OK)")
                passed += 1
            else:
                print(f"✗ {dsl['verb']:15} → {result.name:20} (args mismatch: {result.arguments})")
                failed += 1
        else:
            print(f"✗ {dsl['verb']:15} → {result.name:20} (expected: {expected_fn})")
            failed += 1
    except Exception as e:
        print(f"✗ {dsl['verb']:15} → ERROR: {e}")
        failed += 1

# ── Wide DSL Tests ────────────────────────────────────────────────────────────
print("\n=== Wide DSL Tests ===\n")

wide_tests = [
    ({"intent": "buy", "asset": "BTC", "amount": 0.1},
     "place_order", {"ticker": "BTC", "side": "buy", "qty": 0.1}),
    
    ({"intent": "sell", "asset": "ETH", "amount": 1.0, "price": 3000},
     "place_order", {"ticker": "ETH", "side": "sell", "qty": 1.0}),
    
    ({"intent": "get price", "asset": "BTC"},
     "get_price", {"ticker": "BTC"}),
    
    ({"intent": "check balance", "asset": "ETH"},
     "get_balance", {"asset": "ETH"}),
    
    ({"intent": "set alert", "asset": "BTC", "trigger": "BTC >= 60000"},
     "set_alert", {"ticker": "BTC", "condition": "gte"}),
    
    ({"intent": "conditional sell", "asset": "BTC", "trigger": "BTC >= 60000",
      "target_asset": "ETH", "target_amount": 1},
     "set_conditional_order", {"trigger_ticker": "BTC"}),
    
    ({"intent": "cancel order", "asset": "BTC", "modifiers": ["지정가", "매수"]},
     "cancel_order", {"ticker": "BTC"}),
    
    ({"intent": "portfolio", "asset": "BTC"},
     "get_portfolio", {}),
    
    ({"intent": "get history", "asset": "BTC", "amount": 20},
     "get_order_history", {"ticker": "BTC", "limit": 20}),
]

for dsl, expected_fn, expected_args in wide_tests:
    try:
        result = parse_wide(dsl)
        if result.name == expected_fn:
            match = all(result.arguments.get(k) == v for k, v in expected_args.items())
            if match:
                print(f"✓ {dsl['intent']:20} → {result.name:25} (args OK)")
                passed += 1
            else:
                print(f"✗ {dsl['intent']:20} → {result.name:25} (args mismatch: {result.arguments})")
                failed += 1
        else:
            print(f"✗ {dsl['intent']:20} → {result.name:25} (expected: {expected_fn})")
            failed += 1
    except Exception as e:
        print(f"✗ {dsl['intent']:20} → ERROR: {e}")
        failed += 1

# ── Fuzzy Parser Tests ────────────────────────────────────────────────────────
print("\n=== Fuzzy Parser Tests ===\n")

fuzzy_tests = [
    # Korean verb aliases
    ({"verb": "매수", "asset": "BTC", "qty": 0.1, "price_type": "market"}, "medium", "place_order"),
    ({"verb": "매도", "asset": "ETH", "qty": 1.0}, "medium", "place_order"),
    
    # Korean ticker aliases
    ({"intent": "buy", "asset": "비트코인", "amount": 0.1}, "wide", "place_order"),
    ({"intent": "sell", "asset": "이더리움", "amount": 1.0}, "wide", "place_order"),
    
    # Condition aliases
    ({"intent": "set alert", "asset": "BTC", "trigger": "BTC 60000 이상"}, "wide", "set_alert"),
]

for dsl, width, expected_fn in fuzzy_tests:
    try:
        result, rules = parse_dsl_fuzzy(dsl, width)
        if result.name == expected_fn:
            rule_info = f" [rules: {len(rules)}]" if rules else ""
            print(f"✓ {str(dsl['verb'] if 'verb' in dsl else dsl['intent']):15} → {result.name:25}{rule_info}")
            passed += 1
        else:
            print(f"✗ {str(dsl['verb'] if 'verb' in dsl else dsl['intent']):15} → {result.name:25} (expected: {expected_fn})")
            failed += 1
    except Exception as e:
        print(f"✗ {str(dsl['verb'] if 'verb' in dsl else dsl['intent']):15} → ERROR: {e}")
        failed += 1

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"Summary: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
else:
    print("\n✓ All tests passed! POC 2 DSL parser is ready.")
    print("\nTo run full experiment:")
    print("  python -m poc2.main --smoke")
    print("\nTo run full experiment:")
    print("  python -m poc2.main")
