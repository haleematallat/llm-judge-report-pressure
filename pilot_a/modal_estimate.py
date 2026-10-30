"""Modal GPU-hour and cost estimate for running this pipeline on open-weight models.

    python -m pilot_a.modal_estimate

Prices are Modal's published per-second GPU prices (modal.com/pricing, read
2026-10-30), converted to per-hour. Throughput is a transparent analytic model, not
a measurement: the Phase 0.4 smoke test that would replace it could not run because
the Modal token in ~/.modal.toml is rejected. Substitute measured numbers in
THROUGHPUT once a smoke test succeeds.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import data
from .attack import N_CANDIDATES, N_LADDER, WORD_CAP

# --- Modal prices, USD per second (modal.com/pricing, 2026-10-30) ------------
GPU_USD_PER_SEC = {
    "B300": 0.001972,
    "B200": 0.001736,
    "H200": 0.001261,
    "H100": 0.001097,
    "RTX PRO 6000": 0.000842,
    "A100-80GB": 0.000694,
    "A100-40GB": 0.000583,
    "L40S": 0.000542,
    "A10": 0.000306,
    "L4": 0.000222,
    "T4": 0.000164,
}
GPU_USD_PER_HOUR = {k: v * 3600 for k, v in GPU_USD_PER_SEC.items()}

# Peak dense bf16 TFLOP/s, used only through MFU below.
GPU_TFLOPS = {"H100": 990.0, "H200": 990.0, "A100-80GB": 312.0, "L40S": 362.0, "L4": 121.0}
MFU = 0.40  # assumed prefill model-FLOPs utilisation with large batched prefill
TP_EFFICIENCY = 0.80  # assumed tensor-parallel scaling across GPUs in one container
CONTAINER_START_MIN = 5.0  # weights download + vLLM warm-up, per model per run


@dataclass
class Model:
    name: str
    params_b: float
    gpu: str
    n_gpu: int = 1
    quant: str = "bf16"
    bytes_per_param: float = 2.0

    def prefill_tok_per_s(self) -> float:
        eff = GPU_TFLOPS[self.gpu] * 1e12 * MFU
        eff *= self.n_gpu * (TP_EFFICIENCY if self.n_gpu > 1 else 1.0)
        # 2 FLOP per parameter per token for a forward pass
        return eff / (2 * self.params_b * 1e9)

    def decode_tok_per_s(self) -> float:
        # memory-bound and heavily batched; taken as a flat fraction of prefill,
        # and it never moves the total much because decode is <5% of our tokens
        return 0.12 * self.prefill_tok_per_s()

    @property
    def usd_per_hour(self) -> float:
        return GPU_USD_PER_HOUR[self.gpu] * self.n_gpu

    @property
    def vram_gb(self) -> float:
        return self.params_b * self.bytes_per_param


@dataclass
class Work:
    calls: int = 0
    tok_in: int = 0
    tok_out: int = 0

    def add(self, calls, tok_in, tok_out):
        self.calls += calls
        self.tok_in += calls * tok_in
        self.tok_out += calls * tok_out


@dataclass
class Config:
    name: str
    items: list
    judges: list  # Model, index 0 is J_dev
    attacker: Model
    generations: list = field(default_factory=list)  # extra judges for the scaling arm
    k: int = 5
    n_candidates: int = N_CANDIDATES
    ladder: tuple = N_LADDER


def tok(s: str) -> int:
    return len(s) // 4 + 1


def account(cfg: Config) -> dict[str, Work]:
    """Calls and tokens per model, matching what pilot_a.run actually issues."""
    work = {m.name: Work() for m in [*cfg.judges, cfg.attacker, *cfg.generations]}
    n_cond = 2 + len(cfg.ladder)  # C0, C_honest, one per N
    report_tok = WORD_CAP * 2
    j_dev, held = cfg.judges[0], cfg.judges[1:]
    for it in cfg.items:
        base = tok(it["transcript"]) + tok(it["prompt_text"]) + tok("\n".join(it["options"])) + 120
        with_rep = base + report_tok
        work[cfg.attacker.name].add(cfg.n_candidates + 1, base, report_tok)
        work[j_dev.name].add(cfg.n_candidates * cfg.k, with_rep, 40)  # candidate scoring
        for m in cfg.judges:  # M1, every judge, every condition
            work[m.name].add(n_cond * cfg.k, with_rep, 40)
        if held:
            work[held[0].name].add(n_cond, with_rep, 150)  # M4 critique
            work[j_dev.name].add(n_cond * cfg.k, with_rep + 150, 40)  # M4 judge
            work[j_dev.name].add(n_cond, with_rep, 300)  # M5 propose
            work[held[0].name].add(n_cond * cfg.k, with_rep + 200, 40)  # M5 pick
        for m in cfg.generations:  # scaling arm: same reports, extra judges
            work[m.name].add(n_cond * cfg.k, with_rep, 40)
    return work


def price(cfg: Config) -> dict:
    work = account(cfg)
    models = {m.name: m for m in [*cfg.judges, cfg.attacker, *cfg.generations]}
    rows, total_usd, total_gpu_h = [], 0.0, 0.0
    for name, w in work.items():
        if not w.calls:
            continue
        m = models[name]
        hours = (
            w.tok_in / m.prefill_tok_per_s() + w.tok_out / m.decode_tok_per_s()
        ) / 3600 + CONTAINER_START_MIN / 60
        usd = hours * m.usd_per_hour
        total_usd += usd
        total_gpu_h += hours * m.n_gpu
        rows.append(
            {
                "model": name,
                "gpu": f"{m.n_gpu}x{m.gpu}" + ("" if m.quant == "bf16" else f" {m.quant}"),
                "vram_gb": round(m.vram_gb),
                "calls": w.calls,
                "tok_in": w.tok_in,
                "tok_out": w.tok_out,
                "wall_h": round(hours, 2),
                "gpu_h": round(hours * m.n_gpu, 2),
                "usd_per_gpu_h": round(m.usd_per_hour / m.n_gpu, 4),
                "usd": round(usd, 2),
            }
        )
    return {
        "name": cfg.name,
        "n_items": len(cfg.items),
        "rows": rows,
        "total_calls": sum(r["calls"] for r in rows),
        "total_gpu_hours": round(total_gpu_h, 2),
        "total_usd": round(total_usd, 2),
    }


# --- the two configurations -------------------------------------------------
QWEN35_9B = Model("Qwen/Qwen3.5-9B", 9, "H100")
LLAMA31_8B = Model("meta-llama/Llama-3.1-8B-Instruct", 8, "H100")
MISTRAL_24B = Model("mistralai/Mistral-Small-24B-Instruct-2501", 24, "H100")
GEMMA3_12B = Model("google/gemma-3-12b-it", 12, "H100")
LLAMA33_70B_FP8 = Model(
    "meta-llama/Llama-3.3-70B-Instruct", 70, "H100", n_gpu=2, quant="FP8", bytes_per_param=1.0
)
QWEN3_8B = Model("Qwen/Qwen3-8B", 8, "H100")
QWEN25_7B = Model("Qwen/Qwen2.5-7B-Instruct", 7, "H100")


def balanced_pool(all_items, cap_per_dataset=2000):
    """The full public pools are 91% Liar's Bench; cap it so the suite stays balanced."""
    return data.take_per_dataset(all_items, cap_per_dataset)


def configs():
    sampled = data.load_items()
    all_items = []
    for load in data.LOADERS.values():
        all_items.extend(load())
    for it in all_items:
        it.setdefault("split", "test")
    balanced = balanced_pool(all_items)
    return [
        Config(
            "planned (plan Phase 1-4, 100 items/dataset, 4 judges)",
            sampled,
            judges=[QWEN35_9B, LLAMA31_8B, MISTRAL_24B, GEMMA3_12B],
            attacker=QWEN3_8B,
        ),
        Config(
            "scaled-balanced (<=2,000 items/dataset, 5 judges incl. 70B, generations arm)",
            balanced,
            judges=[QWEN35_9B, LLAMA31_8B, MISTRAL_24B, GEMMA3_12B, LLAMA33_70B_FP8],
            attacker=LLAMA33_70B_FP8,
            generations=[QWEN25_7B, QWEN3_8B],
        ),
        Config(
            "scaled-balanced, 24B attacker (RECOMMENDED: 70B judges but does not write reports)",
            balanced,
            judges=[QWEN35_9B, LLAMA31_8B, MISTRAL_24B, GEMMA3_12B, LLAMA33_70B_FP8],
            attacker=MISTRAL_24B,
            generations=[QWEN25_7B, QWEN3_8B],
        ),
        Config(
            "scaled-full (every public item in the three pools, same models)",
            all_items,
            judges=[QWEN35_9B, LLAMA31_8B, MISTRAL_24B, GEMMA3_12B, LLAMA33_70B_FP8],
            attacker=LLAMA33_70B_FP8,
            generations=[QWEN25_7B, QWEN3_8B],
        ),
    ]


def main():
    print("\nModal GPU prices used (modal.com/pricing, read 2026-10-30):")
    for g in ("H100", "H200", "A100-80GB", "L40S", "A10", "L4"):
        print(f"  {g:12s} ${GPU_USD_PER_SEC[g]:.6f}/s = ${GPU_USD_PER_HOUR[g]:.4f}/h")
    print(
        f"\nThroughput model (ASSUMPTION, not measured): prefill = {MFU:.0%} MFU of peak bf16, "
        f"2 FLOP/param/token; decode = 12% of prefill; TP scaling {TP_EFFICIENCY:.0%}; "
        f"+{CONTAINER_START_MIN:.0f} min container start per model."
    )
    print(f"  e.g. a 9B on 1xH100 -> {QWEN35_9B.prefill_tok_per_s():,.0f} prefill tok/s; "
          f"70B FP8 on 2xH100 -> {LLAMA33_70B_FP8.prefill_tok_per_s():,.0f} prefill tok/s")
    print("\nValue per token at 40% MFU (prefill tok/s per USD of GPU-hour), 9B model:")
    for g in ("H100", "H200", "A100-80GB", "L40S", "L4"):
        m = Model("9B probe", 9, g)
        print(f"  {g:12s} {m.prefill_tok_per_s():>9,.0f} tok/s  ${m.usd_per_hour:6.2f}/h  "
              f"{m.prefill_tok_per_s() / m.usd_per_hour * 3600 / 1e6:6.1f} M tok per USD")
    for cfg in configs():
        res = price(cfg)
        print(f"\n=== {res['name']} — {res['n_items']:,} items ===")
        print(f"{'model':46s}{'gpu':16s}{'calls':>10s}{'tok_in':>14s}{'gpu_h':>9s}{'usd':>9s}")
        for r in res["rows"]:
            print(f"{r['model']:46s}{r['gpu']:16s}{r['calls']:>10,}{r['tok_in']:>14,}"
                  f"{r['gpu_h']:>9.2f}{r['usd']:>9.2f}")
        print(f"{'TOTAL':46s}{'':16s}{res['total_calls']:>10,}{'':>14s}"
              f"{res['total_gpu_hours']:>9.2f}{res['total_usd']:>9.2f}")
    print()


if __name__ == "__main__":
    main()
