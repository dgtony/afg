import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session, convert_errors
from afg import Supervisor


app = Flask("stupid Alexa bot")
ask = Ask(app, '/')
sup = Supervisor("scenario.yaml")


@ask.on_session_started
@sup.start
def new_session():
    app.logger.info('new session started')


@ask.launch
@sup.guide
def launched():
    return question(render_template('welcome'))


@ask.intent('AMAZON.YesIntent')
@sup.guide
def start_coffee():
    return question(render_template('choose_coffemaker'))


@ask.intent('AMAZON.NoIntent')
@sup.guide
def stop_coffee():
    return stop_the_party()


@ask.intent('ChooseCoffeemakerIntent', convert={'cfm_num': int})
@sup.guide
def choose_coffemaker(cfm_num):
    # validation
    if cfm_num in convert_errors:
        app.logger.debug("catch input error: choose coffeemaker")
        return sup.reprompt_error

    if cfm_num > 3:
        app.logger.error("O'rly? you've got {} coffemakers?".format(cfm_num))
        return sup.reprompt_error

    session.attributes['coffemaker_number'] = cfm_num
    return question(render_template('user_pin'))


@ask.intent('MakeCoffeeIntent', convert={'pin': int})
@sup.guide
def make_coffee(pin):
    if pin in convert_errors:
        return sup.reprompt_error

    app.logger.info("user enter PIN-code: {}".format(pin))

    # TODO: verify pin
    # TODO: some real action here

    cfm_num = session.attributes['coffemaker_number']
    app.logger.debug("ok, now coffee maker number {} is activated...".format(cfm_num))
    return statement(render_template('ready', number=cfm_num))


# No need to guide some events
@ask.intent('AMAZON.HelpIntent')
def helper():
    app.logger.debug("user requests for help")
    return question(render_template('help'))


@ask.intent('AMAZON.StopIntent')
def stop_intent():
    return stop_the_party()


@ask.intent('AMAZON.CancelIntent')
def cancel_intent():
    return stop_the_party()


def stop_the_party():
    return statement(render_template('stop'))


@ask.session_ended
@sup.stop
def session_ended():
    app.logger.info('session stopped: {}'.format(session.sessionId))
    return "", 200


if __name__ == "__main__":
    # logging
    log_handler = RotatingFileHandler('alexa_backend.log', maxBytes=10000, backupCount=4)
    formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(formatter)
    app.logger.addHandler(log_handler)
    app.run(host='127.0.0.1', port=1234, debug=False)

