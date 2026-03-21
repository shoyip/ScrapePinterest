from collections import Counter
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
NMF_LDA_JSON = BASE_DIR / "pinterest_2025_topic_labels.json"
BERTOPIC_JSON = BASE_DIR / "pinterest_2025_bertopic_labels.json"
OUT_DIR = BASE_DIR / "topic_viz"


def parse_rows(section: dict, prefix: str):
    rows = []
    for _, payload in section.items():
        label = payload[f"{prefix}_topic_label"]
        words = [w.strip().lower() for w in payload[f"{prefix}_topic_words"].split(",")]
        rows.append((label, words))
    return rows


def build_counters(rows):
    land = Counter()
    char = Counter()
    for label, words in rows:
        if label in ("landscape_strong", "landscape_mixed"):
            land.update(words)
        if label == "character_focused":
            char.update(words)
    return land, char


def top_keys(counters, n=15):
    merged = Counter()
    for c in counters:
        merged.update(c)
    return [w for w, _ in merged.most_common(n)]


def grouped_bar(models, title, out_path):
    # models: list[(name, counter)]
    words = top_keys([c for _, c in models], n=14)
    x = np.arange(len(words))
    width = 0.25

    plt.figure(figsize=(13, 5))
    for i, (name, counter) in enumerate(models):
        vals = [counter.get(w, 0) for w in words]
        plt.bar(x + (i - 1) * width, vals, width, label=name)

    plt.xticks(x, words, rotation=35, ha="right")
    plt.ylabel("Word frequency across topic keywords")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def heatmap(models_cols, out_path):
    # models_cols: list[(label, counter)]
    words = top_keys([c for _, c in models_cols], n=28)
    mat = np.array([[counter.get(w, 0) for _, counter in models_cols] for w in words], dtype=float)

    fig, ax = plt.subplots(figsize=(12, 11))
    im = ax.imshow(mat, aspect="auto", cmap="YlOrRd")
    ax.set_yticks(range(len(words)))
    ax.set_yticklabels(words)
    ax.set_xticks(range(len(models_cols)))
    ax.set_xticklabels([n for n, _ in models_cols], rotation=25, ha="right")
    ax.set_title("Wordmap Heatmap: NMF vs LDA vs BERTopic")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Word frequency")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def main():
    OUT_DIR.mkdir(exist_ok=True)

    with open(NMF_LDA_JSON, "r", encoding="utf-8") as f:
        old = json.load(f)
    with open(BERTOPIC_JSON, "r", encoding="utf-8") as f:
        bt = json.load(f)

    nmf_rows = parse_rows(old["nmf_topic_labels"], "nmf")
    lda_rows = parse_rows(old["lda_topic_labels"], "lda")
    bt_rows = parse_rows(bt["bertopic_topic_labels"], "bertopic")

    nmf_land, nmf_char = build_counters(nmf_rows)
    lda_land, lda_char = build_counters(lda_rows)
    bt_land, bt_char = build_counters(bt_rows)

    grouped_bar(
        [("NMF", nmf_land), ("LDA", lda_land), ("BERTopic", bt_land)],
        "Landscape Wordmap Comparison",
        OUT_DIR / "wordmap_landscape_nmf_lda_bertopic.png",
    )
    grouped_bar(
        [("NMF", nmf_char), ("LDA", lda_char), ("BERTopic", bt_char)],
        "Character Wordmap Comparison",
        OUT_DIR / "wordmap_character_nmf_lda_bertopic.png",
    )

    heatmap(
        [
            ("NMF landscape", nmf_land),
            ("NMF character", nmf_char),
            ("LDA landscape", lda_land),
            ("LDA character", lda_char),
            ("BERTopic landscape", bt_land),
            ("BERTopic character", bt_char),
        ],
        OUT_DIR / "wordmap_heatmap_nmf_lda_bertopic.png",
    )
    print(f"Saved 3-model wordmaps in: {OUT_DIR}")


if __name__ == "__main__":
    main()

