package budget

# Budget enforcement policy
# Gates deployments if team is over budget or forecast exceeds limit

default allow = false

# Allow if within budget and forecast is acceptable
allow {
    within_budget
    forecast_acceptable
}

# Check current spend is within threshold (90% by default)
within_budget {
    current_spend := input.current_spend
    limit := input.budget.limit
    threshold := object.get(input.budget, "threshold", 0.9)
    current_spend <= (limit * threshold)
}

# Check forecasted spend won't exceed limit
forecast_acceptable {
    forecast := input.forecast_spend
    limit := input.budget.limit
    forecast <= limit
}

# Violation messages
violations[msg] {
    not within_budget
    current_spend := input.current_spend
    limit := input.budget.limit
    threshold := object.get(input.budget, "threshold", 0.9)
    msg := sprintf("Budget threshold exceeded: $%.2f > $%.2f (%.0f%% of limit)", [current_spend, limit * threshold, threshold * 100])
}

violations[msg] {
    not forecast_acceptable
    forecast := input.forecast_spend
    limit := input.budget.limit
    msg := sprintf("Forecasted spend exceeds budget: $%.2f > $%.2f", [forecast, limit])
}

# Burn rate check (spending too fast)
burn_rate_high {
    days_in_month := 30
    days_elapsed := input.days_elapsed
    current_spend := input.current_spend
    limit := input.budget.limit

    # Calculate daily burn rate
    daily_burn := current_spend / days_elapsed

    # Project to end of month
    projected := daily_burn * days_in_month

    # High burn rate if projection > 110% of limit
    projected > (limit * 1.1)
}

violations[msg] {
    burn_rate_high
    msg := "Burn rate too high - projected to exceed budget by >10%"
}
