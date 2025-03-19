import re
from typing import List


def extract_urls(content: str) -> List[str]:
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F])|[;/?:@=&#])+'
    urls = re.findall(url_pattern, content)
    cleaned_urls = [url.rstrip('.,!?;:') for url in urls]
    return cleaned_urls

def nonewlines(s: str) -> str:
    return s.replace("\n", " ").replace("\r", " ")