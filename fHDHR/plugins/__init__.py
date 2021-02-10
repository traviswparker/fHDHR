import os
import json

from .plugin import Plugin


class PluginsHandler():

    def __init__(self, settings, logger, db, versions):
        self.config = settings
        self.logger = logger
        self.db = db
        self.versions = versions

        self.plugins = {}

        self.found_plugins = []
        self.list_plugins(self.config.internal["paths"]["internal_plugins_dir"])
        if self.config.internal["paths"]["external_plugins_dir"]:
            self.list_plugins(self.config.internal["paths"]["external_plugins_dir"])
        self.load_plugins()
        versions.register_plugins(self)
        self.setup()

    def setup(self):
        for plugin_name in list(self.plugins.keys()):
            self.plugins[plugin_name].setup()

    def list_plugins(self, plugins_dir):

        base = os.path.abspath(plugins_dir)
        for filename in os.listdir(base):
            abspath = os.path.join(base, filename)

            if os.path.isdir(abspath):

                plugin_conf = []
                for subfilename in os.listdir(abspath):
                    subabspath = os.path.join(abspath, subfilename)
                    if subfilename.endswith("_conf.json"):
                        plugin_conf.append(subabspath)

                # Plugin/multi-plugin must have a basic manifest json
                conffilepath = os.path.join(abspath, 'plugin.json')
                if os.path.isfile(conffilepath):
                    plugin_manifest = json.load(open(conffilepath, 'r'))

                    for plugin_man_item in ["name", "version", "type"]:
                        if plugin_man_item not in list(plugin_manifest.keys()):
                            plugin_manifest[plugin_man_item] = None

                    plugin_import_print_string = "Found %s type plugin: %s %s. " % (plugin_manifest["type"], plugin_manifest["name"], plugin_manifest["version"])

                    if not any(plugin_manifest[plugin_item] for plugin_item in ["name", "version", "type"]):
                        plugin_import_print_string += " ImportWarning: Missing PLUGIN_* Value."
                    else:

                        # Single Plugin
                        if os.path.isfile(os.path.join(abspath, '__init__.py')):
                            plugin_manifest["tagged_mod"] = None
                            plugin_manifest["tagged_mod_type"] = None
                            self.found_plugins.append((os.path.basename(filename), abspath, plugin_conf, plugin_manifest))

                        else:

                            # Multi-Plugin
                            for subfilename in os.listdir(abspath):
                                subabspath = os.path.join(abspath, subfilename)

                                if os.path.isdir(subabspath):

                                    subconffilepath = os.path.join(subabspath, 'plugin.json')
                                    if os.path.isfile(subconffilepath):
                                        subplugin_manifest = json.load(open(subconffilepath, 'r'))

                                        for subplugin_man_item in ["name", "version", "type"]:
                                            if subplugin_man_item not in list(subplugin_manifest.keys()):
                                                subplugin_manifest[subplugin_man_item] = plugin_manifest[subplugin_man_item]
                                    else:
                                        subplugin_manifest = plugin_manifest

                                    subplugin_manifest["tagged_mod"] = None
                                    subplugin_manifest["tagged_mod_type"] = None
                                    if plugin_manifest["type"] != subplugin_manifest["type"]:
                                        subplugin_manifest["tagged_mod"] = plugin_manifest["name"]
                                        subplugin_manifest["tagged_mod_type"] = plugin_manifest["type"]

                                    if os.path.isfile(os.path.join(subabspath, '__init__.py')):
                                        self.found_plugins.append((os.path.basename(filename), subabspath, plugin_conf, subplugin_manifest))

                    self.logger.info(plugin_import_print_string)

    def load_plugins(self):
        for plugin_name, plugin_path, plugin_conf, plugin_manifest in self.found_plugins:
            plugin_item = Plugin(self.config, self.logger, self.db, self.versions, plugin_name, plugin_path, plugin_conf, plugin_manifest)
            self.plugins[plugin_item.plugin_dict_name] = plugin_item
