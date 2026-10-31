"""A poisoned validity flag cannot invoke callbacks or retain a real owner."""
import pytest
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import sql_facts, forbid_execution
from sim2act.errors import DomainError


@pytest.mark.parametrize('foreign',[False,True])
def test_invalidating_real_issued_scope_closes_without_flag_dispatch(sql_facts,foreign):
    f=sql_facts;callbacks=[];finished=False
    class ForeignFlag:
        def __bool__(self):
            callbacks.append(True)
            raise AssertionError('Validity flag callback executed during cleanup')
    with pytest.raises(DomainError):
        with f.store.tx() as c,native_segment(f,c) as issued:
            assert issued.mode is not None and issued.mode.active
            assert issued.mode.scope._active and issued.mode.scope._issued
            if foreign:issued.graph.active=ForeignFlag()
            issued.graph.invalidate()
            assert issued.graph.active is False
            assert issued.mode.active is False and issued.mode.scope._active is False
            assert issued.mode.scope._issued=={} and issued.candidate.completed=={}
            assert callbacks==[]
            finished=True
            # The original context rejects further use of the invalid scope.
    assert finished and callbacks==[]
