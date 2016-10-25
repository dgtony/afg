import actions
import inspect
import yaml


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


def _get_caller_name(nesting_level=3):
    """
    Use reflection to obtain trigger name
    """
    return inspect.stack()[nesting_level].function


def action2fun(action_name):
    return actions.action_map[action_name]


def error_catcher(fun):
    def wrapper(*args):
        try:
            response = fun(*args)
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


class Scenario(object):

    def __init__(self, filename):
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

    def init_scenario(self, session_ctx):
        session_ctx['step'] = self.first_step
