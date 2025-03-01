from .constants import EXTRAS_INSTALLED

if EXTRAS_INSTALLED:
    from keyed_extras import *  # noqa: F403  # type: ignore
else:

    def post_process_tokens(code, tokens, filename):
        """This function intentionally does nothing."""
        return tokens

    class Editor:
        def find(self, x, y, frame) -> tuple[None, float]:
            return None, float("inf")

    from .context import ContextWrapper as FreeHandContext  # noqa: F401


del EXTRAS_INSTALLED
