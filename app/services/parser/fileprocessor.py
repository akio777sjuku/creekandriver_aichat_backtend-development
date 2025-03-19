from dataclasses import dataclass

from app.services.parser.parser import Parser
from app.services.textsplitter import TextSplitter


@dataclass(frozen=True)
class FileProcessor:
    parser: Parser
    splitter: TextSplitter
