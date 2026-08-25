package sap.sox

import rego.v1

# Default stance: Block all unauthorized requests
default allow := false
default requires_hitl := false

# Rule 1: Allow credit limit updates under or equal to $50,000
allow if {
    input.action == "update_credit_limit"
    input.payload.new_limit <= 50000
}

# Rule 2: Require Human-in-the-Loop escalation for requests over $50,000
requires_hitl if {
    input.action == "update_credit_limit"
    input.payload.new_limit > 50000
}

deny_reason := "SOX Control Breach: Credit increase over $50,000 requires manager approval." if {
    requires_hitl
}
