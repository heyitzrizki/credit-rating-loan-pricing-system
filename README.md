# 📊 Credit Rating & ECL Stress Testing Engine  
### Hybrid TCN-Attention + XGBoost for Credit Risk Scoring, Expected Credit Loss, and Stress Testing

---

## 🚀 Overview

This project is an end-to-end **credit risk decision-support system** designed to simulate how financial institutions can connect machine learning credit scoring with business-facing credit rating, expected loss estimation, portfolio monitoring, and stress testing.

The system combines:

- **Temporal behavior modeling** using TCN + Attention
- **Static borrower risk modeling** using XGBoost
- **Adjusted default risk estimation** through probability calibration
- **AAA–D credit grade assignment**
- **Expected Credit Loss simulation**
- **Portfolio-level macro stress testing**
- **Borrower-level stress scenario analysis**
- **High-risk borrower watchlist**
- **Explainability for business users**

This project is designed as a portfolio-ready prototype for **credit rating model development (신용평가모형 개발)** by translating model outputs into practical credit risk decisions.

---

## 💡 Why This Project Matters

Many machine learning credit scoring projects stop at prediction accuracy. This project goes further by connecting model output to credit risk management workflows:

    Borrower Data
       ↓
    Risk Model
       ↓
    Adjusted Default Risk
       ↓
    Credit Grade
       ↓
    Decision Recommendation
       ↓
    Expected Credit Loss
       ↓
    Stress Testing & Portfolio Monitoring

The goal is not only to predict borrower risk, but also to show how a model can support:

- Credit approval strategy
- Manual underwriting
- Portfolio risk monitoring
- Expected loss estimation
- Stress scenario analysis
- High-risk borrower prioritization

---

## 🎯 Key Objectives

- Estimate borrower default risk using static and temporal information
- Convert risk estimates into an interpretable AAA–D credit grade
- Translate credit grades into business recommendations: **Approve**, **Review**, or **Reject**
- Estimate expected credit loss using:

    Expected Loss = Estimated Default Risk × Loss Severity Assumption × Credit Exposure

- Simulate portfolio-level expected loss under macroeconomic stress scenarios
- Simulate borrower-level rating migration under adverse stress assumptions
- Provide explainability through main risk drivers and temporal attention

---

## 🧠 Model Architecture

### Hybrid Credit Risk Model

    Temporal Repayment Data
       ↓
    TCN + Attention Encoder
       ↓
    Temporal Risk Embedding
       ↓
    Static Borrower Features + Engineered Features
       ↓
    XGBoost Risk Model
       ↓
    Raw Risk Score
       ↓
    Probability Calibration
       ↓
    Adjusted Default Risk Estimate
       ↓
    Credit Grade + Business Recommendation

### Components

| Component | Purpose |
|---|---|
| TCN Encoder | Captures sequential repayment behavior |
| Attention Layer | Highlights important time periods in borrower history |
| XGBoost | Final borrower risk prediction model |
| Probability Calibration | Converts raw model scores into more interpretable risk estimates |
| Credit Rating Layer | Maps risk estimates into AAA–D grades |
| ECL Layer | Estimates expected loss using PD × LGD × EAD logic |
| Stress Testing Layer | Simulates portfolio and borrower-level risk under adverse conditions |
| Streamlit Dashboard | Converts the model pipeline into an interactive business-facing application |

---

## 📊 Dashboard Pages

### 1. Executive Dashboard

Provides a high-level view of portfolio health:

- Total borrowers
- Portfolio average estimated risk
- Approval / review / rejection rate
- High-risk share
- Baseline expected loss
- Severe stress expected loss
- Credit grade distribution
- Recommended action mix

---

### 2. About the System

Explains the business purpose, methodology, governance, and limitations of the system.

This page is designed for non-technical users and clarifies:

- What the model does
- How borrower rating works
- How expected loss is calculated
- How stress testing should be interpreted
- Why the system is decision-support only

---

### 3. Borrower Rating & Stress Scenario

Allows users to select an existing borrower and review:

- Model risk score
- Adjusted default risk estimate
- Credit grade
- Recommendation
- Risk segment
- Borrower profile
- Main risk drivers
- Borrower-level stress scenario

The stress scenario is **not** a new-borrower application form. It starts from an existing borrower and applies assumptions such as:

- Income decline
- Credit exposure increase
- Employment instability
- Repayment behavior deterioration

The page then shows rating migration and expected loss impact.

---

### 4. Portfolio Monitoring

Monitors portfolio-level risk concentration:

- Borrower distribution by credit grade
- Borrower distribution by risk segment
- Observed repayment difficulty by grade
- Average estimated risk by grade
- Recommended action mix
- Policy comparison
- Expected loss scenario snapshot

---

### 5. High-Risk Watchlist

Provides an operational review list for borrowers with elevated repayment risk.

Users can filter by:

- Estimated default risk
- Credit grade
- Review priority
- Observed repayment difficulty in the test dataset

The page helps prioritize borrowers for:

- Immediate review
- Manual underwriting
- Analyst review
- Routine monitoring

---

### 6. ECL & Macro Stress Testing

Estimates expected credit loss under baseline and stressed macroeconomic assumptions.

The ECL framework uses:

    ECL = Estimated Default Risk × Loss Severity Assumption × Credit Exposure

The page includes:

- Base expected loss
- Total credit exposure
- Average estimated default risk
- Average loss severity assumption
- Total expected loss by scenario
- Expected loss uplift
- Expected loss by credit grade
- Borrower-level base ECL table

---

## 🧾 Credit Rating Framework

The system uses a fixed business-friendly rating scale for borrower-level interpretation.

| Grade | Risk Level | Business Recommendation |
|---|---|---|
| AAA | Very Low Risk | Approve |
| AA | Low Risk | Approve |
| A | Moderate-Low Risk | Approve |
| BBB | Medium Risk | Review |
| BB | Elevated Risk | Review |
| B | High Risk | Reject |
| CCC | Very High Risk | Reject |
| CC | Severe Risk | Reject |
| D | Default-like / Extreme Risk | Reject |

The rating scale is used to support business interpretation and should be treated as a decision-support layer, not a regulatory rating system.

---

## 📉 Expected Credit Loss Framework

Expected Credit Loss is calculated as:

    ECL = PD × LGD × EAD

In this project:

| Component | Implementation |
|---|---|
| PD | Adjusted default risk estimate from the calibrated credit rating model |
| LGD | Rating-based loss severity assumption |
| EAD | Credit exposure proxy based on approved credit amount |

Because the Home Credit dataset does not contain actual recovery, write-off, or collateral liquidation outcomes, LGD is not estimated as a supervised model. Instead, it is implemented as a rating-based assumption for expected loss simulation.

---

## 🌪️ Stress Testing Framework

The project includes two stress testing layers.

### 1. Portfolio Macro Stress Testing

Portfolio-level ECL is evaluated under macroeconomic scenarios:

- Baseline
- Monetary Tightening
- Mild Recession
- Severe Downturn

The macro stress module uses literature-informed sensitivity assumptions to adjust:

- Default risk
- Loss severity
- Credit exposure

These assumptions are not estimated as causal macroeconomic effects from the dataset. They are used for scenario simulation and portfolio sensitivity analysis.

### 2. Borrower-Level Stress Scenario

Borrower-level stress testing starts from an existing borrower and applies adverse assumptions such as:

- Income decline
- Higher credit exposure
- Employment instability
- Worse repayment behavior

The system then compares:

- Baseline risk vs stressed risk
- Baseline grade vs stressed grade
- Baseline recommendation vs stressed recommendation
- Baseline expected loss vs stressed expected loss

---

## 📈 Explainability

The system provides multiple explanation layers:

### Main Risk Drivers

Business-friendly labels for the borrower-level factors that increased or reduced estimated default risk.

### Temporal Attention

Highlights which historical time periods received more model attention.

### Portfolio-Level Risk Distribution

Shows how risk is distributed across grades, decisions, and segments.

### Expected Loss Decomposition

Shows how exposure and expected loss are distributed by credit grade.

Explanation outputs should be interpreted as model explanation support, not causal proof.

---

## 🧪 Model Evaluation

The model evaluation focuses on predictive quality and probability usability.

Metrics include:

- ROC-AUC
- PR-AUC
- Brier Score
- Expected Calibration Error

The evaluation focus is not only raw classification accuracy. The system emphasizes calibrated risk estimation because credit decisions and expected loss calculations require meaningful probability outputs.

---

## 📦 Project Structure

    Credit-Rating-System/
    │
    ├── app/
    │   ├── streamlit_app.py
    │   ├── utils.py
    │   └── pages/
    │       ├── 1_Overview.py
    │       ├── 2_About_the_System.py
    │       ├── 3_Borrower_Rating_Stress_Scenario.py
    │       ├── 4_Portfolio_Segmentation.py
    │       ├── 5_Watchlist.py
    │       └── 6_ECL_Stress_Testing.py
    │
    ├── artifacts/
    │   ├── model files (.joblib, .pt)
    │   ├── processed datasets (.csv)
    │   ├── credit rating outputs
    │   ├── expected loss outputs
    │   └── stress testing outputs
    │
    ├── notebooks/
    │   └── credit_rating_final.ipynb
    │
    └── requirements.txt

If your local file names still use the previous names, the dashboard will still run, but the updated naming above is recommended for a cleaner Streamlit sidebar.

---

## ⚙️ Installation

    git clone https://github.com/heyitzrizki/Credit-Rating-System.git
    cd Credit-Rating-System
    pip install -r requirements.txt

---

## ▶️ Run the App

    streamlit run app/streamlit_app.py

---

## 🛠️ Tech Stack

- Python
- pandas
- NumPy
- scikit-learn
- XGBoost
- PyTorch
- Streamlit
- Plotly
- SHAP
- joblib

---

## 🧩 Design Philosophy

This project is built around three principles.

### 1. Business usability over raw model output

The model does not only return a score. It translates the score into grades, recommendations, portfolio views, and expected loss.

### 2. Risk management workflow

The dashboard follows credit risk workflow logic:

    Borrower Scoring → Rating → Decisioning → Monitoring → Watchlist → Stress Testing

### 3. Transparent limitations

The system clearly separates:

- Model-estimated risk
- Assumption-based expected loss
- Scenario-based stress testing
- Final business decision-making

---

## ⚠️ Limitations

This project is a portfolio prototype and has important limitations:

- It uses a historical benchmark dataset, not a live bank production database.
- The system does not include a real-time scoring API.
- LGD is assumption-based because actual recovery and write-off outcomes are unavailable.
- EAD is proxied using approved credit amount.
- Macro stress testing uses scenario assumptions rather than estimated causal macroeconomic models.
- Borrower-level stress testing is a what-if overlay, not a retrained model.
- Model explanations are interpretability aids, not causal evidence.
- Final credit decisions should remain subject to analyst review, policy rules, and governance controls.

---

## 🔮 Future Improvements

Potential future upgrades include:

- Real-time scoring API
- Automated feature pipeline
- Model monitoring and drift detection
- Macroeconomic data integration
- Estimated LGD and EAD models using richer recovery and exposure data
- Reject inference framework
- Fairness and bias monitoring
- Challenger model comparison
- Automated retraining pipeline
- Deployment with authentication and role-based access

---

## 👤 Author

**Rizki Anwar**  
Business Analytics & Machine Learning  
Credit Risk Modeling | Machine Learning | Financial Analytics

---

## 📌 Notes

This project is intended for:

- Portfolio demonstration
- Credit risk modeling practice
- Financial analytics learning
- Simulation of real-world credit rating model development workflows

It is not intended to be used as an automated final credit approval system.
