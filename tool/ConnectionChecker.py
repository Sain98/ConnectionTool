from PyQt5.QtCore import QThread, pyqtSignal
import tool.Constants as const
import socket
import requests


class ConnectionWorker(QThread):
    worker_response = pyqtSignal(dict, str)     # Return/emit types

    def __init__(self, name, ip, port, is_website, logger=None):
        QThread.__init__(self)

        self.logger = logger

        self.name = name
        self.ip = ip
        self.port = port
        self.is_website = is_website
        self.response = ""

    def run_webcheck(self):
        """
        First it formats the given url/ip and port to a workable format
        Then it runs a check on the given url and port, treating it as a website/http server
        Stores results in self.response
        :return:
        """

        url = self.format_url(self.ip, self.port)

        # Requests requires a url to have either, 'http' or 'https' infront
        try:
            req = requests.get(url, stream=True)

            # Get status code and description
            status = f"[{req.status_code}] - {req.reason}"

            # Get server ip from url
            ipv46 = req.raw._connection.sock.getsockname()[0]

            # Close connection
            req.close()

            # Lots of error handling
        except requests.exceptions.ConnectionError:
            # Server offline or atleast, from the clients point is unable to make any connection
            status = "OFFLINE"
            ipv46 = "OFFLINE"
        except requests.exceptions.Timeout:
            # Request timed out
            status = "Request timed out"
            ipv46 = "TIMEOUT"
        except requests.exceptions.TooManyRedirects:
            # Got redirected too many times
            status = "Redirect limit"
            ipv46 = "REDIRECTED"
        except requests.exceptions.RequestException as ex:
            if self.logger is not None:
                # If logger is set, log error message
                self.logger.debug(f"Uncaught exception - run_webcheck()\n\t"
                                  f"- {ex}")
            status = "Unknown exception"
            ipv46 = "Unknown exception"

        self.response = {"status": status,
                         "ipv4/6": ipv46,
                         "port": self.port,
                         "url": self.ip,
                         "is_web": True
                         }

    def run_socketcheck(self):
        try:
            sock = socket.create_connection((self.ip, self.port), timeout=const.MAX_TIMEOUT)
            s_family = "IPv6" if socket.AddressFamily.AF_INET6 == sock.family else "IPv4"
            s_raddr = sock.getpeername()
            sock.close()

            status = "Online"
        except socket.gaierror:
            status = "Offline"
            s_family = "None"
        except ConnectionRefusedError:
            status = "Refused"
            s_family = "Connection refused"
        except TimeoutError:
            status = "Unknown/Timed out"
            s_family = "Timeout"
        except Exception as ex:
            if self.logger is not None:
                self.logger.debug("Caught exception - run_socketcheck()\n\t"
                                  f"- {ex}")

        self.response = {"status": status,
                         "ipv4/6": s_family,
                         "port": str(self.port),
                         "url": self.ip,
                         "is_web": False
                         }

    @staticmethod
    def format_url(url, port):
        """
        Formats the given url and port so it is valid for the requests.get()
        :param url: str
        :param port: int
        :return: new_url -> str
        """
        new_url = ""
        url_s = url.split("/")

        if "http" in url:
            # Get rid of first 2 items in list
            # No need to add "or 'https'" as that includes the 'http' check already
            http = url_s[0]    # we require http later, save it so we know what the user provided (http, https)
            url_s = url_s[2:]
        else:
            http = "http"

        new_url = url_s[0] + f":{port}"

        # The url had sub-dirs after the part where we place our port
        if len(url_s) > 1:
            new_url += "/"
            new_url += "/".join(url_s[1:])

        # Prepend the http(s) to the url again and return
        return http + "://" + new_url

    def validate_ip(self):
        pass

    def run(self):
        if self.is_website:
            self.run_webcheck()
        else:
            self.run_socketcheck()

        self.worker_response.emit(self.response, self.name)

        # Unsure on how to clean up this thread after it's done
        # This might not work
        self.isFinished()
