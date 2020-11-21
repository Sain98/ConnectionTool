import configparser
from os.path import isfile
from os import getcwd


class ConfigHandler:
    """
    Handles anything config related;
    Reading, writing, updating the config file.
    and returning any requested values or sections

    Config layout:
    DEFAULT - Section - contains most of the general stuff
        such as the interval timer and whether to notify on status change
    WINDOW - Section - All the window related settings are  here
        such as width, height and location
    """

    def __init__(self, filename, logger):

        # config parser
        self.config = configparser.ConfigParser()

        # local variables
        self.logger = logger
        self.filename = getcwd() + filename

        # init, check if config file exists
        if isfile(self.filename):
            # File exists, load config
            self.logger.debug("Config file exists, loading values...")
            self.load_config()
        else:
            self.logger.error(f"Config file '{filename}' not found!\n"
                              "Making default config")
            self.make_default_config()

    def make_default_config(self):
        self.config['DEFAULT'] = {
            'interval_checks': '30',
            'notify_status_change': 'True'
        }
        self.config['WINDOW'] = {
            'width': '800',
            'height': '600',
            'location_x': '0',
            'location_y': '0',
            'custom_style': 'False'
        }
        self.write_config()

    # == Reading/Writing config-file ==
    def load_config(self):
        self.config.read(self.filename, encoding='utf-8')

    def write_config(self):
        try:
            self.logger.debug(f"filename: {self.filename} | cwd: {getcwd()}")
            with open(self.filename, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            self.logger.error("Exception caught writing config", exc_info=e)

    # == Updating values/sections ==
    def update_value(self, section, value_name, new_value):
        """
        Updates the value in the configparser, then writes it to the config file
        :param section: str - Section/Key for the config dict
        :param value_name: str - The key for the value inside the section
        :param new_value: str - New value, gets formatted to string for output

        Dictionary build example
        config = { "SECTION": { "VALUE_NAME": "VALUE", ... }, ... }
        """
        if not isinstance(new_value, str):
            new_value = str(new_value)
        self.config[section][value_name] = new_value
        self.write_config()

    def update_section(self, section, new_values):
        if not isinstance(new_values, dict):
            self.logger.warning("Wrong value type for update_section\n"
                                f"Expected {type(dict)} | Got: {type(new_values)}")
            raise TypeError
        else:
            self.config[section] = new_values
            self.write_config()

    # == getting values/sections ==
    def get_value(self, value_name, section="DEFAULT", return_type=None):
        """
        Simple gets the value from the configparser and returns it,
        default type for returning is a string, unless requested otherwise
        :param value_name:
        :param section:
        :param return_type:
        :return: string, unless return_type is given
        """
        if return_type is int:
            try:
                value = int(self.config[section][value_name])
                return value
            except ValueError:
                self.logger.error("Unable to return requested type in get_value\n"
                                  f"Requested type was '{return_type}' "
                                  f"for value: {self.config[section][value_name]}")
        else:
            if return_type is not None:
                self.logger.warning("Returning value as default, requested type not available")

            return self.config[section][value_name]

    def get_section(self, section):
        return self.config[section]

    def get_sections(self):
        return self.config.sections()
