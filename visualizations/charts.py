import plotly.graph_objects as go
import numpy as np
import plotly.express as px

def dcf_chart(projected, terminal, total_value):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[f'Year {i+1}' for i in range(len(projected))], y=projected, name='Projected FCF'))
    fig.add_trace(go.Bar(x=[f'Year {len(projected)}'], y=[terminal], name='Terminal Value'))
    fig.update_layout(title=f"DCF Breakdown (Total: ${total_value:,.0f})")
    return fig

def render_sensitivity_heatmap(latest_fcf, discount_rate, terminal_growth, project_cash_flows, calculate_terminal_value, discounted_cash_flows):
    rates = np.linspace(discount_rate - 0.03, discount_rate + 0.03, 7)
    growths = np.linspace(terminal_growth - 0.01, terminal_growth + 0.01, 5)

    Z = [[
        discounted_cash_flows(
            project_cash_flows(latest_fcf, g),
            calculate_terminal_value(project_cash_flows(latest_fcf, g)[-1], g, r),
            r
        ) for r in rates] for g in growths]

    fig = px.imshow(Z,
        x=[f"{r*100:.1f}%" for r in rates],
        y=[f"{g*100:.1f}%" for g in growths],
        labels={"x": "Discount Rate", "y": "Terminal Growth", "color": "Valuation ($)"},
        title="DCF Sensitivity: Terminal Growth vs WACC"
    )
    return fig

def render_exit_multiple_heatmap(latest_fcf, discount_rate, exit_multiple, project_cash_flows, calculate_terminal_value_exit_multiple, discounted_cash_flows):
    rates = np.linspace(discount_rate - 0.03, discount_rate + 0.03, 7)
    multiples = np.arange(exit_multiple - 5, exit_multiple + 6, 2)  # e.g., 7x to 17x

    Z = [[
        discounted_cash_flows(
            project_cash_flows(latest_fcf, 0.10),  # Assume flat 10% growth
            calculate_terminal_value_exit_multiple(project_cash_flows(latest_fcf, 0.10)[-1], m),
            r
        ) for r in rates] for m in multiples]

    fig = px.imshow(Z,
        x=[f"{r*100:.1f}%" for r in rates],
        y=[f"{m}x" for m in multiples],
        labels={"x": "Discount Rate", "y": "Exit Multiple", "color": "Valuation ($)"},
        title="Exit Multiple Sensitivity: Terminal Multiple vs WACC"
    )
    return fig