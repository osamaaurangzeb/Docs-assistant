import pytest

from app.services.vector_store import VectorIndex


def make_index():
    return VectorIndex(["x-axis", "y-axis", "diagonal"], [[1, 0], [0, 1], [1, 1]])


def test_returns_best_match_first():
    matches = make_index().search([1, 0.1], top_k=3)
    assert [m.index for m in matches][0] == 0
    assert matches[0].score > matches[1].score


def test_top_k_limits_results():
    assert len(make_index().search([1, 1], top_k=2)) == 2


def test_min_score_filters_out_weak_matches():
    matches = make_index().search([1, 0], top_k=3, min_score=0.9)
    assert [m.index for m in matches] == [0]


def test_scale_of_vectors_does_not_change_similarity():
    a = make_index().search([1, 0], top_k=1)[0].score
    b = make_index().search([100, 0], top_k=1)[0].score
    assert a == pytest.approx(b)


def test_zero_query_matches_nothing_above_threshold():
    assert make_index().search([0, 0], top_k=3, min_score=0.1) == []


def test_dimension_mismatch_is_rejected():
    with pytest.raises(ValueError):
        make_index().search([1, 0, 0], top_k=1)


def test_construction_validates_inputs():
    with pytest.raises(ValueError):
        VectorIndex(["a"], [[1], [2]])
    with pytest.raises(ValueError):
        VectorIndex([], [])
