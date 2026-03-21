from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import umap
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "pinterest_2025_topics_labeled.csv"
OUT_DIR = BASE_DIR / "topic_viz"
OUT_PATH = OUT_DIR / "pinterest_umap_kmeans_clusters.png"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    df = pd.read_csv(INPUT_CSV)
    df = df[df["text"].fillna("").astype(str).str.strip() != ""].copy()

    texts = df["text"].astype(str).tolist()
    vec = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.85, max_features=3000)
    X = vec.fit_transform(texts)

    reducer = umap.UMAP(
        n_neighbors=15,
        min_dist=0.1,
        metric="cosine",
        random_state=42,
    )
    emb = reducer.fit_transform(X)
    df["umap_x"] = emb[:, 0]
    df["umap_y"] = emb[:, 1]

    k = min(8, max(3, len(df) // 25))
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=20)
    df["cluster"] = kmeans.fit_predict(emb)

    landscape_mask = df["is_landscape_related"].fillna(False).astype(bool)

    plt.figure(figsize=(11, 8))
    scatter = plt.scatter(
        df["umap_x"],
        df["umap_y"],
        c=df["cluster"],
        cmap="tab10",
        s=32,
        alpha=0.75,
        edgecolors="none",
    )

    # Overlay landscape points with dark ring to highlight them.
    plt.scatter(
        df.loc[landscape_mask, "umap_x"],
        df.loc[landscape_mask, "umap_y"],
        facecolors="none",
        edgecolors="black",
        s=60,
        linewidths=0.8,
        label="Landscape-related",
    )

    # Label cluster centroids
    centroids = df.groupby("cluster")[["umap_x", "umap_y"]].mean()
    for cid, row in centroids.iterrows():
        plt.text(row["umap_x"], row["umap_y"], f"C{int(cid)}", fontsize=10, weight="bold")

    cbar = plt.colorbar(scatter)
    cbar.set_label("KMeans cluster")

    plt.title("Pinterest 2025 UMAP + KMeans Clusters\n(black ring = landscape-related)")
    plt.xlabel("UMAP 1")
    plt.ylabel("UMAP 2")
    plt.legend(loc="best")
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=180)
    plt.close()

    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()

