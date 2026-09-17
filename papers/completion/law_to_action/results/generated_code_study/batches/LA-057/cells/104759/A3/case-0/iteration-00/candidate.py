def run(payload):
    # Query AbuseIPDB for IP risk score
    # This is the only permitted handler for this source family
    result = emit_allowed(payload)
    return result