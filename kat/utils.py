class Color:
    @staticmethod
    def green(s: str) -> str:
        return "\x1b[0;32m" + s + "\x1b[0m"

    @staticmethod
    def red(s: str) -> str:
        return "\x1b[0;31m" + s + "\x1b[0m"

    @staticmethod
    def yellow(s: str) -> str:
        return "\x1b[0;33m" + s + "\x1b[0m"
