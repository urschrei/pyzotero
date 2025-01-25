from pathlib import Path

import pytest

from pyzotero.filetransport import AsyncClient

# ruff: noqa: PLR2004
# ruff: noqa: S101


@pytest.mark.asyncio
async def test_file_transport():
    test_file = Path("test.txt")
    test_file.write_text("test content")

    client = AsyncClient()
    try:
        async with client:
            resp = await client.get(f"file:///{test_file.absolute()}")
            content = await resp.aread()
            assert resp.status_code == 200
            assert content == b"test content"
    finally:
        test_file.unlink()
