class JUnitXMLFile():
    def __init__(self, path):
        self.path = path
        self.fd = None

    def __enter__(self):
        self.fd = open(self.path, "w")
        self.fd.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.fd.write('<testsuite name="Integration test">\n')

        return self

    def write(self, __s: str) -> int:
        return self.fd.write(__s)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.fd.write('</testsuite>\n')
        self.fd.close()
