import logging
import pickle

from os import (
    getcwd
)

# PyQt5 imports - All the UI stuff
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QAction,
    QTableView,
    QHeaderView,
    QLineEdit,
    QCheckBox,
    QHBoxLayout,
    QMessageBox,
    QAbstractItemView,
)
from PyQt5.QtGui import (
    QIcon, QStandardItemModel, QStandardItem
)

# Local imports
from tool import (
    ConnectionChecker,
    ConfigHandler,
    NotificationHandler,
    Constants as const
)

# Logging setup
logging.basicConfig(level=logging.DEBUG if const.DEBUG_MODE else logging.INFO,
                    format=const.LOGGER_FORMAT,
                    datefmt=const.LOGGER_DATE_FORMAT,
                    filename=const.DEBUG_FILE if const.DEBUG_OUT else None,
                    filemode="w+" if const.DEBUG_OUT else None)


class ConnectionTool(QMainWindow):
    """
    Main window for the connection tool
    Docs -> docs/tool.ConnectionTool.rst
    Handles all of the UI things
    """
    def __init__(self):
        super().__init__()

        # Logger
        self.logger = logging.getLogger("tool.ConnectionTool")

        # Main working directory (full path of where main.py got executed)
        self.dir = getcwd()

        # Config handler
        self.config = ConfigHandler.ConfigHandler(
            const.CONFIG_FILENAME,
            logging.getLogger("tool.ConfigHandler")
        )

        # Interval between connection checks, int
        _, self.interval = self.convert_to_int(self.config.get_value("interval_checks"))

        # Notify on status changes?, bool
        self.notify = self.convert_to_bool(self.config.get_value("notify_status_change"))

        # Counts ticks, +1 per second. if tick_counter == interval -> connection check
        self.tick_counter = 0

        # The server list, updated through add_server_clicked()
        # Format: name: {url: str, port: int, web: bool}
        self.servers = {}

        # The saved statuses for if the user uses notifications
        self.saved_status = {}

        # Workers and assigned rows for the results
        # {name: {worker: workerObj, row: int}, ...}
        self.workers = {}
        # Keep track of how many workers are currently running a check
        self.active_workers = 0

        # Widget pointers, mainly for widgets that get used often
        # These get set during init_ui() or one of the init_ui() sub functions
        # Status bar, a display of the timer and a display of the active workers
        self.status_bar = None
        self.status_bar_timer = None
        self.status_bar_workers = None
        # The server list given/added by the user (on the "settings" side) | Note: is a QStandardItemModel()
        self.server_list_settings = None
        # The server list on the status side, build by the program | QStandardItemModel
        self.server_list_status = None

        # Start initializing UI
        self.init_ui()
        self.logger.debug("Initialized UI")

        # Load saved serverlist and write to table if any
        self.load_servers()

        # Start timer
        self.timer = self.init_timer()

    """
        = UI INITIALIZATION =
    """
    def init_ui(self):
        """
        Build main window for the ui
        window size, title, icon, status bars, ...
        """
        # Get window settings, resolution and where to initially draw it
        width = self.config.get_value("width", "WINDOW", return_type=int)
        height = self.config.get_value("height", "WINDOW", return_type=int)
        x = self.config.get_value("location_x", "WINDOW", return_type=int)
        y = self.config.get_value("location_y", "WINDOW", return_type=int)

        self.logger.debug(f"{width}, {height}, {x}, {y}")   # debug

        # Set window size, title and icon
        self.setGeometry(x, y, width, height)
        self.setWindowTitle(const.WINDOW_TITLE)
        self.setWindowIcon(QIcon(self.dir + const.WINDOW_ICON))

        # Setup main widget and layout
        main_widget = QWidget()
        main_layout = QGridLayout()
        main_widget.setLayout(main_layout)

        # Using custom stylesheet?
        use_stylesheet = self.config.get_value("custom_style", "WINDOW")
        use_stylesheet = self.convert_to_bool(use_stylesheet)
        if use_stylesheet:
            main_widget.setStyleSheet(open(self.dir + "\\css\\stylesheet.css").read())

        # Initialize menu and status bar
        self.init_ui_bars()

        # Initialize settings area
        self.init_ui_settings(main_layout)

        # Initialize status area
        self.init_ui_status(main_layout)

        # Display main widget and make window visible
        self.setCentralWidget(main_widget)
        self.show()

        self.main_widget = main_widget

    def init_ui_bars(self):
        """
        Build both, the menu bar (top) and status bar (bottom).
        For the main window
        """

        # setting up the menu bar
        menu_bar = self.menuBar()

        # Add new section to menu bar
        tool_menu = menu_bar.addMenu("Tool")

        # Toggle custom style
        style_toggle = QAction("&Toggle Style", self, checkable=True)
        style_toggle.setStatusTip("Toggle custom style")
        style_toggle.triggered.connect(self.toggle_style)

        # Exit action for the tool menu section in the menu bar
        tool_exit = QAction(QIcon(self.dir + const.EXIT_ICON), "Exit", self)
        tool_exit.setShortcut("Ctrl+Q")
        tool_exit.setStatusTip("Exit the application")
        tool_exit.triggered.connect(self.close)

        # Add new action to the given section 'Tool' in the menu bar
        tool_menu.addAction(style_toggle)
        tool_menu.addAction(tool_exit)

        # setting up the status bar
        status_bar = self.statusBar()

        # pointer to the QLabel on self.status_bar_timer.
        # Since the timer function needs this a lot
        # Also a pointer to the worker label
        self.status_bar_workers = QLabel("- No active workers -")
        self.status_bar_timer = QLabel("...")

        status_bar.addPermanentWidget(self.status_bar_workers)
        status_bar.addPermanentWidget(self.status_bar_timer)

        # Startup message
        status_bar.showMessage("Idle...")

        # Make accessible for other functions that need it
        self.status_bar = status_bar

    def init_ui_settings(self, main_layout):
        """
        Build settings (left side) of the UI
        """
        # Settings area, row 0, col 0 in layout
        settings_box = QGroupBox("Settings")
        settings_layout = QVBoxLayout()
        settings_box.setLayout(settings_layout)
        main_layout.addWidget(settings_box, 0, 0)

        # Server list QTable - settings side
        server_list = QTableView()
        server_list_model = QStandardItemModel()
        server_list_model.setHorizontalHeaderLabels([
            "Name/ID", "Server", "Port", "is website?"
        ])
        server_list.setModel(server_list_model)

        # Alternating row colors
        server_list.setAlternatingRowColors(True)

        # Stretch "Name" and "Server" header
        server_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        server_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        # Disable editing (for now?)
        server_list.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Accessible through self.findChild() if needed
        server_list.setObjectName("settings_server_list")

        # More often needed, also causes issues through findChild()
        # So we are adding a pointer to the model in self.server_list_settings
        self.server_list_settings = server_list_model

        # Server list buttons
        # Delete selected, button
        server_list_delete = QPushButton("Delete selected")
        server_list_delete.clicked.connect(self.server_delete_clicked)
        # Force refresh server status now
        server_list_refresh = QPushButton("Check status now")
        server_list_refresh.clicked.connect(self.server_refresh_clicked)

        # Adding widgets to layout
        settings_layout.addWidget(server_list)
        settings_layout.addWidget(server_list_delete)
        settings_layout.addWidget(server_list_refresh)

        # Build the "add server" form
        self.init_ui_settings_add_server(settings_layout)

        self.init_ui_settings_additional(settings_layout)

    def init_ui_settings_add_server(self, settings_layout):
        """
        Builds the form for adding new servers to the server list
        """

        server_form = QGroupBox("Add server")
        server_form_layout = QVBoxLayout()
        server_form.setLayout(server_form_layout)

        # Make all our widgets
        form_url = QLineEdit()
        form_name = QLineEdit()
        form_port = QLineEdit("80")
        form_web = QCheckBox()

        form_add = QPushButton("Add server")
        form_add.clicked.connect(self.add_server_clicked)

        # Name our widgets so we can access them later with self.findChild()
        form_url.setObjectName("server_form_url")
        form_name.setObjectName("server_form_name")
        form_port.setObjectName("server_form_port")
        form_web.setObjectName("server_form_web")

        # Make the 'port' textbox smaller as it does not need much space
        form_port.setMaximumWidth(65)

        # Make a grid layout for our form
        form_grid = QGridLayout()

        # Place all our widgets on the grid layout
        form_grid.addWidget(QLabel("URL/IP:"), 0, 0)
        form_grid.addWidget(form_url, 0, 1)
        form_grid.addWidget(QLabel("Port:"), 0, 2)
        form_grid.addWidget(form_port, 0, 3)
        form_grid.addWidget(QLabel("Name"), 1, 0)
        form_grid.addWidget(form_name, 1, 1)
        form_grid.addWidget(QLabel("Website?: "), 1, 2)
        form_grid.addWidget(form_web, 1, 3)

        # Add our grid layout to the parent layout
        server_form_layout.addLayout(form_grid)

        # Add our button so the user can click to add a new server, outside grid layout
        server_form_layout.addWidget(form_add)

        # Add our new form to the main layout
        settings_layout.addWidget(server_form)

    def init_ui_settings_additional(self, settings_layout):
        # Interval form, so the user can change the time between server checks
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Interval (seconds)")

        interval_text = QLineEdit(str(self.interval))
        interval_text.setObjectName("interval_text")

        interval_button = QPushButton("Update interval")
        interval_button.clicked.connect(self.interval_update_clicked)

        # Add our widgets to the interval layout
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(interval_text)
        interval_layout.addWidget(interval_button)

        # Add interval form to our main layout
        settings_layout.addLayout(interval_layout)

        # Checkbox, notify on server status change? - toggles self.notify
        notify_check = QCheckBox("Notify on status change?")
        notify_check.stateChanged.connect(self.notify_changed)
        settings_layout.addWidget(notify_check)

        save_settings = QPushButton("Save settings")
        save_settings.clicked.connect(self.save_settings_clicked)
        settings_layout.addWidget(save_settings)

    def init_ui_status(self, main_layout):
        """
        Build status (right side) of the UI
        """
        # Server status area, row 0, col 1 in layout
        status_area = QGroupBox("Server status")
        status_layout = QVBoxLayout()
        status_area.setLayout(status_layout)
        main_layout.addWidget(status_area, 0, 1)

        # Server status table
        status = QTableView()
        status_model = QStandardItemModel()
        status_model.setHorizontalHeaderLabels([
            "Status", "Name", "IPv4/6", "URL", "Port"
        ])
        status.setModel(status_model)

        # Enable alternating rows
        status.setAlternatingRowColors(True)

        # Stretch Ip and URL headers to fit any given table size
        status.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        status.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        # Disables user editing of this table
        status.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Set object name for our QTableView
        status.setObjectName("status_server_list")

        # Make our model easily accessible
        self.server_list_status = status_model

        # Add our table to the layout
        status_layout.addWidget(status)

    """
        = Timer =
    """
    def init_timer(self):
        """
        Setup the timer, 1 second == 1 tick
        every tick it calls self.timer_handler
        :return: The "QTimer" object setup here
        """
        timer = QTimer()
        timer.timeout.connect(self.timer_handler)
        timer.start(1000)   # Time per tick, in ms = 1000ms -> 1sec

        return timer

    def timer_handler(self):
        """
        Handles anything that needs to be done on a specific interval such as:
        updating the displayed ticks until next connection check.
        updating the displayed active connections from a connection check - if any.
        incrementing the current tick by +1.
        Starting a connection check once the tick counter reaches its given interval
        :return:
        """
        self.status_bar_timer.setText(f"{self.tick_counter}/{self.interval}")

        if self.active_workers > 0:
            self.status_bar_workers.setText(f"Connections active - {self.active_workers}")
        else:
            self.status_bar_workers.setText("No active connections")

        if self.tick_counter >= self.interval:
            self.logger.debug("197 - Attempting connection check now")

            self.refresh_servers()

            # Connection check done, reset tick counter
            self.tick_counter = 0
        else:
            self.tick_counter += 1

    """
        = Loading/Saving settings & servers
    """

    def load_servers(self):

        # Load server list
        try:
            # Open and read the saved servers into self.servers
            with open(self.dir + const.SERVER_FILE, 'rb') as handle:
                self.servers = pickle.load(handle)

            # Loaded server list, write onto table
            for server in self.servers:
                self.logger.debug("Server loaded:\n\t"
                                  f"- {server} | {self.servers[server]}")

                self.server_list_settings.appendRow([
                    QStandardItem(server),
                    QStandardItem(self.servers[server]['url']),
                    QStandardItem(str(self.servers[server]['port'])),
                    QStandardItem(str(self.servers[server]['web'])),
                ])

        except FileNotFoundError:
            pass

    def save(self):

        # Save server list
        with open(self.dir + "\\config\\servers.pickle", 'wb') as handle:
            pickle.dump(self.servers, handle, protocol=pickle.HIGHEST_PROTOCOL)

        # Save window settings
        width = self.frameGeometry().width()
        height = self.frameGeometry().height()
        x = self.pos().x()
        y = self.pos().y()
        style = self.config.get_value('custom_style', "WINDOW")

        values = {'width': width, 'height': height, 'location_x': x, 'location_y': y, 'custom_style': style}

        self.config.update_section("WINDOW", values)

    """
        = Value type handling =
    """

    def convert_to_int(self, val, hide_error=False):
        """
        Converts string to int, displays error message if string is not a valid number
        :param hide_error: bool -> if true, does not display the error message
        :param val: str
        :return: int
        """
        try:
            val = int(val)
            return True, val
        except ValueError:
            self.logger.debug(f"Value error converting {val}")
            if not hide_error:
                self.error_message(f"Failed to convert value to int '{val}'", "ValueError")
            return False, val

    def convert_to_bool(self, val):
        """
        Returns either True if val == true or False if val == false,
        Hacky way of "converting" string to bool
        :param val: str
        :return: bool
        """
        try:
            if val.lower() == "true":
                return True
            elif val.lower() == "false":
                return False
            else:
                raise ValueError
        except ValueError:
            self.logger.debug(f"Value error converting {val}")
            self.error_message(f"Failed to convert value to int '{val}'", "ValueError")

    """
        = Error messages
    """

    def error_message(self, msg, error_name="Error"):
        """
        Displays a simple error box, containing a message and error name
        :param msg: str
        :param error_name: str -> default = "Error"
        """
        box = QMessageBox()

        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle(error_name)
        box.setWindowIcon(QIcon(self.dir + const.WINDOW_ICON))
        box.setText(msg)

        box.exec_()

    """
        = Connection checking =
    """

    def refresh_servers(self):
        """
        Every check we do, assign a row to each server for where it will
        get saved in the table.
        Then start a worker for each server

        Note: Currently it always makes a new worker and i am unsure if
        The old workers get cleaned up, be aware of possible memleak?
        :return:
        """
        row = 0
        for server in self.servers:
            worker = ConnectionChecker.ConnectionWorker(
                    server,
                    self.servers[server]['url'],
                    self.servers[server]['port'],
                    self.servers[server]['web']
            )

            worker.worker_response.connect(self.server_response)

            worker.start()

            # Keep track of what row is assigned to what worker
            self.workers[server] = {
                'worker': worker,
                'row': row
            }

            row += 1

            self.active_workers += 1

    def server_response(self, response, server_name):
        """
        Worker thread emitted a response, get corresponding row for current worker
        located in self.workers
        :param response: dict
        :param server_name: str
        :return:
        """
        self.logger.debug(f"Got response from {server_name}\n"
                          f"\t- Contents: {response}\n"
                          f"\t- Assigned row: {self.workers[server_name]['row']}")

        row = self.workers[server_name]['row']
        self.server_list_status.setItem(row, 0, QStandardItem(response['status']))
        self.server_list_status.setItem(row, 1, QStandardItem(server_name))
        self.server_list_status.setItem(row, 2, QStandardItem(response['ipv4/6']))
        self.server_list_status.setItem(row, 3, QStandardItem(response['url']))
        self.server_list_status.setItem(row, 4, QStandardItem(str(response['port'])))

        # Not displaying this, unsure if needed, user can see this on the settings side aswell
        # self.server_list_status.setItem(row, 5, QStandardItem(response['is_web']))

        # Check if notifications are enabled
        if self.notify:
            # Try to get previous server status
            old_status = self.saved_status.get(server_name)
            # Compare with current server status
            # if value is None -> Server did not exist yet in saved_status
            if old_status != response['status'] and old_status is not None:
                NotificationHandler.notification(old_status, response['status'], server_name)
                
        # Save server status
        self.saved_status[server_name] = response['status']

        # Worker finished, -1 from active_workers
        self.active_workers -= 1
        return

    """
        = Button handling =
    """

    def server_delete_clicked(self):
        """
        Get all rows from the selected cells, get rid of any duplicate rows.
        Pop the server from the self.servers
        Ignore the server on the status list,
        it will get overwritten next server check
        :return:
        """

        # Get the table and selected cells from that table
        table = self.findChild(QTableView, "settings_server_list")
        selected = table.selectedIndexes()

        # Get the rows from all selected cells
        rows = [item.row() for item in selected]

        # Get rid of duplicated in rows
        rows = list(dict.fromkeys(rows))

        self.logger.debug(f"selected: {selected}\n"
                          f"\t- Rows: {rows}")

        for row in rows:
            # Get the name (key) to pop from self.servers
            name = self.server_list_settings.item(row, 0).text()

            # Pop the server from the server list
            self.servers.pop(name)

            # Remove the row from the settings table
            self.server_list_settings.removeRows(row, 1)

            # See if the server is also in the status list
            try:
                row = self.workers[name]['row']

                # Remove the row from the status table
                self.server_list_status.removeRows(row, 1)
            except KeyError as ke:
                self.logger.debug(f"No row found for {name} on the status list")
                # Not found on status list, ignore
                pass
        return

    def server_refresh_clicked(self):
        self.refresh_servers()
        return

    def add_server_clicked(self):
        name = self.findChild(QLineEdit, "server_form_name").text()
        url = self.findChild(QLineEdit, "server_form_url").text()
        port = self.findChild(QLineEdit, "server_form_port").text()
        web = "True" if self.findChild(QCheckBox, "server_form_web").isChecked() else "False"

        # The 2 variables made below are kept seperate
        # Because QStandardItem requires a string, not int or bool
        # But the self.servers dictionary does needs them as int and bool

        # Test if port is a valid int and make a new variable with the int version of the port
        success, _port = self.convert_to_int(port, hide_error=True)
        # Make a bool version of the web variable
        _web = self.convert_to_bool(web)

        exists = name in self.servers

        self.logger.debug(f"424 - Attempting to add | Valid port: {success} | Server exists: {exists}")

        # If the port was a valid number and name not already registered in self.servers:
        if success and not exists:
            # Add new server to dictionary (using int and bool version of port and web)
            self.servers[name] = {'url': url, 'port': _port, 'web': _web}

            # Add new row to the server list on the left, ready for checks
            self.server_list_settings.appendRow([
                QStandardItem(name),
                QStandardItem(url),
                QStandardItem(port),
                QStandardItem(web),
            ])
        elif exists:
            # Server name already in use, skip
            self.error_message("Server name already in use, they are required to be unique", "Name already in use")
        elif not success:
            # Was unable to convert port to int, not adding this
            self.error_message("Unable to add server because of the invalid port!\nMust be a number!", "Invalid number")
            pass

    def interval_update_clicked(self):
        interval_obj = self.findChild(QLineEdit, "interval_text")

        success, new_interval = self.convert_to_int(interval_obj.text())

        # If new interval is a valid number, set new interval
        # if not, ignore and skip -> convert_to_int will give a error message for the user
        if success:
            self.interval = new_interval
            self.status_bar.showMessage(f"Interval updated, new interval {self.interval} seconds")
        else:
            interval_obj.setText(str(self.interval))

    def save_settings_clicked(self):
        self.logger.debug("save_settings clicked - Not implemented yet")

        self.save()
        return

    def notify_changed(self, state):
        """
        :param state: int -> is either: 0 if unchecked, 2 if checked
        """
        self.logger.debug(f"Notify changed, new state: {state} | Type: {type(state)}")
        self.notify = bool(state)   # 0 = False, 2 = True

    """
        Menu bar - options
    """

    def toggle_style(self):
        self.logger.debug("Custom style toggled")

        use_stylesheet = self.config.get_value("custom_style", "WINDOW")
        use_stylesheet = self.convert_to_bool(use_stylesheet)

        # Toggle stylesheet, True->False, False->True
        if use_stylesheet:
            use_stylesheet = False
        else:
            use_stylesheet = True

        self.config.update_value("WINDOW", 'custom_style', str(use_stylesheet))

        # Requires a restart
        self.error_message(f"Custom stylesheet {'ENABLED' if use_stylesheet else 'DISABLED'}\n"
                           f"Restart required for changes", error_name="Important")
        return
