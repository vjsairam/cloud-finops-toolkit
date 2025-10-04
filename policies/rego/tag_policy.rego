package tags

# Tag governance policy
# Enforces required tags on all cloud resources

default allow = false

# Required tags for all resources
required_tags := ["Environment", "Team", "CostCenter"]

# Allow if all required tags are present and valid
allow {
    all_required_tags_present
    tags_have_valid_values
}

# Check all required tags exist
all_required_tags_present {
    resource_tags := object.keys(input.tags)
    count([tag | tag := required_tags[_]; tag in resource_tags]) == count(required_tags)
}

# Check tag values are not empty
tags_have_valid_values {
    count([tag | tag := input.tags[_]; tag != ""]) == count(object.keys(input.tags))
}

# Generate violation messages for missing tags
violations[msg] {
    not all_required_tags_present
    resource_tags := object.keys(input.tags)
    missing := [tag | tag := required_tags[_]; not tag in resource_tags]
    msg := sprintf("Missing required tags: %v", [missing])
}

# Check for empty tag values
violations[msg] {
    not tags_have_valid_values
    empty_tags := [key | value := input.tags[key]; value == ""]
    msg := sprintf("Tags have empty values: %v", [empty_tags])
}

# Environment-specific rules
violations[msg] {
    input.tags.Environment == "prod"
    not input.tags.Backup
    msg := "Production resources must have 'Backup' tag"
}

violations[msg] {
    input.tags.Environment == "prod"
    not input.tags.Owner
    msg := "Production resources must have 'Owner' tag"
}

# Cost center validation (must be numeric)
violations[msg] {
    cost_center := input.tags.CostCenter
    not regex.match("^[0-9]+$", cost_center)
    msg := sprintf("CostCenter must be numeric, got: %v", [cost_center])
}
