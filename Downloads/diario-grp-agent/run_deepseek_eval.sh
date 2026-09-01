#!/usr/bin/env bash
# =============================================================================
# DeepSeek-R1 Evaluation Script
# Requires: CUDA GPU (≥24GB VRAM for 8B model), Python 3.10+, vllm
# Install deps:  pip install lm-eval[openai] vllm transformers accelerate
# =============================================================================

set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────
# Supports DeepSeek API, OpenRouter, and multiple models (Llama, Qwen, Gemini).
# Set OPENAI_API_KEY to your provider key.
# Set API_PROVIDER: deepseek | openrouter (default: deepseek)
# Set API_MODEL_SLUG: model slug (default: deepseek-reasoner)
export OPENAI_API_KEY="${OPENAI_API_KEY:?Set OPENAI_API_KEY to your DeepSeek or OpenRouter key}"
API_PROVIDER="${API_PROVIDER:-deepseek}"
API_MODEL_SLUG="${API_MODEL_SLUG:-}"

# ─── Model resolution ──────────────────────────────────────────────────────
resolve_model() {
  local provider="$1" custom_slug="$2"
  if [ -n "$custom_slug" ]; then
    echo "$custom_slug"
    return
  fi
  case "$provider" in
    openrouter)
      echo "deepseek/deepseek-r1" ;;
    deepseek)
      echo "deepseek-reasoner" ;;
    *)
      echo "ERROR: Unknown provider '$provider'" >&2; exit 1 ;;
  esac
}

API_MODEL=$(resolve_model "$API_PROVIDER" "$API_MODEL_SLUG")

if [ "$API_PROVIDER" = "openrouter" ]; then
  API_BASE_URL="https://openrouter.ai/api/v1"
  echo "Using OpenRouter API ($API_MODEL)"
else
  API_BASE_URL="https://api.deepseek.com/v1"
  echo "Using DeepSeek API ($API_MODEL)"
fi

RESULTS_DIR="./deepseek_eval_results"
mkdir -p "$RESULTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$RESULTS_DIR/eval_log_${TIMESTAMP}.txt"

# ─── Helpers ─────────────────────────────────────────────────────────────────
log() { echo -e "\n══════════════════════════════════════════════════════════════"; echo "[$(date '+%H:%M:%S')] $1"; echo "══════════════════════════════════════════════════════════════"; }
run() { echo "+ $*"; "$@" 2>&1 | tee -a "$LOG_FILE"; }

# ─── Preflight Checks ──────────────────────────────────────────────────────
log "Preflight checks"
echo "GPU(s):"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || { echo "ERROR: nvidia-smi not found. A CUDA GPU is required."; exit 1; }

python3 -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'" 2>/dev/null \
  || { echo "ERROR: torch.cuda.is_available() == False. Install CUDA-enabled torch."; exit 1; }

for cmd in lm_eval vllm; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: '$cmd' not found. pip install lm-eval vllm"; exit 1; }
done

echo "Log file: $LOG_FILE"

# =============================================================================
# PART 1 — LOCAL MODELS VIA vLLM
# =============================================================================

# ─── 1A. DeepSeek-R1-Distill-Qwen-8B ───────────────────────────────────────
MODEL_8B="deepseek-ai/DeepSeek-R1-Distill-Qwen-8B"
VLLM_ARGS_8B="pretrained=${MODEL_8B},trust_remote_code=True,dtype=bfloat16,max_model_len=8192,gpu_memory_utilization=0.9"

log "1A  vLLM | ${MODEL_8B} | GSM8K CoT"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_8B" \
  --tasks gsm8k_cot \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1a_gsm8k_cot_8b.json"

log "1A  vLLM | ${MODEL_8B} | Hendrycks Math"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_8B" \
  --tasks hendrycks_math \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1a_math_8b.json"

log "1A  vLLM | ${MODEL_8B} | GPQA Diamond CoT"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_8B" \
  --tasks gpqa_diamond_cot_zeroshot \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1a_gpqa_diamond_8b.json"

log "1A  vLLM | ${MODEL_8B} | AIME 2024"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_8B" \
  --tasks aime24 \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1a_aime24_8b.json"

log "1A  vLLM | ${MODEL_8B} | MMLU"
run lm_eval --model vllm \
  --model_args "pretrained=${MODEL_8B},trust_remote_code=True,tensor_parallel_size=1,dtype=bfloat16" \
  --tasks mmlu \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1a_mmlu_8b.json"

# ─── 1B. DeepSeek-R1-Distill-Qwen-14B (if GPU ≥ 40GB) ─────────────────────
MODEL_14B="deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
VLLM_ARGS_14B="pretrained=${MODEL_14B},trust_remote_code=True,dtype=bfloat16,max_model_len=8192,gpu_memory_utilization=0.9"

log "1B  vLLM | ${MODEL_14B} | GSM8K CoT"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_14B" \
  --tasks gsm8k_cot \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1b_gsm8k_cot_14b.json"

log "1B  vLLM | ${MODEL_14B} | Hendrycks Math"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_14B" \
  --tasks hendrycks_math \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1b_math_14b.json"

log "1B  vLLM | ${MODEL_14B} | GPQA Diamond CoT"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_14B" \
  --tasks gpqa_diamond_cot_zeroshot \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1b_gpqa_diamond_14b.json"

log "1B  vLLM | ${MODEL_14B} | AIME 2024"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_14B" \
  --tasks aime24 \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1b_aime24_14b.json"

log "1B  vLLM | ${MODEL_14B} | MMLU"
run lm_eval --model vllm \
  --model_args "pretrained=${MODEL_14B},trust_remote_code=True,tensor_parallel_size=1,dtype=bfloat16" \
  --tasks mmlu \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1b_mmlu_14b.json"

# ─── 1C. DeepSeek-R1-Distill-Qwen-32B (if GPU ≥ 80GB or multi-GPU) ────────
MODEL_32B="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
VLLM_ARGS_32B="pretrained=${MODEL_32B},trust_remote_code=True,dtype=bfloat16,max_model_len=8192,gpu_memory_utilization=0.9"

log "1C  vLLM | ${MODEL_32B} | GSM8K CoT"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_32B" \
  --tasks gsm8k_cot \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1c_gsm8k_cot_32b.json"

log "1C  vLLM | ${MODEL_32B} | Hendrycks Math"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_32B" \
  --tasks hendrycks_math \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1c_math_32b.json"

log "1C  vLLM | ${MODEL_32B} | GPQA Diamond CoT"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_32B" \
  --tasks gpqa_diamond_cot_zeroshot \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1c_gpqa_diamond_32b.json"

log "1C  vLLM | ${MODEL_32B} | AIME 2024"
run lm_eval --model vllm \
  --model_args "$VLLM_ARGS_32B" \
  --tasks aime24 \
  --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
  --batch_size auto \
  --output_path "$RESULTS_DIR/1c_aime24_32b.json"

# =============================================================================
# PART 2 — DeepSeek-R1 Full (671B) VIA API
# =============================================================================
# The full R1 model is too large to run locally. Use the DeepSeek API.

log "2   API  | deepseek-reasoner (671B) | GSM8K CoT"
run lm_eval --model local-chat-completions \
  --model_args model=$API_MODEL,base_url=$API_BASE_URL,timeout=900 \
  --tasks gsm8k_cot \
  --gen_kwargs max_gen_toks=4096,temperature=0.6 \
  --batch_size 1 \
  --limit 10 \
  --output_path "$RESULTS_DIR/2_gsm8k_cot_reasoner.json"

log "2   API  | deepseek-reasoner (671B) | Hendrycks Math"
run lm_eval --model local-chat-completions \
  --model_args model=$API_MODEL,base_url=$API_BASE_URL,timeout=900 \
  --tasks hendrycks_math \
  --gen_kwargs max_gen_toks=4096,temperature=0.6 \
  --batch_size 1 \
  --limit 10 \
  --output_path "$RESULTS_DIR/2_math_reasoner.json"

log "2   API  | deepseek-reasoner (671B) | GPQA Diamond CoT"
run lm_eval --model local-chat-completions \
  --model_args model=$API_MODEL,base_url=$API_BASE_URL,timeout=900 \
  --tasks gpqa_diamond_cot_zeroshot \
  --gen_kwargs max_gen_toks=4096,temperature=0.6 \
  --batch_size 1 \
  --limit 10 \
  --output_path "$RESULTS_DIR/2_gpqa_diamond_reasoner.json"

log "2   API  | deepseek-reasoner (671B) | AIME 2024"
run lm_eval --model local-chat-completions \
  --model_args model=$API_MODEL,base_url=$API_BASE_URL,timeout=900 \
  --tasks aime24 \
  --gen_kwargs max_gen_toks=4096,temperature=0.6 \
  --batch_size 1 \
  --limit 10 \
  --output_path "$RESULTS_DIR/2_aime24_reasoner.json"

# =============================================================================
# PART 3 — SELF-CONSISTENCY EVALUATION (Multiple Samples)
# =============================================================================
# Self-consistency: generate N samples per question, take majority vote.
# For R1 models, use temperature=0.6-0.7 and generate 8-16 samples.
# This requires --log_samples to save all outputs for post-processing.

SC_SAMPLES=8  # Number of samples per question for self-consistency

# ─── 3A. 8B Self-Consistency ──────────────────────────────────────────────
log "3A  SC (${SC_SAMPLES}x) | ${MODEL_8B} | GSM8K CoT"
for i in $(seq 1 $SC_SAMPLES); do
  run lm_eval --model vllm \
    --model_args "$VLLM_ARGS_8B" \
    --tasks gsm8k_cot \
    --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
    --batch_size auto \
    --log_samples \
    --output_path "$RESULTS_DIR/3a_gsm8k_sc_8b_sample${i}.json"
done

log "3A  SC (${SC_SAMPLES}x) | ${MODEL_8B} | GPQA Diamond CoT"
for i in $(seq 1 $SC_SAMPLES); do
  run lm_eval --model vllm \
    --model_args "$VLLM_ARGS_8B" \
    --tasks gpqa_diamond_cot_zeroshot \
    --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
    --batch_size auto \
    --log_samples \
    --output_path "$RESULTS_DIR/3a_gpqa_sc_8b_sample${i}.json"
done

log "3A  SC (${SC_SAMPLES}x) | ${MODEL_8B} | AIME 2024"
for i in $(seq 1 $SC_SAMPLES); do
  run lm_eval --model vllm \
    --model_args "$VLLM_ARGS_8B" \
    --tasks aime24 \
    --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
    --batch_size auto \
    --log_samples \
    --output_path "$RESULTS_DIR/3a_aime_sc_8b_sample${i}.json"
done

# ─── 3B. 14B Self-Consistency ─────────────────────────────────────────────
log "3B  SC (${SC_SAMPLES}x) | ${MODEL_14B} | GSM8K CoT"
for i in $(seq 1 $SC_SAMPLES); do
  run lm_eval --model vllm \
    --model_args "$VLLM_ARGS_14B" \
    --tasks gsm8k_cot \
    --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
    --batch_size auto \
    --log_samples \
    --output_path "$RESULTS_DIR/3b_gsm8k_sc_14b_sample${i}.json"
done

log "3B  SC (${SC_SAMPLES}x) | ${MODEL_14B} | GPQA Diamond CoT"
for i in $(seq 1 $SC_SAMPLES); do
  run lm_eval --model vllm \
    --model_args "$VLLM_ARGS_14B" \
    --tasks gpqa_diamond_cot_zeroshot \
    --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
    --batch_size auto \
    --log_samples \
    --output_path "$RESULTS_DIR/3b_gpqa_sc_14b_sample${i}.json"
done

log "3B  SC (${SC_SAMPLES}x) | ${MODEL_14B} | AIME 2024"
for i in $(seq 1 $SC_SAMPLES); do
  run lm_eval --model vllm \
    --model_args "$VLLM_ARGS_14B" \
    --tasks aime24 \
    --gen_kwargs max_gen_toks=4096,temperature=0.6,top_p=0.95 \
    --batch_size auto \
    --log_samples \
    --output_path "$RESULTS_DIR/3b_aime_sc_14b_sample${i}.json"
done

# ─── 3C. API Self-Consistency (DeepSeek-R1 671B) ──────────────────────────
log "3C  SC (${SC_SAMPLES}x) | deepseek-reasoner (671B) | GSM8K CoT"
for i in $(seq 1 $SC_SAMPLES); do
  run lm_eval --model local-chat-completions \
    --model_args model=$API_MODEL,base_url=$API_BASE_URL,timeout=900 \
    --tasks gsm8k_cot \
    --gen_kwargs max_gen_toks=4096,temperature=0.6 \
    --batch_size 1 \
    --limit 10 \
    --log_samples \
    --output_path "$RESULTS_DIR/3c_gsm8k_sc_reasoner_sample${i}.json"
done

log "3C  SC (${SC_SAMPLES}x) | deepseek-reasoner (671B) | GPQA Diamond CoT"
for i in $(seq 1 $SC_SAMPLES); do
  run lm_eval --model local-chat-completions \
    --model_args model=$API_MODEL,base_url=$API_BASE_URL,timeout=900 \
    --tasks gpqa_diamond_cot_zeroshot \
    --gen_kwargs max_gen_toks=4096,temperature=0.6 \
    --batch_size 1 \
    --limit 10 \
    --log_samples \
    --output_path "$RESULTS_DIR/3c_gpqa_sc_reasoner_sample${i}.json"
done

# =============================================================================
# PART 4 — MULTI-MODEL COMPARISON (OpenRouter)
# =============================================================================
# Compare DeepSeek-R1 against Llama 4, Qwen3, Gemini 2.5 on key benchmarks.
# Requires: API_PROVIDER=openrouter

if [ "$API_PROVIDER" = "openrouter" ]; then
  OR_BASE="https://openrouter.ai/api/v1"
  # Tasks used in the loop below
  SC_LIMIT=10

  declare -A OR_MODELS=(
    # ─── Paid models ────────────────────────────────────────────────────────
    ["r1"]="deepseek/deepseek-r1"
    ["r1_0528"]="deepseek/deepseek-r1-0528"
    ["llama4_mav"]="meta-llama/llama-4-maverick"
    ["llama4_sct"]="meta-llama/llama-4-scout"
    ["llama33_70b"]="meta-llama/llama-3.3-70b-instruct"
    ["qwen3_32b"]="qwen/qwen3-32b"
    ["qwen3_235b"]="qwen/qwen3-235b-a22b"
    ["qwen3_think"]="qwen/qwen3-235b-a22b-thinking-2507"
    ["gemini25_flash"]="google/gemini-2.5-flash"
    ["gemini25_pro"]="google/gemini-2.5-pro"
    # ─── Free models (:free suffix, zero cost, rate-limited) ────────────────
    ["nemotron_ultra"]="nvidia/nemotron-3-ultra-550b-a55b:free"
    ["nemotron_super"]="nvidia/nemotron-3-super-120b-a12b:free"
    ["nemotron_light"]="nvidia/nemotron-3.5-lightning:free"
    ["gemma4_31b"]="google/gemma-4-31b-it:free"
    ["minimax_m3"]="minimax/minimax-m3:free"
  )

  for key in $(echo "${!OR_MODELS[@]}" | tr ' ' '\n' | sort); do
    slug="${OR_MODELS[$key]}"
    log "4   OpenRouter | ${slug} | GSM8K + GPQA + AIME (limit=${SC_LIMIT})"
    run lm_eval --model local-chat-completions \
      --model_args model=${slug},base_url=${OR_BASE},timeout=900 \
      --tasks gsm8k_cot \
      --gen_kwargs max_gen_toks=4096,temperature=0.6 \
      --batch_size 1 \
      --limit ${SC_LIMIT} \
      --output_path "$RESULTS_DIR/4_${key}_gsm8k.json"

    run lm_eval --model local-chat-completions \
      --model_args model=${slug},base_url=${OR_BASE},timeout=900 \
      --tasks gpqa_diamond_cot_zeroshot \
      --gen_kwargs max_gen_toks=4096,temperature=0.6 \
      --batch_size 1 \
      --limit ${SC_LIMIT} \
      --output_path "$RESULTS_DIR/4_${key}_gpqa.json"

    run lm_eval --model local-chat-completions \
      --model_args model=${slug},base_url=${OR_BASE},timeout=900 \
      --tasks aime24 \
      --gen_kwargs max_gen_toks=4096,temperature=0.6 \
      --batch_size 1 \
      --limit ${SC_LIMIT} \
      --output_path "$RESULTS_DIR/4_${key}_aime.json"
  done
else
  log "4   SKIPPED — Multi-model comparison requires API_PROVIDER=openrouter"
fi

# =============================================================================
# SELF-CONSISTENCY AGGREGATION
# =============================================================================
log "Aggregating self-consistency results..."
python3 parse_sc_results.py --results_dir "$RESULTS_DIR" --num_samples $SC_SAMPLES 2>&1 | tee -a "$LOG_FILE"

# =============================================================================
# SUMMARY
# =============================================================================
log "ALL EVALUATIONS COMPLETE"
echo "Results saved to: $RESULTS_DIR/"
echo "Full log: $LOG_FILE"
echo ""
echo "Files:"
ls -lh "$RESULTS_DIR"/*.json 2>/dev/null || echo "(no JSON results yet)"

echo ""
echo "To view a specific result:"
echo "  python3 -c \"import json; print(json.dumps(json.load(open('$RESULTS_DIR/1a_gsm8k_cot_8b.json')), indent=2))\""

echo ""
echo "Self-consistency results:"
echo "  python3 parse_sc_results.py --results_dir $RESULTS_DIR --num_samples $SC_SAMPLES"
