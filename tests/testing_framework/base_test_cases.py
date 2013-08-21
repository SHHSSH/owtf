import unittest
import sys
import re
from io import BytesIO as StringIO
from os import path
from tests.testing_framework.server import HandlerBuilder, WebServerProcess
import shlex
from owtf import ProcessOptions
from framework.core import Core
import os
from tests.testing_framework.utils import ExpensiveResourceProxy
from tests.testing_framework.doubles.mock import StreamMock
import shutil


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        try:
            self.before()
        except AttributeError:
            pass  # The subclass does not implement the set up method

    def tearDown(self):
        try:
            self.after()
        except AttributeError:
            pass  # The subclass does not implement the tear down method

    def init_stdout_recording(self):
        self.stdout_backup = sys.stdout
        self.replace_stdout_with_string_buffer()

    def get_recorded_stdout(self, flush_buffer=False):
        output = self.stdout_content.getvalue()
        if (flush_buffer):
            self.stdout_content.close()
            self.replace_stdout_with_string_buffer()
        return output

    def replace_stdout_with_string_buffer(self):
        self.stdout_content = StringIO()
        sys.stdout = self.stdout_content

    def stop_stdout_recording(self):
        self.stdout_content.close()
        sys.stdout = self.stdout_backup

    def get_recorded_stdout_and_close(self):
        output = self.get_recorded_stdout()
        self.stop_stdout_recording()
        return output

    def get_abs_path(self, relative_path):
        return path.abspath(relative_path)


class CoreInitialiser():

    def __init__(self, target):
        self.target = target

    def __call__(self):
        root_dir = path.abspath("..")  # Relative to tests/ directory
        options = "-g web -i no " + self.target  # Example options to initialise the framework
        self.core_instance = Core(root_dir)
        processed_options = self.process_options(options)
        self.core_instance.initialise_framework(processed_options)
        return self.core_instance

    def process_options(self, options):
        args = shlex.split(options)
        return ProcessOptions(self.core_instance, args)


class WebPluginTestCase(BaseTestCase):

    TARGET = "localhost:8888"
    DYNAMIC_METHOD_REGEX = "^set_(head|get|post|put|delete|options|connect)_response"

    core_instance_proxy = None

    @classmethod
    def setUpClass(cls):
        cls.clean_temp_files()
        cls.core_instance_proxy = ExpensiveResourceProxy(CoreInitialiser("http://" + cls.TARGET))
        super(WebPluginTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            if hasattr(cls, "core_instance_proxy") and getattr(cls, "core_instance_proxy") is not None:
                cls.core_instance_proxy.get_instance().Finish(Report=False)
        except SystemExit:
            pass  # Exit is invoked from the core)
        finally:
            cls.clean_temp_files()
            super(WebPluginTestCase, cls).tearDownClass()

    @classmethod
    def clean_temp_files(cls):
        if os.path.isdir("owtf_review"):
            shutil.rmtree("owtf_review")
        if os.path.isfile("logfile"):
            os.remove("logfile")

    def setUp(self):
        """Initialise the WebPluginTestCase instance variables."""
        self.responses = {}
        self.server = None
        self.owtf_output = ""
        self.custom_handlers = []
        self.core_instance = self.core_instance_proxy.get_instance()
        super(WebPluginTestCase, self).setUp()

    def tearDown(self):
        if self.server is not None:
            self.stop_server()
        super(WebPluginTestCase, self).tearDown()

    def set_response(self, path, content="", headers={}, method="get", status_code=200):
        if not (path in self.responses):
            self.responses[path] = {}
        self.responses[path][method] = {"content": content,
                                        "headers": headers,
                                        "code": status_code}

    def set_response_from_file(self, path, file_path, headers={}, method="get", status_code=200):
        response_file = open(file_path, "r")
        self.set_response(path, response_file.read(), headers, method, status_code)
        response_file.close()

    def set_custom_handler(self, path, handler_class, init_params={}):
        self.custom_handlers.append((path, handler_class, init_params),)

    def start_server(self):
        """Creates a server process with the provided handlers and starts it"""
        autogenerated_handlers = self.build_handlers()
        handlers = autogenerated_handlers + self.custom_handlers
        self.server = WebServerProcess(handlers)
        self.server.start()

    def build_handlers(self):
        """
            For each recorded response, generates a (path, handler) tuple which
            will be passed to the Tornado web server.
        """
        handlers = []
        handler_builder = HandlerBuilder()
        for path, params in self.responses.items():
            handlers.append((path, handler_builder.get_handler(params)))
        return handlers

    def stop_server(self):
        self.server.stop()

    def __getattr__(self, name):
        """
            If the method name matches with set_post_response, set_put_response,
            set_post_response_from_file, etc. generates a dynamic method.
        """
        dynamic_method_matcher = re.match(self.DYNAMIC_METHOD_REGEX, name)
        if dynamic_method_matcher is not None:
            method_name = dynamic_method_matcher.group(1)
            return self.generate_callable_for_set_response(method_name, name.endswith("_from_file"))
        else:
            raise AttributeError("'WebPluginTestCase' object has no attribute '" + name + "'")

    def generate_callable_for_set_response(self, method_name, from_file):
        """Returns a function that will be called to set a response."""
        def dynamic_method(path, content="", headers={}, status_code=200):
                if from_file:
                    self.set_response_from_file(path, content, headers, method_name, status_code)
                else:
                    self.set_response(path, content, headers, method_name, status_code)
        return dynamic_method

    def owtf(self, args_string=""):
        """Runs OWTF against the server."""
        processed_options = self.process_options(args_string + " -i no " + self.TARGET)
        plugin_dir, plugin = self.get_dir_and_plugin_from_options(processed_options)
        result = self.run_plugin(plugin_dir, plugin)
        self.owtf_output = "\n".join(result[:])

    def process_options(self, options):
        args = shlex.split(options)
        return ProcessOptions(self.core_instance, args)

    def get_dir_and_plugin_from_options(self, options):
        criteria = {"Group": options["PluginGroup"],
                    "Type": options["PluginType"],
                    "Name": options["OnlyPlugins"][0]}
        directory = os.path.abspath("../plugins/" + criteria["Group"])
        return directory, self.core_instance.Config.Plugin.GetPlugins(criteria)[0]

    def run_plugin(self, plugin_dir, plugin):
        result = []
        self.init_stdout_recording()
        try:
            result.append(str(self.core_instance.PluginHandler.ProcessPlugin(plugin_dir, plugin, {})))
        except:
            result.append(str(sys.exc_info()[0]))
        finally:
            stdout_output = self.get_recorded_stdout_and_close()
            result.append(str(stdout_output))
        return result

