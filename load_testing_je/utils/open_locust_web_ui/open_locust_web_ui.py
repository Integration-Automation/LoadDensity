import webbrowser

def open_web_ui(port: str = "8089", **kwargs):
    webbrowser.open("http://localhost:" + port, **kwargs)
