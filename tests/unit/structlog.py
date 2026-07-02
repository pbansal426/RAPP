# Mock structlog module to allow running unit tests without external package installation
class DummyLogger:
    def info(self, msg, *args, **kwargs):
        pass
    def warning(self, msg, *args, **kwargs):
        pass
    def error(self, msg, *args, **kwargs):
        pass
    def exception(self, msg, *args, **kwargs):
        pass

def get_logger(*args, **kwargs):
    return DummyLogger()

def configure(*args, **kwargs):
    pass

class StdlibModule:
    @staticmethod
    def add_log_level(*args, **kwargs):
        pass
    @staticmethod
    def add_logger_name(*args, **kwargs):
        pass
    @staticmethod
    def LoggerFactory(*args, **kwargs):
        return lambda: None
    class BoundLogger:
        pass

class ProcessorsModule:
    @staticmethod
    def TimeStamper(*args, **kwargs):
        return lambda *a, **kw: None
    @staticmethod
    def StackInfoRenderer(*args, **kwargs):
        return lambda *a, **kw: None
    @staticmethod
    def format_exc_info(*args, **kwargs):
        return lambda *a, **kw: None
    @staticmethod
    def JSONRenderer(*args, **kwargs):
        return lambda *a, **kw: None

class DevModule:
    @staticmethod
    def ConsoleRenderer(*args, **kwargs):
        return lambda *a, **kw: None

stdlib = StdlibModule
processors = ProcessorsModule
dev = DevModule
