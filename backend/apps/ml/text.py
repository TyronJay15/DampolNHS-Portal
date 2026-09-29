import math
import re
from collections import Counter, defaultdict

TOKEN = re.compile(r'[a-z0-9]+')


def tokenize(text):
    words = TOKEN.findall(str(text or '').lower())
    grams = list(words)
    grams.extend(f'{left} {right}' for left, right in zip(words, words[1:]))
    return grams


class TfidfVectorizer:
    def __init__(self):
        self.idf = {}

    def fit(self, documents):
        df = Counter()
        for doc in documents:
            df.update(set(tokenize(doc)))
        total = max(len(documents), 1)
        self.idf = {token: math.log((1 + total) / (1 + count)) + 1 for token, count in df.items()}
        return self

    def transform_one(self, text):
        tokens = tokenize(text)
        if not tokens:
            return {}
        tf = Counter(tokens)
        length = len(tokens)
        return {token: (tf[token] / length) * self.idf[token] for token in tf if token in self.idf}

    def dump(self):
        return {'idf': self.idf}

    @classmethod
    def load(cls, payload):
        model = cls()
        model.idf = {key: float(value) for key, value in (payload or {}).get('idf', {}).items()}
        return model


class MultinomialNB:
    def __init__(self, alpha=1.0):
        self.alpha = alpha
        self.classes = []
        self.log_prior = {}
        self.log_prob = {}

    def fit(self, vectors, labels):
        grouped = defaultdict(list)
        for vector, label in zip(vectors, labels):
            grouped[label].append(vector)
        total = len(labels)
        vocab = {token for vector in vectors for token in vector}
        self.classes = sorted(grouped)
        self.log_prior = {}
        self.log_prob = {}
        for label in self.classes:
            rows = grouped[label]
            self.log_prior[label] = math.log(len(rows) / total)
            weights = Counter()
            for vector in rows:
                weights.update(vector)
            total_weight = sum(weights.values()) + self.alpha * max(len(vocab), 1)
            self.log_prob[label] = {
                token: math.log((weights[token] + self.alpha) / total_weight) for token in vocab
            }
        return self

    def predict_proba(self, vector):
        scores = {}
        for label in self.classes:
            score = self.log_prior[label]
            fallback = math.log(self.alpha / (self.alpha * max(len(self.log_prob[label]), 1)))
            for token, weight in vector.items():
                score += weight * self.log_prob[label].get(token, fallback)
            scores[label] = score
        peak = max(scores.values()) if scores else 0
        exp = {label: math.exp(score - peak) for label, score in scores.items()}
        denom = sum(exp.values()) or 1
        return {label: value / denom for label, value in exp.items()}

    def dump(self):
        return {
            'alpha': self.alpha,
            'classes': self.classes,
            'log_prior': self.log_prior,
            'log_prob': self.log_prob,
        }

    @classmethod
    def load(cls, payload):
        model = cls(alpha=float((payload or {}).get('alpha', 1)))
        model.classes = list((payload or {}).get('classes') or [])
        model.log_prior = {key: float(value) for key, value in (payload or {}).get('log_prior', {}).items()}
        model.log_prob = {
            label: {token: float(weight) for token, weight in probs.items()}
            for label, probs in (payload or {}).get('log_prob', {}).items()
        }
        return model
