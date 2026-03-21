import json
from pathlib import Path

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON = BASE_DIR / "pinterest_2025_topic_labels.json"
OUTPUT_DIR = BASE_DIR / "topic_viz"


def load_topic_table(section: dict, prefix: str):
    rows = []
    for topic_id_str, payload in section.items():
        rows.append(
            {
                "topic_id": int(topic_id_str),
                "label": payload[f"{prefix}_topic_label"],
                "landscape_score": payload[f"{prefix}_landscape_score"],
                "portrait_score": payload[f"{prefix}_portrait_score"],
                "words": payload[f"{prefix}_topic_words"],
            }
        )
    rows.sort(key=lambda x: x["topic_id"])
    return rows


def plot_label_distribution(rows, model_name: str, out_path: Path):
    label_counts = {}
    for r in rows:
        label_counts[r["label"]] = label_counts.get(r["label"], 0) + 1

    labels = list(label_counts.keys())
    counts = [label_counts[l] for l in labels]

    plt.figure(figsize=(8, 4))
    bars = plt.bar(labels, counts)
    plt.title(f"{model_name} Topic Label Distribution")
    plt.ylabel("Number of topics")
    plt.xticks(rotation=20, ha="right")
    for b in bars:
        plt.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, str(int(b.get_height())), ha="center")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_score_comparison(rows, model_name: str, out_path: Path):
    topic_ids = [r["topic_id"] for r in rows]
    land = [r["landscape_score"] for r in rows]
    portrait = [r["portrait_score"] for r in rows]

    x = list(range(len(topic_ids)))
    w = 0.38

    plt.figure(figsize=(10, 4))
    plt.bar([i - w / 2 for i in x], land, width=w, label="landscape_score")
    plt.bar([i + w / 2 for i in x], portrait, width=w, label="portrait_score")
    plt.title(f"{model_name} Topic Characterization Scores")
    plt.xlabel("Topic ID")
    plt.ylabel("Score")
    plt.xticks(x, topic_ids)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_topic_keyword_cards(rows, model_name: str, out_path: Path):
    # A compact text visualization for quick interpretation per cluster
    fig_h = max(4, 0.7 * len(rows))
    plt.figure(figsize=(12, fig_h))
    plt.axis("off")
    y = 1.0
    step = 1.0 / (len(rows) + 1)
    for r in rows:
        line = (
            f"Topic {r['topic_id']} | {r['label']} | "
            f"L={r['landscape_score']} P={r['portrait_score']} | {r['words']}"
        )
        plt.text(0.01, y, line, fontsize=9, family="monospace", va="top")
        y -= step
    plt.title(f"{model_name} Topic Keywords and Scores", loc="left")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    nmf_rows = load_topic_table(data["nmf_topic_labels"], "nmf")
    lda_rows = load_topic_table(data["lda_topic_labels"], "lda")

    plot_label_distribution(nmf_rows, "NMF", OUTPUT_DIR / "nmf_label_distribution.png")
    plot_label_distribution(lda_rows, "LDA", OUTPUT_DIR / "lda_label_distribution.png")

    plot_score_comparison(nmf_rows, "NMF", OUTPUT_DIR / "nmf_score_comparison.png")
    plot_score_comparison(lda_rows, "LDA", OUTPUT_DIR / "lda_score_comparison.png")

    plot_topic_keyword_cards(nmf_rows, "NMF", OUTPUT_DIR / "nmf_topic_cards.png")
    plot_topic_keyword_cards(lda_rows, "LDA", OUTPUT_DIR / "lda_topic_cards.png")

    print(f"Saved visualizations to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
