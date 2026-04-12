# FinTrack AI

FinTrack AI is a personal finance analytics dashboard that I built to explore how structured financial data can be transformed into actionable insights using KPI modeling, visualization dashboards, and goal feasibility estimation.

This project reflects how I approach data analysis problems:

raw inputs → meaningful metrics → interpretable dashboards → decision-support insights

Portfolio Project — Built for Data Analyst role preparation.

---

## Live Application

https://fintrack-ai.onrender.com

---

## Why I Built This Project

While preparing for Data Analyst roles, I wanted to build something beyond static charts.

My goal was to demonstrate:

• KPI definition  
• ratio modeling  
• behavioral interpretation  
• forecasting logic  
• dashboard design thinking  
• insight generation from structured datasets  

FinTrack AI represents that effort.

---

## What This Dashboard Analyzes

The system evaluates financial behavior using derived indicators such as:

• savings efficiency  
• surplus generation capacity  
• expense category dominance  
• allocation patterns  
• goal feasibility timelines  
• recommended savings thresholds  

Instead of only displaying numbers, the dashboard explains what those numbers mean.

---

## Example Metrics Generated

The application automatically calculates:

• Monthly income  
• Monthly expenses  
• Net disposable income  
• Savings rate (%)  
• Top expense category  
• Category distribution share  
• Monthly savings capacity  
• Goal completion timeline estimate  

These simulate real-world personal finance analytics indicators.

---

## Savings Rate Modeling

Savings efficiency is calculated using:

Savings Rate = (Monthly Savings / Monthly Income) × 100

Example output:

Savings Rate: 22.3%  
Status: On Track

This helps evaluate whether saving behavior aligns with recommended benchmarks.

---

## Income vs Expense Flow Analysis

FinTrack AI compares income against spending behavior to estimate surplus capacity.

This helps identify:

• overspending risk  
• available investment capacity  
• emergency fund readiness  
• goal acceleration opportunities  

Displayed using an interactive monthly comparison chart.

---

## Expense Category Distribution

Instead of listing expenses only, the dashboard evaluates category impact.

Example output:

Monthly Rent → 27.6%  
Emergency Saving → 23.0%  
Medical & Fitness → 14.7%  
Fashion → 11.0%  
Groceries → 6.4%

This highlights where financial pressure exists.

Displayed using donut-chart analytics visualization.

---

## Spending Ranking Logic

Expense categories are ranked by magnitude.

This helps detect:

• primary cost drivers  
• discretionary spending zones  
• optimization opportunities  

Displayed using horizontal ranking visualization.

---

## Goal Feasibility Estimation

Instead of only tracking progress, the system estimates whether a goal is realistically achievable.

Example:

Goal achievable in ~51 months

The estimate considers:

• remaining target amount  
• current savings level  
• monthly contribution capacity  

This mirrors logic used in financial planning analytics tools.

---

## Savings Capacity Indicator

The dashboard calculates remaining income available after expenses.

Example:

Monthly surplus: ₹31,200

This becomes the basis for:

• goal timeline prediction  
• recommendation generation  
• investment allocation suggestions  

---

## Timeline Projection Model

Completion forecast formula:

Remaining Target Amount / Monthly Contribution Capacity

Example output:

Estimated completion: ~51 months (~4.3 years)

This introduces forecasting capability into the dashboard.

---

## Recommendation Engine

Based on calculated indicators, the system generates suggestions such as:

Savings rate meets recommended 20% threshold  
Aim for 30%+ to accelerate goal completion  
Consider allocating surplus toward investment instruments  

These are rule-based insights derived from financial benchmarks.

---

## Visual Analytics Included

The dashboard includes:

• savings rate gauge visualization  
• income vs expense comparison chart  
• category distribution donut chart  
• spending ranking chart  
• goal feasibility indicators  
• timeline estimation panels  

Charts are implemented using Chart.js.

---

## Technologies Used

Frontend:

HTML  
CSS  
JavaScript  
Chart.js  

Backend:

Python  
Flask  

Database:

SQLite  

Deployment:

Render

---

## How to Run Locally

Clone repository

git clone https://github.com/Kirito263V/Fintrack-AI.git

Move into project folder

cd Fintrack-AI

Install dependencies

pip install flask

Run application

python app.py

Open browser

http://127.0.0.1:5000

---

## What This Project Demonstrates (From a Data Analyst Perspective)

Through this project I practiced:

• designing financial KPIs  
• transforming raw inputs into interpretable indicators  
• building interactive dashboards  
• modeling behavioral financial ratios  
• estimating completion timelines  
• generating decision-support insights  
• structuring analytics workflows inside an application environment  

---

## Future Improvements

Planned enhancements include:

• time-series spending trend tracking  
• predictive savings forecasting  
• exportable analytics reports  
• cloud database integration  
• multi-user benchmarking analytics  

---

## Author

FinTrack AI was designed and developed independently by

**Binaya Kumar Meher**

Portfolio Project — 2026

Built as part of my preparation for Data Analyst roles and dashboard-based analytics work.

---

## License

This project is licensed under the MIT License.
