# Congestion Prediction Model - Evaluation Report

## Model
XGBoost Classifier (xgboost-v1)

## Input Features
| Feature | Description |
|---------|-------------|
| packet_rate | Packets per second on observed flows |
| avg_latency_ms | Average round-trip latency in milliseconds |
| byte_rate | Bytes per second |
| flow_count | Number of active TCP/UDP flows in window |
| tcp_ratio | Fraction of traffic that is TCP (0.0 - 1.0) |

## Best Hyperparameters
| Param | Value |
|-------|-------|
| learning_rate | 0.05 |
| max_depth | 3 |
| n_estimators | 100 |
| subsample | 0.8 |

## Test Set Performance
| Metric | Score |
|--------|-------|
| Accuracy | 1.00 |
| Precision (Congested) | 1.00 |
| Recall (Congested) | 1.00 |
| F1-score (Congested) | 1.00 |
| ROC-AUC | 1.00 |

Support: 2400 test samples (1680 Normal, 720 Congested).

## Artifacts
- Trained model: `backend/ml/congestion/model.joblib`
- Fitted scaler: `backend/ml/congestion/scaler.joblib`
- Evaluation plots: `backend/ml/congestion/evaluation_plots.png`
- Saved metrics: `backend/ml/congestion/metrics.json`

## Limitations and Honest Caveats
1. **Perfect scores are a warning sign.** The synthetic dataset (`synthetic_traffic.csv`) was generated with non-overlapping feature ranges - normal traffic has `packet_rate` between 10-300, congested between 400-2000. A linear threshold solves this. XGBoost is overkill on this data. Real network traffic will not be this clean, and we expect significant performance drop when the model is deployed on real flows. The 100% scores measure how well the model fits the synthetic generator, not how well it predicts real congestion.

2. **No temporal modeling.** Each 5-second window is classified independently. Real network congestion builds over time. Day 10s LSTM aims to capture this.

3. **Threshold fixed at 0.5.** In production, tuning this for cost asymmetry (a false negative may cost more than a false positive, or vice versa, depending on use case) is important.

4. **Trained on 12000 rows of synthetic data.** Sample size is fine for the synthetic problem but does not generalize to real network distributions.

## Recommendations for Day 10+
- Make the synthetic generator add more overlap between normal and congested ranges (e.g., `packet_rate` overlap zone 250-450). Then re-train and report realistic metrics.
- Add at least 2 ambiguous test cases to the integration test (e.g., `packet_rate=350, tcp_ratio=0.7`) and document what the model predicts on borderline traffic.
- When LSTM lands on Day 10, compare both models on the same held-out test set.
