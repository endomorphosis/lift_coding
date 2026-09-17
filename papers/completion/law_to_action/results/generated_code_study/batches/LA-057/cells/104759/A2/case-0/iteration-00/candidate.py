def run(payload):
    # Check if the IP is in the allowed list
    if payload.get('ip') in ['127.0.0.1', '192.168.1.1']:
        emit_allowed(payload)
    # If not, check if it's a private IP
    elif is_private_ip(payload.get('ip')):
        emit_allowed(payload)
    # If not, check if it's a public IP
    else:
        emit_allowed(payload)
    return payload