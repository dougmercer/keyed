import re

from bs4 import BeautifulSoup


def on_post_page(html, page, config):
    """Post-process the HTML after it's been rendered."""
    if "api/easing/" not in page.url:
        return html

    soup = BeautifulSoup(html, "html.parser")

    # Look for all elements that might contain docstring content
    docstring_elements = soup.select(".doc-md-description, .doc-contents p, .doc-contents div")

    for element in docstring_elements:
        # Check if the element's text contains the @video: tag
        text = str(element)
        if "@video:" in text:
            # Use regex to find all @video: tags
            pattern = r"@video:(\w+)"

            # Function to replace tags with video HTML
            def replace_video_tag(match):
                video_name = match.group(1)
                return f"""<div class="centered-video">
    <video autoplay loop muted playsinline>
        <source src="../../media/easing/{video_name}.webm" type="video/webm">
    </video>
</div>"""

            # Replace the tags in the element's HTML
            new_html = re.sub(pattern, replace_video_tag, text)

            # If changes were made, update the element
            if new_html != text:
                # Need to replace the whole element
                new_soup = BeautifulSoup(new_html, "html.parser")
                element.replace_with(new_soup)

    # Return the modified HTML
    return str(soup)
