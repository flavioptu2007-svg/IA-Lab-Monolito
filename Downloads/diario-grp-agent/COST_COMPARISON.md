# DeepSeek-R1 Evaluation: Cost Comparison — DeepSeek API vs OpenRouter

> Prices in **USD per 1M tokens**. Last updated: September 2026.
> Sources: [DeepSeek API Docs](https://api-docs.deepseek.com/quick_start/pricing/) | [OpenRouter Models](https://openrouter.ai/models)

---

## 1. Model Pricing

### DeepSeek Models

| Model | Provider | Input (1M) | Output (1M) | Context | Notes |
|-------|----------|-----------|------------|---------|-------|
| **DeepSeek-R1** (671B) | DeepSeek API | $0.55 | $2.19 | 64K | Original reasoning model |
| **DeepSeek-R1** (671B) | OpenRouter | $0.70 | $2.50 | 64K | +27% markup over API |
| **DeepSeek-R1-0528** | OpenRouter | $0.50 | $2.15 | 164K | Updated R1, longer context |
| **DeepSeek-V4-Flash** | DeepSeek API | $0.22 | $0.66 | 1M | Fast, cheap (peak) |
| **DeepSeek-V4-Pro** | DeepSeek API | $0.66 | $1.98 | 1M | Best quality (peak) |
| **DeepSeek-R1-Distill-Qwen-8B** | Local (vLLM) | $0.00 | $0.00 | 8K | Self-hosted, GPU required |
| **DeepSeek-R1-Distill-Qwen-14B** | Local (vLLM) | $0.00 | $0.00 | 8K | Self-hosted, GPU required |
| **DeepSeek-R1-Distill-Qwen-32B** | Local (vLLM) | $0.00 | $0.00 | 8K | Self-hosted, GPU required |

### Llama Models (OpenRouter only)

| Model | Input (1M) | Output (1M) | Context | Notes |
|-------|-----------|------------|---------|-------|
| **Llama 4 Maverick** | $0.20 | $0.70 | 1M | Best Llama, MoE 400B |
| **Llama 4 Scout** | $0.10 | $0.30 | 1.3M | Ultra-long context |
| **Llama 3.3 70B** | $0.71 | $0.71 | 131K | Solid general model |

### Qwen Models (OpenRouter only)

| Model | Input (1M) | Output (1M) | Context | Notes |
|-------|-----------|------------|---------|-------|
| **Qwen3-235B** | $0.45 | $1.82 | 131K | Largest Qwen |
| **Qwen3-235B-Thinking** | $0.23 | $2.30 | 131K | CoT reasoning variant |
| **Qwen3-32B** | $0.08 | $0.28 | 131K | Best value Qwen |
| **Qwen3-30B-A3B** | $0.12 | $0.50 | 131K | MoE, very efficient |

### Gemini Models (OpenRouter only)

| Model | Input (1M) | Output (1M) | Context | Notes |
|-------|-----------|------------|---------|-------|
| **Gemini 2.5 Pro** | $1.25 | $10.00 | 1M | Best quality Google |
| **Gemini 2.5 Flash** | $0.30 | $2.50 | 1M | Fast, good reasoning |

### Free Models (OpenRouter, zero cost, rate-limited)

| Model | Input (1M) | Output (1M) | Context | Notes |
|-------|-----------|------------|---------|-------|
| **NVIDIA Nemotron-3 Ultra 550B** | $0.00 | $0.00 | 1M | Largest free model |
| **NVIDIA Nemotron-3 Super 120B** | $0.00 | $0.00 | 262K | Strong free option |
| **NVIDIA Nemotron-3.5 Lightning** | $0.00 | $0.00 | 1M | Fast free model |
| **Google Gemma 4 31B** | $0.00 | $0.00 | 262K | Google's free model |
| **MiniMax M3** | $0.00 | $0.00 | 1M | Large context free |

> ⚠️ Free models have **rate limits** (typically 1-20 req/min) and may be less reliable for large evals.

---

## 2. Cost Estimate: Full Evaluation Run

Assuming **GSM8K CoT** (~1320 questions) with CoT reasoning (~2000 output tokens/question):

### Per-Question Token Usage (estimated)

| Metric | Value |
|--------|-------|
| Input tokens/question | ~800 |
| Output tokens/question (CoT) | ~2000 |
| Total questions (GSM8K) | 1,320 |

### Cost per Full GSM8K CoT Run

| Model | Provider | Input Cost | Output Cost | **Total** | vs DeepSeek-R1 |
|-------|----------|-----------|------------|-----------|----------------|
| DeepSeek-R1 (671B) | DeepSeek API | $0.58 | $5.81 | **$6.39** | baseline |
| DeepSeek-R1 (671B) | OpenRouter | $0.74 | $6.60 | **$7.34** | +15% |
| DeepSeek-V4-Flash | DeepSeek API | $0.23 | $1.74 | **$1.97** | -69% |
| DeepSeek-V4-Pro | DeepSeek API | $0.70 | $5.23 | **$5.93** | -7% |
| Llama 4 Maverick | OpenRouter | $0.21 | $1.85 | **$2.06** | -68% |
| Llama 4 Scout | OpenRouter | $0.11 | $0.79 | **$0.90** | -86% |
| Qwen3-235B | OpenRouter | $0.47 | $4.82 | **$5.29** | -17% |
| Qwen3-235B-Thinking | OpenRouter | $0.24 | $6.09 | **$6.34** | -1% |
| Qwen3-32B | OpenRouter | $0.08 | $0.74 | **$0.82** | -87% |
| Gemini 2.5 Flash | OpenRouter | $0.32 | $6.60 | **$6.92** | +8% |
| Gemini 2.5 Pro | OpenRouter | $1.32 | $26.40 | **$27.72** | +334% |
| Distill-Qwen-8B | Local GPU | $0.00 | $0.00 | **$0.00** | -100% |
| Distill-Qwen-32B | Local GPU | $0.00 | $0.00 | **$0.00** | -100% |
| Nemotron-3 Ultra 550B | OpenRouter Free | $0.00 | $0.00 | **$0.00** | -100% (rate-limited) |
| Gemma 4 31B | OpenRouter Free | $0.00 | $0.00 | **$0.00** | -100% (rate-limited) |

---

## 3. Full Evaluation Suite Cost (5 benchmarks × ~1300 questions each)

| Model | Provider | Est. Total Cost |
|-------|----------|----------------|
| DeepSeek-R1 (671B) | DeepSeek API | **~$32** |
| DeepSeek-R1 (671B) | OpenRouter | **~$37** |
| DeepSeek-V4-Flash | DeepSeek API | **~$10** |
| Llama 4 Maverick | OpenRouter | **~$10** |
| Qwen3-32B | OpenRouter | **~$4** |
| Gemini 2.5 Pro | OpenRouter | **~$139** |
| Distill-Qwen-8B | Local GPU | **~$0** (electricity only) |
| Nemotron-3 Ultra 550B | OpenRouter Free | **~$0** (rate-limited) |
| Gemma 4 31B | OpenRouter Free | **~$0** (rate-limited) |

---

## 4. Recommendations

| Scenario | Best Choice | Est. Cost |
|----------|-------------|-----------|
| **Cheapest API** | Qwen3-32B via OpenRouter | $4/eval |
| **Best reasoning/cost** | DeepSeek-V4-Flash (DeepSeek API) | $10/eval |
| **Best quality (API)** | DeepSeek-R1 via DeepSeek API | $32/eval |
| **Zero cost (local)** | Distill-Qwen-8B on local GPU | $0 (need 24GB VRAM) |
| **Zero cost (API)** | Nemotron-3 Ultra 550B via OpenRouter | $0 (rate-limited) |
| **Best value overall** | Llama 4 Scout via OpenRouter | $5/eval |

### DeepSeek API vs OpenRouter

- **DeepSeek API** is ~15-27% cheaper for DeepSeek models (no markup)
- **OpenRouter** adds convenience (one API key, model switching, fallbacks) but charges a markup
- **OpenRouter free tier**: Some models have free variants (`:free` suffix) with rate limits

### DeepSeek Off-Peak Discount

DeepSeek API offers **50% off** during off-peak hours:
- Off-peak: Weekends + weekdays 04:00-06:00 and 10:00-01:00 UTC
- Run evals during off-peak to halve costs

---

## 5. Quick Start Commands

```bash
# DeepSeek API (cheapest for DeepSeek models)
export OPENAI_API_KEY="your_deepseek_key"
API_PROVIDER=deepseek ./run_deepseek_eval.sh

# OpenRouter (multi-model comparison)
export OPENAI_API_KEY="your_openrouter_key"
API_PROVIDER=openrouter ./run_deepseek_eval.sh

# Single model via OpenRouter
export OPENAI_API_KEY="your_openrouter_key"
API_MODEL_SLUG=qwen/qwen3-32b ./run_deepseek_eval.sh
```
