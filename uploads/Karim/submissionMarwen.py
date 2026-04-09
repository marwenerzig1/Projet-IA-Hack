
import os
import argparse
import pandas as pd
import numpy as np
import json
import joblib


from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.neighbors import KNeighborsClassifier



# 🔹 Train
def train_model(train_csv, model_dir):
    df = pd.read_csv(train_csv)

    X = df.drop("Species", axis=1)
    y = df["Species"]

    if "Id" in X.columns:
        X = X.drop("Id", axis=1)

    model = KNeighborsClassifier(n_neighbors=5)
    model.fit(X, y)

    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(model, os.path.join(model_dir, "model.joblib"))

    print("Modèle entraîné et sauvegardé")


# 🔹 Load
def load_model(model_dir):
    path = os.path.join(model_dir, "model.joblib")
    if not os.path.exists(path):
        raise FileNotFoundError("Modèle non trouvé")
    return joblib.load(path)





# 🔹 Evaluate + save JSON
def evaluate_model(model, test_csv, output_json):
    df = pd.read_csv(test_csv)

    if "Species" not in df.columns:
        raise ValueError("Le test doit contenir 'Species'")

    y_true = df["Species"]
    X = df.drop("Species", axis=1)

    if "Id" in X.columns:
        X = X.drop("Id", axis=1)

    y_pred = model.predict(X)

    acc = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, average='macro')
    recall = recall_score(y_true, y_pred, average='macro')
    f1 = f1_score(y_true, y_pred, average='macro')

    cm = confusion_matrix(y_true, y_pred)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
    diag_mean = np.mean(np.diag(cm_norm))

    metrics = {
        "accuracy": float(acc),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "diag_mean": float(diag_mean)
    }

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w") as f:
        json.dump(metrics, f, indent=4)

    print(f" Métriques sauvegardées dans {output_json}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline ML Iris")

    subparsers = parser.add_subparsers(dest="command")

    # Train
    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("train_csv")
    train_parser.add_argument("model_dir")

    # Test (évaluation)
    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("test_csv")
    test_parser.add_argument("model_dir")
    test_parser.add_argument("output_json")


    args = parser.parse_args()

    if args.command == "train":
        train_model(args.train_csv, args.model_dir)

    elif args.command == "test":
        model = load_model(args.model_dir)
        evaluate_model(model, args.test_csv, args.output_json)


    else:
        parser.print_help()
