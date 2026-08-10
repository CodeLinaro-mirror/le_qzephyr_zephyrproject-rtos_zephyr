# Copyright (c) 2026 Qualcomm Technologies, Inc. and/or its subsidiaries
# SPDX-License-Identifier: Apache-2.0

import base64
import netrc
import ssl
import urllib.request
from urllib.parse import urlparse

from fetchers.core import ZephyrBlobException, ZephyrBlobFetcher


class GitilesFetcher(ZephyrBlobFetcher):
    """Fetcher for Gitiles URLs (e.g. review-android.quicinc.com).

    Gitiles returns base64-encoded content when the query parameter
    ``?format=TEXT`` is appended to the URL.  This fetcher downloads the
    page, base64-decodes it, and writes the raw bytes to *path*.
    Credentials are read from ~/.netrc.
    """

    @classmethod
    def schemes(cls):
        return ['gitiles']

    def fetch(self, west_command, blob, path):
        url = blob['url']
        west_command.dbg(f'GitilesFetcher fetching {url} to {path}')

        # Ensure format=TEXT so Gitiles returns base64-encoded content
        if 'format=TEXT' not in url:
            sep = '&' if '?' in url else '?'
            url = url + sep + 'format=TEXT'

        host = urlparse(url).hostname

        req = urllib.request.Request(url)
        try:
            creds = netrc.netrc().authenticators(host)
            if creds:
                login, _, password = creds
                token = base64.b64encode(f'{login}:{password}'.encode()).decode()
                req.add_header('Authorization', f'Basic {token}')
        except Exception:
            pass

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            with urllib.request.urlopen(req, timeout=60, context=ssl_ctx) as resp:
                content = resp.read()
        except urllib.error.HTTPError as e:
            raise ZephyrBlobException(f'HTTP {e.code} fetching {url}') from e
        except urllib.error.URLError as e:
            raise ZephyrBlobException(f'URL error fetching {url}: {e}') from e

        try:
            raw = base64.b64decode(content)
        except Exception as e:
            raise ZephyrBlobException(
                f'Failed to base64-decode response from {url}: {e}'
            ) from e

        with open(path, 'wb') as f:
            f.write(raw)
