"""Fetch config.json for candidate bases; compute KV cache cost per token.

PLAN-DAY-01.md Block 6. Extends the plan's original script to handle hybrid
linear/full-attention architectures (e.g. Qwen3.5's Gated DeltaNet + Gated
Attention at a 3:1 ratio — docs/DECISIONS.md D9), which the plain formula
gets wrong in two ways:

  1. Qwen3.5-style configs nest every language-model field under
     "text_config" instead of the top level, so a naive `cfg["num_hidden_layers"]`
     raises KeyError immediately.
  2. Only full-attention layers hold a cache that grows with context; linear-
     attention layers (Gated DeltaNet) keep a fixed-size recurrent state that
     does not scale with sequence length. Treating every layer as full
     attention overstates KV@64K by ~4x for a 3:1 hybrid model.

Usage:
    python scripts/model_configs.py <model_id> [<model_id> ...]
"""
import json
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

TARGET_CONTEXT = 65536  # PLAN.md §1: the 64K deployment target


def text_config(cfg: dict) -> dict:
    """Qwen3.5-style configs nest language-model fields under "text_config";
    plain configs (Qwen3, Llama, ...) already have them at the top level."""
    return cfg.get("text_config", cfg)


def kv_cache_shape(tc: dict) -> dict:
    """PLAN.md §3.4: 2 * n_layers * n_kv_heads * head_dim * bytes_per_element,
    applied only to the layers whose cache actually grows with context.

    Returns layer counts plus growing_bytes_per_token (fp16), so callers can
    compute KV@some_context = growing_bytes_per_token * context_len.
    """
    head_dim = tc.get("head_dim") or tc["hidden_size"] // tc["num_attention_heads"]
    kv_heads = tc.get("num_key_value_heads", tc["num_attention_heads"])
    layer_types = tc.get("layer_types")

    if layer_types and "linear_attention" in layer_types:
        full_attn_layers = sum(1 for t in layer_types if t == "full_attention")
        return {
            "hybrid": True,
            "total_layers": len(layer_types),
            "full_attention_layers": full_attn_layers,
            "linear_attention_layers": len(layer_types) - full_attn_layers,
            "kv_heads": kv_heads,
            "head_dim": head_dim,
            "growing_bytes_per_token": 2 * full_attn_layers * kv_heads * head_dim * 2,
        }

    layers = tc["num_hidden_layers"]
    return {
        "hybrid": False,
        "total_layers": layers,
        "full_attention_layers": layers,
        "linear_attention_layers": 0,
        "kv_heads": kv_heads,
        "head_dim": head_dim,
        "growing_bytes_per_token": 2 * layers * kv_heads * head_dim * 2,
    }


def kv_at(growing_bytes_per_token: int, context_len: int) -> tuple[float, float]:
    """Returns (GB fp16, GB Q8) for the growing KV cache at context_len tokens."""
    total = growing_bytes_per_token * context_len
    return total / 1e9, total / 2e9


def describe(model_id: str) -> None:
    cfg = json.loads(Path(hf_hub_download(model_id, "config.json")).read_text())
    tc = text_config(cfg)
    shape = kv_cache_shape(tc)
    native_ctx = tc.get("max_position_embeddings")

    print(f"\n{model_id}")
    print(f"  native ctx          {native_ctx}")
    print(f"  rope_scaling        {tc.get('rope_scaling') or tc.get('rope_parameters')}")
    print(f"  architecture        {'hybrid linear+full attention' if shape['hybrid'] else 'full attention'}")
    print(f"  layers total        {shape['total_layers']}")
    if shape["hybrid"]:
        print(f"  full-attn layers    {shape['full_attention_layers']}  (only these scale with context)")
        print(f"  linear-attn layers  {shape['linear_attention_layers']}  (fixed-size state, ~constant memory)")
    print(f"  kv heads            {shape['kv_heads']}")
    print(f"  head dim            {shape['head_dim']}")
    print(f"  KV/token fp16       {shape['growing_bytes_per_token']/1024:.1f} KB")

    fp16, q8 = kv_at(shape["growing_bytes_per_token"], TARGET_CONTEXT)
    print(f"  KV @ {TARGET_CONTEXT} target   {fp16:.2f} GB fp16 / {q8:.2f} GB Q8")

    if native_ctx and native_ctx != TARGET_CONTEXT:
        fp16_native, q8_native = kv_at(shape["growing_bytes_per_token"], native_ctx)
        print(f"  KV @ {native_ctx} native   {fp16_native:.2f} GB fp16 / {q8_native:.2f} GB Q8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: python {sys.argv[0]} <model_id> [<model_id> ...]")
        sys.exit(1)
    for model_id in sys.argv[1:]:
        describe(model_id)
