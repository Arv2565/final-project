"""Unit tests for ambiguity remover node helpers."""

from src.nodes.ambiguity_remover_node import _already_answered_question


def test_already_answered_question_true_for_answered_duplicate():
    history = [
        {"question": "Which district in Kerala?", "answer": "Thiruvananthapuram"},
    ]

    assert _already_answered_question("Which district in Kerala?", history) is True


def test_already_answered_question_false_for_unanswered_or_different():
    history = [
        {"question": "Which district in Kerala?", "answer": ""},
        {"question": "What is the property type?", "answer": "Residential"},
    ]

    assert _already_answered_question("Which district in Kerala?", history) is False
    assert _already_answered_question("Which municipality in Kerala?", history) is False
