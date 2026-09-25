from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def average(values):
    """Mean of decimal scores, rounded half-up to two places. None when empty."""
    if not values:
        return None
    total = sum(values, Decimal('0'))
    return (total / len(values)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def parse_score(value):
    try:
        score = Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None
    if score < 0 or score > 100:
        return None
    return score.quantize(Decimal('0.01'))
