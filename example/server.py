from flask import Flask, render_template
from flask_ask import Ask, statement, question, session, convert_errors
from afg import Supervisor


app = Flask("Alexa bot")
ask = Ask(app, '/')
sup = Supervisor("scenario.yaml")


@ask.on_session_started
@sup.start
def new_session():
    app.logger.debug('new user session started')


@sup.stop
def close_user_session():
    app.logger.debug("user session stopped")


@ask.session_ended
def session_ended():
    close_user_session()
    return "", 200


@ask.intent('AMAZON.HelpIntent')
def help_user():
    context_help = sup.get_help()
    # context_help string could be extended with some dynamic information
    return question(context_help)


@ask.launch
@sup.guide
def launched():
    return question(render_template('welcome'))


@ask.intent('ChooseTeaIntent')
@sup.guide
def choose_tea():
    session.attributes['drink'] = 'tea'
    return question(render_template('drink_amount'))


@ask.intent('ChooseCoffeeIntent')
@sup.guide
def choose_coffee():
    session.attributes['drink'] = 'coffee'
    return question(render_template('coffee_strength'))


@ask.intent('CoffeeStrengthIntent')
@sup.guide
def choose_coffee_strength(strength):
    # validate parameter
    if strength not in ['weak', 'strong']:
        return sup.reprompt_error()
    session.attributes['coffee_strength'] = strength
    return question(render_template('drink_amount'))


@ask.intent('DrinkAmountIntent')
@sup.guide
def choose_drink_amount(amount):
    if amount not in ['small', 'big']:
        return sup.reprompt_error("I'm not sure, make it big or small?")

    # make a drink
    drink = session.attributes['drink']
    if drink == 'tea':
        make_tea(amount)
    elif drink == 'coffee':
        coffee_strength = session.attributes['coffee_strength']
        make_coffee(amount, strength=coffee_strength)
    else:
        # unknown drink -> move to drink choice
        sup.move_to_step('drink_choice')
        return question(render_template('welcome'))

    close_user_session()
    return statement(render_template('drink_ready', drink=drink, amount=amount))


# stub
def make_tea(amount):
    pass


def make_coffee(amount, strength):
    pass


@ask.intent('AMAZON.CancelIntent')
def cancel():
    close_user_session()
    return statement(render_template('cancel'))


@ask.intent('AMAZON.StopIntent')
def stop():
    close_user_session()
    return statement(render_template('stop'))


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=1234, debug=True)
