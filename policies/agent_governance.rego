package agent.governance

import rego.v1

default allow = false
default require_hitl = false

# Allow execution ONLY IF all safety checks pass
allow if {
    valid_action
    not exceeeds_financial_threshold
    user_authorized
}

# Require Human-in-the-Loop (HITL) if threshold is exceeded but below hard lock
require_hitl if {
    valid_action
    exceeeds_financial_threshold
    input.hitl_approval_token == null
}

# 1. Action Authorization Check
valid_action if {
    input.tool_name in ["update_credit_limit", "get_customer_balance"]
}

# 2. Financial Boundary Enforcement ($50,000 threshold limit)
exceeeds_financial_threshold if {
    input.tool_name == "update_credit_limit"
    input.parameters.new_limit > 50000
}

# 3. Role-Based Access Check
user_authorized if {
    input.user_role in ["Finance_Manager", "System_Admin"]
}
