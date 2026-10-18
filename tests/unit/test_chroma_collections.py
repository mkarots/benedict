"""Shared Chroma client: one database, two collection families."""

from benedict.lib.chroma import code_collection_name, conversation_collection_name


def test_code_and_conversation_collection_names_do_not_collide():
    same_id = "acme/repo"
    code = code_collection_name(same_id)
    conversation = conversation_collection_name(same_id)
    assert code != conversation
    assert code.startswith("repo_")
    assert conversation.startswith("conversation_")
    assert code_collection_name(same_id) == code
    assert conversation_collection_name("C1") != conversation_collection_name("C2")
