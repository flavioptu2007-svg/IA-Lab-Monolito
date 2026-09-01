#!/usr/bin/env bash
# =============================================================================
# Quick Multi-Model Comparison via OpenRouter
# =============================================================================
# Lightweight runner — only Part 4 from run_deepseek_eval.sh
# Compares models on GSM8K CoT, GPQA Diamond CoT, and AIME 2024.
#
# Usage:
#   export OPENROUTER_API_KEY="your_key"   # or OPENAI_API_KEY
#   ./run_quick_compare.sh                  # all 15 models
#   ./run_quick_compare.sh --free-only      # free models only
#   ./run_quick_compare.sh --models r1,llama4_mav,qwen3_32b  # specific models
#   ./run_quick_compare.sh --limit 5        # 5 questions per task (fast test)
#   ./run_quick_compare.sh --tasks gsm8k_cot  # single task
# =============================================================================

set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────
OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-${OPENAI_API_KEY:-}}"
if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "ERROR: Set OPENROUTER_API_KEY or OPENAI_API_KEY"
  exit 1
fi
export OPENAI_API_KEY="$OPENROUTER_API_KEY"

API_BASE="https://openrouter.ai/api/v1"
LIMIT="${LIMIT:-10}"
TASKS="${TASKS:-gsm8k_cot gpqa_diamond_cot_zeroshot aime24}"
RESULTS_DIR="./compare_results"
SELECTED_MODELS=""

# ─── Parse args ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --limit)      LIMIT="$2"; shift 2 ;;
    --tasks)      TASKS="$2"; shift 2 ;;
    --models)     SELECTED_MODELS="$2"; shift 2 ;;
    --free-only)  SELECTED_MODELS="nemotron_ultra,nemotron_super,nemotron_light,gemma4_31b,minimax_m3"; shift ;;
    --output)     RESULTS_DIR="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: ./run_quick_compare.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --limit N           Questions per task (default: 10)"
      echo "  --tasks 't1 t2'     Space-separated task list"
      echo "  --models 'm1,m2'    Comma-separated model keys"
      echo "  --free-only         Only run free models"
      echo "  --output DIR        Results directory"
      echo ""
      echo "Available model keys:"
      echo "  r1, r1_0528, llama4_mav, llama4_sct, llama33_70b,"
      echo "  qwen3_32b, qwen3_235b, qwen3_think,"
      echo "  gemini25_flash, gemini25_pro,"
      echo "  nemotron_ultra, nemotron_super, nemotron_light,"
      echo "  gemma4_31b, minimax_m3"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$RESULTS_DIR/compare_log_${TIMESTAMP}.txt"

# ─── Helpers ─────────────────────────────────────────────────────────────────
log() { echo -e "\n══════════════════════════════════════════════════════════════"; echo "[$(date '+%H:%M:%S')] $1"; echo "══════════════════════════════════════════════════════════════"; }
run() { echo "+ $*"; "$@" 2>&1 | tee -a "$LOG_FILE"; }

# ─── Model Registry ─────────────────────────────────────────────────────────
declare -A MODELS=(
  [r1]="deepseek/deepseek-r1"
  [r1_0528]="deepseek/deepseek-r1-0528"
  [llama4_mav]="meta-llama/llama-4-maverick"
  [llama4_sct]="meta-llama/llama-4-scout"
  [llama33_70b]="meta-llama/llama-3.3-70b-instruct"
  [qwen3_32b]="qwen/qwen3-32b"
  [qwen3_235b]="qwen/qwen3-235b-a22b"
  [qwen3_think]="qwen/qwen3-235b-a22b-thinking-2507"
  [gemini25_flash]="google/gemini-2.5-flash"
  [gemini25_pro]="google/gemini-2.5-pro"
  [nemotron_ultra]="nvidia/nemotron-3-ultra-550b-a55b:free"
  [nemotron_super]="nvidia/nemotron-3-super-120b-a12b:free"
  [nemotron_light]="nvidia/nemotron-3.5-lightning:free"
  [gemma4_31b]="google/gemma-4-31b-it:free"
  [minimax_m3]="minimax/minimax-m3:free"
)

# ─── Select models ──────────────────────────────────────────────────────────
if [ -n "$SELECTED_MODELS" ]; then
  IFS=',' read -ra MODEL_KEYS <<< "$SELECTED_MODELS"
else
  mapfile -t MODEL_KEYS < <(echo "${!MODELS[@]}" | tr ' ' '\n' | sort)
fi

# ─── Preflight ──────────────────────────────────────────────────────────────
log "Quick Multi-Model Comparison"
echo "Models:  ${MODEL_KEYS[*]}"
echo "Tasks:   $TASKS"
echo "Limit:   $LIMIT questions per task"
echo "Output:  $RESULTS_DIR/"
echo "Log:     $LOG_FILE"
echo ""

if ! command -v lm_eval &>/dev/null; then
  echo "ERROR: lm_eval not found. Install: pip install lm-eval[openai]"
  exit 1
fi

# ─── Run ────────────────────────────────────────────────────────────────────
TOTAL_RUNS=$(( ${#MODEL_KEYS[@]} * $(echo $TASKS | wc -w) ))
RUN_COUNT=0

for key in "${MODEL_KEYS[@]}"; do
  slug="${MODELS[$key]}"
  if [ -z "$slug" ]; then
    echo "WARNING: Unknown model key '$key', skipping"
    continue
  fi

  for task in $TASKS; do
    RUN_COUNT=$((RUN_COUNT + 1))
    log "[${RUN_COUNT}/${TOTAL_RUNS}] ${slug} | ${task}"

    run lm_eval --model local-chat-completions \
      --model_args model=${slug},base_url=${API_BASE},timeout=900 \
      --tasks "$task" \
      --gen_kwargs max_gen_toks=4096,temperature=0.6 \
      --batch_size 1 \
      --limit "$LIMIT" \
      --output_path "$RESULTS_DIR/${key}_${task}.json"
  done
done

# ─── Summary ────────────────────────────────────────────────────────────────
log "COMPARISON COMPLETE"
echo ""
echo "Results: $RESULTS_DIR/"
echo ""

# Print quick accuracy summary
echo "┌─────────────────────┬────────────┬──────────┬──────────┐"
echo "│ Model               │ GSM8K CoT  │ GPQA     │ AIME 24  │"
echo "├─────────────────────┼────────────┼──────────┼──────────┤"

for key in "${MODEL_KEYS[@]}"; do
  gsm=$(python3 -c "
import json, sys
try:
  d=json.load(open('$RESULTS_DIR/${key}_gsm8k_cot.json'))
  acc=d.get('results',{}).get('gsm8k_cot,none',{}).get('acc,none',0)
  print(f'{acc*100:.1f}%')
except: print('  N/A')
" 2>/dev/null)
  gpqa=$(python3 -c "
import json, sys
try:
  d=json.load(open('$RESULTS_DIR/${key}_gpqa_diamond_cot_zeroshot.json'))
  acc=d.get('results',{}).get('gpqa_diamond_cot_zeroshot,none',{}).get('acc,none',0)
  print(f'{acc*100:.1f}%')
except: print('  N/A')
" 2>/dev/null)
  aime=$(python3 -c "
import json, sys
try:
  d=json.load(open('$RESULTS_DIR/${key}_aime24.json'))
  acc=d.get('results',{}).get('aime24,none',{}).get('acc,none',0)
  print(f'{acc*100:.1f}%')
except: print('  N/A')
" 2>/dev/null)
  printf "│ %-19s │ %10s │ %8s │ %8s │\n" "$key" "$gsm" "$gpqa" "$aime"
done

echo "└─────────────────────┴────────────┴──────────┴──────────┘"
echo ""
echo "Full log: $LOG_FILE"
