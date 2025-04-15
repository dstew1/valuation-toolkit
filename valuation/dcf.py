import numpy as np

def project_cash_flows(cash_flows, growth_rate, years=5):
    return [cash_flows * ((1 + growth_rate) ** i) for i in range(1, years + 1)]

def calculate_terminal_value_gordon(fcf, terminal_growth, discount_rate):
    """
    Calculates terminal value using the Gordon Growth Model.
    """
    return (fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)

def calculate_terminal_value_exit_multiple(fcf, exit_multiple):
    """
    Calculates terminal value using an exit multiple on final year cash flow.
    """
    return fcf * exit_multiple


def discounted_cash_flows(projected, terminal, discount_rate):
    return sum([cf / ((1 + discount_rate) ** (i + 1)) for i, cf in enumerate(projected)]) + terminal / ((1 + discount_rate) ** len(projected))

