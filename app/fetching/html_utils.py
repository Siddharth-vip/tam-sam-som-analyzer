import html
from html.parser import HTMLParser
import re
from typing import List, Set


class TextExtractingParser(HTMLParser):
    """HTML Parser that strips boilerplate tags and preserves structural text content."""

    IGNORED_TAGS: Set[str] = {
        "script",
        "style",
        "noscript",
        "svg",
        "nav",
        "header",
        "footer",
        "iframe",
    }

    BLOCK_TAGS: Set[str] = {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "tr",
        "article",
        "section",
        "div",
        "blockquote",
        "br",
        "hr",
    }

    def __init__(self) -> None:
        super().__init__()
        self.pieces: List[str] = []
        self.ignore_depth = 0
        self.title_text: List[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.IGNORED_TAGS:
            self.ignore_depth += 1
        elif tag_lower == "title":
            self.in_title = True
        elif tag_lower in self.BLOCK_TAGS:
            self.pieces.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.IGNORED_TAGS:
            if self.ignore_depth > 0:
                self.ignore_depth -= 1
        elif tag_lower == "title":
            self.in_title = False
        elif tag_lower in self.BLOCK_TAGS:
            self.pieces.append("\n")

    def handle_data(self, data: str) -> None:
        if self.ignore_depth > 0:
            return
        if self.in_title:
            self.title_text.append(data)
        self.pieces.append(data)

    def get_text(self) -> str:
        raw_text = "".join(self.pieces)
        decoded = html.unescape(raw_text)
        # Normalize whitespace while preserving linebreaks
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in decoded.splitlines()]
        # Collapse multiple empty lines
        cleaned_text = "\n".join(line for line in lines if line)
        return cleaned_text

    def get_title(self) -> str:
        return html.unescape(" ".join(self.title_text)).strip()


def extract_text_from_html(html_content: str) -> tuple[str, str]:
    """Parse HTML string and return (clean_text, extracted_title)."""
    parser = TextExtractingParser()
    try:
        parser.feed(html_content)
        parser.close()
        return parser.get_text(), parser.get_title()
    except Exception:
        # Fallback to regex-based tag stripping if HTML parsing encounters extreme malformation
        clean = re.sub(r"<script.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<style.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", " ", clean)
        clean = html.unescape(clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean, ""
