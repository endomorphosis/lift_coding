def guarded_flag(enabled: bool, blocked: bool) -> bool:
    return enabled and not blocked
