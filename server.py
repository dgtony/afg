import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_ask import Ask, statement, question, session, convert_errors
import scenarios


app = Flask("stupid Alexa bot")
ask = Ask(app, '/')


@ask.on_session_started
def new_session():
    app.logger.info('new session started')
    sp.init_scenario(session_ctx=session.attributes)


@ask.launch
def launched():
    app.logger.info('launched invoked')
    return sp.process_event(action_args={}, response_render_args={}, reprompt_render_args={})


@ask.intent('AMAZON.YesIntent')
def start_coffee():
    return sp.process_event(action_args={}, response_render_args={}, reprompt_render_args={})


@ask.intent('AMAZON.NoIntent')
def stop_coffee():
    return statement("ok, see you later")


@ask.intent('ChooseCoffeemakerIntent', convert={'cfm_num': int})
def choose_coffemaker(cfm_num):

    # TODO: methods to choose scenario next steps and explicit reprompt?

    return sp.process_event(action_args={'cfm_num': cfm_num}, response_render_args={}, reprompt_render_args={})


@ask.intent('MakeCoffeeIntent', convert={'pin': int})
def make_coffee(pin):
    if pin in convert_errors or not (0 < pin < 9999):
        return question("repeat fucking code")

    app.logger.info("user enter PIN-code: {}".format(pin))

    # TODO: verify pin
    # TODO: some real action here

    cfm_num = session.attributes['cfm_num']
    app.logger.debug("ok, now coffee maker number {} is activated...".format(cfm_num))
    return sp.process_event(action_args={}, response_render_args={'cfm_num': cfm_num}, reprompt_render_args={})


@ask.intent('AMAZON.HelpIntent')
def helper():
    app.logger.debug("user requests for help")
    return statement("read the fuckin manuals!")


@ask.intent('AMAZON.StopIntent')
def stop_the_party():
    return statement("stopping")


@ask.intent('AMAZON.CancelIntent')
def cancel_intent():
    return stop_the_party()


@ask.session_ended
def session_ended():
    return "", 200


if __name__ == "__main__":
    # load scenarios
    scenario_file = "./scenarios.yaml"
    sp = scenarios.ScenarioProcessor(scenario_filename=scenario_file, server_app=app)

    # logging
    log_handler = RotatingFileHandler('alexa_backend.log', maxBytes=10000, backupCount=4)
    formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(formatter)
    app.logger.addHandler(log_handler)
    app.run(host='127.0.0.1', port=1234, debug=True)

