"""Per-outlet HTML -> field extraction for the raw snapshot.

One function per outlet, all returning the same schema (see ArticleFields).
Field semantics are identical across outlets and periods by construction;
behavior is pinned by committed HTML fixtures in tests/fixtures/.

PARSER_VERSION is recorded on every extracted row.
"""

import json
import re
from dataclasses import asdict, dataclass

from bs4 import BeautifulSoup

PARSER_VERSION = "1"

# Block-level elements whose text constitutes the article body. v1 extracted
# <p> only and lost attributions living in lists/blockquotes.
BODY_BLOCKS = ("p", "li", "blockquote", "h2", "h3", "h4", "figcaption")

RUBRIC_RE = re.compile(r"ukrinform\.ua/(rubric-[a-z-]+)/")
SLUG_ID_RE = re.compile(r"^\d+-")


@dataclass
class ArticleFields:
    url: str
    outlet: str
    date_published: str | None  # ISO-8601 as found in the page
    date_modified: str | None
    rubric: str | None
    slug: str | None
    title: str | None
    og_description: str | None
    body_text: str | None
    parse_error: str | None
    parser_version: str = PARSER_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _ld_news_article(soup: BeautifulSoup) -> dict:
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if isinstance(item, dict) and item.get("@type") in ("NewsArticle", "Article"):
                return item
    return {}


def _meta(soup: BeautifulSoup, **attrs) -> str | None:
    tag = soup.find("meta", attrs=attrs)
    return tag.get("content") if tag and tag.get("content") else None


def _body_text(container) -> str | None:
    if container is None:
        return None
    blocks = container.find_all(BODY_BLOCKS)
    if blocks:
        parts = [b.get_text(" ", strip=True) for b in blocks]
    else:
        parts = [container.get_text(" ", strip=True)]
    text = "\n".join(p for p in parts if p)
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text or None


def parse_ukrinform(url: str, html: str) -> ArticleFields:
    soup = BeautifulSoup(html, "lxml")
    ld = _ld_news_article(soup)
    m = RUBRIC_RE.search(url)
    rubric = m.group(1) if m else None
    tail = url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".html")
    slug = SLUG_ID_RE.sub("", tail) or None

    title_tag = soup.select_one("h1.newsTitle")
    title = title_tag.get_text(" ", strip=True) if title_tag else _meta(soup, property="og:title")

    # Drop non-body embeds Ukrinform injects into the text flow.
    container = soup.select_one("div.newsText") or soup.find("article")
    if container is not None:
        for junk in container.select("div.read-also, div.newsRelated, script, style, figure.video"):
            junk.decompose()

    body = _body_text(container)
    return ArticleFields(
        url=url,
        outlet="ukrinform",
        date_published=ld.get("datePublished")
        or _meta(soup, itemprop="datePublished"),
        date_modified=ld.get("dateModified"),
        rubric=rubric,
        slug=slug,
        title=title,
        og_description=_meta(soup, property="og:description"),
        body_text=body,
        parse_error=None if (body and title) else "missing body or title",
    )


def parse_pravda(url: str, html: str) -> ArticleFields:
    soup = BeautifulSoup(html, "lxml")
    ld = _ld_news_article(soup)

    title_tag = soup.select_one("h1.post_title, h1.post__title, div.post_news__title h1, h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else _meta(soup, property="og:title")

    container = soup.select_one(
        "div.post_text, div.post__text, div.post_news__text, article"
    )
    if container is not None:
        for junk in container.select("div.post__banner, div.adv, script, style, div.social_item"):
            junk.decompose()

    published = (
        ld.get("datePublished")
        or _meta(soup, property="article:published_time")
        or _meta(soup, itemprop="datePublished")
    )
    body = _body_text(container)
    return ArticleFields(
        url=url,
        outlet="pravda",
        date_published=published,
        date_modified=ld.get("dateModified") or _meta(soup, property="article:modified_time"),
        rubric="news",
        slug=url.rstrip("/").rsplit("/", 1)[-1],
        title=title,
        og_description=_meta(soup, property="og:description"),
        body_text=body,
        parse_error=None if (body and title) else "missing body or title",
    )


def parse_suspilne(url: str, html: str) -> ArticleFields:
    soup = BeautifulSoup(html, "lxml")
    ld = _ld_news_article(soup)

    title_tag = soup.select_one("h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else _meta(soup, property="og:title")

    container = soup.select_one("article.post-body") or soup.find("article")
    if container is not None:
        for junk in container.select("div.c-article-card, aside, script, style"):
            junk.decompose()

    slug_tail = url.rstrip("/").rsplit("/", 1)[-1]
    published = (
        ld.get("datePublished")
        or _meta(soup, itemprop="datePublished")
        or _meta(soup, property="article:published_time")
    )
    body = _body_text(container)
    return ArticleFields(
        url=url,
        outlet="suspilne",
        date_published=published,
        date_modified=ld.get("dateModified") or _meta(soup, itemprop="dateModified"),
        rubric="news",
        slug=SLUG_ID_RE.sub("", slug_tail) or None,
        title=title,
        og_description=_meta(soup, property="og:description"),
        body_text=body,
        parse_error=None if (body and title) else "missing body or title",
    )


PARSERS = {
    "ukrinform": parse_ukrinform,
    "pravda": parse_pravda,
    "suspilne": parse_suspilne,
}
