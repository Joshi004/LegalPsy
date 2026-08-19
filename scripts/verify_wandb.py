"""Smoke-test the W&B run-tracking setup end to end, then delete the run it
created. PLAN-DAY-01.md Block 7: "verify with one throwaway run that logs a
two-row table, then delete it." Safe to re-run any time you want to confirm
`wandb login` plus the tracking helper (docs/DECISIONS.md D10) still work.

Usage:
    python scripts/verify_wandb.py
"""
import wandb

from legalpsy.tracking import RunMeta, log_table, start_run


def main() -> None:
    meta = RunMeta(
        phase="eval",
        model_token="qwen3.5-4b",
        model_id="Qwen/Qwen3.5-4B-Base",
        split="cuaddev",
        prompt_version="v1",
        # No real prompt/split-manifest files exist yet (Days 3/4/6), so
        # these are placeholders for this smoke test only, not real hashes.
        prompt_hash="placeholder-no-prompt-file-yet",
        split_manifest_hash="placeholder-no-manifest-until-day-4",
    )

    run = start_run(meta, extra_config={"note": "Block 7 smoke test — safe to ignore"})
    entity, project, run_id = run.entity, run.project, run.id
    print(f"run name: {run.name}")
    print(f"run url:  {run.url}")

    log_table(
        run,
        "generations",
        rows=[
            {"contract_id": "smoke-1", "field": "term", "predicted_value": "3 years", "correct": True},
            {"contract_id": "smoke-2", "field": "term", "predicted_value": "not present", "correct": True},
        ],
        columns=["contract_id", "field", "predicted_value", "correct"],
    )

    run.finish()

    wandb.Api().run(f"{entity}/{project}/{run_id}").delete()
    print("Deleted the verification run — smoke test passed.")


if __name__ == "__main__":
    main()
