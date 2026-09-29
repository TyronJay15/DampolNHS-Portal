def fit_line(xs, ys):
    points = [(float(x), float(y)) for x, y in zip(xs, ys)]
    count = len(points)
    if count < 2:
        return {'slope': 0.0, 'intercept': points[0][1] if points else 0.0, 'r2': 0.0, 'n': count}
    mean_x = sum(x for x, _y in points) / count
    mean_y = sum(y for _x, y in points) / count
    variance = sum((x - mean_x) ** 2 for x, _y in points)
    slope = 0.0 if variance == 0 else sum((x - mean_x) * (y - mean_y) for x, y in points) / variance
    intercept = mean_y - slope * mean_x
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    total = sum((y - mean_y) ** 2 for _x, y in points)
    return {
        'slope': slope,
        'intercept': intercept,
        'r2': 0.0 if total == 0 else max(0.0, 1 - residual / total),
        'n': count,
    }


def predict_line(model, x):
    return float(model['intercept']) + float(model['slope']) * float(x)
