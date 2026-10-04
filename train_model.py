"""
Phase 3: Predictive Maintenance ML Model
Trains a Random Forest classifier to detect pre-failure degradation patterns.
Uses ground truth failure events to create labels, trains on engineered features
from ASSET_SENSOR_STATS, and validates against hidden degrading/false-alarm assets.

Usage:
  uv run python train_model.py                    # loads from local CSV cache
  uv run python train_model.py --fetch-from-sf    # fetches fresh data from Snowflake first
"""
import os
import sys
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.impute import SimpleImputer
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GROUND_TRUTH_PATH = os.path.join(BASE_DIR, "data_pdm", "ground_truth_failures.csv")
MODEL_OUTPUT_PATH = os.path.join(BASE_DIR, "model_artifacts")
FEATURES_CACHE_PATH = os.path.join(MODEL_OUTPUT_PATH, "sensor_features.parquet")
os.makedirs(MODEL_OUTPUT_PATH, exist_ok=True)

FEATURE_COLS = [
    "VIBRATION_MM_S", "TEMPERATURE_C", "RPM", "MOTOR_CURRENT_A",
    "VIB_AVG_1H", "VIB_AVG_6H", "VIB_AVG_24H", "VIB_AVG_7D",
    "TEMP_AVG_1H", "TEMP_AVG_6H", "TEMP_AVG_24H", "TEMP_AVG_7D",
    "CURR_AVG_1H", "CURR_AVG_6H", "CURR_AVG_24H", "CURR_AVG_7D",
    "VIB_STD_6H", "VIB_STD_24H",
    "TEMP_STD_6H", "TEMP_STD_24H",
    "CURR_STD_6H", "CURR_STD_24H",
    "VIB_DELTA_1H", "VIB_DELTA_6H",
    "TEMP_DELTA_1H", "TEMP_DELTA_6H",
    "CURR_DELTA_1H", "CURR_DELTA_6H",
    "VIB_BASELINE_DEV_PCT", "TEMP_BASELINE_DEV_PCT", "CURR_BASELINE_DEV_PCT",
    "VIB_BREACH_COUNT_24H", "TEMP_BREACH_COUNT_24H",
    "SENSOR_DROPOUT_FLAG",
]

TRAIN_CUTOFF = pd.Timestamp("2026-09-01")


def fetch_from_snowflake():
    """Fetch ASSET_SENSOR_STATS from Snowflake via Snowpark and cache as parquet."""
    from snowpark_session import create_snowpark_session
    session = create_snowpark_session("PT09219")
    print("Fetching sensor features from Snowflake...")
    df = session.table("PREDICT_MAINT_DB.ANALYTICS.ASSET_SENSOR_STATS").to_pandas()
    df.to_parquet(FEATURES_CACHE_PATH, index=False)
    session.close()
    print(f"  Cached {len(df):,} rows to {FEATURES_CACHE_PATH}")
    return df


def load_data():
    """Load features from local parquet cache."""
    if not os.path.exists(FEATURES_CACHE_PATH):
        raise FileNotFoundError(
            f"Feature cache not found at {FEATURES_CACHE_PATH}.\n"
            "Run with --fetch-from-sf or use the export SQL to create it."
        )
    print(f"Loading features from {FEATURES_CACHE_PATH}...")
    df = pd.read_parquet(FEATURES_CACHE_PATH)
    df["READING_TS"] = pd.to_datetime(df["READING_TS"].astype(str).str.strip('"'))
    for col in FEATURE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    print(f"  Loaded {len(df):,} rows, {df['ASSET_ID'].nunique()} assets")
    return df


def load_ground_truth():
    print("Loading ground truth labels...")
    gt = pd.read_csv(GROUND_TRUTH_PATH)
    gt["degradation_start_ts"] = pd.to_datetime(gt["degradation_start_ts"])
    gt["failure_ts"] = pd.to_datetime(gt["failure_ts"])
    failures = gt[gt["event_type"] == "FAILURE"].copy()
    degrading = gt[gt["event_type"] == "DEGRADING_NOW"].copy()
    false_alarms = gt[gt["event_type"] == "FALSE_ALARM"].copy()
    print(f"  {len(failures)} failures, {len(degrading)} degrading-now, {len(false_alarms)} false-alarms")
    return failures, degrading, false_alarms


def create_labels(df, failures):
    """Label sensor readings: 1 if within a degradation window before failure, 0 otherwise."""
    df["LABEL"] = 0
    for _, row in failures.iterrows():
        mask = (
            (df["ASSET_ID"] == row["asset_id"])
            & (df["READING_TS"] >= row["degradation_start_ts"])
            & (df["READING_TS"] <= row["failure_ts"])
        )
        df.loc[mask, "LABEL"] = 1
    pos = df["LABEL"].sum()
    print(f"  Labels created: {pos:,} pre-failure ({pos / len(df) * 100:.2f}%), {len(df) - pos:,} normal")
    return df


def train_model(df):
    """Time-based split and Random Forest training."""
    train = df[df["READING_TS"] < TRAIN_CUTOFF].copy()
    test = df[df["READING_TS"] >= TRAIN_CUTOFF].copy()
    print(f"\nTrain/test split (cutoff {TRAIN_CUTOFF.date()}):")
    print(f"  Train: {len(train):,} rows ({train['LABEL'].sum():,} positive)")
    print(f"  Test:  {len(test):,} rows ({test['LABEL'].sum():,} positive)")

    imputer = SimpleImputer(strategy="median")
    X_train = imputer.fit_transform(train[FEATURE_COLS])
    X_test = imputer.transform(test[FEATURE_COLS])
    y_train, y_test = train["LABEL"].values, test["LABEL"].values

    print("\nTraining Random Forest (n_estimators=200, class_weight=balanced)...")
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_leaf=10,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    print("\n=== TEST SET CLASSIFICATION REPORT ===")
    print(classification_report(y_test, y_pred, target_names=["Normal", "Pre-Failure"]))

    return clf, imputer, test, y_test, y_pred, y_prob


def validate_hidden_assets(df, clf, imputer, degrading, false_alarms):
    """Check if model detects the 5 degrading assets and ignores 6 false-alarm assets."""
    print("\n=== HIDDEN ASSET VALIDATION ===")
    latest = df.sort_values("READING_TS").groupby("ASSET_ID").tail(48)

    print("\n-- Degrading-now assets (should have HIGH risk scores) --")
    deg_results = []
    for _, row in degrading.iterrows():
        asset_data = latest[latest["ASSET_ID"] == row["asset_id"]]
        if len(asset_data) == 0:
            continue
        X = imputer.transform(asset_data[FEATURE_COLS])
        probs = clf.predict_proba(X)[:, 1]
        max_prob = probs.max()
        mean_prob = probs.mean()
        detected = max_prob > 0.5
        status = "DETECTED" if detected else "MISSED"
        print(f"  {row['asset_id']} ({row['failure_mode']}): max_risk={max_prob:.3f}, avg_risk={mean_prob:.3f} [{status}]")
        deg_results.append(detected)
    deg_detection_rate = sum(deg_results) / len(deg_results) * 100 if deg_results else 0
    print(f"  Detection rate: {deg_detection_rate:.0f}% ({sum(deg_results)}/{len(deg_results)})")

    print("\n-- False-alarm assets (should have LOW risk scores) --")
    fa_assets = false_alarms["asset_id"].unique()
    fa_results = []
    for asset_id in fa_assets:
        asset_data = latest[latest["ASSET_ID"] == asset_id]
        if len(asset_data) == 0:
            continue
        X = imputer.transform(asset_data[FEATURE_COLS])
        probs = clf.predict_proba(X)[:, 1]
        max_prob = probs.max()
        flagged = max_prob > 0.5
        status = "FALSE POSITIVE" if flagged else "CORRECT"
        print(f"  {asset_id}: max_risk={max_prob:.3f} [{status}]")
        fa_results.append(not flagged)
    fa_correct_rate = sum(fa_results) / len(fa_results) * 100 if fa_results else 0
    print(f"  Correct rejection rate: {fa_correct_rate:.0f}% ({sum(fa_results)}/{len(fa_results)})")

    return deg_detection_rate, fa_correct_rate


def plot_feature_importance(clf, output_dir):
    importance = pd.Series(clf.feature_importances_, index=FEATURE_COLS).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(10, 10))
    importance.plot(kind="barh", ax=ax, color="#1f77b4")
    ax.set_title("Feature Importance (Random Forest)")
    ax.set_xlabel("Importance")
    plt.tight_layout()
    path = os.path.join(output_dir, "feature_importance.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Feature importance plot saved to {path}")


def plot_confusion_matrix(y_test, y_pred, output_dir):
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=["Normal", "Pre-Failure"],
                yticklabels=["Normal", "Pre-Failure"], ax=ax)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix")
    plt.tight_layout()
    path = os.path.join(output_dir, "confusion_matrix.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Confusion matrix saved to {path}")


def register_model(clf, imputer, df):
    """Register model in Snowflake Model Registry."""
    from snowpark_session import create_snowpark_session
    from snowflake.ml.registry import Registry
    from sklearn.pipeline import Pipeline

    session = create_snowpark_session("PT09219")
    print("\nRegistering model in Snowflake Model Registry...")
    reg = Registry(session=session, database_name="PREDICT_MAINT_DB", schema_name="ANALYTICS")

    sample_input = df[FEATURE_COLS].head(10).copy()
    sample_input = pd.DataFrame(imputer.transform(sample_input), columns=FEATURE_COLS)

    pipeline = Pipeline([
        ("imputer", imputer),
        ("classifier", clf),
    ])

    mv = reg.log_model(
        model=pipeline,
        model_name="PREDICT_MAINT_FAILURE_DETECTOR",
        version_name="V1",
        sample_input_data=sample_input,
        comment="Random Forest classifier for pre-failure degradation detection. "
                "Trained on 34 features from ASSET_SENSOR_STATS.",
    )
    print(f"  Model registered: PREDICT_MAINT_DB.ANALYTICS.PREDICT_MAINT_FAILURE_DETECTOR version V1")
    session.close()
    return mv


def main():
    print("=" * 60)
    print("PHASE 3: Predictive Maintenance ML Model Training")
    print("=" * 60)

    if "--fetch-from-sf" in sys.argv:
        df = fetch_from_snowflake()
        df["READING_TS"] = pd.to_datetime(df["READING_TS"])
    else:
        df = load_data()

    failures, degrading, false_alarms = load_ground_truth()
    df = create_labels(df, failures)

    clf, imputer, test_df, y_test, y_pred, y_prob = train_model(df)

    deg_rate, fa_rate = validate_hidden_assets(df, clf, imputer, degrading, false_alarms)

    plot_feature_importance(clf, MODEL_OUTPUT_PATH)
    plot_confusion_matrix(y_test, y_pred, MODEL_OUTPUT_PATH)

    model_path = os.path.join(MODEL_OUTPUT_PATH, "failure_detector.pkl")
    with open(model_path, "wb") as f:
        pickle.dump({"classifier": clf, "imputer": imputer, "features": FEATURE_COLS}, f)
    print(f"\nModel saved to {model_path}")

    if "--register" in sys.argv:
        print("\nRegistering model in Snowflake...")
        try:
            register_model(clf, imputer, df)
        except Exception as e:
            print(f"  Warning: Model registration failed ({e}). Model saved locally.")

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print(f"  Degrading asset detection:  {deg_rate:.0f}%")
    print(f"  False alarm rejection:      {fa_rate:.0f}%")
    print(f"  F1 (test set):              {f1_score(y_test, y_pred):.3f}")
    print(f"  Artifacts:                  {MODEL_OUTPUT_PATH}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
