import pytest
from .statem import FSMStore, FSMCleaner, UninitializedStateMachine


def get_last_access_time(fsm, session_id):
    return fsm.store[session_id]['access_time']


class TestFSM:
    @pytest.fixture()
    def sample_fsm(self):
        session_id = 1
        init_step = 'top'
        last_step = 'down'
        transition_map = [{'name': 'first', 'src': 'top', 'dst': 'left'},
                          {'name': 'second', 'src': 'top', 'dst': 'right'},
                          {'name': 'third', 'src': 'left', 'dst': 'down'},
                          {'name': 'fourth', 'src': 'right', 'dst': 'down'},
                          {'name': 'short', 'src': 'top', 'dst': 'down'}]
        sample_fsm = FSMStore(init_step, last_step, transition_map)
        sample_fsm.create_fsm(session_id)
        return sample_fsm

    def test_create_session(self, sample_fsm):
        assert len(sample_fsm.store) == 1
        sample_fsm.create_fsm(2)
        assert len(sample_fsm.store) == 2
        # replace existing session state machine
        sample_fsm.create_fsm(1)
        assert len(sample_fsm.store) == 2

    def test_transitions1(self, sample_fsm):
        session_id = 1
        assert sample_fsm.can(session_id, 'first')
        assert sample_fsm.can(session_id, 'second') is None
        assert sample_fsm.can(session_id, 'third')

    def test_transitions2(self, sample_fsm):
        session_id = 1
        assert sample_fsm.can(session_id, 'short')
        assert sample_fsm.can(session_id, 'first') is None
        assert sample_fsm.can(session_id, 'fourth') is None

    def test_transitions3(self, sample_fsm):
        session_id = 1
        assert sample_fsm.can(session_id, 'second')
        assert sample_fsm.can(session_id, 'third') is None
        assert sample_fsm.can(session_id, 'fourth')

    def test_transitions4(self, sample_fsm):
        session_id = 1
        assert sample_fsm.can(session_id, 'third') is None
        assert sample_fsm.can(session_id, 'fourth') is None
        assert sample_fsm.can(session_id, 'non_existent_event') is None

    def test_non_existing_session(self, sample_fsm):
        non_ex_session_id = 2
        with pytest.raises(UninitializedStateMachine):
            assert sample_fsm.can(non_ex_session_id, 'third')

    @pytest.mark.parametrize('step', ['top', 'right', 'left', 'down'])
    def test_set_state(self, step, sample_fsm):
        session_id = 1
        sample_fsm.set_state(session_id, step)
        assert sample_fsm.current_state(session_id) == step

    def test_access_time(self, sample_fsm):
        session_id = 1
        curr_time = get_last_access_time(sample_fsm, session_id)
        sample_fsm.can(session_id, 'second')
        assert get_last_access_time(sample_fsm, session_id) != curr_time

        curr_time = get_last_access_time(sample_fsm, session_id)
        sample_fsm.current_state(session_id)
        assert get_last_access_time(sample_fsm, session_id) != curr_time

        curr_time = get_last_access_time(sample_fsm, session_id)
        sample_fsm.set_state(session_id, 'third')
        assert get_last_access_time(sample_fsm, session_id) != curr_time

        curr_time = get_last_access_time(sample_fsm, session_id)
        sample_fsm.rollback_fsm(session_id)
        assert get_last_access_time(sample_fsm, session_id) != curr_time

    def test_delete_fsm(self, sample_fsm):
        session_id = 1
        sample_fsm.delete_fsm(session_id)
        assert len(sample_fsm.store) == 0

    def test_delete_non_existing_fsm(self, sample_fsm):
        non_ex_session_id = 2
        with pytest.raises(UninitializedStateMachine):
            sample_fsm.delete_fsm(non_ex_session_id)

    def test_fsm_rollback1(self, sample_fsm):
        session_id = 1
        # single transition
        sample_fsm.can(session_id, 'first')
        sample_fsm.rollback_fsm(session_id)
        assert sample_fsm.current_state(session_id) == 'top'
        # continuous transitions
        sample_fsm.can(session_id, 'first')
        sample_fsm.can(session_id, 'third')
        sample_fsm.rollback_fsm(session_id)
        assert sample_fsm.current_state(session_id) == 'left'

    def test_fsm_rollback2(self, sample_fsm):
        session_id = 1
        sample_fsm.can(session_id, 'first')
        sample_fsm.set_state(session_id, 'down')
        sample_fsm.rollback_fsm(session_id)
        assert sample_fsm.current_state(session_id) == 'left'

    def test_fsm_rollback3(self, sample_fsm):
        session_id = 1
        sample_fsm.set_state(session_id, 'down')
        sample_fsm.set_state(session_id, 'right')
        sample_fsm.rollback_fsm(session_id)
        assert sample_fsm.current_state(session_id) == 'down'

        # set state history
        sample_fsm.set_state(session_id, 'right')
        sample_fsm.set_state(session_id, 'left')
        sample_fsm.set_state(session_id, 'down')
        sample_fsm.set_state(session_id, 'down')
        sample_fsm.rollback_fsm(session_id)
        assert sample_fsm.current_state(session_id) == 'left'

    def test_fsm_rollback4(self, sample_fsm):
        session_id = 1
        sample_fsm.rollback_fsm(session_id)
        assert sample_fsm.current_state(session_id) == 'top'

        # more steps then have been done
        sample_fsm.can(session_id, 'first')
        sample_fsm.rollback_fsm(session_id)
        sample_fsm.rollback_fsm(session_id)
        sample_fsm.rollback_fsm(session_id)
        assert sample_fsm.current_state(session_id) == 'top'

        # set repeated states
        sample_fsm.set_state(session_id, 'right')
        sample_fsm.set_state(session_id, 'right')
        sample_fsm.set_state(session_id, 'right')
        sample_fsm.rollback_fsm(session_id)
        assert sample_fsm.current_state(session_id) == 'top'

