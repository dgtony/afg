import actions
import inspect
import yaml
from flask import render_template_string
from flask_ask import statement, question, session


import copy
from fysom import Fysom, FysomError
import time


class ScenarioError(ValueError):
    pass


class UnknownStep(ScenarioError):
    pass


class UndefinedStep(ScenarioError):
    pass


class CurrentStepUndefined(UndefinedStep):
    pass


class StateDuplicates(ScenarioError):
    pass



def action2fun(action_name):
    return actions.action_map[action_name]


def error_catcher(fun):
    def wrapper(*args, **kwargs):
        try:
            response = fun(*args, **kwargs)
        except CurrentStepUndefined as e:
            response = {'type': 'error', 'reason': "current step undefined: {}".format(e)}
        except UnknownStep as e:
            response = {'type': 'error', 'reason': "unknown step: {}".format(e)}
        except actions.UndefinedAction as e:
            response = {'type': 'error', 'reason': "undefined action: {}".format(e)}
        except actions.MissingArg as e:
            response = {'type': 'error', 'reason': "missing argument: {}".format(e)}
        except Exception as e:
            response = {'type': 'error', 'reason': "general: {}".format(e)}
        return response
    return wrapper


######################


def _get_caller_name(nesting_level=3):
    """
    Use reflection to obtain trigger name
    """
    return inspect.stack()[nesting_level].function


class UninitializedStateMachine(ValueError):
    pass


class Supervisor(object):

    def __init__(self, filename):
        super(Supervisor, self).__init__()
        with open(filename, 'r') as fd:
            data = yaml.load(fd)
        first_step = data['first_step']
        scenario_steps = data['steps']

        ev_trans = self._prepare_fsm(scenario_steps)

        # TODO: validate for connectivity

        # load this shit
        self.reference_fsm = Fysom(initial=first_step, events=ev_trans)
        self.session_states = {}

    @classmethod
    def _prepare_fsm(cls, steps):
        event_transitions = []
        for step in steps.keys():
            event_transitions.extend([{'name': event, 'src': step, 'dst': steps[step]['events'][event]['next_step']}
                                for event in steps[step]['events'].keys() if steps[step]['events'][event] is not None])
        return event_transitions

    def start(self):
        self.session_states[session.sessionId] = {
            'fsm': copy.deepcopy(self.reference_fsm),
            'mod_time': time.time()
        }

    def stop(self):
        del self.session_states[session.sessionId]

    def proceed(self):
        sid = session.sessionId
        if sid not in self.session_states.keys():
            raise UninitializedStateMachine("session {} didn't initialize its state machine".format(sid))
        fsm = self.session_states[session.sessionId]['fsm']

        invocation_trigger = _get_caller_name()

        # TODO: remove debug
        print("invocation trigger for session {}: {}".format(sid, invocation_trigger))

        if fsm.can(invocation_trigger):
            # move fsm to new allowed state
            fsm.trigger(invocation_trigger)
            return True

    # TODO: periodically clean old unfinished state machines (what is session max lifetime?)


################################

class Scenario(object):

    def __init__(self, filename):
        super(Scenario, self).__init__()
        with open(filename, 'r') as fd:
            data = yaml.load(fd)
            self.first_step = data['first_step']
            self.scenario = data['steps']
        self.defined_steps = [step_name for step_name in self.scenario.keys()]
        self._validate_scenario()

    def _validate_scenario(self):
        """
        Scenario correctness verification
        """
        # verify for duplicates in state definitions
        if len(self.defined_steps) != len(set(self.defined_steps)):
            raise StateDuplicates

        called_steps, called_actions = set(), set()
        for s in self.defined_steps:
            step_triggers = self.scenario[s]['events']
            for trigger in step_triggers:
                if 'next_step' in step_triggers[trigger]:
                    called_steps.add(step_triggers[trigger]['next_step'])
                if 'action' in step_triggers[trigger]:
                    called_actions.add(step_triggers[trigger]['action'])
        # ok check out states
        for step in called_steps:
            if step not in self.defined_steps:
                raise UndefinedStep("scenario autocheck failure, state: {}".format(step))
        # check out actions
        defined_actions = actions.action_map.keys()
        for action in called_actions:
            if action not in defined_actions:
                raise actions.UndefinedAction("scenario autocheck failure, action: {}".format(action))

    @error_catcher
    def follow_scenario(self, args_ctx, session_ctx):
        event_trigger = _get_caller_name()

        # TODO: remove debug
        print("event trigger: {}".format(event_trigger))

        if 'step' not in session_ctx:
            raise CurrentStepUndefined
        current_step_name = session_ctx['step']

        if current_step_name not in self.defined_steps:
            raise UnknownStep("no step {} in scenario".format(current_step_name))
        elif event_trigger not in self.scenario[current_step_name]['events'].keys():
            return {'type': 'bad_trigger', 'reprompt': self.scenario[current_step_name]['reprompt']}
        else:
            scenario_variant = self.scenario[current_step_name]['events'][event_trigger]
            if 'action' in scenario_variant and scenario_variant['action'] is not None:
                # make defined action
                actions.make_action(scenario_variant['action'], args_ctx, session_ctx)

            if 'next_step' in scenario_variant and scenario_variant['next_step'] is not None:
                # set next step in context
                scenario_variant['response']['type'] = 'question'
                session_ctx['step'] = scenario_variant['next_step']
            else:
                scenario_variant['response']['type'] = 'statement'

            return {'type': 'ok', 'response': scenario_variant['response'],
                    'reprompt': self.scenario[current_step_name]['reprompt']}

    def _init_scenario(self, session_ctx):
        session_ctx['step'] = self.first_step


class ScenarioProcessor(object):

    def __init__(self, scenario_filename, server_app):
        super(ScenarioProcessor, self).__init__()
        self.scenario = Scenario(scenario_filename)
        self.app = server_app

    def _parse_scenario_response(self, scen_parser_response: dict, response_render_args: dict, reprompt_render_args: dict):
        if scen_parser_response['type'] == 'error':
            self.app.logger.error(scen_parser_response['reason'])
        elif scen_parser_response['type'] == 'bad_trigger':
            return question(render_template_string(scen_parser_response['reprompt'], **reprompt_render_args))
        elif scen_parser_response['type'] == 'ok':
            # successful response
            response = scen_parser_response['response']
            if response['type'] == 'question':
                alexa_response = question(render_template_string(response['speech'], **response_render_args))
                if 'reprompt' in scen_parser_response and scen_parser_response['reprompt'] is not None:
                    alexa_response = alexa_response.reprompt(render_template_string(scen_parser_response['reprompt'],
                                                                             **reprompt_render_args))
            else:
                alexa_response = statement(render_template_string(response['speech'], **response_render_args))
            # add card to response
            if 'card' in response and response['card'] is not None:
                response_card = response['card']
                if response_card['type'] == 'standard':
                    # make standard card
                    alexa_response = alexa_response.standard_card(**response_card['info'])
                else:
                    # simple card
                    alexa_response = alexa_response.simple_card(**response_card['info'])
            return alexa_response
        else:
            self.app.logger.error("unknown response from scenario parser: {}".format(scen_parser_response['type']))

    def process_event(self, action_args, response_render_args, reprompt_render_args):
        # TODO: remove debug
        self.app.logger.debug("current session attributes (before processing): {}".format(session.attributes))

        scen_parser_response = self.scenario.follow_scenario(args_ctx=action_args, session_ctx=session.attributes)
        return self._parse_scenario_response(scen_parser_response, response_render_args=response_render_args,
                                             reprompt_render_args=reprompt_render_args)

    def init_scenario(self, session_ctx):
        self.scenario._init_scenario(session_ctx)


# FIXME: got a problem with wrong input data. User defined actions cannot return errors by now,
# FIXME: dunno how to change responses depending on it.
# FIXME: Another problem is direct access to vars, especially in session context. Incapsulate somehow?

# FIXME: problem: current implementation use one state machine for all sessions, kindda shitty ;(
