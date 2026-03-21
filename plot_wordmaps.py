from collections import Counter
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON = BASE_DIR / "pinterest_2025_topic_labels.json"
OUT_DIR = BASE_DIR / "topic_viz"


def parse_topic_words(topic_dict, prefix):
    rows = []
    for _, payload in topic_dict.items():
        label = payload[f"{prefix}_topic_label"]
        words = [w.strip().lower() for w in payload[f"{prefix}_topic_words"].split(",")]
        rows.append((label, words))
    return rows


def build_counters(rows):
    landscape_counter = Counter()
    character_counter = Counter()
    for label, words in rows:
        if label in ("landscape_strong", "landscape_mixed"):
            landscape_counter.update(words)
        if label == "character_focused":
            character_counter.update(words)
    return landscape_counter, character_counter


def top_keys(*counters, n=20):
    merged = Counter()
    for c in counters:
        merged.update(c)
    return [w for w, _ in merged.most_common(n)]


def bar_compare(nmf_counter, lda_counter, title, out_path):
    words = top_keys(nmf_counter, lda_counter, n=12)
    nmf_vals = [nmf_counter.get(w, 0) for w in words]
    lda_vals = [lda_counter.get(w, 0) for w in words]

    x = np.arange(len(words))
    width = 0.38

    plt.figure(figsize=(12, 5))
    plt.bar(x - width / 2, nmf_vals, width, label="NMF")
    plt.bar(x + width / 2, lda_vals, width, label="LDA")
    plt.xticks(x, words, rotation=35, ha="right")
    plt.ylabel("Word frequency across topic keywords")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def heatmap_compare(nmf_land, nmf_char, lda_land, lda_char, out_path):
    words = top_keys(nmf_land, nmf_char, lda_land, lda_char, n=25)
    mat = np.array(
        [
            [nmf_land.get(w, 0), nmf_char.get(w, 0), lda_land.get(w, 0), lda_char.get(w, 0)]
            for w in words
        ],
        dtype=float,
    )

    fig, ax = plt.subplots(figsize=(10, 10))
    im = ax.imshow(mat, aspect="auto", cmap="YlGnBu")
    ax.set_yticks(range(len(words)))
    ax.set_yticklabels(words)
    ax.set_xticks(range(4))
    ax.set_xticklabels(
        ["NMF landscape", "NMF character", "LDA landscape", "LDA character"],
        rotation=20,
        ha="right",
    )
    ax.set_title("Wordmap Comparison: NMF vs LDA (landscape/character)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Word frequency")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def main():
    OUT_DIR.mkdir(exist_ok=True)
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    nmf_rows = parse_topic_words(data["nmf_topic_labels"], "nmf")
    lda_rows = parse_topic_words(data["lda_topic_labels"], "lda")

    nmf_land, nmf_char = build_counters(nmf_rows)
    lda_land, lda_char = build_counters(lda_rows)

    bar_compare(
        nmf_land,
        lda_land,
        "Landscape-related Wordmap (NMF vs LDA)",
        OUT_DIR / "wordmap_landscape_nmf_vs_lda.png",
    )
    bar_compare(
        nmf_char,
        lda_char,
        "Character-related Wordmap (NMF vs LDA)",
        OUT_DIR / "wordmap_character_nmf_vs_lda.png",
    )
    heatmap_compare(
        nmf_land,
        nmf_char,
        lda_land,
        lda_char,
        OUT_DIR / "wordmap_heatmap_nmf_lda.png",
    )
    print(f"Saved wordmaps in: {OUT_DIR}")


if __name__ == "__main__":
    main()

