# This is a modified version of httpx_file:
# The aiofiles dependency has been removed by modifying the async functionality to use
# asyncio instead. A specific test for this modification can be found in tests/test_async.py
# https://github.com/nuno-andre/httpx-file


# The license and copyright notice are reproduced below
# Copyright (c) 2021, Nuno André Novo
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of the <copyright holder> nor the names of its contributors
#   may be used to endorse or promote products derived from this software without
#   specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import asyncio
from pathlib import Path
from typing import Optional

import httpx
from httpx import (
    AsyncBaseTransport,
    BaseTransport,
    ByteStream,
    Request,
    Response,
)
from httpx import (
    AsyncClient as _AsyncClient,
)
from httpx import (
    Client as _Client,
)
from httpx._utils import URLPattern


# monkey patch to fix httpx URL parsing
def is_relative_url(self):
    return not (self._uri_reference.scheme or self._uri_reference.host)


def is_absolute_url(self):
    return not self.is_relative_url


httpx.URL.is_relative_url = property(is_relative_url)  # type: ignore
httpx.URL.is_absolute_url = property(is_absolute_url)  # type: ignore


class FileTransport(AsyncBaseTransport, BaseTransport):
    def _handle(self, request: Request) -> tuple[Optional[int], httpx.Headers]:
        if request.url.host and request.url.host != "localhost":
            raise NotImplementedError("Only local paths are allowed")
        if request.method in {"PUT", "DELETE"}:
            status = 501  # Not Implemented
        elif request.method not in {"GET", "HEAD"}:
            status = 405  # Method Not Allowed
        else:
            status = None
        return status, request.headers

    def handle_request(self, request: Request) -> Response:
        status, headers = self._handle(request)
        stream = None
        if not status:
            parts = request.url.path.split("/")
            if parts[1].endswith((":", "|")):
                parts[1] = parts[1][:-1] + ":"
                parts.pop(0)
            ospath = Path("/".join(parts))
            try:
                content = ospath.read_bytes()
                status = 200
            except FileNotFoundError:
                status = 404
            except PermissionError:
                status = 403
            else:
                stream = ByteStream(content)
                headers["Content-Length"] = str(len(content))
        return Response(
            status_code=status,
            headers=headers,
            stream=stream,
            extensions=dict(),
        )

    async def handle_async_request(self, request: Request) -> Response:
        status, headers = self._handle(request)
        stream = None
        if not status:
            parts = request.url.path.split("/")
            if parts[1].endswith((":", "|")):
                parts[1] = parts[1][:-1] + ":"
                parts.pop(0)
            ospath = Path("/".join(parts))
            try:
                loop = asyncio.get_event_loop()
                content = await loop.run_in_executor(None, ospath.read_bytes)
                status = 200
            except FileNotFoundError:
                status = 404
            except PermissionError:
                status = 403
            else:
                stream = ByteStream(content)
                headers["Content-Length"] = str(len(content))
        return Response(
            status_code=status,
            headers=headers,
            stream=stream,
            extensions=dict(),
        )


class Client(_Client):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.mount("file://", FileTransport())

    def mount(self, protocol: str, transport: BaseTransport) -> None:
        self._mounts.update({URLPattern(protocol): transport})


class AsyncClient(_AsyncClient):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.mount("file://", FileTransport())

    def mount(self, protocol: str, transport: AsyncBaseTransport) -> None:
        self._mounts.update({URLPattern(protocol): transport})


__all__ = ["AsyncClient", "Client", "FileTransport"]
