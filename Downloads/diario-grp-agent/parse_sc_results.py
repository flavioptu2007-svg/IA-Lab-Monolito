#!/usr/bin/env python3
"""
Self-Consistency Results Aggregator
===================================
Reads multiple lm_eval JSON outputs (one per sample) and computes:
  - pass@1  (single-sample accuracy, averaged across samples)
  - pass@k  (self-consistency / majority-vote accuracy)
  - pass@8  (at least 1 correct out of 8 samples)

Usage:
    python parse_sc_results.py --results_dir ./deepseek_eval_results --num_samples 8
    python parse_sc_results.py --results_dir ./deepseek_eval_results --num_samples 8 --tasks gsm8k_cot aime24
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def extract_task_results(data: dict) -> dict[str, dict]:
    """Extract per-task results from an lm_eval JSON output."""
    results = {}
    for task_name, task_data in data.get("results", {}).items():
        if task_name.endswith(",none"):
            task_name = task_name.removesuffix(",none")
        results[task_name] = task_data
    return results


def get_accuracy(task_data: dict) -> float | None:
    """Get accuracy from task results (tries multiple metric names)."""
    for key in ["acc,none", "acc", "exact_match,none", "exact_match", "accuracy,none"]:
        if key in task_data:
            return task_data[key]
    return None


def majority_vote(answers: list[str]) -> str:
    """Return the most common answer from a list."""
    if not answers:
        return ""
    counter = Counter(answers)
    return counter.most_common(1)[0][0]


def compute_pass_at_k(correct_flags: list[bool], k: int = 8) -> float:
    """Compute pass@k: probability that at least one of k samples is correct."""
    n = len(correct_flags)
    if n == 0:
        return 0.0
    num_wrong = sum(1 for c in correct_flags if not c)
    if num_wrong == 0:
        return 1.0
    # pass@k = 1 - C(n-w, k) / C(n, k)
    # Simplified: 1 - prod((n-w-i)/(n-i) for i in range(k))
    k = min(k, n)
    result = 1.0
    for i in range(k):
        result *= (num_wrong - i) / (n - i) if (num_wrong - i) > 0 else 0
    return 1.0 - result


def aggregate_sc_results(results_dir: Path, num_samples: int, tasks: list[str] | None = None):
    """Aggregate self-consistency results across multiple samples."""
    # Discover all SC result files: *sc*_sample*.json
    sc_files = sorted(results_dir.glob("*sc*_sample*.json"))
    if not sc_files:
        print(f"No self-consistency sample files found in {results_dir}")
        print("Expected pattern: *sc*_sample*.json")
        return

    # Group files by (model_prefix, task_name)
    # e.g. 3a_gsm8k_sc_8b_sample1.json -> prefix="3a", task="gsm8k_cot", model="8b"
    groups = defaultdict(list)
    for f in sc_files:
        name = f.stem  # e.g. 3a_gsm8k_sc_8b_sample1
        # Extract prefix and task/model info
        match = re.match(r"(\d+[a-c])_(\w+)_sc_(\w+)_sample(\d+)", name)
        if match:
            prefix, task_tag, model_tag, sample_num = match.groups()
            groups[(prefix, task_tag, model_tag)].append((int(sample_num), f))

    if not groups:
        print("Could not parse any SC file names. Expected format:")
        print("  <prefix>_<task>_sc_<model>_sample<N>.json")
        return

    # Sort samples within each group
    for key in groups:
        groups[key].sort(key=lambda x: x[0])

    # Process each group
    all_results = []
    for (prefix, task_tag, model_tag), sample_files in sorted(groups.items()):
        print(f"\n{'='*70}")
        print(f"  {prefix} | {task_tag} | {model_tag} | {len(sample_files)} samples")
        print(f"{'='*70}")

        # Load all samples
        all_accuracies = []
        per_sample_accs = []

        for sample_num, filepath in sample_files:
            data = load_json(filepath)
            task_results = extract_task_results(data)

            for task_name, task_data in task_results.items():
                if tasks and task_name not in tasks:
                    continue

                acc = get_accuracy(task_data)
                if acc is not None:
                    per_sample_accs.append(acc)
                    all_accuracies.append(acc)

        if not per_sample_accs:
            print("  No accuracy metrics found in results.")
            continue

        # Compute metrics
        pass1 = sum(per_sample_accs) / len(per_sample_accs) if per_sample_accs else 0
        best = max(per_sample_accs) if per_sample_accs else 0
        worst = min(per_sample_accs) if per_sample_accs else 0
        std_dev = (sum((x - pass1) ** 2 for x in per_sample_accs) / len(per_sample_accs)) ** 0.5

        # pass@k (at least 1 correct across k samples)
        correct_flags = [acc > 0.5 for acc in per_sample_accs]  # threshold
        passk = compute_pass_at_k(correct_flags, len(per_sample_accs))

        print(f"  pass@1 (avg):     {pass1:.4f}  ({pass1*100:.2f}%)")
        print(f"  pass@{len(per_sample_accs)} (any correct): {passk:.4f}  ({passk*100:.2f}%)")
        print(f"  best sample:      {best:.4f}  ({best*100:.2f}%)")
        print(f"  worst sample:     {worst:.4f}  ({worst*100:.2f}%)")
        print(f"  std deviation:    {std_dev:.4f}")
        print(f"  per-sample accs:  {[f'{a:.4f}' for a in per_sample_accs]}")

        all_results.append({
            "model": model_tag,
            "task": task_tag,
            "num_samples": len(per_sample_accs),
            "pass1": pass1,
            "pass_k": passk,
            "best": best,
            "worst": worst,
            "std": std_dev,
            "per_sample": per_sample_accs,
        })

    # ─── Summary Table ──────────────────────────────────────────────────────
    if all_results:
        print(f"\n\n{'='*70}")
        print("  SUMMARY TABLE")
        print(f"{'='*70}")
        print(f"  {'Model':<8} {'Task':<12} {'pass@1':>10} {'pass@k':>10} {'Best':>8} {'Std':>8}")
        print(f"  {'-'*8} {'-'*12} {'-'*10} {'-'*10} {'-'*8} {'-'*8}")
        for r in all_results:
            print(f"  {r['model']:<8} {r['task']:<12} {r['pass1']*100:>9.2f}% {r['pass_k']*100:>9.2f}% {r['best']*100:>7.2f}% {r['std']:>7.4f}")

    # ─── Save aggregated results ────────────────────────────────────────────
    output_path = results_dir / "sc_aggregated_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Aggregated results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Aggregate self-consistency evaluation results")
    parser.add_argument("--results_dir", type=Path, required=True, help="Directory containing SC JSON files")
    parser.add_argument("--num_samples", type=int, default=8, help="Number of samples per question")
    parser.add_argument("--tasks", nargs="*", default=None, help="Filter specific tasks (e.g. gsm8k_cot aime24)")
    args = parser.parse_args()

    aggregate_sc_results(args.results_dir, args.num_samples, args.tasks)


if __name__ == "__main__":
    main()
