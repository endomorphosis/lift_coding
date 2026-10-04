# Authored final fixture with Unicode parameters.
def ordered_window(下界: int, 上界: int) -> bool:
    return 下界 + 7 <= 上界 and 下界 != 上界
