import pytest
from pydantic import ValidationError

from backend.core.config import Settings


def test_settings_allows_missing_resend_key_in_development():
    Settings(environment="development", resend_api_key=None)


def test_settings_allows_missing_resend_key_in_test():
    Settings(environment="test", resend_api_key=None)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_settings_rejects_missing_resend_key_outside_dev(environment):
    with pytest.raises(ValidationError, match="RESEND_API_KEY must be set"):
        Settings(environment=environment, resend_api_key=None)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_settings_allows_configured_resend_key_outside_dev(environment):
    Settings(environment=environment, resend_api_key="re_test_key")
