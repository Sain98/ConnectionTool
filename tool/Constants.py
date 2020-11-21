# Logger settings
LOGGER_FORMAT = '%(asctime)s - %(levelname)s - %(name)s\n\t%(message)s'
LOGGER_DATE_FORMAT = '%H:%M:%S'     # '%d/%m/%Y - %H:%M:%S'
DEBUG_MODE = True                   # Debug if True, else Info mode
DEBUG_OUT = False                   # True -> output logs to file, False -> Console
DEBUG_FILE = "../logs.txt"  # log output filename

# Connection Checker settings
MAX_TIMEOUT = 10

# Config settings
CONFIG_FILENAME = "\\config\\config.ini"  # Filename for the config
SERVER_FILE = "\\config\\servers.pickle"  # Filename containing all saved servers

# Default values
DEFAULT_INTERVAL = 30               # Default interval between checks
DELETE_WARNING = 5                  # Have the user confirm,
                                    # if he wants to delete more than x servers

# Window settings
WINDOW_TITLE = "Sain's connection checker"

# Icons
WINDOW_ICON = "\\icons\\window.png"
EXIT_ICON = "\\icons\\exit.png"
BELL_ICON = "\\icons\\bell.png"
