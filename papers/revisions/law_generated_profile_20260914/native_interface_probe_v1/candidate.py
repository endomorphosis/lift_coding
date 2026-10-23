def run(payload):
    total = 0
    for n in payload['numbers']:
        total = total + n
    write_json('public/result.json', {'sum': total})
