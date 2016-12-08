from flask import Flask, render_template
from flask_ask import Ask, statement, question, session, convert_errors
from afg import Supervisor


app = Flask("Alexa bot")
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
    return question(render_template('how_many'))


@ask.intent('AMAZON.NoIntent')
@sup.guide
def no_more_coffee():
    return statement(render_template('stop'))


@ask.intent('NumCupsIntent', convert={'cups_num': int})
@sup.guide
def make_coffee(cups_num):
    # validation
    if cups_num in convert_errors:
        return sup.reprompt_error
    if cups_num > 3:
        app.logger.error("too much coffee: {}".format(cups_num))
        return sup.reprompt_error

    return statement(render_template('ready'))


@ask.intent('AMAZON.HelpIntent')
def help_user():
    context_help = sup.get_help()
    return question(context_help)


@ask.session_ended
@sup.stop
def session_ended():
    app.logger.info('session stopped: {}'.format(session.sessionId))
    return "", 200


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=1234, debug=True)
