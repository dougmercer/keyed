"""Extension for processing custom documentation tags in docstrings."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from griffe import Docstring, Extension

if TYPE_CHECKING:
    from griffe.dataclasses import Attribute, Function, Module, Object


def process_docstring(docstring: str) -> str:
    """
    Process the docstring to replace custom tags with HTML.
    """
    if not docstring:
        return docstring
    
    # Process @experimental tag
    if "@experimental" in docstring:
        experimental_html = (
            '<span class="mdx-badge">'
            '<span class="mdx-badge__icon">'
            '[:material-flask-outline:](/keyed/conventions#experimental "Experimental")'
            '</span>'
            '</span>'
        )
        docstring = docstring.replace("@experimental", experimental_html)
    
    # Process @sponsors tag
    if "@sponsors" in docstring:
        sponsors_html = (
            '<span class="mdx-badge mdx-badge--heart">'
            '<span class="mdx-badge__icon">'
            '[:material-heart:](/keyed/extras/ "Sponsors only")'
            '</span>'
            '</span>'
        )
        docstring = docstring.replace("@sponsors", sponsors_html)
    
    # Process @version: x.y.z tag
    version_pattern = r"@version: ([\d.]+)"
    if re.search(version_pattern, docstring):
        def version_replacement(match):
            version = match.group(1)
            return (
                '<span class="mdx-badge">'
                '<span class="mdx-badge__icon">'
                '[:material-tag-outline:](/keyed/conventions#version "Minimum version")'
                '</span>'
                f'<span class="mdx-badge__text">[{version}](/keyed/changelog#{version})</span>'
                '</span>'
            )
        docstring = re.sub(version_pattern, version_replacement, docstring)
    
    # Process @video: tag
    video_pattern = r"@video:([\w/\-\.]+)"
    if re.search(video_pattern, docstring):
        def video_replacement(match):
            video_name = match.group(1)
            return (
                '<div class="centered-video">'
                '<video autoplay loop muted playsinline>'
                f'<source src="../../media/{video_name}.webm" type="video/webm">'
                '</video>'
                '</div>'
            )
        docstring = re.sub(video_pattern, video_replacement, docstring)
    
    return docstring


class CustomTagsExtension(Extension):
    """Griffe extension that processes custom tags in docstrings."""

    def __init__(self) -> None:
        self._handled: set[str] = set()

    def _handle_object_docstring(self, obj: Object) -> None:
        """Process an object's docstring if it has one."""
        if obj.path in self._handled or not obj.docstring:
            return
        
        self._handled.add(obj.path)
        obj.docstring.value = process_docstring(obj.docstring.value)

    def _process_recursively(self, obj: Object) -> None:
        """Process an object and all its members recursively."""
        if obj.is_alias:
            return
            
        self._handle_object_docstring(obj)
        
        if obj.is_module or obj.is_class:
            for member in obj.members.values():
                self._process_recursively(member)

    def on_package_loaded(
        self,
        *,
        pkg: Module,
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """Process all docstrings in the package after it's loaded."""
        self._process_recursively(pkg)

    def on_function_instance(
        self,
        *,
        func: Function,
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """Process function docstrings."""
        self._handle_object_docstring(func)

    def on_attribute_instance(
        self,
        *,
        attr: Attribute,
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """Process attribute docstrings."""
        self._handle_object_docstring(attr)
