"""
train_dga_detector.py
----------------------
Train a LightGBM binary classifier (DGA vs benign) using features from dga_core.py.

Usage:
    python train_dga_detector.py --csv dga_data.csv [--wordlist words_alpha.txt]

Outputs:
    dga_detector_pipeline.pkl   — serialised pipeline (StandardScaler + LGBMClassifier)

The script also prints a classification report and holds out 5 DGA families
for a "zero-shot generalisation" evaluation (family hold-out).
"""

import argparse
import os
import sys
import warnings
warnings.filterwarnings("ignore")

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from sklearn.pipeline import Pipeline

try:
    import lightgbm as lgb
    LGB_AVAILABLE = True
except ImportError:
    LGB_AVAILABLE = False
    from sklearn.ensemble import GradientBoostingClassifier

from dga_core import extract_features_batch, FEATURE_NAMES, _load_wordlist, _WORD_SET


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train a DGA domain detector.")
    p.add_argument("--csv",      default="dga_data.csv",   help="Training CSV file")
    p.add_argument("--wordlist", default=None,              help="Path to words_alpha.txt")
    p.add_argument("--output",   default="dga_detector_pipeline.pkl", help="Output model file")
    p.add_argument("--test-size", type=float, default=0.2, help="Fraction reserved for test set")
    p.add_argument("--seed",     type=int,   default=42,   help="Random seed")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(csv_path: str) -> pd.DataFrame:
    print(f"\n[train] Loading data from '{csv_path}' …")
    df = pd.read_csv(csv_path)
    required_cols = {"domain", "label"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSV must have columns: {required_cols}. Found: {set(df.columns)}")
    df["domain"] = df["domain"].astype(str).str.strip().str.lower()
    df = df.dropna(subset=["domain", "label"])
    df = df[df["domain"] != ""]
    print(f"  Loaded {len(df):,} rows. Label distribution:")
    print(df["label"].value_counts().to_string())
    return df


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def build_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    print("\n[train] Extracting features …")
    X = extract_features_batch(df["domain"].tolist())
    y = (df["label"].str.lower() == "dga").astype(int).values
    print(f"  Feature matrix: {X.shape[0]:,} samples × {X.shape[1]} features")
    return X, y


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def build_model(seed: int) -> Pipeline:
    if LGB_AVAILABLE:
        clf = lgb.LGBMClassifier(
            n_estimators=400,
            learning_rate=0.05,
            max_depth=7,
            num_leaves=63,
            min_child_samples=20,
            colsample_bytree=0.8,
            subsample=0.8,
            random_state=seed,
            verbose=-1,
        )
    else:
        print("[train] LightGBM not found; falling back to GradientBoostingClassifier.")
        clf = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            random_state=seed,
        )
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    clf),
    ])


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def print_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                  y_prob: np.ndarray, prefix: str = "") -> None:
    tag = f"[{prefix}] " if prefix else ""
    print(f"\n{tag}Classification report:")
    print(classification_report(y_true, y_pred, target_names=["benign", "dga"]))
    try:
        auc = roc_auc_score(y_true, y_prob)
        print(f"  ROC-AUC: {auc:.4f}")
    except Exception:
        pass
    cm = confusion_matrix(y_true, y_pred)
    print(f"  Confusion matrix (benign=0, dga=1):\n{cm}")


# ---------------------------------------------------------------------------
# Family hold-out evaluation
# ---------------------------------------------------------------------------

def family_holdout(df: pd.DataFrame, pipeline: Pipeline, n_holdout: int = 5) -> None:
    if "family" not in df.columns:
        return
    dga_families = [f for f in df["family"].unique() if f != "benign"]
    if len(dga_families) <= n_holdout:
        return

    import random
    rng = random.Random(99)
    held_out = rng.sample(dga_families, n_holdout)
    print(f"\n[train] Family hold-out: {n_holdout} DGA families → {held_out}")

    mask = df["family"].isin(held_out) | (df["family"] == "benign")
    df_ho = df[mask].copy()
    X_ho, y_ho = build_feature_matrix(df_ho)
    y_pred = pipeline.predict(X_ho)
    y_prob = pipeline.predict_proba(X_ho)[:, 1]
    print_metrics(y_ho, y_pred, y_prob, prefix="family-holdout")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    # Re-load wordlist if specified
    if args.wordlist:
        _load_wordlist(args.wordlist)
    elif os.environ.get("DGA_WORDLIST"):
        _load_wordlist(os.environ["DGA_WORDLIST"])

    # 1. Data
    df = load_data(args.csv)

    # 2. Features
    X, y = build_feature_matrix(df)

    # 3. Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, stratify=y, random_state=args.seed
    )
    print(f"\n[train] Train size: {len(X_train):,}   Test size: {len(X_test):,}")

    # 4. Cross-validation
    model = build_model(args.seed)
    print("\n[train] 5-fold cross-validation on training set …")
    cv_scores = cross_val_score(model, X_train, y_train, cv=5,
                                 scoring="roc_auc", n_jobs=-1)
    print(f"  CV ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # 5. Final fit on full training set
    print("\n[train] Fitting final model …")
    model.fit(X_train, y_train)

    # 6. Test-set evaluation
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    print_metrics(y_test, y_pred, y_prob, prefix="test-set")

    # 7. Family hold-out
    family_holdout(df, model, n_holdout=5)

    # 8. Feature importance (if LightGBM)
    clf = model.named_steps["clf"]
    if hasattr(clf, "feature_importances_"):
        importances = clf.feature_importances_
        fi = sorted(zip(FEATURE_NAMES, importances), key=lambda x: -x[1])
        print("\n[train] Feature importances (top 10):")
        for fname, imp in fi[:10]:
            print(f"  {fname:<22} {imp:.1f}")

    # 9. Save — also embed wordlist size in the pipeline object for reference
    n_words = len(_WORD_SET)
    model._dga_wordlist_size = n_words
    joblib.dump(model, args.output)
    print(f"\n[train] Saved to '{args.output}' (wordlist of {n_words:,} words stored inside)")


if __name__ == "__main__":
    main()
