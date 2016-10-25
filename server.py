import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session, convert_errors
import scenario_parser as sp


app = Flask("stupid Alexa bot")
ask = Ask(app, '/')


def parse_scenario_response(scen_parser_response: dict, response_render_args: dict, reprompt_render_args: dict):
    if scen_parser_response['type'] == 'error':
        app.logger.error(scen_parser_response['reason'])
    elif scen_parser_response['type'] == 'bad_trigger':
        return question(render_template(scen_parser_response['reprompt'], **reprompt_render_args))
    elif scen_parser_response['type'] == 'ok':
        # successful response
        response = scen_parser_response['response']
        if response['type'] == 'question':
            alexa_response = question(render_template(response['speech'], **response_render_args))
            if 'reprompt' in scen_parser_response and scen_parser_response['reprompt'] is not None:
                alexa_response = alexa_response.reprompt(render_template(scen_parser_response['repromt'],
                                                                         **reprompt_render_args))
        else:
            alexa_response = statement(render_template(response['speech'], **response_render_args))
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
        app.logger.error("unknown response from scenario parser: {}".format(scen_parser_response['type']))


def process_event(action_args, response_render_args, reprompt_render_args):
    scen_parser_response = scen.follow_scenario(args_ctx=action_args, session_ctx=session.attributes)
    return parse_scenario_response(scen_parser_response, response_render_args=response_render_args,
                                   reprompt_render_args=reprompt_render_args)


@ask.on_session_started
def new_session():
    scen.init_scenario(session_ctx=session.attributes)
    app.logger.info('new session started')


@ask.launch
def launched():
    action_args = {}
    response_render_args = {}
    reprompt_render_args = {}
    return process_event(action_args, response_render_args, reprompt_render_args)


@ask.intent('AMAZON.YesIntent')
def start_coffee():
    return question(render_template('choose_coffemaker'))


@ask.intent('AMAZON.NoIntent')
def stop_coffee():
    return stop_the_party()


@ask.intent('ChooseCoffemakerIntent', convert={'cfm_num': int})
def choose_coffemaker(cfm_num):
    if 'cfm_num' in convert_errors or cfm_num is None:
        return question(render_template('incorrect_number'))
    if cfm_num > 3:
        return question(render_template('exceeding_number'))

    app.logger.debug("user choose coffeemaker #{}".format(cfm_num))

    session.attributes['coffemaker_number'] = cfm_num
    return question(render_template('user_pin'))


@ask.intent('MakeCoffeeIntent', convert={'pin': int})
def make_coffee(pin):
    if pin in convert_errors or not (0 < pin < 9999):
        return question("can you repeat your code, please?")

    app.logger.info("user enter PIN-code: {}".format(pin))

    # TODO: verify pin
    # TODO: some real action here

    cfm_num = session.attributes['coffemaker_number']
    app.logger.debug("ok, now coffee maker number {} is activated...".format(cfm_num))
    return statement(render_template('ready', number=cfm_num))


@ask.intent('AMAZON.HelpIntent')
def helper():
    app.logger.debug("user requests for help")
    return statement(render_template('help'))


@ask.intent('AMAZON.StopIntent')
def stop_the_party():
    app.logger.debug("the party is stopped")
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
    scen = sp.Scenario(scenario_file)

    # logging
    log_handler = RotatingFileHandler('alexa_backend.log', maxBytes=10000, backupCount=4)
    formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(formatter)
    app.logger.addHandler(log_handler)
    app.run(host='127.0.0.1', port=1234, debug=True)

