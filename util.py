import locale
import os
import re
import tempfile
import subprocess


STREAM_STDOUT = 1
STREAM_STDERR = 2
STREAM_BOTH = STREAM_STDOUT + STREAM_STDERR

XML_TAG_REGEX = re.compile('<[^>]+>')
JSON_TAG_REGEX = re.compile('[{}\[\]]')


def decode(bytes):
    """
    Decode and return a byte string using utf8, falling back to system's encoding if that fails.

    So far we only have to do this because javac is so utterly hopeless it uses CP1252
    for its output on Windows instead of UTF8, even if the input encoding is specified as UTF8.
    Brilliant! But then what else would you expect from Oracle?

    """
    if not bytes:
        return ''

    try:
        return bytes.decode('utf8')
    except UnicodeError:
        return bytes.decode(locale.getpreferredencoding(), errors='replace')


def popen(cmd, stdout=None, stderr=None, output_stream=STREAM_BOTH):
    """Open a pipe to an external process and return a Popen object."""

    info = None

    if os.name == 'nt':
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESTDHANDLES | subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE

    if output_stream == STREAM_BOTH:
        stdout = stdout or subprocess.PIPE
        stderr = stderr or subprocess.PIPE
    elif output_stream == STREAM_STDOUT:
        stdout = stdout or subprocess.PIPE
        stderr = subprocess.DEVNULL
    else:  # STREAM_STDERR
        stdout = subprocess.DEVNULL
        stderr = stderr or subprocess.PIPE

    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=stdout,
        stderr=stderr,
        startupinfo=info,
    )


def communicate(cmd, code=None, output_stream=STREAM_STDOUT):
    """
    Return the result of sending code via stdin to an executable.

    The result is a string which comes from stdout, stderr or the
    combining of the two, depending on the value of output_stream.

    """

    # On Windows, using subprocess.PIPE with Popen() is broken when not
    # sending input through stdin. So we use temp files instead of a pipe.
    if code is None and os.name == 'nt':
        if output_stream != STREAM_STDERR:
            stdout = tempfile.TemporaryFile()
        else:
            stdout = None

        if output_stream != STREAM_STDOUT:
            stderr = tempfile.TemporaryFile()
        else:
            stderr = None
    else:
        stdout = stderr = None

    process = popen(cmd, stdout=stdout, stderr=stderr, output_stream=output_stream)

    if process is not None:
        if code is not None:
            code = code.encode('utf8')

        out = process.communicate(code)
        if process.returncode != 0:
            raise Exception(decode(out[0]))

        if code is None and os.name == 'nt':
            out = list(out)

            for f, index in ((stdout, 0), (stderr, 1)):
                if f is not None:
                    f.seek(0)
                    out[index] = f.read()

        return decode(out[0])
    else:
        return ''


class DataTypeRecognition(object):
    def __init__(self, code):
        self.code = code

    def calculate_xml_factor(self):
        xml_matches = len(XML_TAG_REGEX.findall(self.code))
        return 100.0 * xml_matches / len(self.code)

    def calculate_json_factor(self):
        json_matches = len(JSON_TAG_REGEX.findall(self.code))
        return 500.0 * json_matches / len(self.code)

    def recognise(self):
        factors = {
            'json': self.calculate_json_factor(),
            'xml': self.calculate_xml_factor()
        }
        max_key = max(factors.keys(), key=lambda key: factors[key])
        if factors[max_key]:
            return max_key


def data_type_recognition(code):
    return DataTypeRecognition(code).recognise()
