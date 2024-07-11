from .constants import EXTRAS_INSTALLED

if EXTRAS_INSTALLED:
    from keyed_extras import *  # noqa: F401,F403
else:

    def post_process_tokens(code, tokens, filename):
        """This function intentionally does nothing."""
        return tokens

    from .context import ContextWrapper as FreeHandContext  # noqa: F401


del EXTRAS_INSTALLED
