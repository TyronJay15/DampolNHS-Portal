"""Linear trend (KDD data-mining stage) and its forward-in-time evaluation.

Fitting uses scikit-learn's LinearRegression and runs only when a model is trained. Prediction is plain
arithmetic on the stored slope and intercept, so page requests never load scikit-learn into memory.

Evaluation never lets a model see the future: each later year is predicted from the years before it
only, and compared with the naive baseline "same as last year".
"""

import math


def fit_line(xs, ys):
    """Least-squares line through the points: slope, intercept, r2 and the number of points."""
    import numpy as np  # imported here so only training pays for the libraries
    from sklearn.linear_model import LinearRegression

    x = np.asarray(xs, dtype=float).reshape(-1, 1)
    y = np.asarray(ys, dtype=float)
    count = len(y)
    if count < 2:
        return {'slope': 0.0, 'intercept': float(y[0]) if count else 0.0, 'r2': 0.0, 'n': count}
    model = LinearRegression().fit(x, y)
    # R² is undefined when every year has the same count; report 0 then, as there is nothing to explain.
    r2 = float(model.score(x, y)) if float(np.ptp(y)) else 0.0
    return {'slope': float(model.coef_[0]), 'intercept': float(model.intercept_), 'r2': max(0.0, r2), 'n': count}


def predict_line(model, x):
    return float(model['intercept']) + float(model['slope']) * float(x)


def forward_tests(points, min_train):
    """Predict each year after the first min_train from the earlier years only.

    points: [(x, y)] sorted by x. Returns one row per tested year with the trend's prediction, the
    "same as last year" baseline, and the actual count.
    """
    tests = []
    for end in range(min_train, len(points)):
        train = points[:end]
        x, actual = points[end]
        model = fit_line(*zip(*train))
        tests.append(
            {
                'trained_through': train[-1][0],
                'x': x,
                'predicted': predict_line(model, x),
                'baseline': float(train[-1][1]),
                'actual': float(actual),
            }
        )
    return tests


def mae(errors):
    return sum(abs(error) for error in errors) / len(errors) if errors else None


def rmse(errors):
    return math.sqrt(sum(error**2 for error in errors) / len(errors)) if errors else None
