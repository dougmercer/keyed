from __future__ import annotations

import re
from functools import lru_cache
from html import escape
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from markdown import Markdown
from material.extensions.emoji import to_svg, twemoji
from mkdocs.utils import get_relative_url

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.pages import Page

SHORTCODE_PATTERN = re.compile(r"<!--\s*md:(\w+)(.*?)\s*-->")
INLINE_TAG_PATTERN = re.compile(
    r"@deprecated:\s*(?P<deprecated>[A-Za-z0-9_.-]+)"
    r"|@version:\s*(?P<version>[A-Za-z0-9_.-]+)"
    r"|@experimental\b"
    r"|@sponsors\b"
)
VIDEO_TAG_PATTERN = re.compile(r"^\s*@video:(?P<path>[\w./-]+)\s*$")
DOCSTRING_TAG_HINTS = ("@deprecated:", "@version:", "@experimental", "@sponsors", "@video:")
SKIP_TAGS = {"code", "pre", "script", "style", "summary"}
SKIP_CLASSES = {"highlight"}


def on_page_markdown(
    markdown: str,
    *,
    page: Page,
    config: MkDocsConfig,  # noqa: ARG001
    files: Files,  # noqa: ARG001
) -> str:
    def replace(match: re.Match[str]) -> str:
        kind, raw_args = match.groups()
        rendered = _render_shortcode(kind.lower(), raw_args.strip(), page.url)
        return rendered or match.group(0)

    return SHORTCODE_PATTERN.sub(replace, markdown)


def on_page_content(
    html: str,
    *,
    page: Page,
    config: MkDocsConfig,  # noqa: ARG001
    files: Files,  # noqa: ARG001
) -> str:
    if not any(token in html for token in DOCSTRING_TAG_HINTS):
        return html

    soup = BeautifulSoup(html, "html.parser")

    for container in soup.select(".doc-contents"):
        _replace_block_videos(container, page.url)
        _replace_inline_tags(container, page.url)

    return str(soup)


def _render_shortcode(kind: str, args: str, page_url: str) -> str | None:
    if kind == "version":
        return _version_badge(args, page_url)
    if kind == "sponsors":
        return _sponsors_badge(page_url)
    if kind == "deprecated":
        return _deprecated_badge(args, page_url)
    if kind == "flag" and args == "experimental":
        return _experimental_badge(page_url)
    return None


def _replace_block_videos(container: Tag, page_url: str) -> None:
    for element in list(container.find_all(["p", "li"])):
        if _should_skip(element):
            continue
        if any(isinstance(child, Tag) for child in element.contents):
            continue

        match = VIDEO_TAG_PATTERN.fullmatch(element.get_text())
        if not match:
            continue

        _replace_node_with_html(element, _video_html(match.group("path"), page_url))


def _replace_inline_tags(container: Tag, page_url: str) -> None:
    for node in list(container.find_all(string=True)):
        if _should_skip(node):
            continue

        text = str(node)
        if not INLINE_TAG_PATTERN.search(text):
            continue

        rendered = _render_inline_text(text, page_url)
        if rendered == escape(text):
            continue

        _replace_node_with_html(node, rendered)


def _render_inline_text(text: str, page_url: str) -> str:
    parts: list[str] = []
    cursor = 0

    for match in INLINE_TAG_PATTERN.finditer(text):
        parts.append(escape(text[cursor:match.start()]))
        parts.append(_render_inline_tag(match, page_url))
        cursor = match.end()

    parts.append(escape(text[cursor:]))
    return "".join(parts)


def _render_inline_tag(match: re.Match[str], page_url: str) -> str:
    if version := match.group("deprecated"):
        return _deprecated_badge(version, page_url)
    if version := match.group("version"):
        return _version_badge(version, page_url)
    if match.group(0) == "@experimental":
        return _experimental_badge(page_url)
    return _sponsors_badge(page_url)


def _experimental_badge(page_url: str) -> str:
    return _badge_html(
        icon="material-flask-outline",
        title="Experimental",
        icon_target="conventions/#experimental",
        page_url=page_url,
    )


def _deprecated_badge(version: str, page_url: str) -> str:
    return _badge_html(
        icon="material-alert",
        title="Deprecated",
        icon_target="conventions/#deprecated",
        page_url=page_url,
        badge_type="deprecated",
        text=version,
        text_target=f"changelog/#{version}",
    )


def _version_badge(version: str, page_url: str) -> str:
    return _badge_html(
        icon="material-tag-outline",
        title="Minimum version",
        icon_target="conventions/#version",
        page_url=page_url,
        text=version,
        text_target=f"changelog/#{version}",
    )


def _sponsors_badge(page_url: str) -> str:
    return _badge_html(
        icon="material-heart",
        title="Sponsors only",
        icon_target="extras/",
        page_url=page_url,
        badge_type="heart",
    )


def _badge_html(
    *,
    icon: str,
    title: str,
    icon_target: str,
    page_url: str,
    badge_type: str = "",
    text: str = "",
    text_target: str = "",
) -> str:
    classes = "mdx-badge"
    if badge_type:
        classes = f"{classes} mdx-badge--{badge_type}"

    icon_href = _relative_url(icon_target, page_url)
    badge = [
        f'<span class="{classes}">',
        f'<span class="mdx-badge__icon">{_icon_link(icon, icon_href, title)}</span>',
    ]

    if text:
        text_html = escape(text)
        if text_target:
            href = escape(_relative_url(text_target, page_url), quote=True)
            text_html = f'<a href="{href}">{text_html}</a>'
        badge.append(f'<span class="mdx-badge__text">{text_html}</span>')

    badge.append("</span>")
    return "".join(badge)


def _video_html(path: str, page_url: str) -> str:
    href = escape(_relative_url(f"media/{path}.webm", page_url), quote=True)
    return (
        '<div class="centered-video">'
        '<video autoplay loop muted playsinline>'
        f'<source src="{href}" type="video/webm">'
        "</video>"
        "</div>"
    )


@lru_cache(maxsize=None)
def _icon_link(icon: str, href: str, title: str) -> str:
    return _render_markdown_fragment(f'[:{icon}:]({href} "{title}")')


@lru_cache(maxsize=None)
def _render_markdown_fragment(source: str) -> str:
    markdown = Markdown(
        extensions=["pymdownx.emoji"],
        extension_configs={
            "pymdownx.emoji": {
                "emoji_index": twemoji,
                "emoji_generator": to_svg,
            }
        },
    )
    rendered = markdown.convert(source).strip()
    if rendered.startswith("<p>") and rendered.endswith("</p>"):
        return rendered[3:-4]
    return rendered


def _relative_url(target: str, page_url: str) -> str:
    return get_relative_url(target, page_url or "")


def _replace_node_with_html(node: Tag | NavigableString, fragment: str) -> None:
    replacement = BeautifulSoup(fragment, "html.parser")
    for child in list(replacement.contents):
        node.insert_before(child.extract())
    node.extract()


def _should_skip(node: Tag | NavigableString) -> bool:
    parents = [node] if isinstance(node, Tag) else []
    parents.extend(node.parents)

    for parent in parents:
        if getattr(parent, "name", None) in SKIP_TAGS:
            return True

        classes = set(parent.get("class", [])) if isinstance(parent, Tag) else set()
        if classes & SKIP_CLASSES:
            return True
        if parent.name == "details" and "quote" in classes:
            return True

    return False
