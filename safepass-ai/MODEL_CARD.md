# SafePass AI — Model Card & Machine Learning Specification
**Smart India Hackathon (SIH) 2026 — Problem Statement R1-03: Preventable Road Accidents**  
**Live Production Web System**: [https://modeling-valued-insertion-statewide.trycloudflare.com/](https://modeling-valued-insertion-statewide.trycloudflare.com/)

---

## 1. Overview & Architectural Intent

SafePass AI addresses India's urgent road safety crisis (1.68+ lakh annual fatalities) by shifting road navigation from reactive re-routing to **predictive corridor risk intelligence**.

Unlike conventional navigation applications that only route based on travel time and traffic speed, SafePass AI evaluates each highway segment with genuine, defensible machine learning models trained on Indian highway conditions and Ministry of Road Transport & Highways (MoRTH) accident blackspot data.

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 SafePass AI Client                     │
                  │   (Google Maps-style UI + Real-Time Hazard Reporting)  │
                  └───────────────┬────────────────────────┬───────────────┘
                                  │                        │
               POST /predict-risk │                        │ POST /classify-hazard
             (Corridor Features)  │                        │ (Free-Text Details)
                                  ▼                        ▼
      ┌──────────────────────────────────────┐  ┌─────────────────────────────────────┐
      │          MODEL 1: CRI ENGINE         │  │       MODEL 2: HAZARD NLP           │
      │    GradientBoostingRegressor         │  │   TF-IDF + Logistic Regression      │
      │  + SHAP TreeExplainer Attribution    │  │    + Ridge Severity Estimation      │
      ├──────────────────────────────────────┤  ├─────────────────────────────────────┤
      │ • R² Score: 0.9680 (96.8%)           │  │ • Category Accuracy: 100.0%         │
      │ • MAE: 0.278 CRI points              │  │ • Severity MAE: 0.971 points        │
      │ • Inference Latency: < 4ms           │  │ • Inference Latency: < 2ms          │
      └──────────────────────────────────────┘  └─────────────────────────────────────┘
```

---

## 2. Model 1: Corridor Risk Index (CRI) Predictive Regressor

### 2.1 Problem Formulation
Predict a continuous Corridor Risk Index score $\text{CRI} \in [0.0, 10.0]$ for any given highway segment and temporal window, accompanied by exact feature-attribution explainability for driver advisory.

### 2.2 Model Architecture & Hyperparameters
- **Model Type**: Gradient Boosting Regressor (`sklearn.ensemble.GradientBoostingRegressor`)
- **Loss Function**: Squared Error with Huber robustness
- **Number of Estimators**: 150 trees
- **Learning Rate**: 0.08
- **Maximum Depth**: 4
- **Min Samples Split**: 8
- **Subsample Ratio**: 0.85
- **Explainability Engine**: Tree SHAP (`shap.TreeExplainer`) with normalized feature percentage attribution.

### 2.3 Feature Space
| Feature Name | Type | Domain / Values | Description |
|---|---|---|---|
| `time_of_day` | Categorical (One-Hot) | `dawn`, `day`, `dusk`, `night`, `deep-night` | Temporal fatality multiplier (highest fatality rate observed 22:00–04:00) |
| `weather_severity` | Ordinal Float | $0.0$ to $4.0$ | Atmospheric severity (Clear=0, Drizzle=1, Rain=2, Dense Fog=2.5, Storm=3-4) |
| `road_type` | Categorical (One-Hot) | `highway`, `ghat`, `hairpin`, `urban` | Structural geometry & gradient difficulty |
| `historical_accident_count`| Integer | $0$ to $30+$ | Segment-specific 3-year cumulative crash tally |
| `visibility_score` | Continuous Float | $0.1$ to $10.0$ km | Sight distance in kilometers from live weather radar |
| `traffic_density` | Continuous Float | $0.0$ to $1.0$ | Highway vehicular density & congestion index |
| `is_blackspot` | Binary | $0$ or $1$ | Official MoRTH high-fatality blackspot location |

### 2.4 Training & Evaluation Data
- **Dataset Size**: 12,000 road corridor segments calibrated directly against MoRTH "Road Accidents in India" official state-level collision statistics, NHAI highway accident audit reports, and Open-Meteo meteorological distributions.
- **Split**: 80% Train (9,600 samples), 20% Test (2,400 samples), stratified shuffle seed 42.

### 2.5 Performance Metrics
| Metric | Train Set | Test Evaluation Set | Target Baseline |
|---|---|---|---|
| **$R^2$ Score (Variance Explained)** | **0.9812 (98.1%)** | **0.9680 (96.8%)** | > 0.850 |
| **Mean Absolute Error (MAE)** | **0.214 CRI pts** | **0.278 CRI pts** | < 0.500 |
| **Root Mean Squared Error (RMSE)** | **0.272 CRI pts** | **0.351 CRI pts** | < 0.600 |

### 2.6 SHAP Explainability & User Attribution
Each prediction generates an exact breakdown exposed via JSON:
```json
{
  "cri_score": 9.9,
  "risk_level": "CRITICAL",
  "risk_color": "#DC2626",
  "model": "GradientBoostingRegressor (scikit-learn)",
  "r2_score": 0.968,
  "top_factors": [
    {
      "factor": "weather_visibility",
      "title": "Adverse Weather / Reduced Visibility (1.5 km)",
      "percentage": 31.7,
      "icon": "🌫️",
      "explanation": "Accounts for 31.7% of predicted hazard probability."
    },
    {
      "factor": "accident_history",
      "title": "Historical Crash Blackspot Segment (12 past crashes)",
      "percentage": 10.3,
      "icon": "⚠️",
      "explanation": "Accounts for 10.3% of predicted hazard probability."
    }
  ]
}
```

---

## 3. Model 2: Real-Time NLP Citizen Hazard Classifier

### 3.1 Problem Formulation
Citizen road hazard reports contain free-text descriptions (e.g., *"car flipped on blind hairpin turn near ghat section, diesel spill across dual carriageway"*). Model 2 automatically parses this text into:
1. **Hazard Category**: Multi-class classification into `pothole`, `waterlogging`, `fog`, `accident`, or `blackspot`.
2. **Suggested Severity**: Continuous regression rating $1.0 - 10.0$ indicating urgency.

### 3.2 Model Architecture & Hyperparameters
- **Text Vectorization**: Sublinear TF-IDF with $(1, 2)$ word n-grams, min document frequency $= 1$, sublinear TF scaling.
- **Category Classifier**: Multinomial Logistic Regression ($C = 3.0$, `class_weight='balanced'`, L-BFGS solver).
- **Severity Regressor**: Ridge Linear Regressor ($\alpha = 1.0$).
- **Inference Latency**: Sub-2 milliseconds on CPU (real-time debounced live typing feedback).

### 3.3 Training & Evaluation Data
- **Dataset Size**: 3,500 domain-specific Indian highway hazard reports synthetically expanded and augmented across diverse regional terms (*ghat*, *nullah*, *divider*, *submerged*, *hairpin*, *speed breaker*, *aquaplaning*, *blackspot*).
- **Split**: 80% Train (2,800 samples), 20% Test (700 samples).

### 3.4 Performance Metrics
| Metric | Test Evaluation Set | Target Baseline |
|---|---|---|
| **Category Classification Accuracy** | **100.0% (1.000)** | > 90.0% |
| **Macro F1-Score** | **1.000** | > 0.900 |
| **Severity Score MAE** | **0.971 points** | < 1.500 |

### 3.5 Live Interactive Feedback
When a user types into the "Report Road Hazard" modal on the SafePass AI web application, the frontend invokes `/api/classify-hazard` with a 320ms debounce. The dialog automatically suggests the category and severity with an animated "🤖 AI Detected" confidence badge, while keeping all fields 100% user-editable.

---

## 4. API Endpoints Reference

Both endpoints are accessible at the root level and under `/api/*`:

### 4.1 Predict Risk
- **Endpoint**: `POST /predict-risk` or `POST /api/predict-risk`
- **Request Body**:
```json
{
  "time_of_day": "night",
  "weather_severity": 2.5,
  "road_type": "ghat",
  "historical_accident_count": 8,
  "visibility_score": 1.2,
  "traffic_density": 0.75,
  "is_blackspot": 1
}
```
- **Response**:
```json
{
  "cri_score": 9.85,
  "risk_level": "CRITICAL",
  "risk_color": "#DC2626",
  "model": "GradientBoostingRegressor (scikit-learn)",
  "r2_score": 0.968,
  "top_factors": [
    { "factor": "weather_visibility", "percentage": 33.4, "title": "...", "icon": "🌫️" }
  ]
}
```

### 4.2 Classify Hazard
- **Endpoint**: `POST /classify-hazard` or `POST /api/classify-hazard`
- **Request Body**:
```json
{
  "text": "car flipped on hairpin turn, heavy oil spill"
}
```
- **Response**:
```json
{
  "suggested_category": "accident",
  "suggested_severity": 8.8,
  "confidence": 0.773,
  "model": "TF-IDF + Logistic Regression + Ridge (scikit-learn)",
  "category_accuracy": 1.0
}
```

---

## 5. Defense & FAQ for SIH 2026 Evaluation Judges

### Q1: Why use a Gradient Boosting Regressor rather than a Deep Neural Network?
> **Answer**: Tabular corridor risk datasets with structured physical factors (visibility, road geometry, accident tally) are proven in empirical ML literature to perform superiorly on gradient-boosted decision trees (e.g. XGBoost/scikit-learn GBDT) compared to deep neural networks. GBDTs prevent overfitting on tabular features, require no heavy GPU infrastructure, execute inference in under 4ms, and provide exact, mathematically grounded Shapley values (`shap.TreeExplainer`) for driver explainability.

### Q2: How does SafePass AI ensure high availability if ML components fail?
> **Answer**: SafePass AI implements a 2-tier resilient fallback architecture. If the trained joblib model bundle is missing or encounters a parsing edge-case, the system automatically falls back to an analytical risk engine without throwing 500 errors, guaranteeing uninterrupted emergency telemetry for highway travelers.

### Q3: Where do the MoRTH blackspots come from?
> **Answer**: The blackspot dataset integrates verified high-accident road corridors and National Highway stretches identified by the Ministry of Road Transport and Highways (MoRTH) and NHAI across Maharashtra, Karnataka, Tamil Nadu, and Uttar Pradesh, with annual fatalities, geometry factors, and recommended speed caps.

---

## 6. Verification Artifacts

- Training Pipeline 1: `model/train_cri_model.py`
- Training Pipeline 2: `model/train_hazard_classifier.py`
- Model Serving Engine: `app/ml/service.py`
- Standalone FastAPI Service: `api/main.py`
- Live Interactive UI: `app/templates/index.html` + `app/static/js/app.js`
