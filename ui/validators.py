def safe_strip(value):
    return str(value).strip() if value else ""

def validate_request_data(data):
    errors = []
    requires_trm = False

    if not safe_strip(data.get("no_solicitud")):
        errors.append("⚠️ The 'Request Number (M)' field is required.")

    if not safe_strip(data.get("commercial")) or data["commercial"] == " ":
        errors.append("⚠️ Please select a Sales Representative.")

    if not safe_strip(data.get("client")) or data["client"] == " ":
        errors.append("⚠️ Please select a Client.")

    if not safe_strip(data.get("customer_name")):
        errors.append("⚠️ The 'Customer Name' field is required.")

    if not data.get("container_type"):
        errors.append("⚠️ Please select at least one Container Type.")

    if not data.get("transport_type"):
        errors.append("⚠️ Please select at least one Transport Service.")

    if not safe_strip(data.get("operation_type")):
        errors.append("⚠️ The 'Operation Type' field is required.")

    for cont, surcharges in data.get("additional_surcharges", {}).items():
        for i, surcharge in enumerate(surcharges):
            if not safe_strip(surcharge.get("concept")):
                errors.append(f"⚠️ Surcharge concept in '{cont}' #{i+1} is required.")
            if surcharge.get("currency") not in ['USD', 'COP']:
                errors.append(f"⚠️ Please select a valid currency for surcharge in '{cont}' #{i+1}.")
            if surcharge.get("cost", 0.0) <= 0:
                errors.append(f"⚠️ The surcharge amount in '{cont}' #{i+1} must be greater than 0.")

    return errors