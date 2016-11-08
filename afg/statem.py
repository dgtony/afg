import time
import threading
from fysom import Fysom


CLEAN_PERIOD = 60
MAX_SESSION_LIFETIME = 3600


class UninitializedStateMachine(ValueError):
    pass


class FSMStore(object):
    def __init__(self, first_step, last_step, transition_map):
        super(FSMStore, self).__init__()
        self.store = {}
        self.lock = threading.Lock()
        self.first_step = first_step
        self.last_step = last_step
        self.transition_map = transition_map
        self.cleaner = FSMCleaner(self.store, self.lock, last_step)
        self.cleaner.start()

    def _update_access_time(self, session_id):
        self.store[session_id]['access_time'] = time.time()

    def _verify_session_id(self, session_id):
        if session_id not in self.store.keys():
            raise UninitializedStateMachine("no machine for session: {}".format(session_id))

    def create_fsm(self, session_id):
        new_fsm = dict(fsm=Fysom(initial=self.first_step, events=self.transition_map),
                       access_time=time.time(), previous_step=None)

        def save_previous_step(ev):
            self.store[session_id]['previous_step'] = ev.src

        new_fsm['fsm'].onchangestate = save_previous_step
        self.lock.acquire()
        self.store[session_id] = new_fsm
        self.lock.release()

    def can(self, session_id, trigger_event):
        self._verify_session_id(session_id)
        with self.lock:
            self._update_access_time(session_id)
            if self.store[session_id]['fsm'].can(trigger_event):
                self.store[session_id]['fsm'].trigger(trigger_event)
                return True

    def current_state(self, session_id):
        self._verify_session_id(session_id)
        with self.lock:
            self._update_access_time(session_id)
            current_state = self.store[session_id]['fsm'].current
        return current_state

    def set_state(self, session_id, state_name):
        self._verify_session_id(session_id)
        with self.lock:
            self._update_access_time(session_id)
            self.store[session_id]['fsm'].current = state_name

    def delete_fsm(self, session_id):
        self._verify_session_id(session_id)
        with self.lock:
            del self.store[session_id]

    def rollback_fsm(self, session_id):
        self._verify_session_id(session_id)
        with self.lock:
            self._update_access_time(session_id)
            previous_step = self.store[session_id]['previous_step']
            self.store[session_id]['fsm'].current = previous_step


class FSMCleaner(threading.Thread):

    def __init__(self, store, store_lock, last_step):
        super(FSMCleaner, self).__init__()
        self.store = store
        self.store_lock = store_lock
        self.last_step = last_step
        self.setDaemon(True)
        self.setName("fsm-cleaner")

    def run(self):
        while True:
            time.sleep(CLEAN_PERIOD)
            with self.store_lock:
                self.make_clean()

    def make_clean(self):
        check_time = time.time()
        outdated_sessions = [k for k, v in self.store.items()
                                if (check_time - v['access_time']) > MAX_SESSION_LIFETIME
                                    or v['fsm'].current == self.last_step]
        for session in outdated_sessions:
            del self.store[session]
