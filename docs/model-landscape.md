# Model Landscape + KV Cache Math

`PLAN-DAY-01.md` Block 6. Verifies `PLAN.md`'s model-size assumptions (§2, §3.4) against real `config.json` files pulled from Hugging Face — not model cards, and not the hypothetical example in §3.4 — for two candidate families: **Qwen3** (uniform full attention) and **Qwen3.5** (hybrid attention — 3 Gated DeltaNet linear-attention layers per 1 Gated Attention full-attention layer). The resulting decision is recorded in `docs/DECISIONS.md` D9; this doc is the evidence behind it.

Reproduce any row: `python scripts/model_configs.py <model_id>` (e.g. `python scripts/model_configs.py Qwen/Qwen3.5-4B-Base`). Licence and instruct-variant existence were checked against the Hugging Face API (`/api/models/<id>`), not the card text. All figures below were pulled live on 2026-08-19.

## Candidates

### Qwen3 — considered, not chosen

| model id | params | native ctx | rope_scaling | layers | kv heads | head dim | KV/tok fp16 | KV @64K Q8 | licence | instruct variant | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Qwen/Qwen3-0.6B-Base` | ~0.6B | 32,768 | `null` | 28 | 8 | 128 | 112.0 KB | 3.76 GB | Apache 2.0 | `Qwen/Qwen3-0.6B` | Debug rung. Full attention. YaRN factor 2.0× needed to reach 64K. |
| `Qwen/Qwen3-4B-Base` | ~4B | 32,768 | `null` | 36 | 8 | 128 | 144.0 KB | 4.83 GB | Apache 2.0 | `Qwen/Qwen3-4B` | Workhorse rung. Full attention. Matches `PLAN.md` §3.4's hypothetical "typical GQA 4B" config exactly — see Conclusion 3. |
| `Qwen/Qwen3-8B-Base` | ~8B | 32,768 | `null` | 36 | 8 | 128 | 144.0 KB | 4.83 GB | Apache 2.0 | `Qwen/Qwen3-8B` | Scaling-point rung. Identical KV shape to Qwen3-4B-Base — width scales via `hidden_size` (2560→4096), not KV heads or layers. |

### Qwen3.5 — chosen (D9)

| model id | params | native ctx | rope_scaling | layers | kv heads | head dim | KV/tok fp16 | KV @64K Q8 | licence | instruct variant | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Qwen/Qwen3.5-0.8B-Base` | ~0.8B | 262,144 | `null` ¹ | 24 (18 lin / 6 full) | 2 | 256 | 12.0 KB | 0.40 GB | Apache 2.0 | `Qwen/Qwen3.5-0.8B` | **Debug rung.** Hybrid 3:1. Native ctx already 4× the 64K target — no YaRN. |
| `Qwen/Qwen3.5-4B-Base` | ~4B | 262,144 | `null` ¹ | 32 (24 lin / 8 full) | 4 | 256 | 32.0 KB | 1.07 GB | Apache 2.0 | `Qwen/Qwen3.5-4B` | **Workhorse rung.** Hybrid 3:1. ~4.5× smaller KV@64K than Qwen3-4B-Base at equal context — see Conclusion 3. |
| `Qwen/Qwen3.5-9B-Base` | ~9B | 262,144 | `null` ¹ | 32 (24 lin / 8 full) | 4 | 256 | 32.0 KB | 1.07 GB | Apache 2.0 | `Qwen/Qwen3.5-9B` | **Scaling-point rung.** Hybrid 3:1. Identical KV shape to the 4B rung — width scales via `hidden_size` (2560→4096), not KV heads/layers. |

¹ Qwen3.5 configs name this field `rope_parameters`, not `rope_scaling`: `{"rope_type": "default", "rope_theta": 10000000, "partial_rotary_factor": 0.25, "mrope_section": [11, 11, 10], "mrope_interleaved": true}`. It is not a YaRN/context-extension setting — none is applied, because native context already exceeds the 64K target.

**On "layers" and "kv heads" for hybrid rows:** the layer count shown is total (linear + full-attention); only the full-attention layers hold a cache that scales with context, so "kv heads" / "head dim" / "KV/tok" describe only those layers (this is what `scripts/model_configs.py`'s `kv_cache_shape()` computes). Linear-attention (Gated DeltaNet) layers instead hold a fixed-size recurrent state — for the 4B/9B rung: `linear_num_key_heads: 16`, `linear_num_value_heads: 32`, `linear_key/value_head_dim: 128`, `linear_conv_kernel_dim: 4` — that does **not** grow with sequence length and is intentionally excluded from the "KV/tok" and "KV @64K" columns, since those columns exist to track the part of memory that threatens the 64K deployment budget as context grows.

## Conclusions

### 1. Do the rungs exist?

Yes, in both families, but not at identical sizes. `PLAN.md` §2 names ~0.6B / ~4B / ~8B. Qwen3 has exactly those three checkpoints. Qwen3.5 does not ship a dense 0.6B or 8B — its closest dense sizes are **0.8B / 4B / 9B**. Per D9, we're standardizing on Qwen3.5 for all three rungs; §2's sizes are stated with "~", so 0.8B/4B/9B sits within that intent rather than deviating from it.

Choosing one family for all three rungs — instead of, say, Qwen3 for the debug rung and Qwen3.5 for the rest — keeps one tokenizer end to end. That buys two things `PLAN.md` calls out explicitly: the 0.8B becomes a free speculative-decoding draft model for the 4B/9B rungs (§7.4, no separate draft-model training run), and ablation A6 (the cross-rung scaling comparison) stays a clean comparison instead of a confounded one where tokenizer differences could explain part of any scaling effect.

### 2. Is 64K free?

For Qwen3 (all three rungs checked): native `max_position_embeddings` is **32,768** — not free. `factor = 65536 / 32768 = 2.0×` YaRN scaling would be required, i.e. the full §5 extension phase (days 25–32) would need to actually run.

For Qwen3.5 (all three chosen rungs): native context is **262,144** — 4× past the 65,536 target, entirely free. No `rope_scaling`/YaRN config is present or needed. This is the schedule-relevant finding from this block: §5's YaRN phase (days 25–32) isn't skipped by assumption, it's skipped because the verified config says so — that phase becomes a measurement/regression-check exercise (confirm long-context quality holds, extend nothing) instead of an actual context-extension effort.

### 3. Does the deployment claim hold for a real model?

`PLAN.md` §3.4's "typical GQA 4B" example (36 layers, 8 KV heads, 128 head dim, 144 KB/token) isn't a rough approximation — it's, digit for digit, real `Qwen/Qwen3-4B-Base`'s actual config. Recomputing at the plan's rounded "64K" (64,000 tokens) reproduces §3.4's table almost exactly: 9.44 GB fp16 / 4.72 GB Q8 vs. the plan's stated 9.4 GB / 4.7 GB. At this block's own precise target (65,536 = 2¹⁶ tokens, what `scripts/model_configs.py` actually computes), it's 9.66 GB fp16 / **4.83 GB Q8** — about 2–3% above the plan's rounded figure, purely from 65,536 vs. 64,000, not a config surprise. Added to §3.4's ~2.5 GB Q4-weight estimate, real Qwen3-4B-Base lands at **~7.3 GB total**, still comfortably inside the 12 GB deployment target. So for the family named in the plan's own example, the claim holds as written.

But Qwen3-4B-Base isn't the model that got picked. For the model actually chosen, **Qwen3.5-4B-Base**, real Q8 KV @ 64K is **1.07 GB** — 4.5× below the plan's own hypothetical, because only 8 of its 32 layers are full-attention. Adding the same ~2.5 GB Q4-weight estimate (parameter-count-driven, so it should transfer to Qwen3.5 at the same ~4B size) gives roughly **~3.6 GB total** — about half of what §3.4 budgeted. That headroom holds all the way to Qwen3.5's full native 262,144-token context: 4.29 GB Q8 KV, still comfortable inside 12 GB. Reaching that same 262,144 tokens with Qwen3-4B's architecture would need ~19.3 GB of Q8 KV alone (linear extrapolation of its 144 KB/token rate) — moot in practice, since getting Qwen3-4B to 262K at all would need an 8× YaRN factor (native 32,768), far beyond the 2.0× needed just to hit the 64K target — but it isolates how much of Qwen3.5's memory advantage comes from the hybrid layout itself, not just from a longer native context.

## Status

- [x] Table filled from `config.json` files actually read (`scripts/model_configs.py`, live HTTP fetch, 2026-08-19) — not model cards.
- [x] Three rungs chosen: Qwen3.5 0.8B / 4B / 9B (`docs/DECISIONS.md` D9).
- [x] 64K memory claim recomputed for the picked model: Qwen3.5-4B-Base, 1.07 GB Q8 KV @ 64K (vs. the plan's 4.7 GB hypothetical for plain Qwen3-4B).
