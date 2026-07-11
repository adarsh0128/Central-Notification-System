from app.services.preference import PreferenceService
from app.models.user_preference import UserPreference
from app.schemas.notification import ChannelEnum

def test_preference_filtering_no_preferences_defaults_to_all() -> None:
    service = PreferenceService()
    channels = [ChannelEnum.EMAIL, ChannelEnum.SMS, ChannelEnum.PUSH]
    
    result = service.filter_channels(None, channels)
    assert result == channels

def test_preference_filtering_respects_opt_out() -> None:
    service = PreferenceService()
    user_pref = UserPreference(
        user_id="user123",
        email_enabled=True,
        sms_enabled=False,  # Opted out of SMS
        push_enabled=True,
    )
    
    requested = [ChannelEnum.EMAIL, ChannelEnum.SMS, ChannelEnum.PUSH]
    result = service.filter_channels(user_pref, requested)
    assert result == [ChannelEnum.EMAIL, ChannelEnum.PUSH]

def test_preference_filtering_resolves_all_opted_in() -> None:
    service = PreferenceService()
    user_pref = UserPreference(
        user_id="user123",
        email_enabled=True,
        sms_enabled=False,
        push_enabled=True,
    )
    
    # requested channels is None => defaults to all opted-in
    result = service.filter_channels(user_pref, None)
    assert result == [ChannelEnum.EMAIL, ChannelEnum.PUSH]

def test_preference_filtering_all_disabled() -> None:
    service = PreferenceService()
    user_pref = UserPreference(
        user_id="user123",
        email_enabled=False,
        sms_enabled=False,
        push_enabled=False,
    )
    
    result = service.filter_channels(user_pref, [ChannelEnum.EMAIL, ChannelEnum.SMS])
    assert result == []
