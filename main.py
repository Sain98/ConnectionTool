from PyQt5.QtWidgets import QApplication
from tool.tool import ConnectionTool

if __name__ == "__main__":
    print("[?] - Starting ConnectionTool...")
    app = QApplication([])
    tool = ConnectionTool()
    app.exec_()
