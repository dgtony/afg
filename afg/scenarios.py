from flask_ask import question, statement, session
from .statem import FSMStore, UninitializedStateMachine
import logging
import wrapt
import yaml


logger = logging.getLogger('scenario guide')


INTERNAL_ERROR_MSG = 'server error occured'


class UndefinedState(KeyError):
    pass


class UnreachableState(ValueError):
    pass


def _get_transitions(steps):
    defined_steps = set()
    transitions = {}
    for step_name, step in steps.items():
        defined_steps.add(step_name)
        transitions[step_name] = []
        if isinstance(step, dict) and 'events' in step:
            transitions[step_name].extend([ev['next'] for ev in step['events'].values()
                                  if isinstance(ev, dict) and 'next' in ev and ev['next'] is not None])
    return defined_steps, transitions


def _walk_steps(step, transition_map, visited):
    visited.add(step)
    try:
        curr_state = transition_map[step]
    except KeyError:
        raise UndefinedState("step {} not defined in scenario".format(step))
    for ns in curr_state:
        if ns is not None and ns not in visited:
            visited.update(_walk_steps(ns, transition_map, visited))
    return visited


def _analyze_steps(init_step, steps):
    defined_steps, transitions = _get_transitions(steps)
    reachable_steps = _walk_steps(init_step, transitions, set())
    return defined_steps, reachable_steps


def validate_scenario(init_step, steps):
    defined_steps, reachable_steps = _analyze_steps(init_step, steps)
    diff = defined_steps.difference(reachable_steps)
    if len(diff) > 0:
        raise UnreachableState("following states are unreachable: {}".format(diff))


class Supervisor(object):

    def __init__(self, filename):
        super(Supervisor, self).__init__()
        with open(filename, 'r') as fd:
            data = yaml.load(fd)
        self._first_step = data['first_step']
        self._last_step = data['last_step']
        self._default_help = data['default_help']
        self._scenario_steps = data['steps']

        # validate scenario for connectivity (unreachable states) and undefined states
        validate_scenario(self._first_step, self._scenario_steps)
        self.transition_map = self._get_fsm_transitions()
        self.session_machines = FSMStore(self._first_step, self._last_step, self.transition_map)

    def _get_fsm_transitions(self):
        event_transitions = []
        steps = self._scenario_steps
        for step in steps.keys():
            if steps[step] is not None:
                event_transitions.extend([{'name': event, 'src': step, 'dst': steps[step]['events'][event]['next']}
                                for event in steps[step]['events'].keys() if steps[step]['events'][event] is not None])
        return event_transitions

    @wrapt.decorator
    def start(self, handler, _instance, args, kwargs):
        # create state machine for current session
        self.session_machines.create_fsm(session.sessionId)
        return handler(*args, **kwargs)

    @wrapt.decorator
    def stop(self, handler, _instance, args, kwargs):
        try:
            self.session_machines.delete_fsm(session.sessionId)
            return handler(*args, **kwargs)

        except UninitializedStateMachine as e:
            logger.error(e)
            return statement(INTERNAL_ERROR_MSG)

    @wrapt.decorator
    def guide(self, handler, _instance, args, kwargs):
        try:
            invocation_trigger = handler.__name__
            session_id = session.sessionId
            if self.session_machines.can(session_id, invocation_trigger):
                return handler(*args, **kwargs)
            else:
                current_state = self.session_machines.current_state(session_id)
                return question(self._scenario_steps[current_state]['reprompt'])

        except UninitializedStateMachine as e:
            logger.error(e)
            return statement(INTERNAL_ERROR_MSG)

    @property
    def reprompt_error(self):
        """
        Intended to be used in case of erroneous input data
        """
        try:
            session_id = session.sessionId
            self.session_machines.rollback_fsm(session_id)
            current_state = self.session_machines.current_state(session_id)
            return question(self._scenario_steps[current_state]['reprompt'])
        except UninitializedStateMachine as e:
            logger.error(e)
            return statement(INTERNAL_ERROR_MSG)

    def move_to_step(self, step):
        """
        Use in cases when you need to move in given step depending on input
        """
        if step not in self._scenario_steps.keys():
            raise UndefinedState("step {} not defined in scenario".format(step))
        try:
            session_id = session.sessionId
            self.session_machines.set_state(session_id, step)
        except UninitializedStateMachine as e:
            logger.error(e)
            return statement(INTERNAL_ERROR_MSG)

    def get_current_state(self):
        """
        Get current state for user session or None if session doesn't exist
        """
        try:
            session_id = session.sessionId
            return self.session_machines.current_state(session_id)
        except UninitializedStateMachine as e:
            logger.error(e)

    def get_help(self):
        """
        Get context help, depending on the current step. If no help for current step
        was specified in scenario description file, default one will be returned.
        """
        current_state = self.get_current_state()
        if current_state is None:
            return statement(INTERNAL_ERROR_MSG)
        else:
            try:
                return self._scenario_steps[current_state]['help']
            except KeyError:
                return self._default_help
