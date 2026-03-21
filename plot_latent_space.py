from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "pinterest_2025_topics_labeled.csv"
OUT_DIR = BASE_DIR / "topic_viz"
OUT_PATH = OUT_DIR / "pinterest_latent_space_landscape.png"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    df = pd.read_csv(INPUT_CSV)
    df = df[df["text"].fillna("").astype(str).str.strip() != ""].copy()

    # Build a text latent space using TF-IDF + truncated SVD (2D).
    vec = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.85, max_features=3000)
    X = vec.fit_transform(df["text"].astype(str).tolist())
    svd = TruncatedSVD(n_components=2, random_state=42)
    coords = svd.fit_transform(X)

    df["latent_x"] = coords[:, 0]
    df["latent_y"] = coords[:, 1]

    landscape_mask = df["is_landscape_related"].fillna(False).astype(bool)

    plt.figure(figsize=(10, 7))
    plt.scatter(
        df.loc[~landscape_mask, "latent_x"],
        df.loc[~landscape_mask, "latent_y"],
        s=28,
        alpha=0.7,
        c="#6c757d",
        label="Not landscape-related",
    )
    plt.scatter(
        df.loc[landscape_mask, "latent_x"],
        df.loc[landscape_mask, "latent_y"],
        s=30,
        alpha=0.85,
        c="#2a9d8f",
        label="Landscape-related",
    )

    # Add topic labels at cluster centroids for readability.
    for topic_id, g in df.groupby("nmf_topic"):
        cx = g["latent_x"].mean()
        cy = g["latent_y"].mean()
        plt.text(cx, cy, f"NMF {int(topic_id)}", fontsize=9, weight="bold")

    plt.title("Pinterest 2025 Latent Space (TF-IDF + SVD)")
    plt.xlabel("Latent dimension 1")
    plt.ylabel("Latent dimension 2")
    plt.legend()
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=180)
    plt.close()

    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()

