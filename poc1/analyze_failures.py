"""
Failure Analysis Script for POC 1 Results

Analyzes DSL→Function mapping errors and categorizes failure patterns.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime


def load_latest_results() -> dict:
    """Load the most recent results file."""
    results_dir = Path(__file__).parent / "results"
    json_files = sorted(results_dir.glob("results_*.json"), reverse=True)
    
    if not json_files:
        raise FileNotFoundError("No results files found")
    
    latest = json_files[0]
    print(f"Loading: {latest}")
    return json.loads(latest.read_text())


def extract_errors(data: dict) -> list[dict]:
    """Extract all error cases from results."""
    errors = []
    for record in data.get("raw", []):
        if record.get("error"):
            errors.append({
                "query_id": record["query_id"],
                "method": record["method"],
                "model": record["model"],
                "error": record["error"],
                "dsl_output": record.get("dsl_output"),
            })
    return errors


def categorize_error(error_msg: str) -> str:
    """Categorize error by pattern."""
    if "could not convert string to float" in error_msg:
        match = re.search(r"float: '([^']+)'", error_msg)
        value = match.group(1) if match else "unknown"
        
        # Categorize by value type
        if value in ("on", "off", "켜", "꺼", "켜줘", "꺼줘"):
            return f"STATE_AS_VALUE: '{value}'"
        elif value in ("어둡게", "밝게", "낮게", "높게"):
            return f"BRIGHTNESS_DESC_AS_VALUE: '{value}'"
        elif value in ("줄여줘", "켜줘", "시켜줘"):
            return f"VERB_AS_VALUE: '{value}'"
        elif value in ("냉방", "난방"):
            return f"MODE_AS_VALUE: '{value}'"
        elif value in ("타이머", "실외", "차이", "온도"):
            return f"NOUN_AS_VALUE: '{value}'"
        elif value in ("current", "low", "outside"):
            return f"ENGLISH_WORD_AS_VALUE: '{value}'"
        elif value in ("energy_saving_mode",):
            return f"COMPOUND_AS_VALUE: '{value}'"
        elif re.match(r"^\d+.*", value):  # Contains numbers
            return f"MIXED_VALUE: '{value}'"
        else:
            return f"OTHER_STRING_AS_VALUE: '{value}'"
    
    elif "Medium DSL 파싱 실패" in error_msg:
        match = re.search(r"verb='([^']+)', target='([^']+)'", error_msg)
        if match:
            return f"UNKNOWN_MAPPING: verb='{match.group(1)}', target='{match.group(2)}'"
        return f"UNKNOWN_MAPPING: {error_msg}"
    
    elif "DSL JSON 파싱 실패" in error_msg:
        return "JSON_PARSE_ERROR"
    
    else:
        return f"OTHER: {error_msg[:50]}"


def analyze_by_query(errors: list[dict], query_map: dict) -> dict:
    """Analyze which queries are most problematic."""
    query_errors = defaultdict(list)
    for err in errors:
        query_errors[err["query_id"]].append(err)
    
    # Get query details
    problematic = []
    for qid, errs in sorted(query_errors.items(), key=lambda x: -len(x[1])):
        query = query_map.get(qid)
        problematic.append({
            "query_id": qid,
            "nl": query.nl if query else "unknown",
            "difficulty": query.difficulty if query else "unknown",
            "error_count": len(errs),
            "errors": errs,
        })
    
    return problematic


def generate_report(data: dict, errors: list[dict]) -> str:
    """Generate a markdown report."""
    from poc1.dataset.queries import QUERY_MAP
    
    total_records = len(data.get("raw", []))
    total_errors = len(errors)
    error_rate = total_errors / total_records * 100 if total_records else 0
    
    # Categorize errors
    categories = Counter(categorize_error(e["error"]) for e in errors)
    
    # By method
    by_method = Counter(e["method"] for e in errors)
    
    # By model
    by_model = Counter(e["model"] for e in errors)
    
    # By query
    query_analysis = analyze_by_query(errors, QUERY_MAP)
    
    report = f"""# POC 1 Failure Analysis Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

| Metric | Value |
|--------|-------|
| Total Records | {total_records} |
| Total Errors | {total_errors} |
| Error Rate | {error_rate:.1f}% |

## Error Categories

| Category | Count | % of Errors |
|----------|-------|-------------|
"""
    
    for cat, count in categories.most_common(20):
        report += f"| {cat} | {count} | {count/total_errors*100:.1f}% |\n"
    
    report += f"""
## Errors by Method

| Method | Errors |
|--------|--------|
"""
    for method, count in by_method.most_common():
        report += f"| {method} | {count} |\n"
    
    report += f"""
## Errors by Model

| Model | Errors |
|-------|--------|
"""
    for model, count in by_model.most_common():
        report += f"| {model} | {count} |\n"
    
    report += f"""
## Top 20 Problematic Queries

| Query ID | NL | Difficulty | Error Count |
|----------|----|------------|-------------|
"""
    for item in query_analysis[:20]:
        report += f"| {item['query_id']} | {item['nl'][:40]} | {item['difficulty']} | {item['error_count']} |\n"
    
    report += """
## Detailed Error Examples

### State Values Passed as 'value' Field (Parser expects number)
"""
    
    state_errors = [e for e in errors if "STATE_AS_VALUE" in categorize_error(e["error"])]
    for e in state_errors[:5]:
        query = QUERY_MAP.get(e["query_id"])
        report += f"\n- **{e['query_id']}** ({e['method']}/{e['model']})\n"
        report += f"  - NL: `{query.nl if query else 'unknown'}`\n"
        report += f"  - Error: {e['error']}\n"
        if e["dsl_output"]:
            report += f"  - DSL: `{json.dumps(e['dsl_output'], ensure_ascii=False)[:100]}`\n"
    
    report += """
### Descriptive Brightness Values
"""
    brightness_errors = [e for e in errors if "BRIGHTNESS_DESC" in categorize_error(e["error"])]
    for e in brightness_errors[:5]:
        query = QUERY_MAP.get(e["query_id"])
        report += f"\n- **{e['query_id']}** ({e['method']}/{e['model']})\n"
        report += f"  - NL: `{query.nl if query else 'unknown'}`\n"
        report += f"  - Error: {e['error']}\n"
        if e["dsl_output"]:
            report += f"  - DSL: `{json.dumps(e['dsl_output'], ensure_ascii=False)[:100]}`\n"
    
    report += """
### Medium DSL Unknown Mappings
"""
    mapping_errors = [e for e in errors if "UNKNOWN_MAPPING" in categorize_error(e["error"])]
    for e in mapping_errors[:5]:
        query = QUERY_MAP.get(e["query_id"])
        report += f"\n- **{e['query_id']}** ({e['method']}/{e['model']})\n"
        report += f"  - NL: `{query.nl if query else 'unknown'}`\n"
        report += f"  - Error: {e['error']}\n"
        if e["dsl_output"]:
            report += f"  - DSL: `{json.dumps(e['dsl_output'], ensure_ascii=False)[:100]}`\n"
    
    return report


def main():
    """Main analysis function."""
    data = load_latest_results()
    errors = extract_errors(data)
    
    if not errors:
        print("No errors found!")
        return
    
    print(f"Found {len(errors)} errors out of {len(data.get('raw', []))} records")
    
    # Generate report
    report = generate_report(data, errors)
    
    # Save report
    results_dir = Path(__file__).parent / "results"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = results_dir / f"failure_analysis_{ts}.md"
    report_path.write_text(report)
    
    print(f"Report saved to: {report_path}")
    print("\n" + "=" * 60)
    print(report[:2000])


if __name__ == "__main__":
    main()
