"""Serve synthetic UI fixtures with the pinned, unpacked Elastic CSS locally.

No proxying, authentication, mail data or writes. Run with --vendor pointing to
the extracted Roundcube skin; bind to loopback only. Not a mail client.
"""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--vendor', required=True, type=Path)
    parser.add_argument('--port', default=8767, type=int)
    args = parser.parse_args()
    roots = {'vendor': args.vendor.resolve(), 'plugin': Path(__file__).resolve().parents[1] / 'jaysonkhan_mail'}
    fixture = Path(__file__).with_name('preview.html')

    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            parts = unquote(urlsplit(path).path).lstrip('/').split('/')
            if parts == ['']:
                return str(fixture)
            if parts == ['regressions']:
                return str(fixture.with_name('regressions.html'))
            root = roots.get(parts[0])
            if root:
                target = root.joinpath(*parts[1:]).resolve()
                if target.is_relative_to(root) and target.is_file():
                    return str(target)
            return str(fixture.parent / '__not_found__')

    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
