"""Compile the production CPU HLE function against test memory/renderer interfaces.

This exercises the actual control flow without loading game data or a Vulkan device.
The harness does not validate the real driver, cache synchronization or device API.
"""
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding='utf-8')
start = text.index('static bool ExecuteCopyShaderHLE(')
end = text.index('\nbool ExecuteShaderHLE(', start)
body = text[start:end]
assert body.rstrip().endswith('}')
Path(sys.argv[2]).write_text(body, encoding='utf-8')
