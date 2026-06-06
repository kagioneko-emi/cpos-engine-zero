from __future__ import annotations

import cpos.goals as goals


def assert_goal_safety(payload):
    assert payload['metadata_only'] is True
    assert payload['raw_request_stored'] is False
    assert payload['raw_diff_stored'] is False
    assert payload['raw_outputs_stored'] is False
    assert payload['secret_values_stored'] is False
    assert payload['execute_automatically'] is False


def test_list_goals_returns_read_only_default_goal_set():
    payload = goals.list_goals()

    assert payload['schema'] == 'kagioneko.goal_set.v1'
    assert payload['write_enabled'] is False
    assert payload['autonomous_goal_updates'] is False
    assert payload['self_preservation_goals'] is False
    assert payload['count'] >= 6
    ids = {goal['goal_id'] for goal in payload['goals']}
    assert 'cpos_v0_1_1_final' in ids
    assert 'zenn_cognitive_agent_os_article' in ids
    assert 'world_model_mvp' in ids
    assert 'goal_manager_mvp' in ids
    for goal in payload['goals']:
        assert goal['schema'] == 'kagioneko.goal.v1'
        assert_goal_safety(goal)
        assert 'self_preservation' not in goal['goal_id']


def test_list_goals_filters_by_state_and_scope():
    planned = goals.list_goals(state='planned')
    release = goals.list_goals(scope='release')

    assert planned['count'] >= 1
    assert all(goal['state'] == 'planned' for goal in planned['goals'])
    assert release['count'] == 1
    assert release['goals'][0]['goal_id'] == 'cpos_v0_1_1_final'


def test_goal_summary_is_metadata_only_and_highlights_review_goals():
    summary = goals.goal_summary()

    assert summary['schema'] == 'kagioneko.goal_summary.v1'
    assert_goal_safety(summary)
    assert summary['write_enabled'] is False
    assert summary['autonomous_goal_updates'] is False
    assert summary['self_preservation_goals'] is False
    assert 'goal_manager_mvp' not in summary['active_or_review_goal_ids']
    assert summary['counts_by_state']['done'] >= 2
    assert 'zenn_cognitive_agent_os_article' in summary['active_or_review_goal_ids']
    assert 'cpos_v0_1_1_final' in summary['confirmation_required_goal_ids']


def test_goals_cli_json(capsys):
    goals.main(['list', '--state', 'paused', '--json'])

    out = capsys.readouterr().out
    assert 'kagioneko.goal_set.v1' in out
    assert 'cpos_v0_1_1_final' in out
    assert '"write_enabled": false' in out
