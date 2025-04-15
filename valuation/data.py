import yfinance as yf

def get_financials(ticker):
    stock = yf.Ticker(ticker)
    income = stock.financials
    cashflow = stock.cashflow
    balance = stock.balance_sheet
    info = stock.info
    currency = info.get("financialCurrency", "N/A")

    return {
        "income": income,
        "cashflow": cashflow,
        "balance": balance,
        "info": info,
        "currency": currency
    }


def extract_latest_fcf(cashflow_df):
    """
    Tries to extract Free Cash Flow (FCF) from cashflow statement.
    If not directly available, approximates FCF = Operating CF - CapEx.
    """
    possible_keys = [
        'Total Cash From Operating Activities',
        'Operating Cash Flow',
        'Net cash provided by operating activities'
    ]

    for key in possible_keys:
        if key in cashflow_df.index:
            return cashflow_df.loc[key][0]

    # Try to approximate if possible
    try:
        op_cf = cashflow_df.loc['Operating Cash Flow'][0]
        capex = cashflow_df.loc['Capital Expenditures'][0]
        return op_cf - abs(capex)
    except:
        return None

def get_valuation_multiples(info):
    return {
        "P/E Ratio (TTM)": info.get("trailingPE", "N/A"),
        "Forward P/E": info.get("forwardPE", "N/A"),
        "EV/EBITDA": info.get("enterpriseToEbitda", "N/A"),
        "Price/Sales (TTM)": info.get("priceToSalesTrailing12Months", "N/A"),
        "EV/Revenue": info.get("enterpriseToRevenue", "N/A"),
        "EPS (TTM)": info.get("trailingEps", "N/A")
    }
