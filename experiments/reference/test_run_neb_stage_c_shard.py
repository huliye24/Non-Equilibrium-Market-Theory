from pathlib import Path


def test_completion_notification_requires_real_evaluations():
    source = Path(__file__).with_name("run_neb_stage_c_shard.py").read_text(encoding="utf-8")
    assert 'STAGE_C_WALK_FORWARD_COMPLETE' in source
    assert 'candidate_evaluations' in source
    assert '阶段C真实滚动实验完成' in source
    assert '阶段C候选' not in source
