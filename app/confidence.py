def calculate_confidence(results, decision_data, answer):
    if not results:
        return 0.0

    # kleinere Distanz = besser → invertieren
    scores = [1 / (1 + r["score"]) for r in results]

    avg_score = sum(scores) / len(scores)

    return round(avg_score, 2)