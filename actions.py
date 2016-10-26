# describe here all actions and define names


# action definitions
def save_coffemaker_number(args_ctx, session_ctx):
    # verify args here
    cfm_num = args_ctx['cfm_num']
    if cfm_num is not None:
        print("ok, I'll save coffeemaker #{} in session context".format(args_ctx['cfm_num']))
        session_ctx['cfm_number'] = args_ctx['cfm_num']
    else:
        print("holly shit, what is coffeemaker: {}".format(cfm_num))


def make_coffee_request(args_ctx, session_ctx):
    print("Make coffee in machine #{}".format(session_ctx['cfm_num']))


def stop_action(args_ctx, session_ctx):
    print("Stop session on step {}".format(session_ctx['step']))


# global action to function mapper:
# action_name => (function, list_of_required_arguments, list_of_required_session_context_args)
action_map = {
    'save_coffeemaker_number': (save_coffemaker_number, ['cfm_num'], []),
    'make_coffee': (make_coffee_request, [], ['cfm_num']),
    'stop_the_party': (stop_action, [], ['step'])
}


########################
#   Internal functions
# ---------------------
# !!! DO NOT CHANGE !!!
########################


class MissingArg(KeyError):
    pass


class UndefinedAction(KeyError):
    pass


def verify_args(action_name: str, args_ctx: dict, session_ctx: dict):
    # verify action
    if action_name not in action_map.keys():
        raise UndefinedAction(action_name)
    # verify arguments
    for arg in action_map[action_name][1]:
        if arg not in args_ctx.keys():
            raise MissingArg("keyword argument: {}".format(arg))
    # verify session context
    for arg in action_map[action_name][2]:
        if arg not in session_ctx.keys():
            raise MissingArg("session context argument: {}".format(arg))


def make_action(action_name, args_ctx, session_ctx):
    """
    Verify arguments and apply it to the given function
    """
    verify_args(action_name, args_ctx, session_ctx)
    required_args = {arg_name: args_ctx[arg_name] for arg_name in action_map[action_name][1]}
    return action_map[action_name][0](required_args, session_ctx)


# FIXME: logging instead of printing in actions
