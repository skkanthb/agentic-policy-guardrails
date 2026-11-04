package agent.governance

import rego.v1

default allow := false

default require_hitl := false

# Requests above this amount need human approval.
credit_approval_threshold := 50000

authorized_roles := {"Finance_Manager", "System_Admin"}

# Exact parameter set each tool accepts. Missing or extra keys are rejected.
tool_parameters := {
	"update_credit_limit": {"account_id", "new_limit"},
	"get_customer_balance": {"account_id"},
}

top_level_fields := {"user_id", "user_role", "tool_name", "parameters", "hitl_approval_token"}

# Allow only a well-formed, authorized request at or under the threshold.
allow if {
	count(violations) == 0
	not exceeds_financial_threshold
}

# Approval is offered only for a well-formed, authorized request over the threshold.
# hitl_approval_token is not verified in this prototype, so it never bypasses approval.
require_hitl if {
	count(violations) == 0
	exceeds_financial_threshold
}

exceeds_financial_threshold if {
	input.tool_name == "update_credit_limit"
	input.parameters.new_limit > credit_approval_threshold
}

# Every reason the request is rejected. Empty set = request is well formed and authorized.
violations contains "unknown top-level field" if {
	count(object.keys(input) - top_level_fields) > 0
}

violations contains "unknown tool_name" if {
	not known_tool
}

violations contains "parameters must be an object" if {
	not parameters_is_object
}

violations contains "parameters do not match tool" if {
	expected := tool_parameters[input.tool_name]
	is_object(input.parameters)
	object.keys(input.parameters) != expected
}

violations contains "account_id must be a non-empty string" if {
	known_tool
	not valid_account_id
}

violations contains "new_limit must be a positive number" if {
	input.tool_name == "update_credit_limit"
	not valid_new_limit
}

violations contains "hitl_approval_token must be a string or null" if {
	"hitl_approval_token" in object.keys(input)
	input.hitl_approval_token != null
	not is_string(input.hitl_approval_token)
}

violations contains "user_role not authorized" if {
	not role_authorized
}

# Helpers. Each negation above goes through a named rule: in OPA 1.20.1,
# `not input.user_role in authorized_roles` is undefined, not true, when user_role is missing.
known_tool if tool_parameters[input.tool_name]

parameters_is_object if is_object(input.parameters)

role_authorized if input.user_role in authorized_roles

valid_account_id if {
	is_string(input.parameters.account_id)
	input.parameters.account_id != ""
}

valid_new_limit if {
	is_number(input.parameters.new_limit)
	input.parameters.new_limit > 0
}
