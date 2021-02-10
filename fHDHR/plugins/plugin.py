import os
import imp

from .plugin_utils import Plugin_Utils


class Plugin():

    def __init__(self, config, logger, db, plugin_name, plugin_path, plugin_conf, plugin_manifest):
        self.config = config
        self.db = db
        self.logger = logger

        # Gather Info about Plugin
        self.plugin_name = plugin_name
        self.modname = os.path.basename(plugin_path)
        self.path = plugin_path
        self.module_type = imp.PKG_DIRECTORY
        self.multi_plugin = (self.plugin_name != self.modname)
        self.default_conf = plugin_conf
        self.manifest = plugin_manifest

        if self.multi_plugin:
            self.plugin_dict_name = "%s_%s" % (plugin_name, self.modname)
        else:
            self.plugin_dict_name = plugin_name

        self.plugin_utils = Plugin_Utils(config, logger, db, plugin_name, plugin_manifest, self.modname, self.path)

        # Load the module
        self._module = self._load()

    def setup(self):
        if self.type == "web":
            self.config.register_web_path(self.manifest["name"], self.path, self.plugin_dict_name)

        if self.has_setup():
            self._module.setup(self)

    def has_setup(self):
        return hasattr(self._module, 'setup')

    def _load(self):
        description = ('', '', self.module_type)
        mod = imp.load_module(self.plugin_dict_name, None, self.path, description)
        return mod

    @property
    def name(self):
        return self.manifest["name"]

    @property
    def version(self):
        return self.manifest["version"]

    @property
    def type(self):
        return self.manifest["type"]

    def __getattr__(self, name):
        ''' will only get called for undefined attributes '''
        if name == "Plugin_OBJ":
            return self._module.Plugin_OBJ