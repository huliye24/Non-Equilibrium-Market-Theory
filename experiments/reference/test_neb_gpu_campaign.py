from neb_gpu_campaign import KS, MS, NS, QL, QT, RHOS, SLOPES, TFS

def test_frozen_stage_a_grid_count():
    structural=len(NS)*len(MS)*len(QL)*len(QT)*len(KS)*len(SLOPES)
    assert structural == 199_584
    assert structural*len(RHOS)*len(TFS) == 2_395_008

def test_live_execution_is_not_imported():
    import neb_gpu_campaign
    source=open(neb_gpu_campaign.__file__,encoding='utf-8').read().lower()
    assert 'fapi/v1/order' not in source
    assert 'live_enabled' in source
