import yaml


class UndefinedStep(ValueError):
    pass


class Scenario(object):

    def __init__(self, filename):
        with open(filename, 'r') as fd:
            self.scenario = yaml.load(fd)

    def get_step_info(self, step_num):
        if step_num not in self.scenario:
            raise UndefinedStep
        return self.scenario[step_num]

    def verify(self, session_step, step_in_scenario):
        if session_step != step_in_scenario:
            return self.get_step_info(session_step)
