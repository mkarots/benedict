"""Unit tests for command classification."""

from benedict.commands.command_classifier import CommandClassifier
from benedict.commands.command_definitions import COMMAND_DEFINITIONS, CommandType


def test_classifies_onboard_and_extracts_repo():
    classifier = CommandClassifier()
    intent = classifier.classify("onboard repo example-org/example-repo")
    assert intent is not None
    assert intent.command_type == CommandType.ONBOARD
    assert intent.parameters.get("repo") == "example-org/example-repo"
    assert intent.confidence >= 0.5


def test_classifies_status():
    classifier = CommandClassifier()
    intent = classifier.classify("what's the status")
    assert intent is not None
    assert intent.command_type == CommandType.STATUS


def test_classifies_update_index():
    classifier = CommandClassifier()
    intent = classifier.classify("update index force")
    assert intent is not None
    assert intent.command_type == CommandType.UPDATE_INDEX


def test_unknown_text_is_not_a_command():
    classifier = CommandClassifier()
    assert classifier.classify("how does authentication work?") is None


def test_get_available_commands():
    classifier = CommandClassifier()
    commands = classifier.get_available_commands()
    names = {item.name for item in commands}
    assert names == {item.name for item in COMMAND_DEFINITIONS}
    assert "onboard" in names


def test_onboard_examples_use_generic_repo_name():
    onboard = next(item for item in COMMAND_DEFINITIONS if item.name == "onboard")
    assert all("mkarots" not in example for example in onboard.examples)
    assert any("example-org/example-repo" in example for example in onboard.examples)
