# Temporary patch for Python 3.13 (cgi removed)
def parse_header(line):
    return line, {}
