import gzip
import io
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread

import pytest
import zstandard
from fixtures import DataDir

from pipeline.common.downloads import read_lines, write_lines

# Content to serve
line_fixtures = [
    "line 1\n",
    "line 2\n",
    "line 3\n",
    "line 4\n",
    "line 5\n",
]
line_fixtures_bytes = "".join(line_fixtures).encode("utf-8")


def write_test_content(output_path: str) -> str:
    with write_lines(output_path) as outfile:
        for line in line_fixtures:
            outfile.write(line)
    return output_path


class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    This test fixture serves files locally for easy http request testing.
    """

    gz_path: str
    zst_path: str
    txt_path: str

    def determine_file(self):
        """
        Determine the file type and location. If "no-mime-type" is passed as a query paraemter
        the file mime type will not be determined.
        """
        split = self.path.split("?")
        path = None
        query = None
        if len(split) == 1:
            path = split[0]
        elif len(split) == 2:
            path, query = split

        file_path = None
        mime_type = None

        if path == "/lines.txt.gz":
            mime_type = "application/gzip"
            file_path = self.gz_path
        elif path == "/lines.txt.zst":
            mime_type = "application/zstd"
            file_path = self.zst_path
        elif path == "/lines.txt":
            mime_type = "text/plain"
            file_path = self.txt_path

        if query == "no_mime_type":
            mime_type = None

        return mime_type, file_path

    def do_GET(self):
        mime_type, file_path = self.determine_file()
        if not file_path:
            self.send_response(404)
            return

        self.send_response(200)
        if mime_type:
            self.send_header("Content-type", mime_type)

        self.end_headers()

        with open(file_path, "rb") as file:
            self.wfile.write(file.read())

    def do_HEAD(self):
        mime_type, file_path = self.determine_file()
        if not file_path:
            self.send_response(404)
            return

        self.send_response(200)
        if mime_type:
            self.send_header("Content-type", mime_type)
        self.end_headers()


@pytest.fixture(scope="function")
def http_server():
    """
    Creates a http server fixture. The server lives in another thread and is torn down after
    the test. It only serves a few files.
    """
    data_dir = DataDir("test_read_lines")
    handler = CustomHTTPRequestHandler

    gz_content = io.BytesIO()
    with gzip.GzipFile(fileobj=gz_content, mode="wb") as f:
        f.write(line_fixtures_bytes)

    cctx = zstandard.ZstdCompressor()
    cctx.compress(line_fixtures_bytes)

    handler.gz_path = write_test_content(data_dir.join("lines.txt.gz"))
    handler.zst_path = write_test_content(data_dir.join("lines.txt.zst"))
    handler.txt_path = write_test_content(data_dir.join("lines.txt"))

    httpd = HTTPServer(("localhost", 0), handler)  # Bind to port 0 to find a free port
    port = httpd.server_address[1]  # Get the actual port assigned
    thread = Thread(target=httpd.serve_forever)
    thread.start()

    print(f"Listening at http://localhost:{port}")
    yield port

    httpd.shutdown()
    thread.join()


@pytest.mark.parametrize(
    "filename",
    ["lines.txt.gz", "lines.txt.zst", "lines.txt"],
)
@pytest.mark.parametrize(
    "query_param",
    ["", "?no-mime-type"],
)
def test_read_lines_remote(filename, query_param, http_server):
    port = http_server
    url = f"http://localhost:{port}/{filename}{query_param}"
    print("Reading", f"http://localhost:{port}/{filename}")
    with read_lines(url) as lines:
        assert list(lines) == line_fixtures


@pytest.mark.parametrize(
    "filename",
    ["lines.txt.gz", "lines.txt.zst", "lines.txt"],
)
def test_read_lines_local(filename):
    """
    This test round-trips a write_lines and read_lines.
    """
    data_dir = DataDir("test_read_lines")
    file_path = data_dir.join(filename)
    write_test_content(file_path)

    with read_lines(file_path) as lines:
        assert list(lines) == line_fixtures


def test_read_lines_local_multiple():
    """
    Read lines can take multiple files.
    """
    data_dir = DataDir("test_read_lines")
    file_paths = [data_dir.join(path) for path in ["lines.txt.gz", "lines.txt.zst", "lines.txt"]]
    for file_path in file_paths:
        write_test_content(data_dir.join(file_path))

    with read_lines(file_paths) as lines:
        assert list(lines) == [*line_fixtures, *line_fixtures, *line_fixtures]
