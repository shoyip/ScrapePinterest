Pinterest Topic Modeling (2025): Simple Pipeline Guide

This README explains, in plain language, how the current topic-modeling pipeline works
and what each output file means.

Current final outputs kept
- pinterest_2025_final_clean_output.csv  <- canonical analysis table
- topic_viz/wordmap_landscape_nmf_lda_bertopic.png
- topic_viz/wordmap_character_nmf_lda_bertopic.png
- topic_viz/wordmap_heatmap_nmf_lda_bertopic.png

Main data source
- Input file: pinterest_pins_output.csv
- Text used: description
- Time filter: only rows from year 2025

------------------------------------------------------------
Easy pipeline overview
------------------------------------------------------------

Step 1 - Filter data to 2025
What it does:
- Reads pinterest_pins_output.csv
- Converts created_at to datetime
- Keeps only rows where year == 2025
- Drops rows with empty description

Why:
- Ensures all modeling is done on one consistent time slice.

Step 2 - Build topics with 3 methods (NMF, LDA, BERTopic)
What it does:
- NMF: finds topics from TF-IDF word patterns
- LDA: finds probabilistic topics from word counts
- BERTopic: uses embeddings + clustering + keyword extraction

Why:
- Running 3 methods gives complementary views:
  - NMF often gives sharper keyword groups
  - LDA gives probabilistic mixtures
  - BERTopic captures more semantic similarity

Step 3 - Extract top words per topic
What it does:
- For each topic from each model, keeps top keywords (usually top 10)

Why:
- These words are the human-readable summary of each cluster.

Step 4 - Label each topic as landscape vs character
What it does:
- Compares topic top words against two keyword dictionaries:
  - landscape_keywords
  - portrait_keywords (character-related)
- Computes:
  - landscape_score = count of top words found in landscape keywords
  - portrait_score = count of top words found in portrait keywords

Why:
- This converts raw topic words into a simple, interpretable category.

Step 5 - Apply threshold rules
Topic label rules:
- landscape_strong: landscape_score >= 4
- landscape_mixed: landscape_score >= 2 AND landscape_score >= portrait_score
- character_focused: portrait_score > landscape_score
- other: anything else

Why:
- These thresholds create a transparent, reproducible decision rule.

Step 6 - Save labeled outputs
What it does:
- Stores one final, clean table with:
  - key Pinterest fields
  - NMF/LDA/BERTopic topic columns
  - per-method soft probabilities
  - final ensemble label/confidence
- Output file:
  - pinterest_2025_final_clean_output.csv

Why:
- You only need one table for downstream analysis.

Step 7 - Build comparison visualizations (NMF vs LDA vs BERTopic)
What it does:
- Creates bar and heatmap wordmaps to compare landscape/character vocabulary by method:
  - wordmap_landscape_nmf_lda_bertopic.png
  - wordmap_character_nmf_lda_bertopic.png
  - wordmap_heatmap_nmf_lda_bertopic.png

Why:
- Makes method differences easy to inspect visually.

------------------------------------------------------------
How to interpret the final plots
------------------------------------------------------------

wordmap_landscape_nmf_lda_bertopic.png
- Compares which landscape words each method emphasizes.

wordmap_character_nmf_lda_bertopic.png
- Compares which character-related words each method emphasizes.

wordmap_heatmap_nmf_lda_bertopic.png
- One compact view with all method/category combinations.
- Darker/higher cells mean that word appears more often in that method/category topic set.

------------------------------------------------------------
Important note
------------------------------------------------------------

The landscape/character decision is rule-based, not supervised learning.
It depends on keyword overlap and chosen thresholds, so it is interpretable and easy to adjust.

------------------------------------------------------------
Data dictionary (final CSV)
------------------------------------------------------------

Canonical output:
- pinterest_2025_final_clean_output.csv

Key Pinterest fields:
- created_at: original Pinterest timestamp string
- username: creator username
- followers: creator follower count
- description: pin text description used for topic modeling
- likes: pin likes/saves proxy from scraping
- color: dominant color hex-like value
- url: pin URL

NMF fields:
- nmf_topic: topic id
- nmf_topic_label: {landscape_strong, landscape_mixed, character_focused, other}
- nmf_topic_words: top keywords for topic
- nmf_landscape_score: keyword-overlap count with landscape dictionary
- nmf_portrait_score: keyword-overlap count with portrait dictionary
- nmf_p_landscape: softmax probability from NMF scores
- nmf_p_character: softmax probability from NMF scores

LDA fields:
- lda_topic
- lda_topic_label
- lda_topic_words
- lda_landscape_score
- lda_portrait_score
- lda_p_landscape
- lda_p_character

BERTopic fields:
- bertopic_topic
- bertopic_topic_label
- bertopic_topic_words
- bertopic_landscape_score
- bertopic_portrait_score
- bertopic_p_landscape
- bertopic_p_character

Final ensemble fields:
- final_p_landscape: average of (nmf, lda, bertopic) landscape probabilities
- final_p_character: average of (nmf, lda, bertopic) character probabilities
- final_label: landscape_related if final_p_landscape >= final_p_character, else character_related
- final_confidence: max(final_p_landscape, final_p_character)
