import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session, convert_errors
import scenario_parser as scn


app = Flask("stupid Alexa bot")
ask = Ask(app, '/')


@ask.on_session_started
def new_session():
    app.logger.info('new session started')
    session.attributes['step'] = 0


@ask.launch
def launched():
    resp = alexa_response(session.attributes, scenario_step=1)
    if resp is not None:
        return resp



    welcome_msg = render_template('welcome')
    return question(welcome_msg)


@ask.intent('AMAZON.YesIntent')
def start_coffee():
    return question(render_template('choose_coffemaker'))


@ask.intent('AMAZON.NoIntent')
def stop_coffee():
    return stop_the_party()


@ask.intent('ChooseCoffemakerIntent', convert={'cfm_num': int})
def choose_coffemaker(cfm_num):
    session.attributes['coffemaker_number'] = cfm_num
    return question(render_template('user_pin'))


#@ask.intent('MakeCoffeeIntent', convert={'pin_first': int, 'pin_second': int, 'pin_third': int, 'pin_fourth': int})
#def make_coffee(pin_first, pin_second, pin_third, pin_fourth):
#    for n in ['pin_first', 'pin_second', 'pin_third', 'pin_fourth']:
#        if n in convert_errors:
#            return question("can you repeat, please?")
#
#    pin_code = 1000 * pin_first + 100 * pin_second + 10 * pin_third + pin_fourth
#    app.logger.info("user enter PIN-code: {}".format(pin_code))
#
#    # TODO: verify pin
#    # TODO: some real action here
#
#    cfm_num = session.attributes['coffemaker_number']
#    app.logger.debug("ok, now coffee maker number {} is activated...".format(cfm_num))
#    return statement(render_template('ready', number=cfm_num))


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


@ask.session_ended
def session_ended():
    return "", 200


# TODO: wipe out that shit
# instead use special error responses - describe in common templates

def alexa_response(session_attributes, scenario_step):
    scen_info = scen.verify(session_attributes['step'], scenario_step)
    if scen_info is not None:
        answer_type, speech, card, attr = scen_info
        # template attributes
        if attr is not None:
            msg = render_template(speech, **attr)
        else:
            msg = render_template(speech)

        # proper type
        if answer_type == 'statement':
            resp = statement(msg)
        elif answer_type == 'question':
            resp = question(msg)
        else:
            return

        # add card
        if card is not None:
            card_type = card.pop('type')
            if card['type'] == 'simple'
                return resp.simple_card()



if __name__ == "__main__":
    # load scenarios
    scenario_file = "./scenarios.yaml"
    scen = scn.Scenario(scenario_file)

    # logging
    log_handler = RotatingFileHandler('alexa_backend.log', maxBytes=10000, backupCount=4)
    formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(formatter)
    app.logger.addHandler(log_handler)
    app.run(host='127.0.0.1', port=1234, debug=True)

