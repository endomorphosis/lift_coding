def run(payload):
    if 'source' in payload:
        return emit_allowed(payload)
    return emit_allowed({'message': 'No source provided'})