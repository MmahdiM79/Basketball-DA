from abc import ABC, abstractmethod
from pathlib import Path

from .models import Page, ParseContext, ParsedData, Row


class PageSource(ABC):
    @abstractmethod
    def get(self, url: str) -> Page:
        raise NotImplementedError


class HtmlParser(ABC):
    def parse_url(
        self, source: PageSource, url: str, context: ParseContext
    ) -> ParsedData:
        return self.parse(source.get(url), context)

    @abstractmethod
    def parse(self, page: Page, context: ParseContext) -> ParsedData:
        raise NotImplementedError


class DatasetWriter(ABC):
    @abstractmethod
    def write(self, datasets: dict[str, list[Row]], output_dir: Path) -> None:
        raise NotImplementedError
