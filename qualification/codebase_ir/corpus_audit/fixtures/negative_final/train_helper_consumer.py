from train import step


def final_consumer(value: int) -> int:
    return step(value) * 11
