# loan-vs-mutualfund

> **Debunking the "Free House via Mutual Funds" Financial Hack with 19 Years of Real Market Data.**

A quantitative backtesting simulation testing the popular financial influencer claim:
> *"Don't pay ₹50L cash for a house. Instead, put ₹10L down, take a ₹40L home loan, invest the ₹40L into an equity mutual fund compounding at 12%, and let an SWP pay your EMI to get a free house!"*

This repository backtests the entire strategy against **19 years of verified Nifty 50 Total Return Index (TRI)** data (September 2007 – August 2026 / 227 monthly periods), factoring in dividend reinvestment, real loan amortization, and the brutal reality of **Sequence of Returns Risk** and forced unit redemption during market crashes (2008 GFC, 2020 Covid).

---

## 📊 Backtest Results Summary

| Strategy | Initial Capital | Ending Portfolio Value | Units Remaining | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Buy & Hold Nifty 50 TRI (No Loan / No SWP)** | ₹40,00,000 | **₹2.77 Crore** (`₹2,77,73,804`) | 885 / 885 (100%) | **+594%** (10.79% CAGR) |
| **6.5% Home Loan (Best Case)** | ₹40,00,000 | **₹31.54 Lakh** (`₹31,54,445`) | 100.5 / 885 (11.4%) | **-21%** (88% Units Sold) |
| **8.0% Home Loan (Normal Case)** | ₹40,00,000 | **₹2.79 Lakh** (`₹2,78,661`) | 8.9 / 885 (1.0%) | **-93%** (99% Units Sold) |

> **Key Takeaway**: When market returns are volatile, withdrawing fixed EMIs during market drawdowns forces you to sell mutual fund units at depressed prices. Even though Nifty 50 TRI compounded at **10.79% CAGR** (higher than the 8% loan interest rate), the investor lost **93% of their capital** in the 8% loan scenario.

---

## 📁 Repository Structure

```text
loan-vs-mutualfund/
├── backtest_loan_swp.py          # Core Python simulation & chart generation script
├── backtest_summary.json         # Backtest summary metrics output
├── charts/                       # Generated 2x2 high-res charts
│   ├── nifty_swp_loan_backtest_6.5%.png
│   └── nifty_swp_loan_backtest_8%.png
├── data/
│   └── nifty50_monthly_data.json # 19-year monthly historical Nifty 50 open prices
├── docs/                         # Presentation slides and video narration scripts
└── README.md
```

---

## 🛠️ Prerequisites

- **Python 3.9+**
- Standard scientific libraries:
  - `pandas`
  - `matplotlib`
  - `yfinance` *(optional, only if fetching fresh data from Yahoo Finance)*

---

## 🚀 How to Run the Backtest

### 1. Clone the Repository

```bash
git clone https://github.com/debunkers9/loan-vs-mutualfund.git
cd loan-vs-mutualfund
```

### 2. Set Up Virtual Environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS / Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install required packages
pip install pandas matplotlib yfinance
```

### 3. Run the Backtest Script

```bash
python backtest_loan_swp.py
```

### 4. Console Output

When executed, the script runs the month-by-month simulation and prints:

```text
============================================================
BACKTEST SETUP (Sep 2007 to Aug 2026: 227 Months / 18.9 Yrs)
============================================================
Property Price       : Rs. 5,000,000.00
Down Payment (20%)   : Rs. 1,000,000.00
Loan Amount (80%)    : Rs. 4,000,000.00
Loan Interest Rate   : 8% per year
Expected MF CAGR     : 13% per year
Monthly EMI          : Rs. 34,244.38
Total Loan Repaid    : Rs. 7,773,473.78
Initial MF Invested  : Rs. 4,000,000.00
============================================================

============================================================
BACKTEST RESULTS (NIFTY 50 TOTAL RETURN INDEX)
============================================================
Realized Nifty 50 TRI CAGR  : 10.79% per year
Expected Benchmark CAGR     : 13% per year
Loan Interest Rate          : 8% per year
Total SWP Cash Extracted    : Rs. 7,773,473.78
Ending Loan Balance         : Rs. 0.00 (Fully Repaid!)
Ending Portfolio Balance    : Rs. 278,660.88 (0.07x of initial)
Ending Units Remaining      : 9 of 885 (1.0%)
Buy-and-Hold Nifty (No SWP) : Rs. 27,773,803.88 (6.94x)
============================================================
```

### 5. Outputs Generated

1. **`backtest_summary.json`**: Contains full machine-readable statistics from the run.
2. **`charts/nifty_swp_loan_backtest_8%.png`**: Generates a high-res 2x2 dashboard visualization:
   - **Subplot 1**: Portfolio Value with SWP vs Buy-and-Hold vs Loan Debt over time.
   - **Subplot 2**: Rolling 1-Year Nifty TRI Returns vs Expected/Realized CAGRs.
   - **Subplot 3**: Depletion of Mutual Fund Units owned over time.
   - **Subplot 4**: Cumulative SWP cash extracted vs Total EMIs repaid.

---

## ⚙️ Customizing Simulation Parameters

You can easily adjust loan parameters or market assumptions directly inside [`backtest_loan_swp.py`](backtest_loan_swp.py):

```python
# Lines 11-15
PROPERTY_PRICE = 50_00_000          # Total property price in INR
DOWN_PAYMENT_PCT = 0.20              # Down payment ratio (0.20 = 20%)
LOAN_INTEREST_RATE = 0.08           # Annual interest rate (0.065 for 6.5%, 0.08 for 8.0%)
EXPECTED_CAGR = 0.13                 # Expected benchmark CAGR (13.0%)
DIVIDEND_YIELD = 0.013               # ~1.3% annual dividend yield for TRI
```

- **Test 6.5% Interest Rate (Best Case)**:
  Set `LOAN_INTEREST_RATE = 0.065` and rerun the script.
- **Test Custom Loan Tenures / Values**:
  Change `PROPERTY_PRICE` or `DOWN_PAYMENT_PCT`.

---

## 🔄 Updating Historical Data

The project ships with pre-cached monthly data in `data/nifty50_monthly_data.json`.

If you wish to download the latest available historical data directly from Yahoo Finance:
1. Delete or rename `data/nifty50_monthly_data.json`.
2. Run `python backtest_loan_swp.py`. The script will query `^NSEI`, reconstitute the monthly TRI series, and save a fresh data file automatically.
