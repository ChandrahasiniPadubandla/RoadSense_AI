import os
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)

# Algorithms to compare
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier

from src.config import settings

class ModelComparisonPipeline:
    """
    Trains and benchmarks 7 distinct intent classification algorithms on traffic dataset:
    1. Logistic Regression
    2. Linear Support Vector Classifier (Calibrated for probabilities)
    3. Multinomial Naive Bayes
    4. Random Forest Classifier
    5. XGBoost Classifier
    6. Multi-Layer Perceptron (Neural Network)
    7. SGD Classifier (Modified Huber loss)

    Evaluates:
    - Train / Test Accuracy, Precision, Recall, F1-Score (Macro & Weighted)
    - Stratified 5-Fold Cross-Validation Accuracy & Std
    - Inference Latency (ms per query)
    - Model Size (KB)
    - Per-class precision, recall, F1-score
    - Confusion matrices
    """

    def __init__(self, dataset_path: str = None, models_dir: str = None):
        self.dataset_path = dataset_path or settings.DATASET_PATH
        self.models_dir = Path(models_dir or settings.MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            sublinear_tf=True,
            min_df=1,
            max_features=3500,
            strip_accents="unicode",
            lowercase=True
        )
        self.label_encoder = LabelEncoder()
        self.algorithms = self._define_algorithms()
        self.results = {}
        self.best_model_name = None

    def _define_algorithms(self) -> Dict[str, Any]:
        return {
            "Logistic Regression": LogisticRegression(
                C=2.0,
                solver="lbfgs",
                max_iter=500,
                random_state=42,
                class_weight="balanced"
            ),
            "Linear SVC (Calibrated)": CalibratedClassifierCV(
                estimator=LinearSVC(C=1.5, max_iter=2000, random_state=42),
                cv=3
            ),
            "Multinomial Naive Bayes": MultinomialNB(
                alpha=0.25
            ),
            "Random Forest": RandomForestClassifier(
                n_estimators=150,
                max_depth=15,
                random_state=42,
                class_weight="balanced"
            ),
            "XGBoost Classifier": XGBClassifier(
                n_estimators=120,
                learning_rate=0.1,
                max_depth=5,
                random_state=42,
                eval_metric="mlogloss"
            ),
            "Multi-Layer Perceptron (Neural Net)": MLPClassifier(
                hidden_layer_sizes=(128, 64),
                max_iter=500,
                random_state=42
            ),
            "SGD Classifier (Modified Huber)": SGDClassifier(
                loss="modified_huber",
                penalty="l2",
                alpha=1e-4,
                max_iter=1000,
                random_state=42
            )
        }

    def load_data(self) -> Tuple[pd.Series, pd.Series]:
        df = pd.read_csv(self.dataset_path)
        df = df.dropna(subset=["question", "intent"]).drop_duplicates(subset=["question"])
        X = df["question"].astype(str).str.strip()
        y = df["intent"].astype(str).str.strip()
        return X, y

    def run_benchmark(self, test_size: float = 0.2, cv_folds: int = 5) -> Dict[str, Any]:
        print("=" * 65)
        print("TRAFFIC & ACCIDENT CHATBOT: MULTI-ALGORITHM BENCHMARK")
        print("=" * 65)
        
        X_raw, y_raw = self.load_data()
        y_encoded = self.label_encoder.fit_transform(y_raw)
        classes = list(self.label_encoder.classes_)
        print(f"Total samples: {len(X_raw)} across {len(classes)} classes:")
        for idx, cls in enumerate(classes):
            print(f"  [{idx}] {cls} ({(y_encoded == idx).sum()} samples)")

        # Split into train/test with stratification
        X_train_raw, X_test_raw, y_train, y_test = train_test_split(
            X_raw, y_encoded, test_size=test_size, random_state=42, stratify=y_encoded
        )

        # Vectorization
        X_train_vec = self.vectorizer.fit_transform(X_train_raw)
        X_test_vec = self.vectorizer.transform(X_test_raw)
        X_all_vec = self.vectorizer.transform(X_raw)

        # Save TF-IDF vectorizer and LabelEncoder
        joblib.dump(self.vectorizer, self.models_dir / "tfidf_vectorizer.pkl")
        joblib.dump(self.label_encoder, self.models_dir / "label_encoder.pkl")

        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)

        comparison_summary = []
        detailed_reports = {}

        best_score = -1.0
        best_name = None

        for name, clf in self.algorithms.items():
            print(f"\n[Benchmarking] {name}...")
            start_train = time.time()

            # Train classifier on train split
            clf.fit(X_train_vec, y_train)
            train_time_ms = (time.time() - start_train) * 1000

            # Test predictions
            y_pred = clf.predict(X_test_vec)

            # Hold-out Metrics
            acc = float(accuracy_score(y_test, y_pred))
            p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
                y_test, y_pred, average="macro", zero_division=0
            )
            p_weighted, r_weighted, f1_weighted, _ = precision_recall_fscore_support(
                y_test, y_pred, average="weighted", zero_division=0
            )

            # 5-Fold Cross Validation on full dataset
            cv_scores = cross_val_score(clf, X_all_vec, y_encoded, cv=skf, scoring="accuracy")
            cv_mean = float(cv_scores.mean())
            cv_std = float(cv_scores.std())

            # Latency benchmark (measure time for 150 single query predictions)
            sample_query = "What is the accident risk between Banjara Hills and Hitech City?"
            sample_vec = self.vectorizer.transform([sample_query])
            
            for _ in range(10):
                _ = clf.predict(sample_vec)
                
            lat_start = time.time()
            reps = 150
            for _ in range(reps):
                _ = clf.predict(sample_vec)
            latency_ms = ((time.time() - lat_start) / reps) * 1000

            # Classification report & confusion matrix
            y_test_names = self.label_encoder.inverse_transform(y_test)
            y_pred_names = self.label_encoder.inverse_transform(y_pred)
            report_dict = classification_report(y_test_names, y_pred_names, output_dict=True, zero_division=0)
            cm = confusion_matrix(y_test, y_pred, labels=range(len(classes))).tolist()

            # Save model to disk
            safe_name = name.lower().replace(' ', '_').replace('(', '').replace(')', '')
            model_filename = f"{safe_name}.pkl"
            model_path = self.models_dir / model_filename
            joblib.dump(clf, model_path)
            model_size_kb = round(os.path.getsize(model_path) / 1024, 2)

            metric_record = {
                "model_name": name,
                "filename": model_filename,
                "accuracy": round(acc, 4),
                "f1_macro": round(f1_macro, 4),
                "f1_weighted": round(f1_weighted, 4),
                "precision_macro": round(p_macro, 4),
                "recall_macro": round(r_macro, 4),
                "cv_mean_accuracy": round(cv_mean, 4),
                "cv_std": round(cv_std, 4),
                "inference_latency_ms": round(latency_ms, 3),
                "training_time_ms": round(train_time_ms, 2),
                "model_size_kb": model_size_kb,
                "per_class": {cls: report_dict.get(cls, {}) for cls in classes},
                "confusion_matrix": cm
            }

            comparison_summary.append(metric_record)
            detailed_reports[name] = metric_record

            print(f"  -> Accuracy: {acc*100:.2f}%, F1-Macro: {f1_macro:.4f}, 5-Fold CV: {cv_mean*100:.2f}% (±{cv_std*100:.2f}%), Latency: {latency_ms:.2f}ms")

            # Selection criteria: Balanced combination of Cross-validation accuracy & Hold-out F1
            composite_score = (cv_mean * 0.6) + (f1_macro * 0.4)
            if composite_score > best_score:
                best_score = composite_score
                best_name = name

        # Sort summary by CV accuracy descending
        comparison_summary.sort(key=lambda x: (x["cv_mean_accuracy"], x["f1_macro"]), reverse=True)

        # Retrain top-ranked model on full dataset for maximum production accuracy
        self.best_model_name = best_name
        best_clf = self.algorithms[best_name]
        print(f"\n[Production Deployment] Retraining best model '{best_name}' on 100% dataset...")
        best_clf.fit(X_all_vec, y_encoded)
        joblib.dump(best_clf, self.models_dir / "best_model.pkl")

        # Save class label maps and metadata
        meta = {
            "classes": classes,
            "best_model": best_name,
            "total_samples": len(X_raw),
            "cv_folds": cv_folds,
            "comparison": comparison_summary
        }
        with open(self.models_dir / "model_comparison_results.json", "w") as f:
            json.dump(meta, f, indent=2)

        self.results = meta
        print("\nAll models trained and evaluated successfully!")
        return meta

if __name__ == "__main__":
    pipeline = ModelComparisonPipeline()
    res = pipeline.run_benchmark()
