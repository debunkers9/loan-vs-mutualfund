import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates

# ==============================================================================
# CONFIGURATION CONSTANTS
# ==============================================================================
PROPERTY_PRICE = 50_00_000          # Total property price in INR
DOWN_PAYMENT_PCT = 0.20              # 20% down payment
LOAN_INTEREST_RATE = 0.08           # Annual interest rate (0.065 = 6.5%, 0.08 = 8.0%)
EXPECTED_CAGR = 0.13                 # Expected benchmark CAGR (0.13 = 13.0%)
DIVIDEND_YIELD = 0.013               # ~1.3% annual Nifty 50 dividend yield for TRI benchmark
TICKER = "^NSEI"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "nifty50_monthly_data.json")
CHART_DIR = os.path.join(BASE_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)
CHART_FILE = os.path.join(CHART_DIR, f"nifty_swp_loan_backtest_{LOAN_INTEREST_RATE*100:g}%.png")
SUMMARY_FILE = os.path.join(BASE_DIR, "backtest_summary.json")

# ==============================================================================
# 1. LOAD DATA & PREPARE TOTAL RETURN INDEX (TRI)
# ==============================================================================
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        df = pd.DataFrame(json.load(f))
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date').sort_index()
else:
    import yfinance as yf
    raw = yf.download(TICKER, start="2000-01-01", interval="1mo", progress=False)
    open_series = raw['Open'][TICKER] if isinstance(raw.columns, pd.MultiIndex) else raw['Open']
    df = pd.DataFrame({'Open': open_series.squeeze()}).dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df['YearMonth'] = df.index.to_period('M')
    df = df.drop_duplicates(subset=['YearMonth']).sort_index()
    json_list = [{'Date': dt.strftime('%Y-%m-%d'), 'YearMonth': str(r['YearMonth']), 'Open': float(r['Open'])} for dt, r in df.iterrows()]
    with open(DATA_FILE, "w") as f:
        json.dump(json_list, f, indent=2)

# End backtest in August 2026 to ensure all monthly calculations are completed
df = df[df.index <= '2026-08-01']

# Generate Nifty 50 Total Return Index (TRI) by adding dividend yield
div_m = (1 + DIVIDEND_YIELD) ** (1 / 12) - 1
tri_navs = [df['Open'].iloc[0]]
for i in range(1, len(df)):
    pr_ret = (df['Open'].iloc[i] / df['Open'].iloc[i - 1]) - 1.0
    tot_ret = (1 + pr_ret) * (1 + div_m) - 1.0
    tri_navs.append(tri_navs[-1] * (1 + tot_ret))
df['NAV'] = tri_navs

# ==============================================================================
# 2. FINANCIAL & LOAN SETUP
# ==============================================================================
DOWN_PAYMENT_AMOUNT = PROPERTY_PRICE * DOWN_PAYMENT_PCT
LOAN_AMOUNT = PROPERTY_PRICE - DOWN_PAYMENT_AMOUNT
INVESTMENT_AMOUNT = LOAN_AMOUNT

# Tenure matches the exact completed data period so loan is fully amortized
TOTAL_MONTHS = len(df) - 1

r = LOAN_INTEREST_RATE / 12
if r > 0:
    MONTHLY_EMI = LOAN_AMOUNT * r * ((1 + r) ** TOTAL_MONTHS) / (((1 + r) ** TOTAL_MONTHS) - 1)
else:
    MONTHLY_EMI = LOAN_AMOUNT / TOTAL_MONTHS
TOTAL_EMI_REPAID = MONTHLY_EMI * TOTAL_MONTHS

rate_str = f"{LOAN_INTEREST_RATE * 100:g}%"
down_pay_pct_str = f"{DOWN_PAYMENT_PCT * 100:g}%"
loan_pct_str = f"{(1.0 - DOWN_PAYMENT_PCT) * 100:g}%"
expected_cagr_str = f"{EXPECTED_CAGR * 100:g}%"

start_str = df.index[0].strftime('%b %Y')
end_str = df.index[-1].strftime('%b %Y')
print("=" * 60)
print(f"BACKTEST SETUP ({start_str} to {end_str}: {TOTAL_MONTHS} Months / {TOTAL_MONTHS/12:.1f} Yrs)")
print("=" * 60)
print(f"Property Price       : Rs. {PROPERTY_PRICE:,.2f}")
print(f"Down Payment ({down_pay_pct_str})   : Rs. {DOWN_PAYMENT_AMOUNT:,.2f}")
print(f"Loan Amount ({loan_pct_str})    : Rs. {LOAN_AMOUNT:,.2f}")
print(f"Loan Interest Rate   : {rate_str} per year")
print(f"Expected MF CAGR     : {expected_cagr_str} per year")
print(f"Monthly EMI          : Rs. {MONTHLY_EMI:,.2f}")
print(f"Total Loan Repaid    : Rs. {TOTAL_EMI_REPAID:,.2f}")
print(f"Initial MF Invested  : Rs. {INVESTMENT_AMOUNT:,.2f}")
print("=" * 60)

# Calculate overall realized Nifty 50 TRI CAGR over the entire backtest tenure
years_sim = TOTAL_MONTHS / 12.0
real_tri_cagr = (df['NAV'].iloc[-1] / df['NAV'].iloc[0]) ** (1.0 / years_sim) - 1.0

# ==============================================================================
# 3. SIMULATION LOOP (SWP = EMI)
# ==============================================================================
units = INVESTMENT_AMOUNT / df['NAV'].iloc[0]
initial_units = units
loan_balance = LOAN_AMOUNT

flat_exp_growth = (1 + EXPECTED_CAGR) ** (1 / 12)
flat_exp_corpus = INVESTMENT_AMOUNT

flat_act_growth = (1 + real_tri_cagr) ** (1 / 12)
flat_act_corpus = INVESTMENT_AMOUNT

cumulative_swp = 0.0

records = [{
    'Date': df.index[0],
    'Portfolio_Value': INVESTMENT_AMOUNT,
    'Loan_Balance': loan_balance,
    'Cumulative_SWP': 0.0,
    'Nifty_Pure_Value': INVESTMENT_AMOUNT,
    'Expected_Corpus': flat_exp_corpus,
    'Actual_CAGR_Corpus': flat_act_corpus,
    'Units': units,
    'Annual_Return': None
}]

for i in range(1, len(df)):
    dt = df.index[i]
    nav = df['NAV'].iloc[i]

    # Loan repayment
    interest = loan_balance * r
    emi_due = min(MONTHLY_EMI, loan_balance + interest)
    loan_balance = max(0.0, loan_balance - (emi_due - interest))

    # SWP withdrawal
    units_to_sell = emi_due / nav
    units = max(0.0, units - units_to_sell)
    port_val = units * nav
    cumulative_swp += emi_due

    # Constant CAGR benchmark compounding with SWP
    flat_exp_corpus = max(0.0, (flat_exp_corpus * flat_exp_growth) - emi_due)
    flat_act_corpus = max(0.0, (flat_act_corpus * flat_act_growth) - emi_due)

    # 1-Year YoY Return
    ann_ret = ((nav / df['NAV'].iloc[i - 12]) - 1.0) * 100 if i >= 12 else None

    records.append({
        'Date': dt,
        'Portfolio_Value': port_val,
        'Loan_Balance': loan_balance,
        'Cumulative_SWP': cumulative_swp,
        'Nifty_Pure_Value': INVESTMENT_AMOUNT * (nav / df['NAV'].iloc[0]),
        'Expected_Corpus': flat_exp_corpus,
        'Actual_CAGR_Corpus': flat_act_corpus,
        'Units': units,
        'Annual_Return': ann_ret
    })

res = pd.DataFrame(records)

# ==============================================================================
# 4. PRINT SUMMARY & SAVE JSON
# ==============================================================================
years_sim = TOTAL_MONTHS / 12.0
real_tri_cagr = (df['NAV'].iloc[-1] / df['NAV'].iloc[0]) ** (1.0 / years_sim) - 1.0
final_port = res['Portfolio_Value'].iloc[-1]
final_pure = res['Nifty_Pure_Value'].iloc[-1]
final_units = res['Units'].iloc[-1]
final_loan = res['Loan_Balance'].iloc[-1]
loan_status_str = "Fully Repaid!" if final_loan <= 1.0 else f"Remaining: Rs. {final_loan:,.2f}"

print("\n" + "=" * 60)
print("BACKTEST RESULTS (NIFTY 50 TOTAL RETURN INDEX)")
print("=" * 60)
print(f"Realized Nifty 50 TRI CAGR  : {real_tri_cagr * 100:.2f}% per year")
print(f"Expected Benchmark CAGR     : {expected_cagr_str} per year")
print(f"Loan Interest Rate          : {rate_str} per year")
print(f"Total SWP Cash Extracted    : Rs. {cumulative_swp:,.2f}")
print(f"Ending Loan Balance         : Rs. {final_loan:,.2f} ({loan_status_str})")
print(f"Ending Portfolio Balance    : Rs. {final_port:,.2f} ({final_port / INVESTMENT_AMOUNT:.2f}x of initial)")
print(f"Ending Units Remaining      : {final_units:,.0f} of {initial_units:,.0f} ({(final_units / initial_units) * 100:.1f}%)")
print(f"Buy-and-Hold Nifty (No SWP) : Rs. {final_pure:,.2f} ({final_pure / INVESTMENT_AMOUNT:.2f}x)")
print("=" * 60)

with open(SUMMARY_FILE, "w") as f:
    json.dump({
        'property_price': PROPERTY_PRICE,
        'down_payment_pct': DOWN_PAYMENT_PCT,
        'down_payment_amount': DOWN_PAYMENT_AMOUNT,
        'loan_amount': LOAN_AMOUNT,
        'loan_interest_rate': LOAN_INTEREST_RATE,
        'expected_cagr': EXPECTED_CAGR,
        'dividend_yield': DIVIDEND_YIELD,
        'initial_investment': INVESTMENT_AMOUNT,
        'monthly_emi': MONTHLY_EMI,
        'total_months': TOTAL_MONTHS,
        'realized_tri_cagr': real_tri_cagr,
        'total_swp_extracted': cumulative_swp,
        'ending_loan_balance': final_loan,
        'ending_portfolio_value': final_port,
        'pure_nifty_tri_value': final_pure,
        'ending_units': final_units
    }, f, indent=2)

# ==============================================================================
# 5. VISUALIZATION (2x2 WINDOW WITH INDEPENDENT AXES)
# ==============================================================================
def format_inr(val, show_rs=True):
    prefix = "Rs. " if show_rs else ""
    if abs(val) >= 1e7:
        return f"{prefix}{val/1e7:.2f}".rstrip('0').rstrip('.') + " Cr"
    elif abs(val) >= 1e5:
        return f"{prefix}{val/1e5:.2f}".rstrip('0').rstrip('.') + " L"
    return f"{prefix}{val:,.0f}"

print("\nGenerating clean 2x2 charts...")
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle(
    f"Property Loan ({rate_str}) vs Nifty 50 TRI SWP Strategy Backtest\n"
    f"(Invest {format_inr(INVESTMENT_AMOUNT)} | Monthly SWP = Rs. {MONTHLY_EMI:,.0f} | {start_str} to {end_str})", 
    fontsize=13, fontweight='bold'
)

formatter = ticker.FuncFormatter(lambda x, _: format_inr(x, show_rs=False))

for ax in axes.flatten():
    ax.xaxis.set_major_locator(mdates.YearLocator(3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.tick_params(axis='x', rotation=25, labelsize=9)
    ax.tick_params(axis='y', labelsize=9)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xlabel("Date", fontsize=9.5, fontweight='bold', alpha=0.8)

# Subplot 1 (Top-Left): Portfolio vs Loan Balance
ax1 = axes[0, 0]
ax1.plot(res['Date'], res['Portfolio_Value'], label='Actual Nifty 50 TRI (Post-SWP)', color='#0052cc', linewidth=2.2)
ax1.plot(res['Date'], res['Expected_Corpus'], label=f'Expected Compounding ({expected_cagr_str} with SWP)', color='#e67e22', linestyle=':', linewidth=2)
ax1.plot(res['Date'], res['Actual_CAGR_Corpus'], label=f'Actual Compounding ({real_tri_cagr*100:.1f}% with SWP)', color='#9333ea', linestyle=':', linewidth=2)
ax1.plot(res['Date'], res['Nifty_Pure_Value'], label='Nifty 50 TRI Buy-and-Hold (No SWP)', color='#2ca02c', linestyle='--', linewidth=2)
ax1.plot(res['Date'], res['Loan_Balance'], label='Remaining Loan Balance', color='#cc0000', linestyle='-.', linewidth=2)
ax1.axhline(INVESTMENT_AMOUNT, color='gray', linestyle=':', alpha=0.7, label=f'Initial Cash Invested ({format_inr(INVESTMENT_AMOUNT, show_rs=False)})')
ax1.set_title("1. Portfolio Value with SWP vs Buy-and-Hold vs Loan Debt", fontsize=10.5, fontweight='bold')
ax1.set_ylabel("Amount (INR)", fontsize=9.5, fontweight='bold', alpha=0.8)
ax1.yaxis.set_major_formatter(formatter)
ax1.legend(loc='upper left', frameon=True, fontsize=7.5)

# Subplot 2 (Top-Right): Actual Annual Return vs Benchmarks
ax2 = axes[0, 1]
valid_ann = res.dropna(subset=['Annual_Return'])

# Actual 1-year YoY returns
ax2.plot(valid_ann['Date'], valid_ann['Annual_Return'], color='#1f77b4', linewidth=1.5, label='Actual 1-Yr Nifty TRI Return (%)')

# Benchmark horizontal lines: Expected CAGR vs Actual Realized TRI CAGR
ax2.axhline(EXPECTED_CAGR * 100.0, color='#dc2626', linestyle='--', linewidth=2, label=f'Expected CAGR ({expected_cagr_str})')
ax2.axhline(real_tri_cagr * 100.0, color='#16a34a', linestyle='--', linewidth=2, label=f'Actual Realized CAGR ({real_tri_cagr*100:.2f}%)')

ax2.set_title("2. Nifty 50 TRI Annual Returns vs Benchmark CAGRs", fontsize=10.5, fontweight='bold')
ax2.set_ylabel("Annual Return (%)", fontsize=9.5, fontweight='bold', alpha=0.8)
ax2.yaxis.set_major_formatter(ticker.PercentFormatter())
ax2.legend(loc='upper right', frameon=True, fontsize=8)

# Subplot 3 (Bottom-Left): Units Remaining
ax3 = axes[1, 0]
ax3.plot(res['Date'], res['Units'], color='#8e44ad', linewidth=2.2, label='Units Remaining')
ax3.set_title("3. Mutual Fund Units Remaining Over Time", fontsize=10.5, fontweight='bold')
ax3.set_ylabel("Units Owned", fontsize=9.5, fontweight='bold', alpha=0.8)
ax3.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f'{y:,.0f}'))
ax3.legend(loc='upper right', frameon=True, fontsize=8.5)

# Subplot 4 (Bottom-Right): Cumulative SWP vs Loan EMIs
ax4 = axes[1, 1]
ax4.plot(res['Date'], res['Cumulative_SWP'], color='#16a085', linewidth=2.2, label='Cumulative Cash Extracted (SWP)')
ax4.axhline(INVESTMENT_AMOUNT, color='black', linestyle='--', label=f'Initial Cash Put In ({format_inr(INVESTMENT_AMOUNT)})')
ax4.axhline(TOTAL_EMI_REPAID, color='red', linestyle=':', label=f'Total EMIs Repaid ({format_inr(TOTAL_EMI_REPAID)})')
ax4.set_title("4. Cumulative Cash Extracted via SWP for Loan Repayment", fontsize=10.5, fontweight='bold')
ax4.set_ylabel("Cumulative SWP (INR)", fontsize=9.5, fontweight='bold', alpha=0.8)
ax4.yaxis.set_major_formatter(formatter)
ax4.legend(loc='upper left', frameon=True, fontsize=8.5)

plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.subplots_adjust(hspace=0.30, wspace=0.22)
plt.savefig(CHART_FILE, dpi=300)
print(f"[+] Visualization saved to: {CHART_FILE}")
print("Finished!")
