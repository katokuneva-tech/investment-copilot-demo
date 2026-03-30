"""Evaluation framework for Investment Intelligence Copilot.

Usage:
    cd backend
    source .venv/bin/activate
    python -m evals.run_evals [--keyword-only] [--test-id TEST_ID]
"""
import asyncio
import json
import sys
import time
from pathlib import Path

# Add parent to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import skill_router
from app.services.llm_client import llm_client


TEST_CASES_PATH = Path(__file__).parent / "test_cases.json"

JUDGE_PROMPT = """Ты — судья качества ответов AI-аналитика.

Оцени ответ по критерию. Верни:
- PASS — если ответ соответствует критерию
- FAIL: [причина] — если не соответствует

Будь строг, но справедлив. Небольшие отклонения в цифрах допустимы (±5%)."""


async def run_single_eval(test_case: dict, keyword_only: bool = False) -> dict:
    """Run a single evaluation test case."""
    test_id = test_case["id"]
    skill_id = test_case["skill_id"]
    message = test_case["message"]
    expected = test_case.get("expected_contains", [])
    eval_prompt = test_case.get("eval_prompt", "")
    history = test_case.get("history")

    start = time.time()
    try:
        response = await skill_router.route(
            skill_id, message, f"eval_{test_id}",
            history=history
        )
        elapsed = time.time() - start

        # Extract text from response
        text_parts = []
        for b in response.blocks:
            if b.type == "text":
                text_parts.append(str(b.data))
        full_text = " ".join(text_parts)

        # 1. Keyword check
        keyword_results = {}
        for kw in expected:
            keyword_results[kw] = kw.lower() in full_text.lower()
        keyword_pass = all(keyword_results.values()) if keyword_results else True

        # 2. LLM-as-judge (skip if keyword_only)
        judge_pass = True
        judge_detail = "Skipped"
        if not keyword_only and eval_prompt:
            try:
                judge_result = await llm_client.chat(
                    system=JUDGE_PROMPT,
                    messages=[{
                        "role": "user",
                        "content": f"Критерий оценки: {eval_prompt}\n\nОтвет AI-аналитика:\n{full_text[:3000]}"
                    }],
                    temperature=0.0,
                )
                judge_pass = judge_result.strip().upper().startswith("PASS")
                judge_detail = judge_result.strip()
            except Exception as e:
                judge_detail = f"Judge error: {e}"

        overall_pass = keyword_pass and judge_pass

        return {
            "id": test_id,
            "skill_id": skill_id,
            "passed": overall_pass,
            "keyword_pass": keyword_pass,
            "keyword_results": keyword_results,
            "judge_pass": judge_pass,
            "judge_detail": judge_detail[:200],
            "elapsed_sec": round(elapsed, 1),
            "response_length": len(full_text),
        }
    except Exception as e:
        return {
            "id": test_id,
            "skill_id": skill_id,
            "passed": False,
            "error": str(e),
            "elapsed_sec": round(time.time() - start, 1),
        }


async def run_all_evals(keyword_only: bool = False, test_id: str | None = None):
    """Run all evaluations and print results."""
    test_cases = json.loads(TEST_CASES_PATH.read_text("utf-8"))

    if test_id:
        test_cases = [t for t in test_cases if t["id"] == test_id]
        if not test_cases:
            print(f"Test case '{test_id}' not found.")
            return

    print(f"\n{'='*60}")
    print(f"Investment Intelligence Copilot — Evaluation")
    print(f"{'='*60}")
    print(f"Test cases: {len(test_cases)}")
    print(f"Mode: {'keyword-only' if keyword_only else 'keyword + LLM-judge'}")
    print(f"{'='*60}\n")

    results = []
    passed = 0
    failed = 0

    for i, tc in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] {tc['id']}: {tc['message'][:50]}...", end=" ", flush=True)
        result = await run_single_eval(tc, keyword_only)
        results.append(result)

        if result["passed"]:
            passed += 1
            print(f"✅ PASS ({result.get('elapsed_sec', 0)}s)")
        else:
            failed += 1
            detail = result.get("judge_detail", result.get("error", ""))[:80]
            kw = result.get("keyword_results", {})
            failed_kw = [k for k, v in kw.items() if not v]
            if failed_kw:
                print(f"❌ FAIL — missing keywords: {failed_kw}")
            else:
                print(f"❌ FAIL — {detail}")

    # Summary
    total = passed + failed
    rate = (passed / total * 100) if total > 0 else 0
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} passed ({rate:.0f}%)")
    print(f"{'='*60}")

    if rate >= 80:
        print("✅ Quality threshold MET (≥80%)")
    else:
        print("❌ Quality threshold NOT MET (<80%)")

    # Save results
    results_path = Path(__file__).parent / "results.json"
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), "utf-8")
    print(f"\nDetailed results saved to: {results_path}")


if __name__ == "__main__":
    keyword_only = "--keyword-only" in sys.argv
    test_id = None
    for arg in sys.argv[1:]:
        if arg.startswith("--test-id="):
            test_id = arg.split("=")[1]
        elif not arg.startswith("--"):
            test_id = arg

    asyncio.run(run_all_evals(keyword_only=keyword_only, test_id=test_id))
