import streamlit as st
from valuation.data import get_financials, extract_latest_fcf, get_valuation_multiples
from valuation.dcf import project_cash_flows, calculate_terminal_value_gordon, calculate_terminal_value_exit_multiple, discounted_cash_flows
from visualizations.charts import dcf_chart
import numpy as np
import plotly.express as px
from visualizations.charts import render_sensitivity_heatmap, render_exit_multiple_heatmap
import pandas as pd
import plotly.graph_objects as go

# Open Source Valuation Toolkit
# This application allows users to perform fundamental company valuations using:
# - Discounted Cash Flow (DCF) with support for Gordon Growth and Exit Multiple methods
# - Comparables valuation metrics like P/E, PEG, EV/EBITDA
# The user interface is powered by Streamlit and includes built-in visualizations and explanatory tooltips.

st.title("💼 Open Source Valuation Toolkit")

# Valuation method selector
valuation_method = st.selectbox(
    "Choose a valuation method:",
    ["Discounted Cash Flow (DCF)", "Valuation Multiples (Comps)", "Dividend Discount Model (DDM)"],
    index=0
)

# DCF Valuation Flow
if valuation_method == "Discounted Cash Flow (DCF)":
    ticker = st.text_input("Enter a stock ticker (e.g., AAPL, TSLA):")

    # Single ticker input
    if ticker:
        financials = get_financials(ticker)
        currency = financials.get("currency", "N/A")
        st.caption(f"All valuation outputs below are in {currency}.")
        st.write(f"**Company Name:** {financials['info'].get('longName', 'N/A')}")

        cashflow_df = financials['cashflow']
        latest_fcf = extract_latest_fcf(cashflow_df)

        if latest_fcf is None:
            st.error("⚠️ Free Cash Flow data not available for this ticker.")
            st.stop()

        st.write(f"Latest Free Cash Flow: ${latest_fcf:,.0f}")

        # Growth assumptions
        st.subheader("📈 Growth Assumptions")
        growth_rate = st.slider(
            "Expected annual FCF growth rate (%)",
            min_value=0, max_value=30, value=10,
            help="How fast you expect the company’s free cash flow to grow per year over the next 5 years. Most mature companies grow 2–10%."
        ) / 100

        terminal_growth = st.slider(
            "Terminal growth rate (%)",
            min_value=0, max_value=5, value=2,
            help="The long-term stable growth rate beyond Year 5. Usually 1–3%, and should not exceed GDP growth (~2%)."
        ) / 100
        
        # Discount rate / WACC
        st.subheader("📈 Discount Rate (WACC)")
        use_auto_wacc = st.checkbox(
            "Auto-calculate WACC using CAPM?",
            value=True,
            help="Automatically calculates the discount rate using CAPM: Risk-free rate + Beta × Equity risk premium."
        )
        if use_auto_wacc:
            rf = 0.045  # Assume 4.5% risk-free rate
            market_return = 0.09  # Assume 9% long-term market return
            beta = financials['info'].get('beta', 1.0)

            cost_of_equity = rf + beta * (market_return - rf)
            discount_rate = cost_of_equity
            st.write(f"📊 CAPM WACC based on Beta ({beta:.2f}): **{discount_rate*100:.2f}%**")
        else:
            discount_rate = st.slider(
                "Manual WACC (%)",
                5, 15, 10,
                help="The discount rate used to calculate present value of cash flows. Often 8–12% for most public companies."
            ) / 100


        projected = project_cash_flows(latest_fcf, growth_rate)

        # Terminal value method selection
        st.subheader("🏋️ Terminal Value Method")
        method = st.radio(
            "Select a terminal value method:",
            ["Gordon Growth", "Exit Multiple"],
            help="Gordon Growth assumes steady long-term growth. Exit Multiple assumes you sell the business at a future cash flow multiple."
        )


        if method == "Gordon Growth":
            terminal = calculate_terminal_value_gordon(projected[-1], terminal_growth, discount_rate)
        else:
            exit_multiple = st.slider("Select exit multiple of FCF", 5, 25, 12)
            terminal = calculate_terminal_value_exit_multiple(projected[-1], exit_multiple)

        total_value = discounted_cash_flows(projected, terminal, discount_rate)

        # DCF Value Output
        st.subheader("💵 DCF Valuation")
        st.write(f"Estimated Intrinsic Value: **${total_value:,.0f}**")

        # Valuation Summary Markdown Output
        st.markdown(f"""
        ### 📋 Valuation Summary

        - **Ticker:** `{ticker.upper()}`
        - **Latest FCF:** ${latest_fcf:,.0f}
        - **Growth Rate:** {growth_rate*100:.1f}%
        - **Terminal Growth Rate:** {terminal_growth*100:.1f}%
        - **Discount Rate (WACC):** {discount_rate*100:.1f}%
        - **Estimated Intrinsic Value:** **${total_value:,.0f}**
        """)

        # Market comparison
        market_price = financials['info'].get('currentPrice', None)
        shares_outstanding = financials['info'].get('sharesOutstanding', None)

        if market_price and shares_outstanding:
            implied_price = total_value / shares_outstanding
            if implied_price > market_price:
                valuation_label = "🔼 Undervalued"
                valuation_tip = "Intrinsic > Market — The stock may be trading below its fair value, potentially offering upside."
            else:
                valuation_label = "🔽 Overvalued"
                valuation_tip = "Market > Intrinsic — The stock may be priced higher than its estimated worth, suggesting limited upside."

            st.markdown("### Market Price Summary")

            st.markdown(f"""
            <style>
            .tooltip-icon {{
                display: inline-block;
                cursor: help;
                transition: transform 0.2s ease, color 0.2s ease;
            }}
            .tooltip-icon:hover {{
                transform: scale(1.2);
                color: #007acc;
            }}
            </style>

            - **Market Price:** ${market_price}  
            - **Implied Intrinsic Price:** ${implied_price:,.2f}  
            - **Valuation vs Market:**  
            <span style="font-weight:bold;">{valuation_label}</span>
            <span class="tooltip-icon" title="{valuation_tip}">ℹ️</span>
            """, unsafe_allow_html=True)


        # DCF Chart
        st.plotly_chart(dcf_chart(projected, terminal, total_value))
        
        # Sensitivity Chart
        st.subheader("📊 Sensitivity Heatmap")
        if method == "Gordon Growth":
            fig = render_sensitivity_heatmap(
                latest_fcf, discount_rate, terminal_growth,
                project_cash_flows, calculate_terminal_value_gordon, discounted_cash_flows
            )
            st.plotly_chart(fig)
        else:
            fig = render_exit_multiple_heatmap(
                latest_fcf, discount_rate, exit_multiple,
                project_cash_flows, calculate_terminal_value_exit_multiple, discounted_cash_flows
            )
            st.plotly_chart(fig)

    # Multiple Ticker DCF Comparison
    st.subheader("📊 Compare Multiple Tickers")
    tickers = st.text_input("Enter up to 5 tickers separated by commas (e.g. AAPL, MSFT, AMZN):")

    # Multiple Ticker Input
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")][:5]
        comparison = []

        for t in ticker_list:
            try:
                f = get_financials(t)
                fcf = extract_latest_fcf(f['cashflow'])
                if fcf is None:
                    raise ValueError("No FCF")

                growth = 0.10
                discount = 0.10
                exit_multiple = 12

                proj = project_cash_flows(fcf, growth)
                
                # Gordon Growth Valuation
                term_gordon = calculate_terminal_value_gordon(proj[-1], 0.02, discount)
                value_gordon = discounted_cash_flows(proj, term_gordon, discount)

                # Exit Multiple Valuation
                term_exit = calculate_terminal_value_exit_multiple(proj[-1], exit_multiple)
                value_exit = discounted_cash_flows(proj, term_exit, discount)


                # Current Market Price
                market = f['info'].get('currentPrice', None)

                # Share Price Conversion
                shares = f['info'].get('sharesOutstanding', None)
                intrinsic_gordon = value_gordon / shares if shares else None
                intrinsic_exit = value_exit / shares if shares else None

                comparison.append({
                    "Ticker": t,
                    "Market Price": round(market, 2) if market else "N/A",
                    "Intrinsic (Gordon)": round(intrinsic_gordon, 2) if intrinsic_gordon else "N/A",
                    "Intrinsic (Exit Multiple)": round(intrinsic_exit, 2) if intrinsic_exit else "N/A",
                    "Valuation (Gordon)": "Undervalued" if intrinsic_gordon and market and intrinsic_gordon > market else "Overvalued",
                    "Valuation (Exit)": "Undervalued" if intrinsic_exit and market and intrinsic_exit > market else "Overvalued"
                })

            except:
                comparison.append({
                    "Ticker": t,
                    "Market Price": "N/A",
                    "Intrinsic (Gordon)": "N/A",
                    "Intrinsic (Exit Multiple)": "N/A",
                    "Valuation (Gordon)":"N/A",
                    "Valuation (Exit)": "N/A"
                })

        st.dataframe(comparison)

# DDM Valuation Flow
elif valuation_method == "Dividend Discount Model (DDM)":
    st.subheader("Dividend Discount Model (DDM)")
    ticker = st.text_input("Enter a dividend-paying stock ticker (e.g., JNJ, KO):")

    if ticker:
        financials = get_financials(ticker)
        currency = financials.get("currency", "N/A")
        st.caption(f"All valuation outputs below are in {currency}.")
        info = financials["info"]

        st.write(f"**Company Name:** {info.get('longName', 'N/A')}")

        dividend = info.get("dividendRate")
        current_price = info.get("currentPrice")
        payout_ratio = info.get("payoutRatio")

        if dividend:
            st.write(f"Most Recent Dividend Rate: **${dividend}**")
            if current_price:
                yield_ttm = dividend / current_price
                st.write(f"TTM Dividend Yield: **{yield_ttm:.2%}**")
        else:
            st.write("Dividend rate not available.")

        if payout_ratio is not None:
            st.write(f"Payout Ratio: **{payout_ratio:.2%}**")
            if payout_ratio > 1:
                st.warning("⚠️ Dividend payout exceeds earnings — may be unsustainable.")
            elif payout_ratio > 0.8:
                st.info("ℹ️ High payout ratio — monitor for sustainability.")

        st.markdown("### Model Type")
        ddm_mode = st.radio("Select DDM Type:", ["Single-Stage", "Multi-Stage"], index=0, help="Single-stage assumes constant dividend growth. Multi-stage models faster growth early on, then a stable terminal phase.")

        if ddm_mode == "Single-Stage":
            g = st.slider("Expected Annual Dividend Growth Rate (%)", 0, 15, 5, help="Estimate of how much the dividend will grow annually forever.") / 100
            r = st.slider("Discount Rate (%)", 5, 15, 9, help="Expected return required by investors — usually tied to company risk or cost of equity.") / 100
            if dividend and r > g:
                value = dividend * (1 + g) / (r - g)
                st.success(f"Estimated Intrinsic Value (DDM): **${value:.2f}**")
                if current_price:
                    comparison = "Undervalued" if value > current_price else "Overvalued"
                    color = "green" if comparison == "Undervalued" else "red"
                    icon = "🔼" if comparison == "Undervalued" else "🔽"
                    st.markdown(f"**Current Price:** ${current_price} → <span style='color:{color}; font-weight:bold;'>{icon} {comparison}</span><br><small>This is not investment advice.</small>", unsafe_allow_html=True)
            elif r <= g:
                st.error("Discount rate must be greater than growth rate to use this model.")

        elif ddm_mode == "Multi-Stage":
            div_years = st.slider("Years of High Growth Phase", 1, 10, 5, help="Number of years the dividend is expected to grow at a higher rate before settling.")
            initial_growth = st.slider("High Growth Rate (%)", 0, 25, 8, help="Expected annual dividend growth during the high-growth phase.") / 100
            terminal_growth = st.slider("Terminal Growth Rate (%)", 0, 10, 3, help="Expected long-term dividend growth rate after the high-growth period ends.") / 100
            discount_rate = st.slider("Discount Rate (%)", 5, 15, 9, help="Required return used to discount future dividends back to present value.") / 100

            if dividend:
                dividends = [dividend * ((1 + initial_growth) ** i) for i in range(1, div_years + 1)]
                terminal_dividend = dividends[-1] * (1 + terminal_growth)
                terminal_value = terminal_dividend / (discount_rate - terminal_growth)
                present_value = sum([d / ((1 + discount_rate) ** (i + 1)) for i, d in enumerate(dividends)])
                present_terminal = terminal_value / ((1 + discount_rate) ** div_years)
                intrinsic_value = present_value + present_terminal
                st.success(f"Estimated Intrinsic Value (Multi-Stage DDM): **${intrinsic_value:.2f}**")
                if current_price:
                    comparison = "Undervalued" if intrinsic_value > current_price else "Overvalued"
                    color = "green" if comparison == "Undervalued" else "red"
                    icon = "🔼" if comparison == "Undervalued" else "🔽"
                    st.markdown(f"**Current Price:** ${current_price} → <span style='color:{color}; font-weight:bold;'>{icon} {comparison}</span><br><small>This is not investment advice.</small>", unsafe_allow_html=True)

                extended_dividends = dividends + [dividends[-1] * ((1 + terminal_growth) ** i) for i in range(1, 6)]
                st.plotly_chart(px.line(
                    x=list(range(1, div_years + 6)),
                    y=extended_dividends,
                    labels={'x': 'Year', 'y': 'Projected Dividend'},
                    title=f"Projected Dividends ({div_years} Years High Growth Phase + 5 Years Terminal Phase)"
                ))


# Comparables Valuation Flow
elif valuation_method == "Valuation Multiples (Comps)":
    st.subheader("Valuation Multiples Comparison")
    st.write("Compare key valuation ratios like P/E, EV/EBITDA, and Price/Sales across multiple tickers.")

    tickers = st.text_input("Enter up to 5 tickers separated by commas (e.g., AAPL, MSFT, AMZN):")

    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")][:5]
        metrics_table = []

        for t in ticker_list:
            try:
                fin = get_financials(t)
                info = fin["info"]
                multiples = get_valuation_multiples(info)

                row = {"Ticker": t}
                row.update(multiples)
                row["Sector"] = info.get("sector", "N/A")
                metrics_table.append(row)
            except:
                metrics_table.append({"Ticker": t, "Error": "Data unavailable or failed to fetch."})

        if metrics_table:
            df = pd.DataFrame(metrics_table)
            numeric_cols = [col for col in df.columns if col not in ["Ticker", "Sector", "Error"]]

            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            st.markdown("""
            **Legend:**
            - 🟩 Green: Lower value (possibly undervalued)
            - 🟥 Red: Higher value (possibly overvalued)
            - ⚪ Gray: Mid-range or not highlighted

            *Note: Coloring is based on generic thresholds (<15 = green, >25 = red) and does not imply investment advice.*
            """)

            st.dataframe(df.style.applymap(
                lambda val: 'background-color: #c8e6c9' if isinstance(val, (int, float)) and val < 15 else ('background-color: #ffcdd2' if isinstance(val, (int, float)) and val > 25 else ''),
                subset=numeric_cols
            ))

            # Allow users to customize which metrics to use for scoring
            st.subheader("Customize Valuation Scoring")
            selected_metrics = st.multiselect("Select metrics to include in scoring:", numeric_cols, default=numeric_cols)

            # Toggle to show/hide normalization formula explanation
            with st.expander("Normalization Formula"):
                st.markdown("""
                Each metric is standardized using Z-score normalization:
                $$ z = \frac{x - \mu}{\sigma} $$
                where \( x \) is the metric value, \( \mu \) is the column mean, and \( \sigma \) is the standard deviation.
                Scores are summed across selected metrics and the lowest total score indicates the best relative valuation.
                """)

            clean_df = df[~df['Ticker'].str.contains("Avg")].copy()
            valid_rows = clean_df[selected_metrics].dropna()

            if not valid_rows.empty:
                z_scores = (valid_rows - valid_rows.mean()) / valid_rows.std()
                z_scores = z_scores.fillna(0)
                score = z_scores.sum(axis=1)
                best_idx = score.idxmin()
                best_ticker = clean_df.loc[best_idx, "Ticker"]
                st.markdown(f"**Best Valuation (based on normalized score using selected metrics):** `{best_ticker}` *(Not investment advice)*")

                # Radar Chart for best ticker
                st.subheader("Best Valuation Profile (Radar Chart)")
                best_row = z_scores.loc[best_idx]
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=best_row.values,
                    theta=best_row.index,
                    fill='toself',
                    name=best_ticker
                ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True)),
                    showlegend=True,
                    title=f"Z-Score Profile of {best_ticker}"
                )
                st.plotly_chart(fig_radar)

            st.subheader("Valuation Metric Comparison")
            metric_choice = st.selectbox("Select a metric to chart:", numeric_cols)

            chart_df = df.dropna(subset=[metric_choice])
            fig = px.bar(
                chart_df,
                x="Ticker",
                y=metric_choice,
                color="Sector" if "Sector" in chart_df.columns else None,
                title=f"{metric_choice} by Ticker",
                text=metric_choice
            )
            st.plotly_chart(fig)




