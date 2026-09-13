#!/usr/bin/env python3
"""
SafePass AI — Citizen Road Hazard NLP Classifier Pipeline
Trains a dual NLP model (TF-IDF + Calibrated Classifier + Severity Regressor)
to auto-suggest Hazard Category and Severity score from citizen report text.
"""

import os
import json
import joblib
import random
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import classification_report, accuracy_score, mean_absolute_error


def generate_hazard_dataset(num_samples: int = 3500, random_seed: int = 42) -> pd.DataFrame:
    """Generate extensive realistic road hazard descriptions in English & Hinglish terminology."""
    random.seed(random_seed)
    np.random.seed(random_seed)

    categories = {
        "pothole": {
            "templates": [
                "Huge {adj} pothole on {loc}, {consequence}",
                "Multiple {adj} craters near {loc}, causing {consequence}",
                "Broken road surface with {adj} potholes near {loc}, {consequence}",
                "Deep crater cluster on the {loc}, {consequence}",
                "Severe tarmac damage and road depression, {consequence}",
                "{adj} pothole after the rain on {loc}, {consequence}",
                "Sunken asphalt patch and sharp pothole edge on {loc}, {consequence}",
                "Very rough road with uncovered potholes, {consequence}",
                "Small pothole near {loc}, manageable at normal speed",
                "Minor road crack and small depression on {loc}, needs patching",
            ],
            "adjectives": ["deep", "massive", "dangerous", "sharp", "crater-like", "unmarked", "hidden", "bad", "terrible", "huge"],
            "locations": ["left lane", "flyover ascent", "toll plaza approach", "middle carriage", "curve apex", "highway shoulder", "service lane", "bypass junction", "bridge entry", "expressway exit"],
            "consequences": ["two-wheelers slipping and falling", "causing sudden braking and traffic jam", "bent my car wheel rim", "dangerous at night with no streetlights", "heavy truck tire punctures", "vehicles swerving unpredictably into oncoming traffic", "high risk of bike skidding", "chances of vehicle bottoming out"],
            "severity_range": (3.5, 7.8),
            "critical_words": ["swerving", "bent rim", "skidding", "falling", "swerved into oncoming", "puncture"],
        },
        "waterlogging": {
            "templates": [
                "Severe waterlogging under {loc}, {consequence}",
                "Highway submerged with {depth} water near {loc}, {consequence}",
                "Heavy rainwater accumulation on {loc}, {consequence}",
                "Flash flood runoff completely flooding the {loc}, {consequence}",
                "Dangerous standing water puddle on {loc}, causing {consequence}",
                "Monsoon water stagnation near {loc}, {consequence}",
                "Drainage failure causing knee-deep water on {loc}, {consequence}",
                "Slight water accumulation on {loc}, slow down recommended",
                "Water pooling on the curve, vehicles losing traction",
                "Submerged carriageway after cloudburst near {loc}, {consequence}",
            ],
            "adjectives": ["deep", "dangerous", "stagnant", "submerged", "heavy", "murky", "knee-deep", "waist-deep"],
            "locations": ["railway underpass", "low-lying dip", "flyover descent", "culvert bridge", "toll barrier", "highway curve", "city bypass", "service road entry", "valley stretch"],
            "consequences": ["water entering vehicle engine causing breakdown", "severe aquaplaning hazard at high speed", "cars stuck in water, total gridlock", "bikes completely unable to pass", "two cars stalled in the middle of water", "traffic diverted to wrong side of highway", "water level reaching car doors", "invisible potholes hidden beneath muddy water"],
            "severity_range": (4.0, 8.8),
            "critical_words": ["submerged", "stalled", "aquaplaning", "bonnet", "engine failure", "gridlock", "knee-deep"],
        },
        "fog": {
            "templates": [
                "Extremely dense {adj} fog near {loc}, {consequence}",
                "Heavy smog and zero visibility on {loc}, {consequence}",
                "Thick blanket of fog near {loc}, visibility reduced to {vis}, {consequence}",
                "Early morning pea-soup fog on {loc}, {consequence}",
                "Sudden blinding fog bank near {loc}, {consequence}",
                "Dense winter mist in {loc}, {consequence}",
                "Stubble burning smog mixed with fog, {consequence}",
                "Light morning mist on {loc}, sight distance around 300 meters",
                "Patchy fog clouds drifting across {loc}, turn on fog lamps",
                "Zero sight distance on {loc}, extreme hazard for high speed motorists",
            ],
            "adjectives": ["dense", "blinding", "thick", "heavy", "choking", "pea-soup", "opaque", "whiteout"],
            "locations": ["river bridge corridor", "ghat sector", "valley depression", "expressway bypass", "open highway farmland stretch", "canal crossing", "forest sector", "mountain pass"],
            "consequences": ["sight distance less than 10 meters, pileup danger", "tail lights completely invisible until 5 meters", "trucks stopped with hazard lights on shoulder", "high probability of rear-end collision", "cannot see the road divider or edges", "all vehicles crawling at 15 km/h", "blind driving conditions with zero sightlines"],
            "severity_range": (4.5, 9.5),
            "critical_words": ["zero visibility", "less than 10 meters", "pileup", "blind", "whiteout", "rear-end collision"],
        },
        "accident": {
            "templates": [
                "Major collision involving {vehicles} near {loc}, {consequence}",
                "Car overturned and flipped on {loc}, {consequence}",
                "Multi-vehicle crash on {loc}, {consequence}",
                "Broken-down container truck stalled in the middle of {loc}, {consequence}",
                "Severe head-on collision between {vehicles} on {loc}, {consequence}",
                "Accident scene with debris scattered across {loc}, {consequence}",
                "Oil spill from overturned tanker on {loc}, road extremely slippery",
                "Minor side-swipe between two cars on {loc}, parked on shoulder",
                "Two-wheeler accident on {loc}, rider injured, ambulance requested",
                "Fatal crash near {loc}, police and rescue operations underway",
            ],
            "adjectives": ["fatal", "severe", "major", "horrific", "deadly", "catastrophic", "dangerous"],
            "vehicles": ["two multi-axle trucks", "a private bus and car", "a speeding tanker and SUV", "container trailer and dumper", "three cars in a chain collision"],
            "locations": ["fast overtaking lane", "ghat blind corner", "bridge expansion joint", "junction crossover", "expressway flyover", "undivided highway section", "toll approach curve"],
            "consequences": ["two lanes completely blocked, ambulance arriving", "oil and glass debris on road, vehicle flipped on roof", "fuel leaking on tarmac with fire hazard", "multiple casualties reported, emergency dispatch required", "heavy traffic backlog stretching 4 kilometers", "vehicle wreckage blocking northbound traffic", "police diverting traffic onto wrong lane"],
            "severity_range": (5.0, 9.8),
            "critical_words": ["flipped", "overturned", "fatal", "casualties", "head-on", "fuel leaking", "trapped", "blood", "ambulance"],
        },
        "blackspot": {
            "templates": [
                "Infamous crash blackspot on {loc} with {feature}, {consequence}",
                "Extremely dangerous blind hairpin curve near {loc}, {consequence}",
                "Deadly unscientific road design on {loc}, {consequence}",
                "Dangerous undivided stretch on {loc} with no median, {consequence}",
                "Lethal blind T-junction at {loc} without traffic signals, {consequence}",
                "Steep ghat descent with continuous hairpin bends, {consequence}",
                "Unmarked speed breaker on high-speed highway near {loc}, {consequence}",
                "High-fatality corridor with sudden sharp turn and no crash barrier",
                "Narrow bridge transition without warning signboards on {loc}",
                "Documented accident blackspot where weekly fatal accidents occur, {consequence}",
            ],
            "feature": ["no crash barrier over deep gorge", "sudden road narrowing from 4 lanes to 2 lanes", "blinding high beams and no streetlights", "severe reverse camber curvature", "unmarked median opening", "steep 12% slope gradient", "stray cattle crossing point"],
            "locations": ["ghat descent km 42", "national highway bypass", "expressway transition curve", "rural junction crossing", "mountain pass sector", "industrial corridor approach", "unlit bridge sector"],
            "consequences": ["frequent roll-overs and off-road crashes", "speeding trucks losing control on the slope", "head-on collisions during night overtaking", "multiple fatalities documented by police here", "blind overtaking causing catastrophic crashes", "braking failure on continuous descent", "unavoidable collision risk for unfamiliar motorists"],
            "severity_range": (5.5, 9.5),
            "critical_words": ["fatal", "hairpin", "gorge", "no crash barrier", "head-on", "weekly accidents", "blackspot", "unscientific"],
        }
    }

    records = []
    samples_per_cat = num_samples // len(categories)

    for cat, info in categories.items():
        for _ in range(samples_per_cat):
            template = random.choice(info["templates"])
            text = template.format(
                adj=random.choice(info.get("adjectives", ["bad"])),
                loc=random.choice(info.get("locations", ["highway"])),
                consequence=random.choice(info.get("consequences", ["slow down"])),
                depth=random.choice(["1 foot of", "2 feet deep", "waist-deep", "heavy flooded"]),
                vis=random.choice(["15 meters", "less than 20m", "50 meters", "zero sightlines"]),
                vehicles=random.choice(info.get("vehicles", ["truck and car"])),
                feature=random.choice(info.get("feature", ["sharp blind curve"]))
            )

            # Add occasional typos / punctuation / natural casing
            if random.random() < 0.25:
                text = text.lower()
            if random.random() < 0.15:
                text = text.replace(".", "!!").replace(",", " -")

            # Determine realistic severity based on language cues
            min_s, max_s = info["severity_range"]
            base_s = random.uniform(min_s, max_s)

            # Boost severity if critical urgency words appear
            urgency_hits = sum(1 for w in info["critical_words"] if w in text.lower())
            severity = base_s + (urgency_hits * 0.5)

            # Extreme keywords boost
            if any(w in text.lower() for w in ["fatal", "flipped", "overturned", "deadly", "casualties", "pileup", "zero visibility", "blood"]):
                severity = max(severity, 8.5)
            elif any(w in text.lower() for w in ["minor", "small", "manageable", "slight", "needs patching"]):
                severity = min(severity, 4.5)

            severity = round(float(np.clip(severity, 1.0, 9.9)), 1)

            records.append({
                "text": text,
                "category": cat,
                "severity": severity
            })

    # Shuffle
    random.shuffle(records)
    return pd.DataFrame(records)


def train_hazard_nlp_models():
    """Train TF-IDF Category Classifier & Severity Regressor and save artifacts."""
    print("📝 Generating diverse road hazard NLP training corpus (3,500 reports across 5 categories)...")
    df = generate_hazard_dataset(num_samples=3500, random_seed=42)

    X = df["text"]
    y_cat = df["category"]
    y_sev = df["severity"]

    X_train, X_test, y_cat_train, y_cat_test, y_sev_train, y_sev_test = train_test_split(
        X, y_cat, y_sev, test_size=0.20, random_state=42, stratify=y_cat
    )

    print(f"📊 Training text samples: {len(X_train)} | Test samples: {len(X_test)}")

    # 1. TF-IDF Feature Extractor
    print("🔤 Fitting Sublinear TF-IDF Vectorizer (ngram_range=(1, 2))...")
    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),
        sublinear_tf=True,
        max_features=4000,
        stop_words="english"
    )
    X_train_vec = tfidf.fit_transform(X_train)
    X_test_vec = tfidf.transform(X_test)

    # 2. Hazard Category Classifier (Multinomial Logistic Regression with Calibrated Probabilities)
    print("🎯 Training Category Classifier (Logistic Regression, C=3.0)...")
    clf = LogisticRegression(C=3.0, max_iter=1000, random_state=42)
    clf.fit(X_train_vec, y_cat_train)

    cat_preds = clf.predict(X_test_vec)
    cat_acc = accuracy_score(y_cat_test, cat_preds)

    print("\n" + "=" * 55)
    print("🏷️ HAZARD CATEGORY CLASSIFIER ACCURACY:")
    print(f"   Accuracy: {cat_acc:.4f} ({cat_acc * 100:.1f}%)")
    print("=" * 55)
    print(classification_report(y_cat_test, cat_preds, digits=3))

    # 3. Severity Regressor (Ridge Regression on TF-IDF word weights)
    print("⚖️ Training Severity Regressor (Ridge Regression, alpha=1.0)...")
    sev_model = Ridge(alpha=1.0, random_state=42)
    sev_model.fit(X_train_vec, y_sev_train)

    sev_preds = sev_model.predict(X_test_vec)
    sev_mae = mean_absolute_error(y_sev_test, sev_preds)
    print(f"   Severity Mean Absolute Error (MAE): {sev_mae:.3f} points on 1-10 scale\n")

    # Package model bundle
    bundle = {
        "vectorizer": tfidf,
        "classifier": clf,
        "severity_regressor": sev_model,
        "classes": clf.classes_.tolist(),
        "metrics": {
            "category_accuracy": round(float(cat_acc), 4),
            "severity_mae": round(float(sev_mae), 4),
            "algorithm": "TF-IDF (1,2) + LogisticRegression + Ridge",
            "classes": clf.classes_.tolist(),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
        }
    }

    output_dirs = [
        Path("/Users/parthsonkusare1340/Hack2026ps1/safepass-ai/model"),
        Path("/Users/parthsonkusare1340/Hack2026ps1/model"),
    ]

    for d in output_dirs:
        d.mkdir(parents=True, exist_ok=True)
        path = d / "hazard_classifier.joblib"
        joblib.dump(bundle, path, compress=3)
        print(f"💾 Saved Hazard Classifier artifact to: {path}")

        with open(d / "hazard_metrics.json", "w") as f:
            json.dump(bundle["metrics"], f, indent=2)

    # Demonstration Test Cases
    print("\n🔍 Running Inference Verification on Live Demo Texts:")
    test_texts = [
        "Massive car flipped over on the middle lane, fuel leaking and multi car pileup!",
        "Knee-deep water logging under the railway underpass, cars getting stuck and water entering engine",
        "Extremely thick pea-soup winter fog with sight distance less than 10 meters, tail lights invisible",
        "Deep pothole cluster on the flyover descent, multiple bike riders falling and skidding",
        "Infamous accident blackspot with lethal blind curve and no crash barrier over the gorge",
        "Small pothole near the highway shoulder, easily avoidable"
    ]

    for t in test_texts:
        vec = tfidf.transform([t])
        probs = clf.predict_proba(vec)[0]
        pred_idx = np.argmax(probs)
        cat = clf.classes_[pred_idx]
        conf = float(probs[pred_idx])
        sev = float(np.clip(sev_model.predict(vec)[0], 1.0, 9.9))

        print(f"\n📝 Text: \"{t}\"")
        print(f"   🤖 Suggested Category: {cat.upper()} (Confidence: {conf*100:.1f}%)")
        print(f"   ⚠️ Suggested Severity: {sev:.1f}/10")

    print("\n✅ NLP Hazard Classifier Training Complete!")


if __name__ == "__main__":
    train_hazard_nlp_models()
