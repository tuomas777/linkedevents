# flake8: noqa
"""
Django settings module for pytest
"""
from .settings import *


def dummy_haystack_connection_without_warnings_for_lang(language_code):
    return {
        f"default-{language_code}": {
            "ENGINE": "multilingual_haystack.backends.LanguageSearchEngine",
            "BASE_ENGINE": "multilingual_haystack.backends.SimpleEngineWithoutWarnings",
        }
    }


for language in [lang[0] for lang in LANGUAGES]:
    connection = dummy_haystack_connection_without_warnings_for_lang(language)
    HAYSTACK_CONNECTIONS.update(connection)
