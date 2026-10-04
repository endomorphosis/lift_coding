def boundary_sign(value: int) -> int:
    if value < -7:
        return -1
    if value > 13:
        return 1
    return 0
