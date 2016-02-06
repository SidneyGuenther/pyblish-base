import os

from pyblish.vendor import mock
import pyblish.api
import pyblish.plugin
from pyblish.vendor.nose.tools import (
    with_setup,
    assert_true,
    assert_equals,
    assert_raises,
    raises,
)

from . import lib


def test_unique_id():
    """Plug-ins and instances have a unique id"""

    class MyPlugin(pyblish.plugin.Collector):
        pass

    assert_true(hasattr(MyPlugin, "id"))

    instance = pyblish.plugin.Instance("MyInstance")
    assert_true(hasattr(instance, "id"))


def test_context_from_instance():
    """Instances provide access to their parent context"""

    context = pyblish.plugin.Context()
    instance = context.create_instance("MyInstance")
    assert_equals(context, instance.context)


def test_legacy():
    """Legacy is determined by existing process_* methods"""
    class LegacyPlugin(pyblish.plugin.Collector):
        def process_context(self, context):
            pass

    class NotLegacyPlugin(pyblish.plugin.Collector):
        def process(self, context):
            pass

    assert_true(hasattr(LegacyPlugin, "__pre11__"))
    assert_equals(LegacyPlugin.__pre11__, True)
    assert_true(hasattr(NotLegacyPlugin, "__pre11__"))
    assert_equals(NotLegacyPlugin.__pre11__, False)


def test_asset():
    """Using asset over instance works fine"""
    context = pyblish.plugin.Context()

    asseta = context.create_asset("MyAssetA", family="myFamily")
    assetb = context.create_asset("MyAssetB", family="myFamily")

    assert_true(asseta in context)
    assert_true(assetb in context)


@with_setup(lib.setup_empty, lib.teardown)
def test_import_mechanism_duplication():
    """Plug-ins don't linger after a second discovery

    E.g. when changing the name of a plug-in and then rediscover
    the previous plug-ins is still around.

    """

    with lib.tempdir() as temp:
        print("Writing temporarily to: %s" % temp)
        module = os.path.join(temp, "selector.py")
        pyblish.api.register_plugin_path(temp)

        with open(module, "w") as f:
            f.write("""
import pyblish.api

class MySelector(pyblish.api.Selector):
    pass
""")

        with open(module) as f:
            print("File contents after first write:")
            print(f.read())

        # MySelector should be accessible by now
        plugins = [p.__name__ for p in pyblish.api.discover()]

        assert "MySelector" in plugins, plugins
        assert "MyOtherSelector" not in plugins, plugins

        # Remove module, and it's .pyc equivalent
        [os.remove(os.path.join(temp, fname))
         for fname in os.listdir(temp)]

        with open(module, "w") as f:
            f.write("""
import pyblish.api

class MyOtherSelector(pyblish.api.Selector):
    pass
""")

        with open(module) as f:
            print("File contents after second write:")
            print(f.read())

        # MySelector should be gone in favour of MyOtherSelector
        plugins = [p.__name__ for p in pyblish.api.discover()]

        assert "MyOtherSelector" in plugins, plugins
        assert "MySelector" not in plugins, plugins


@raises(TypeError)
@with_setup(lib.setup_empty, lib.teardown)
def test_register_unsupported_hosts():
    """Cannot register a unsupported plug-in in an unsupported host"""

    class Unsupported(pyblish.api.Plugin):
        hosts = ["unsupported"]

    pyblish.api.register_plugin(Unsupported)


@raises(TypeError)
@with_setup(lib.setup_empty, lib.teardown)
def test_register_unsupported_version():
    """Cannot register a plug-in of an unsupported version"""

    class Unsupported(pyblish.api.Plugin):
        requires = (999, 999, 999)

    pyblish.api.register_plugin(Unsupported)


@raises(TypeError)
@with_setup(lib.setup_empty, lib.teardown)
def test_register_malformed():
    """Cannot register a malformed plug-in"""

    class Unsupported(pyblish.api.Plugin):
        families = True
        hosts = None

    pyblish.api.register_plugin(Unsupported)


@with_setup(lib.setup_empty, lib.teardown)
def test_temporarily_disabled_plugins():
    """Plug-ins as files starting with an underscore are hidden"""

    discoverable = """
import pyblish.api

class Discoverable(pyblish.api.Plugin):
    pass
"""

    notdiscoverable = """
import pyblish.api

class NotDiscoverable(pyblish.api.Plugin):
    pass
"""

    with lib.tempdir() as d:
        pyblish.api.register_plugin_path(d)

        with open(os.path.join(d, "discoverable.py"), "w") as f:
            f.write(discoverable)

        with open(os.path.join(d, "_undiscoverable.py"), "w") as f:
            f.write(notdiscoverable)

        plugins = [p.__name__ for p in pyblish.api.discover()]
        assert "Discoverable" in plugins
        assert "NotDiscoverable" not in plugins


@with_setup(lib.setup_empty, lib.teardown)
def test_repair_context_backwardscompat():
    """Plug-ins with repair-context are reprogrammed appropriately"""

    class ValidateInstances(pyblish.api.Validator):
        def repair_context(self, context):
            pass

    assert hasattr(ValidateInstances, "repair")
    assert not hasattr(ValidateInstances, "repair_context")


@with_setup(lib.setup_empty, lib.teardown)
def test_unique_logger():
    """A unique logger is applied to every plug-in"""

    count = {"#": 0}

    class MyPlugin(pyblish.api.Plugin):
        def process(self, context):
            self.log.debug("Hello world")
            count["#"] += 1

    pyblish.api.register_plugin(MyPlugin)

    context = pyblish.util.publish()

    assert_equals(count["#"], 1)
    print context.data("results")

    results = context.data("results")[0]
    records = results["records"]
    hello_world = records[0]
    assert_equals(hello_world.msg, "Hello world")

    pyblish.api.deregister_plugin(MyPlugin)


@with_setup(lib.setup_empty, lib.teardown)
def test_current_host():
    """pyblish.api.current_host works"""
    pyblish.plugin.register_host("myhost")
    assert_equals(pyblish.plugin.current_host(), "myhost")

    assert_raises(Exception, pyblish.plugin.deregister_host, "notExist")


@with_setup(lib.setup_empty, lib.teardown)
def test_register_host():
    """Registering and deregistering hosts works fine"""
    pyblish.plugin.register_host("myhost")
    assert "myhost" in pyblish.plugin.registered_hosts()
    pyblish.plugin.deregister_host("myhost")
    assert "myhost" not in pyblish.plugin.registered_hosts()


@with_setup(lib.setup_empty, lib.teardown)
def test_data_dict():
    """.data is a pure dictionary"""

    context = pyblish.api.Context()
    instance = context.create_instance("MyInstance")
    assert isinstance(context.data, dict)
    assert isinstance(instance.data, dict)

    context.data["key"] = "value"
    assert context.data["key"] == "value"

    instance.data["key"] = "value"
    assert instance.data["key"] == "value"

    # Backwards compatibility
    assert context.data("key") == "value"
    assert instance.data("key") == "value"
    assert instance.data("name") == "MyInstance"
    # This returns (a copy of) the full dictionary
    assert context.data() == context.data


@with_setup(lib.setup_empty, lib.teardown)
def test_action():
    """Running an action is like running a plugin"""
    count = {"#": 0}

    class MyAction(pyblish.plugin.Action):
        def process(self, context):
            count["#"] += 1

    class MyPlugin(pyblish.plugin.Plugin):
        actions = [MyAction]

        def process(self, context):
            pass

    context = pyblish.api.Context()
    pyblish.plugin.process(
        plugin=MyPlugin,
        context=context,
        action="MyAction")

    assert count["#"] == 1


@with_setup(lib.setup_empty, lib.teardown)
def test_actions():
    class MyAction(pyblish.plugin.Action):
        def process(self, context):
            context.data["key"] = "value"

    context = pyblish.api.Context()
    pyblish.plugin.process(MyAction, context)
    assert "key" in context.data


@with_setup(lib.setup_empty, lib.teardown)
def test_action_error_checking():
    class MyActionValid(pyblish.plugin.Action):
        on = "all"

    class MyActionInvalid(pyblish.plugin.Action):
        on = "invalid"

    assert MyActionValid.__error__ is None
    assert MyActionInvalid.__error__


@with_setup(lib.setup_empty, lib.teardown)
def test_action_printing():
    class MyAction(pyblish.plugin.Action):
        pass

    print(MyAction())
    print repr(MyAction())

    assert str(MyAction()) == "MyAction"
    assert repr(MyAction()) == "pyblish.plugin.MyAction('MyAction')"


@with_setup(lib.setup_empty, lib.teardown)
def test_category_separator():
    assert issubclass(pyblish.plugin.Category("Test"),
                      pyblish.plugin.Action)
    assert issubclass(pyblish.plugin.Separator,
                      pyblish.plugin.Action)


def test_superclass_process_is_empty():
    """Superclass process() is empty"""
    def e():
        """Doc"""

    assert pyblish.api.Plugin.process.__code__.co_code == e.__code__.co_code
    assert pyblish.api.Plugin.repair.__code__.co_code == e.__code__.co_code


def test_plugin_source_path():
    """Plugins discovered carry a source path"""

    import sys
    plugin = pyblish.plugin.discover()[0]
    module = sys.modules[plugin.__module__]
    assert hasattr(module, "__file__")

    # Also works with inspect.getfile
    import inspect
    assert inspect.getfile(plugin) == module.__file__


@with_setup(lib.setup_empty, lib.teardown)
def test_register_callback():
    """Callback registration/deregistration works well"""

    def my_callback():
        pass

    def other_callback(data=None):
        pass

    pyblish.plugin.register_callback("mySignal", my_callback)

    msg = "Registering a callback failed"
    data = {"mySignal": [my_callback]}
    assert "mySignal" in pyblish.plugin.registered_callbacks() == data, msg

    pyblish.plugin.deregister_callback("mySignal", my_callback)

    msg = "Deregistering a callback failed"
    data = {"mySignal": []}
    assert pyblish.plugin.registered_callbacks() == data, msg

    pyblish.plugin.register_callback("mySignal", my_callback)
    pyblish.plugin.register_callback("otherSignal", other_callback)
    pyblish.plugin.deregister_all_callbacks()

    msg = "Deregistering all callbacks failed"
    assert pyblish.plugin.registered_callbacks() == {}, msg


@with_setup(lib.setup_empty, lib.teardown)
def test_emit_signal_wrongly():
    """Exception from callback prints traceback"""

    def other_callback(data=None):
        print "Ping from 'other_callback' with %s" % data

    pyblish.plugin.register_callback("otherSignal", other_callback)

    with lib.captured_stderr() as stderr:
        pyblish.lib.emit("otherSignal", akeyword="")
        output = stderr.getvalue().strip()
        assert output.startswith("Traceback")


@raises(ValueError)
@with_setup(lib.setup_empty, lib.teardown)
def test_registering_invalid_callback():
    """Can't register non-callables"""
    pyblish.plugin.register_callback("invalid", None)


@raises(KeyError)
def test_deregistering_nonexisting_callback():
    """Can't deregister a callback that doesn't exist"""
    pyblish.plugin.deregister_callback("invalid", lambda: "")


@raises(TypeError)
def test_register_noncallable_plugin():
    """Registered plug-ins must be callable"""
    pyblish.plugin.register_plugin("NotValid")


@raises(TypeError)
def test_register_old_plugin():
    """Can't register plug-ins incompatible with the version of Pyblish"""
    class MyPlugin(pyblish.plugin.Collector):
        requires = "pyblish==0"

    pyblish.plugin.register_plugin(MyPlugin)


@mock.patch("pyblish.plugin.__explicit_process")
def test_implicit_explicit_branching(func):
    """Explicit plug-ins are processed by the appropriate function"""

    # There are two mocks for this (see below); due to
    # @mock.patch.multiple being a dick.

    class Explicit(pyblish.plugin.ContextPlugin):
        pass

    pyblish.util.publish(plugins=[Explicit])
    assert func.call_count == 1, func.call_count


@mock.patch("pyblish.plugin.__implicit_process")
def test_implicit_branching(func):
    """Implicit plug-ins are processed by the appropriate function"""

    class Implicit(pyblish.plugin.Plugin):
        pass

    pyblish.util.publish(plugins=[Implicit])
    assert func.call_count == 1, func.call_count


def test_explicit_plugin():
    """ContextPlugin works as advertised"""

    count = {"#": 0}

    class Collector(pyblish.plugin.ContextPlugin):
        order = pyblish.plugin.CollectorOrder

        def process(self, context):
            self.log.info("Collecting from ContextPlugin")
            i = context.create_instance("MyInstance")
            i.data["family"] = "myFamily"
            count["#"] += 1

    class Validator(pyblish.plugin.InstancePlugin):
        order = pyblish.plugin.ValidatorOrder
        families = ["myFamily"]

        def process(self, instance):
            assert instance.data["name"] == "MyInstance", "fail"
            count["#"] += 10

    class ValidatorFailure(pyblish.plugin.InstancePlugin):
        order = pyblish.plugin.ValidatorOrder
        families = ["myFamily"]

        def process(self, instance):
            count["#"] += 100
            assert "notexist" in instance.data, "fail"

    class Extractor(pyblish.plugin.InstancePlugin):
        order = pyblish.plugin.ExtractorOrder
        families = ["myFamily"]

        def process(self, instance):
            count["#"] += 1000

    pyblish.util.publish(
        plugins=[
            Collector,
            Validator,
            ValidatorFailure,
            Extractor
        ]
    )

    assert count["#"] == 111, count


def test_context_plugin_wrong_arguments():
    """ContextPlugin doesn't take wrong arguments well"""

    count = {"#": 0}

    class Collector(pyblish.plugin.InstancePlugin):
        def process(self, context, instance):
            print("I won't run")
            count["#"] += 1

    pyblish.util.publish(plugins=[Collector])
    assert count["#"] == 0


def test_explicit_action():
    """Actions work with explicit plug-ins"""

    count = {"#": 0}

    class MyAction(pyblish.plugin.Action):
        def process(self, context):
            count["#"] += 1

    class MyPlugin(pyblish.plugin.ContextPlugin):
        actions = [MyAction]

        def process(self, context):
            pass

    context = pyblish.api.Context()
    pyblish.plugin.process(
        plugin=MyPlugin,
        context=context,
        action="MyAction")


def test_explicit_results():
    """Explicit plug-ins contain results"""

    class Collector(pyblish.plugin.ContextPlugin):
        order = pyblish.plugin.CollectorOrder

        def process(self, context):
            self.log.info("logged")

    context = pyblish.util.publish(plugins=[Collector])
    assert "results" in context.data

    result = context.data["results"][0]
    assert result["records"][0].msg == "logged"
