from flask_ask import question, statement, session
from statem import FSMStore, UninitializedStateMachine
import wrapt
import yaml


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
        self._scenario_steps = data['steps']

        # validate scenario for connectivity (unreachable states) and undefined states
        validate_scenario(self._first_step, self._scenario_steps)
        self.transition_map = self._get_fsm_transitions()

        # TODO: remove debug
        print("scenario transition rules: {}".format(self.transition_map))

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
    def start(self, handler, instance, args, kwargs):

        # TODO: remove debug
        print("instance: {}, self: {}".format(instance, self))
        print("start FSM for session {}".format(session.sessionId))

        # create state machine for current session
        self.session_machines.create_fsm(session.sessionId)
        return handler(*args, **kwargs)

    @wrapt.decorator
    def stop(self, handler, _instance, args, kwargs):
        try:
            self.session_machines.delete_fsm(session.sessionId)

            # TODO: remove debug
            print("instance: {}, self: {}".format(_instance, self))
            print("delete FSM for session {}".format(session.sessionId))

            return handler(*args, **kwargs)

        except UninitializedStateMachine as e:

            # TODO: remove debug
            print("catch: {}".format(e))

            return statement('server error occured')

    @wrapt.decorator
    def guide(self, handler, _instance, args, kwargs):

        # TODO: remove debug
        print("handler decorator")
        print("instance: {}, self: {}".format(_instance, self))
        print("args: {}".format(args))
        for k, v in kwargs.items():
            print("{}: {}".format(k,v))

        try:
            invocation_trigger = handler.__name__
            session_id = session.sessionId
            if self.session_machines.can(session_id, invocation_trigger):
                # TODO: remove debug
                print("ok, moved fsm to: {}".format(self.session_machines.current_state(session_id)))
                return handler(*args, **kwargs)
            else:

                # TODO: remove debug
                print("transition not allowed, reprompt")
                current_state = self.session_machines.current_state(session_id)
                return question(self._scenario_steps[current_state]['reprompt'])

        except UninitializedStateMachine as e:

            # TODO: remove debug
            print("catch: {}".format(e))

            return statement('server error occured')


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

            # TODO: remove debug
            print("catch: {}".format(e))

            return statement('server error occured')


    # TODO: periodically clean old unfinished state machines (what is session max lifetime?)
