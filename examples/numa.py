from utils import enter_depend_test, STEPS, RESULT, SETUP
enter_depend_test()

from depend_test_framework.core import Action, ParamsRequire, Provider, Consumer, CheckPoint, TestObject, Mist, MistDeadEndException, MistClearException


@Action.decorator(1)
@ParamsRequire.decorator(['guest_name', 'numa'])
@Consumer.decorator('$guest_name.config', Consumer.REQUIRE)
@Provider.decorator('$guest_name.config.numa', Provider.SET)
def set_guest_numa(params, env):
    """
    """
    pass
