from pathlib import Path
import json

import pandas as pd
from bertopic import BERTopic
import math


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "pinterest_2025_topics_labeled.csv"
INPUT_CSV_FALLBACK = BASE_DIR / "pinterest_2025_topics_labeled_bertopic.csv"
BASE_LABELS_JSON = BASE_DIR / "pinterest_2025_topic_labels.json"
EXISTING_BERTOPIC_LABELS_JSON = BASE_DIR / "pinterest_2025_bertopic_labels.json"

OUT_TOPICS_CSV = BASE_DIR / "pinterest_2025_topics_labeled_bertopic.csv"
OUT_LABELS_JSON = BASE_DIR / "pinterest_2025_bertopic_labels.json"
OUT_FINAL_CLEAN_CSV = BASE_DIR / "pinterest_2025_final_clean_output.csv"
KEEP_DEBUG_ARTIFACTS = False


def label_topic(words, landscape_keywords, portrait_keywords):
    ws = [w.lower() for w in words]
    landscape_score = sum(1 for w in ws if w in landscape_keywords)
    portrait_score = sum(1 for w in ws if w in portrait_keywords)

    if landscape_score >= 4:
        label = "landscape_strong"
    elif landscape_score >= 2 and landscape_score >= portrait_score:
        label = "landscape_mixed"
    elif portrait_score > landscape_score:
        label = "character_focused"
    else:
        label = "other"

    return label, landscape_score, portrait_score


def main():
    source_csv = INPUT_CSV if INPUT_CSV.exists() else INPUT_CSV_FALLBACK
    if not source_csv.exists():
        raise FileNotFoundError(
            "No input topic CSV found. Expected one of: "
            f"{INPUT_CSV.name}, {INPUT_CSV_FALLBACK.name}"
        )

    df = pd.read_csv(source_csv)
    df = df[df["text"].fillna("").astype(str).str.strip() != ""].copy()
    docs = df["text"].astype(str).tolist()

    if BASE_LABELS_JSON.exists():
        with open(BASE_LABELS_JSON, "r", encoding="utf-8") as f:
            base_labels = json.load(f)
        landscape_keywords = set(base_labels["landscape_keywords"])
        portrait_keywords = set(base_labels["portrait_keywords"])
    elif EXISTING_BERTOPIC_LABELS_JSON.exists():
        with open(EXISTING_BERTOPIC_LABELS_JSON, "r", encoding="utf-8") as f:
            base_labels = json.load(f)
        landscape_keywords = set(base_labels["landscape_keywords"])
        portrait_keywords = set(base_labels["portrait_keywords"])
    else:
        landscape_keywords = {
            "beach", "building", "buildings", "city", "cliff", "cloud", "clouds", "field",
            "fields", "flowers", "forest", "garden", "grass", "hill", "hills", "house",
            "lake", "landscape", "meadow", "mountain", "mountains", "nature", "ocean",
            "path", "river", "road", "sea", "sky", "street", "sunrise", "sunset", "tree",
            "trees", "valley", "village", "water", "woods"
        }
        portrait_keywords = {
            "anime", "boy", "character", "dress", "eyes", "face", "girl", "hair",
            "holding", "man", "portrait", "standing", "woman"
        }

    topic_model = BERTopic(
        language="english",
        calculate_probabilities=False,
        min_topic_size=8,
        verbose=False,
    )

    topics, _ = topic_model.fit_transform(docs)
    df["bertopic_topic"] = topics

    # Build BERTopic labels
    topic_info = topic_model.get_topic_info()
    topic_labels = {}
    for _, row in topic_info.iterrows():
        topic_id = int(row["Topic"])
        if topic_id == -1:
            continue
        words_scores = topic_model.get_topic(topic_id) or []
        words = [w for w, _ in words_scores[:10]]
        label, lscore, pscore = label_topic(words, landscape_keywords, portrait_keywords)
        topic_labels[str(topic_id)] = {
            "bertopic_topic_label": label,
            "bertopic_landscape_score": int(lscore),
            "bertopic_portrait_score": int(pscore),
            "bertopic_topic_words": ", ".join(words),
        }

    def map_field(topic_id, key):
        tid = str(int(topic_id))
        return topic_labels.get(tid, {}).get(key)

    # annotate rows
    df["bertopic_topic_label"] = df["bertopic_topic"].map(lambda t: map_field(t, "bertopic_topic_label"))
    df["bertopic_landscape_score"] = df["bertopic_topic"].map(lambda t: map_field(t, "bertopic_landscape_score"))
    df["bertopic_portrait_score"] = df["bertopic_topic"].map(lambda t: map_field(t, "bertopic_portrait_score"))
    df["bertopic_topic_words"] = df["bertopic_topic"].map(lambda t: map_field(t, "bertopic_topic_words"))

    # Build one clean, analysis-ready output with soft probabilities and final label.
    def to_num(x):
        try:
            if x is None or (isinstance(x, float) and pd.isna(x)):
                return 0.0
            return float(x)
        except Exception:
            return 0.0

    def softmax2(a, b):
        ea = math.exp(a)
        eb = math.exp(b)
        s = ea + eb
        return ea / s, eb / s

    # per-method probabilities from landscape vs portrait scores
    for method in ("nmf", "lda", "bertopic"):
        lcol = f"{method}_landscape_score"
        pcol = f"{method}_portrait_score"
        pland = []
        pchar = []
        for _, row in df.iterrows():
            ls = to_num(row.get(lcol))
            ps = to_num(row.get(pcol))
            a, b = softmax2(ls, ps)
            pland.append(a)
            pchar.append(b)
        df[f"{method}_p_landscape"] = pland
        df[f"{method}_p_character"] = pchar

    # final ensemble probabilities (average of methods)
    df["final_p_landscape"] = (
        df["nmf_p_landscape"] + df["lda_p_landscape"] + df["bertopic_p_landscape"]
    ) / 3.0
    df["final_p_character"] = (
        df["nmf_p_character"] + df["lda_p_character"] + df["bertopic_p_character"]
    ) / 3.0
    df["final_label"] = df.apply(
        lambda r: "landscape_related"
        if r["final_p_landscape"] >= r["final_p_character"]
        else "character_related",
        axis=1,
    )
    df["final_confidence"] = df[["final_p_landscape", "final_p_character"]].max(axis=1)

    key_fields = ["created_at", "username", "followers", "description", "likes", "color", "url"]
    method_fields = [
        "nmf_topic",
        "nmf_topic_label",
        "nmf_topic_words",
        "nmf_landscape_score",
        "nmf_portrait_score",
        "nmf_p_landscape",
        "nmf_p_character",
        "lda_topic",
        "lda_topic_label",
        "lda_topic_words",
        "lda_landscape_score",
        "lda_portrait_score",
        "lda_p_landscape",
        "lda_p_character",
        "bertopic_topic",
        "bertopic_topic_label",
        "bertopic_topic_words",
        "bertopic_landscape_score",
        "bertopic_portrait_score",
        "bertopic_p_landscape",
        "bertopic_p_character",
    ]
    final_fields = ["final_label", "final_confidence", "final_p_landscape", "final_p_character"]
    cols = [c for c in key_fields + method_fields + final_fields if c in df.columns]
    clean_df = df[cols].copy()
    clean_df.to_csv(OUT_FINAL_CLEAN_CSV, index=False)

    if KEEP_DEBUG_ARTIFACTS:
        df.to_csv(OUT_TOPICS_CSV, index=False)
        with open(OUT_LABELS_JSON, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "landscape_keywords": sorted(landscape_keywords),
                    "portrait_keywords": sorted(portrait_keywords),
                    "bertopic_topic_labels": topic_labels,
                },
                f,
                indent=2,
            )

    if KEEP_DEBUG_ARTIFACTS:
        print(f"Saved: {OUT_TOPICS_CSV}")
    if KEEP_DEBUG_ARTIFACTS:
        print(f"Saved: {OUT_LABELS_JSON}")
    print(f"Saved: {OUT_FINAL_CLEAN_CSV}")
    print(f"Topics found (excluding -1): {len(topic_labels)}")


if __name__ == "__main__":
    main()

