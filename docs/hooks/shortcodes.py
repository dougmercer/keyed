from __future__ import annotations

import posixpath
import re

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page
from re import Match

def on_page_markdown(
    markdown: str, *, page: Page, config: MkDocsConfig, files: Files
):
    # Replace callback
    def replace(match: Match):
        type, args = match.groups()
        args = args.strip()
        if type == "version":
            return _badge_for_version(args, page, files)
        elif type == "sponsors":
            return _badge_for_sponsors(page, files)
        elif type == "flag":
            if args == "experimental":
                return _badge_for_experimental(page, files)
            # Add more flag types as needed
        return match.group(0)  # Return unchanged if not recognized

    # Find and replace all shortcodes in current page
    return re.sub(
        r"<!-- md:(\w+)(.*?) -->",
        replace, markdown, flags = re.I | re.M
    )

# Create badge
def _badge(icon: str, text: str = "", type: str = ""):
    classes = f"mdx-badge mdx-badge--{type}" if type else "mdx-badge"
    return "".join([
        f"<span class=\"{classes}\">",
        *([f"<span class=\"mdx-badge__icon\">{icon}</span>"] if icon else []),
        *([f"<span class=\"mdx-badge__text\">{text}</span>"] if text else []),
        f"</span>",
    ])

# Safe path resolution that handles missing files
def _safe_resolve_path(path: str, page: Page, files: Files):
    path, anchor, *_ = f"{path}#".split("#")
    file = files.get_file_from_path(path)
    
    # Return a simple link if file doesn't exist
    if not file:
        return f"{path}#{anchor}" if anchor else path
    
    # Otherwise, resolve the path relative to the current page
    rel_path = posixpath.relpath(file.src_uri, page.file.src_uri)
    # Remove the initial "../" if present
    parts = rel_path.split(posixpath.sep)
    if parts and parts[0] == "..":
        parts = parts[1:]
    rel_path = posixpath.sep.join(parts)
    
    return f"{rel_path}#{anchor}" if anchor else rel_path

# Create badge for experimental flag
def _badge_for_experimental(page: Page, files: Files):
    icon = "material-flask-outline"
    href = _safe_resolve_path("conventions.md#experimental", page, files)
    return _badge(
        icon = f"[:{icon}:]({href} 'Experimental')"
    )

# Create badge for version
def _badge_for_version(text: str, page: Page, files: Files):
    spec = text
    path = f"changelog/index.md#{spec}"

    # Return badge
    icon = "material-tag-outline"
    href = _safe_resolve_path("conventions.md#version", page, files)
    
    # For the text part, we'll make a simpler implementation
    version_link = _safe_resolve_path(path, page, files)
    text_part = f"[{text}]({version_link})" if spec else ""
    
    return _badge(
        icon = f"[:{icon}:]({href} 'Minimum version')",
        text = text_part
    )

def _badge_for_sponsors(page: Page, files: Files):
    icon = "material-heart"
    href = _safe_resolve_path("extras/index.md", page, files)
    return _badge(
        icon = f"[:{icon}:]({href} 'Sponsors only')",
        type = "heart"
    )
