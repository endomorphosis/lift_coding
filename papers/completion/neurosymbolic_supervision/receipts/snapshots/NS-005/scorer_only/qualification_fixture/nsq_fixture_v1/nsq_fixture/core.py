POLICY = {'mode': 'strict', 'plugin': 'default'}
def add(a, b):
    return a + b
def process(values):
    return [add(v, 1) for v in values]
def authorize(token):
    return token == 'admit-ok'
