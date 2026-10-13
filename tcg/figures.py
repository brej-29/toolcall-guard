"""Charts, diagrams and the demo animation for the README and the Hugging Face cards, all generated from result files.
Outputs assets/<name>.svg and assets/<name>.png (charts and diagrams), assets/guard_demo.gif (animation) and
assets/figures_data.json (every number drawn, for tcg.check_docs). White card background so the images read on light
and dark themes; SVG keeps its text as text. Usage: uv run --group docs python -m tcg.figures"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from tcg import config  # noqa: E402

R = config.ROOT
OUT = R / "assets"
INK, MUTED, GRID = "#1f2328", "#57606a", "#d0d7de"
COL = {"tuned": "#0072B2", "int8": "#56B4E9", "4bit": "#CC79A7", "zs": "#E69F00", "fs": "#D55E00", "flash": "#009E73",
       "pro": "#6A3D9A", "a": "#8c959f"}
plt.rcParams.update({"svg.fonttype": "none", "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
                     "axes.edgecolor": GRID, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})
DATA = {}


def j(path):
    return json.loads((R / path).read_text(encoding="utf-8"))


def save(fig, name: str) -> None:
    fig.patch.set_facecolor("white")
    fig.patches.append(FancyBboxPatch((0.003, 0.004), 0.994, 0.992, boxstyle="round,pad=0,rounding_size=0.015",
                                      transform=fig.transFigure, fill=False, edgecolor=GRID, linewidth=1))
    for ext, kw in (("svg", {}), ("png", {"dpi": 130})):
        fig.savefig(OUT / f"{name}.{ext}", facecolor="white", **kw)
    plt.close(fig)


def bars(ax, labels, vals, colors, xlabel, title, fmt="{:.2f}", xmax=1.0):
    y = range(len(labels))[::-1]
    for yi, (p, lo, hi), c in zip(y, vals, colors):
        ax.barh(yi, p, color=c, height=0.62)
        if lo is not None:
            ax.errorbar(p, yi, xerr=[[p - lo], [hi - p]], fmt="none", ecolor=INK, capsize=3, linewidth=1)
        end = hi if hi is not None else p
        if end + 0.09 * xmax > xmax:  # no room on the right: write the value inside the bar
            ax.text((lo if lo is not None else p) - 0.015 * xmax, yi, fmt.format(p), va="center", ha="right", fontsize=9,
                    color="white", fontweight="bold")
        else:
            ax.text(end + 0.015 * xmax, yi, fmt.format(p), va="center", ha="left", fontsize=9, color=INK)
    ax.set_yticks(list(y), labels)
    ax.set_xlim(0, xmax)
    ax.set_xlabel(xlabel)
    if title:
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def chart_headline() -> None:
    s = j("results/summary.json")["a_replay"]
    rows = [("Tuned adapter (full precision)", "gemma-4-e4b tuned (ours)", "tuned"),
            ("Untuned Gemma, zero-shot", "gemma-4-e4b untuned zero-shot", "zs"),
            ("Untuned Gemma, few-shot", "gemma-4-e4b untuned few-shot", "fs"),
            ("Gemini 3.8 Flash", "gemini-3.8-flash zero-shot", "flash"),
            ("Gemini 3.1 Pro", "gemini-3.1-pro zero-shot", "pro")]
    m = {lab: s[f"{g} | real_agent"] for lab, g, _ in rows}
    DATA["headline"] = {lab: {"attack_block_rate": m[lab]["attack_block_rate"], "false_positive_rate": m[lab]["false_positive_rate"]} for lab in m}
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4), gridspec_kw={"wspace": 0.08})
    labels, colors = [r[0] for r in rows], [COL[r[2]] for r in rows]
    bars(axs[0], labels, [m[lab]["attack_block_rate"] for lab in labels], colors, "share of attacks blocked (higher is better)",
         "Attack block rate")
    bars(axs[1], labels, [m[lab]["false_positive_rate"] for lab in labels], colors, "share of benign calls blocked (lower is better)",
         "False positive rate", xmax=0.3)
    axs[1].set_yticks([])
    fig.suptitle(f"Project A's real agent traffic ({m[labels[0]]['n'][0]:,} held-out calls), 95% family-clustered bootstrap intervals",
                 x=0.012, ha="left", fontsize=10, color=MUTED, y=0.995)
    fig.subplots_adjust(left=0.235, right=0.98, top=0.82, bottom=0.17)
    save(fig, "chart_headline")


def chart_precision() -> None:
    s = j("results/summary.json")
    lq = j("results/quant/laptop_quant.json")
    rows = [("Full precision", "gemma-4-e4b tuned (ours)", "tuned", f"about 16 GB; laptop CPU {lq['merged_full cpu']['median_latency_ms'] / 1000:.0f} s"),
            ("8-bit (LoRA merged)", "gemma-4-e4b tuned (ours), merged int8", "int8",
             f"{lq['merged_int8 cuda']['peak_gpu_gib']:.1f} GiB GPU; {lq['merged_int8 cuda']['median_latency_ms'] / 1000:.0f} s"),
            ("4-bit (nf4 base + LoRA)", "gemma-4-e4b tuned (ours), 4-bit laptop", "4bit",
             f"{lq['nf4_base+lora cuda']['peak_gpu_gib']:.1f} GiB GPU; {lq['nf4_base+lora cuda']['median_latency_ms'] / 1000:.1f} s")]
    sets = [("A real agent", lambda g: s["a_replay"][f"{g} | real_agent"]), ("Synthetic test", lambda g: s["synthetic_test"][g])]
    DATA["precision"] = {lab: {name: get(g)["attack_block_rate"] for name, get in sets} | {"memory_and_latency": note}
                         for lab, g, _, note in rows}
    fig, ax = plt.subplots(figsize=(10, 3.4))
    w = 0.26
    for k, (lab, g, c, note) in enumerate(rows):
        for i, (name, get) in enumerate(sets):
            p, lo, hi = get(g)["attack_block_rate"]
            x = i + (k - 1) * w
            ax.bar(x, p, width=w * 0.92, color=COL[c], label=f"{lab}  ({note} per decision)" if i == 0 else None)
            ax.errorbar(x, p, yerr=[[p - lo], [hi - p]], fmt="none", ecolor=INK, capsize=3, linewidth=1)
            ax.text(x, hi + 0.02, f"{p:.2f}", ha="center", fontsize=9)
    ax.set_xticks([0, 1], [n for n, _ in sets])
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("attack block rate")
    ax.set_title("Precision choice: 8-bit keeps full-precision recall, 4-bit loses about 20 points", loc="left", fontsize=11,
                 fontweight="bold")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.subplots_adjust(left=0.07, right=0.56, top=0.86, bottom=0.12)
    save(fig, "chart_precision")


def chart_matched() -> None:
    s = j("results/summary.json")["a_replay"]
    mf = [r for r in j("results/matched_fpr.json")["a_replay"] if r["reference"] == "gemini-3.1-pro zero-shot"]
    names = {"gemma-4-e4b tuned (ours)": ("Tuned adapter", "tuned"), "gemma-4-e4b untuned zero-shot": ("Untuned, zero-shot", "zs"),
             "gemma-4-e4b untuned few-shot": ("Untuned, few-shot", "fs"),
             "gemma-4-e4b G5 in-domain (A data)": ("G5, in-domain (A's generator)", "a")}
    rows = [("Gemini 3.1 Pro (default)", s["gemini-3.1-pro zero-shot"]["attack_block_rate"], s["gemini-3.1-pro zero-shot"]["false_positive_rate"][0], "pro"),
            ("Gemini 3.8 Flash (default)", s["gemini-3.8-flash zero-shot"]["attack_block_rate"], s["gemini-3.8-flash zero-shot"]["false_positive_rate"][0], "flash")]
    rows += [(names[r["guard"]][0], r["attack_block_rate"], r["false_positive_rate"][0], names[r["guard"]][1]) for r in mf if r["guard"] in names]
    DATA["matched"] = {lab: {"attack_block_rate": b, "false_positive_rate": f} for lab, b, f, _ in rows}
    fig, ax = plt.subplots(figsize=(10, 3.6))
    bars(ax, [f"{lab}, FPR {f:.3f}" for lab, _, f, _ in rows], [b for _, b, _, _ in rows], [COL[c] for *_, c in rows],
         f"attack block rate on A's replay sample ({s['gemini-3.1-pro zero-shot']['n'][0]:,} calls)", "")
    fig.text(0.012, 0.955, "At a matched false positive rate (about Pro's 3%); Gemma thresholds fit on the val split only",
             fontsize=11, fontweight="bold")
    fig.subplots_adjust(left=0.33, right=0.97, top=0.86, bottom=0.15)
    save(fig, "chart_matched_fpr")


def chart_adaptive() -> None:
    ad = j("results/adaptive/metrics.json")["all"]
    rows = [("Tuned adapter, full precision", "tcg_tuned_fp16_kaggle", "tuned"), ("Tuned adapter, 4-bit", "tcg_tuned_4bit_laptop", "4bit"),
            ("Untuned, zero-shot, full precision", "tcg_untuned_zs_fp16_kaggle", "zs"), ("Untuned, zero-shot, 4-bit", "tcg_untuned_zs_4bit_laptop", "zs"),
            ("A: Model Armor", "model_armor_direct", "a"), ("A: handwritten rules", "handwritten_rules_g2prime", "a"),
            ("A: LLM guard (Flash)", "llm_guard_flash", "a"), ("A: Gemini 3.1 Pro with this guard prompt", "b_prompt_gemini_3_1_pro", "a")]
    vals = [tuple(ad[c]["ci95"]["attack_block_rate"]) for _, c, _ in rows]
    DATA["adaptive"] = {lab: list(v) for (lab, _, _), v in zip(rows, vals)}
    fig, ax = plt.subplots(figsize=(10, 3.8))
    bars(ax, [r[0] for r in rows], [(p, lo if lo != hi or p not in (0, 1) else None, hi if lo != hi or p not in (0, 1) else None) for p, lo, hi in vals],
         [COL[r[2]] for r in rows], f"share of the {ad['tcg_tuned_fp16_kaggle']['ci95']['n'][0]} rewritten attacks blocked", "")
    fig.text(0.012, 0.955, "Adaptive attacks: Project A's attacks rewritten by Gemini 3.1 Pro to evade guards", fontsize=11, fontweight="bold")
    fig.subplots_adjust(left=0.33, right=0.97, top=0.88, bottom=0.14)
    save(fig, "chart_adaptive")


def flow(name: str, size, nodes: dict, edges: list, title: str, notes: list = ()) -> None:
    """nodes: key -> (x, y, w, h, text, color); edges: (from, to, label). Axes run 0..100 in x and y."""
    fig = plt.figure(figsize=size)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    for k, (x, y, w, h, text, color) in nodes.items():
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.4,rounding_size=1.6",
                                    facecolor=color + "22", edgecolor=color, linewidth=1.4))
        ax.text(x, y, text, ha="center", va="center", fontsize=9, color=INK, wrap=True)
    for a, b, lab in edges:
        (x1, y1, w1, h1, *_), (x2, y2, w2, h2, *_) = nodes[a], nodes[b]
        if abs(y1 - y2) < 1 or abs(x1 - x2) > (w1 + w2) / 2:
            p1, p2 = (x1 + w1 / 2 * (1 if x2 > x1 else -1), y1), (x2 - w2 / 2 * (1 if x2 > x1 else -1), y2)
        else:
            p1, p2 = (x1, y1 - h1 / 2 * (1 if y2 < y1 else -1)), (x2, y2 + h2 / 2 * (1 if y2 < y1 else -1))
        ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=12, color=MUTED, linewidth=1.2))
        if lab:
            vertical = abs(p1[0] - p2[0]) < 1
            ax.text((p1[0] + p2[0]) / 2 + (1.2 if vertical else 0), (p1[1] + p2[1]) / 2 + (0 if vertical else 9 if abs(p1[1] - p2[1]) < 1 else 3), lab,
                    ha="left" if vertical else "center", va="center", fontsize=8, color=MUTED)
    ax.text(2, 96, title, fontsize=11, fontweight="bold", va="top")
    for i, n in enumerate(notes):
        ax.text(2, 7 - i * 4.5, n, fontsize=8.5, color=MUTED, va="center")
    save(fig, name)


def diagrams() -> None:
    s = j("results/summary.json")
    rep = j("data/v1/report.json")
    flow("diagram_pipeline", (11, 3.6), {
        "seed": (7.5, 62, 12, 16, "Structured seeds\nrole, category,\ntechnique, surface", COL["a"]),
        "gen": (24, 62, 12.5, 16, "Gemini 3.8 Flash\nwrites a family:\nattack + benign twin", COL["flash"]),
        "lab": (41, 62, 12, 16, "Gemini 3.1 Pro\nteacher labels\n(pass 2 on 15%)", COL["pro"]),
        "disp": (41, 24, 17, 16, f"Dispute pool\nteacher != intent\n{rep['disputed']:,} records,\nnever trained", COL["fs"]),
        "split": (59, 62, 12, 16, "Family-hash split\n80 / 5 / 15\nleakage checks", COL["zs"]),
        "tune": (77, 62, 12, 16, "LoRA tuning\nGemma 4 E4B IT\nrank 16, 2 epochs", COL["tuned"]),
        "eval": (93, 62, 11, 16, "Evaluation\nsynthetic, OOD,\nProject A traffic", COL["int8"])},
        [("seed", "gen", ""), ("gen", "lab", ""), ("lab", "disp", "disagree"), ("lab", "split", "agree"), ("split", "tune", "train + val"),
         ("tune", "eval", "")],
        "Distillation pipeline", [f"{rep['generated']:,} generated records, {rep['kept']:,} kept; teacher self-agreement {rep['self_agreement']['verdict']:.1%} verdict, "
                                  f"{rep['self_agreement']['category']:.1%} category on {rep['self_agreement']['n']} double-labeled records"])
    flow("diagram_guard_replay", (11, 3.8), {
        "agent": (10, 74, 15, 13, "Live: agent proposes\na tool call", COL["a"]),
        "rec": (10, 30, 15, 13, "Replay: Project A's\nsaved decision points", COL["zs"]),
        "guard": (37, 52, 15, 14, "Guard (this adapter)\npre-execution check", COL["tuned"]),
        "run": (66, 80, 17, 10, "allow: the tool runs", COL["flash"]),
        "stop": (66, 55, 17, 10, "block: call stopped,\nagent told why", COL["fs"]),
        "cmp": (66, 28, 17, 13, "Replay only: compare\nverdict with the label", COL["pro"])},
        [("agent", "guard", ""), ("rec", "guard", ""), ("guard", "run", ""), ("guard", "stop", ""), ("guard", "cmp", "")],
        "Where the guard sits, and how replay evaluation works",
        ["Replay scores each saved decision point offline. Limitation: after a block, a live agent may retry another way or",
         "succeed at a later step; replay cannot see that, so block rates are per decision point, not per attack."])
    flow("diagram_split", (11, 3.6), {
        "fam": (12, 62, 16, 16, "family_id\n(record + benign twin\n+ same seed)", COL["a"]),
        "hash": (34, 62, 15, 16, "salted hash\nof family_id", COL["zs"]),
        "tr": (58, 80, 15, 10, "train 80%", COL["tuned"]),
        "va": (58, 62, 15, 10, "val 5% (threshold\nchoice only)", COL["int8"]),
        "te": (58, 44, 15, 10, "test 15%", COL["fs"]),
        "leak": (84, 62, 22, 22, "Leakage check on all splits\nfails on: family crossing splits,\nexact duplicate text,\nnear duplicate\n(5-gram Jaccard >= 0.8)", COL["pro"])},
        [("fam", "hash", ""), ("hash", "tr", ""), ("hash", "va", ""), ("hash", "te", ""), ("tr", "leak", ""), ("va", "leak", ""),
         ("te", "leak", "")],
        "Data split and leakage checks",
        ["A record and its twin always share a split. review_100 families are removed from tuning; Project A's gold records are test only."])
    real = lambda g: s["a_replay"][f"{g} | real_agent"]["attack_block_rate"][0]
    fpr = lambda g: s["a_replay"][f"{g} | real_agent"]["false_positive_rate"][0]
    lq = j("results/quant/laptop_quant.json")
    flow("diagram_precision", (11, 3.0), {
        "full": (17, 58, 26, 26, f"Full precision (bf16 / fp16)\nabout 16 GB: CPU, or a GPU with 18 GB+\nA real agent block rate {real('gemma-4-e4b tuned (ours)'):.2f}", COL["tuned"]),
        "int8": (50, 58, 26, 26, f"8-bit (LoRA merged, LLM.int8)\n{lq['merged_int8 cuda']['peak_gpu_gib']:.1f} GiB, fits a 6 GB GPU\nblock rate {real('gemma-4-e4b tuned (ours), merged int8'):.2f}: recommended", COL["int8"]),
        "4bit": (83, 58, 26, 26, f"4-bit (nf4 base + LoRA)\n{lq['nf4_base+lora cuda']['peak_gpu_gib']:.1f} GiB, fastest\nblock rate {real('gemma-4-e4b tuned (ours), 4-bit laptop'):.2f}: loses recall", COL["4bit"])},
        [("full", "int8", ""), ("int8", "4bit", "")], "Precision choices",
        ["Project A's real agent traffic, default threshold. False positive rates: full " + f"{fpr('gemma-4-e4b tuned (ours)'):.3f}, "
         f"8-bit {fpr('gemma-4-e4b tuned (ours), merged int8'):.3f}, 4-bit {fpr('gemma-4-e4b tuned (ours), 4-bit laptop'):.3f} (4-bit blocks less of everything)."])
    DATA["diagrams"] = {"generated": rep["generated"], "kept": rep["kept"], "disputed": rep["disputed"], "self_agreement": rep["self_agreement"],
                        "precision_fpr": {k: fpr(g) for k, g in (("full", "gemma-4-e4b tuned (ours)"), ("int8", "gemma-4-e4b tuned (ours), merged int8"),
                                                                     ("4bit", "gemma-4-e4b tuned (ours), 4-bit laptop"))},
                        "precision_block_rates": {k: real(g) for k, g in (("full", "gemma-4-e4b tuned (ours)"), ("int8", "gemma-4-e4b tuned (ours), merged int8"),
                                                                          ("4bit", "gemma-4-e4b tuned (ours), 4-bit laptop"))}}


def animation() -> None:
    from io import BytesIO
    from PIL import Image
    recs = [json.loads(line) for line in (R / "hf" / "demo_examples.jsonl").read_text(encoding="utf-8").splitlines() if line]
    outs = {r["id"]: r for r in map(json.loads, (R / "results" / "demo_examples_8bit.jsonl").read_text(encoding="utf-8").splitlines())}
    kinds = {"demo-attack": "attack", "demo-benign": "benign", "demo-tricky": "tricky benign"}
    DATA["animation"] = {r["id"]: outs[r["id"]]["pred"] for r in recs}
    frames, durations = [], []

    def frame(r, step):
        fig = plt.figure(figsize=(8, 3.2), dpi=100)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis("off")
        call = r["proposed_call"]
        args = ", ".join(f"{k}={json.dumps(v)}" for k, v in call["arguments"].items())
        ctx = r["conversation"][-1]["content"]
        ctx = ctx if len(ctx) < 150 else ctx[:147] + "..."
        ax.text(2, 93, f"Example: {kinds[r['id']]} (synthetic)", fontsize=10, fontweight="bold", va="top")
        ax.add_patch(FancyBboxPatch((2, 30), 36, 52, boxstyle="round,pad=0.4,rounding_size=2", facecolor="#f6f8fa", edgecolor=GRID))
        ax.text(4, 76, "Proposed tool call", fontsize=9, fontweight="bold", va="top")
        import textwrap
        ax.text(4, 68, textwrap.fill(f"{call['name']}({args})", 34), fontsize=8, family="DejaVu Sans Mono", va="top")
        ax.text(4, 52, textwrap.fill("Last tool output: " + ctx, 46), fontsize=7, color=MUTED, va="top")
        lit = step >= 1
        ax.add_patch(FancyBboxPatch((44, 45), 14, 22, boxstyle="round,pad=0.4,rounding_size=2",
                                    facecolor=(COL["tuned"] + ("44" if lit else "11")), edgecolor=COL["tuned"], linewidth=1.6))
        ax.text(51, 56, "Guard", ha="center", va="center", fontsize=10, fontweight="bold", color=COL["tuned"])
        if step >= 1:
            ax.add_patch(FancyArrowPatch((39, 56), (43.5, 56), arrowstyle="-|>", mutation_scale=12, color=MUTED))
        if step >= 2:
            ax.add_patch(FancyArrowPatch((58.5, 56), (63, 56), arrowstyle="-|>", mutation_scale=12, color=MUTED))
            p = outs[r["id"]]["pred"]
            color = COL["fs"] if p["verdict"] == "block" else COL["flash"]
            ax.add_patch(FancyBboxPatch((64, 30), 34, 52, boxstyle="round,pad=0.4,rounding_size=2", facecolor=color + "18", edgecolor=color))
            ax.text(66, 76, "JSON verdict", fontsize=9, fontweight="bold", va="top")
            body = (f'"verdict": "{p["verdict"]}",\n"category": "{p["category"]}",\n' +
                    textwrap.fill('"reason": ' + json.dumps(p["reason"]), 40, subsequent_indent="  "))
            ax.text(66, 68, "{\n" + body + "\n}", fontsize=7, family="DejaVu Sans Mono", va="top")
        ax.text(2, 8, "Real output of the 8-bit adapter (greedy decoding) on a synthetic example.", fontsize=8, color=MUTED)
        buf = BytesIO()
        fig.savefig(buf, format="png", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf).convert("RGB")

    for r in recs:
        for step, ms in ((0, 1600), (1, 700), (2, 3600)):
            frames.append(frame(r, step))
            durations.append(ms)
    pal = [f.quantize(colors=64, method=Image.Quantize.MEDIANCUT) for f in frames]
    pal[0].save(OUT / "guard_demo.gif", save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    chart_headline()
    chart_precision()
    chart_matched()
    chart_adaptive()
    diagrams()
    animation()
    (OUT / "figures_data.json").write_text(json.dumps(DATA, indent=1), encoding="utf-8")
    for f in sorted(OUT.iterdir()):
        print(f"{f.stat().st_size / 1024:7.1f} KB  {f.name}")


if __name__ == "__main__":
    main()
