#!/usr/bin/env python3
import os
import argparse

from winpid import create_pid_file_or_exit

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, StaticFileHandler, url, stream_request_body

from tornadostreamform.multipart_streamer import MultiPartStreamer, TemporaryFileStreamedPart

MB = 1024 * 1024
GB = 1024 * MB
TB = 1024 * GB

MAX_BUFFER_SIZE = 4 * MB  # Max. size loaded into memory!
MAX_BODY_SIZE = 4 * MB  # Max. size loaded into memory!
MAX_STREAMED_SIZE = 1 * TB  # Max. size streamed in one request!

UPLOAD_FORM = os.path.splitext(os.path.abspath(__file__))[0] + ".html"


class DropFileStreamer(MultiPartStreamer):
    def __init__(self, total):
        super().__init__(total)
        self._last_progress = 0.0  # Last time of updating the progress

    def create_part(self, headers):
        print(repr(headers))
        return TemporaryFileStreamedPart(self, headers)


class MainPage(RequestHandler):
    def get(self):
        self.add_header("Content-Type", "text/html")
        self.add_header("Content-Encoding", "utf-8")
        self.write(open(args.upload_form_path, "r").read())


@stream_request_body
class DropFileHandler(RequestHandler):
    ps: DropFileStreamer

    def initialize(self) -> None:
        pass

    def prepare(self):
        global MAX_STREAMED_SIZE
        print(self.request.headers)
        if self.request.method.lower() == "post":
            self.request.connection.set_max_body_size(MAX_STREAMED_SIZE)
        try:
            total = int(self.request.headers.get("Content-Length", "0"))
        except KeyError:
            total = 0  # For any well formed browser request, Content-Length should have a value.
        self.ps = DropFileStreamer(total)

    def data_received(self, chunk):
        self.ps.data_received(chunk)

    def post(self):
        try:
            try:
                # Before using the form parts, you **must** call data_complete(), so that the last part can be finalized.
                self.ps.data_complete()
                # Use parts here!
                self.write("Now what?")
            finally:
                self.ps.release_parts()
        finally:
            self.finish()

    put = post


def main():
    handlers = [
        url(r"/", MainPage),
        url(r"/upload", DropFileHandler),
    ]
    if args.static_dir_path:
        handlers.append((r'/static/(.*)', StaticFileHandler, {'path': args.static_dir_path})),
    application = Application(handlers)
    http_server = HTTPServer(
        application,
        max_body_size=MAX_BODY_SIZE,
        max_buffer_size=MAX_BUFFER_SIZE,
    )
    http_server.listen(args.port, args.listen_address)
    IOLoop.instance().start()


parser = argparse.ArgumentParser(description='Dropzone-Backup Server')
parser.add_argument("-p", "--port", dest='port', metavar="PORT",
                    type=int, default=8888,
                    help="Port number to listen on"
                    )
parser.add_argument("-l", "--listen", dest='listen_address', metavar="LISTEN_ADDRESS",
                    type=str, default="",
                    help="Address to listen on. Default is to listen on all addresses."
                    )
parser.add_argument("-m", "--max-file-size", dest='max_file_size', metavar="MAX_STREAMED_SIZE",
                    type=int, default=MAX_STREAMED_SIZE,
                    help="Maximum file size to be accepted. Defaults to 1*TB"
                    )
parser.add_argument("--pidfile", dest='pid_file_path', metavar="PIDFILE",
                    default="dropzone-backup-server.pid",
                    help="Filename where the pid of the process should be written."
                    )
parser.add_argument("--auto-remove-pid-file", dest='auto_remove_pid_file', action="store_true", default=False,
                    help="Auto remove the pid file (useful for testing, when psutil is not available)."
                    )
parser.add_argument("--upload-form", dest='upload_form_path', metavar="UPLOAD_FORM_PATH",
                    default=UPLOAD_FORM,
                    help="File path the the html form that is server at /. You can customize your upload form"
                         "using this file."
                    )
parser.add_argument("--static-dir", dest='static_dir_path', metavar="STATIC_DIR_PATH",
                    default=None,
                    help="Path to a directory that will be server under /static. (Optional)"
                    )

parser.add_argument("-v", "--verbose", dest='verbose', action="store_true", default=False,
                    help="Log processor messages (not just the log files)."
                    )
parser.add_argument("-d", "--debug", dest='debug', action="store_true", default=False,
                    help="Change log level from NOTICE to DEBUG. This does not effect STS (see below)"
                    )
args = parser.parse_args()

create_pid_file_or_exit(args.pid_file_path, auto_remove_pid_file=args.auto_remove_pid_file)
main()
