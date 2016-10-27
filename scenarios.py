import yaml
from flask import render_template_string
from flask_ask import question, session


import copy
from fysom import Fysom, FysomError
import time


class UninitializedStateMachine(ValueError):
    pass


class UndefinedState(KeyError):
    pass


class UnreachableState(ValueError):
    pass


def _get_transitions(steps):
    defined_steps = set()
    transitions = {}
    for step_name, step in steps.items():
        defined_steps.add(step_name)
        transitions[step_name] = [ev['next'] for ev in step['events'].values()
                                  if isinstance(ev, dict) and 'next' in ev and ev['next'] is not None]
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


    ##########


class Supervisor(object):

    def __init__(self, filename):
        super(Supervisor, self).__init__()
        with open(filename, 'r') as fd:
            data = yaml.load(fd)
        self.first_step = data['first_step']
        self.scenario_steps = data['steps']
        ev_trans = self._prepare_fsm(self.scenario_steps)

        # validate scenario for connectivity (unreachable states) and undefined states
        validate_scenario(self.first_step, self.scenario_steps)

        # construct scenario FSM
        self.reference_fsm = Fysom(initial=self.first_step, events=ev_trans)
        self.session_state_machines = {}

    @classmethod
    def _prepare_fsm(cls, steps):
        event_transitions = []
        for step in steps.keys():
            event_transitions.extend([{'name': event, 'src': step, 'dst': steps[step]['events'][event]['next']}
                                for event in steps[step]['events'].keys() if steps[step]['events'][event] is not None])
        return event_transitions

    def start(self):

        # TODO: remove debug
        print("start FSM for session {}".format(session.sessionId))

        self.session_state_machines[session.sessionId] = {
            'fsm': copy.deepcopy(self.reference_fsm),
            'mod_time': time.time()
        }

    def stop(self):
        del self.session_state_machines[session.sessionId]

        # TODO: remove debug
        print("delete FSM for session {}".format(session.sessionId))

    def proceed(self):
        sid = session.sessionId
        if sid not in self.session_state_machines.keys():
            raise UninitializedStateMachine("session {} didn't initialize its state machine".format(sid))
        fsm = self.session_state_machines[session.sessionId]['fsm']

        # TODO: get it from decorator args
        invocation_trigger = _get_caller_name()

        # TODO: remove debug
        print("invocation trigger for session {}: {}".format(sid, invocation_trigger))

        # TODO: think about: maybe move this behaviour to event decorator?
        if fsm.can(invocation_trigger):
            # move fsm to new allowed state
            fsm.trigger(invocation_trigger)
            return True, None
        else:
            # return reprompt for current state
            return False, self.scenario_steps[fsm.current]['reprompt']

    # TODO: periodically clean old unfinished state machines (what is session max lifetime?)
