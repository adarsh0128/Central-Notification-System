import logging
from app.models.user_preference import UserPreference
from app.schemas.notification import ChannelEnum

logger = logging.getLogger(__name__)

class PreferenceService:
    def filter_channels(
        self, user_pref: UserPreference | None, requested_channels: list[ChannelEnum] | None
    ) -> list[ChannelEnum]:
        """Filters requested channels based on the user's preference opt-in/opt-out status.
        
        - If requested_channels is None, returns all channels enabled in preferences.
        - If a requested channel is disabled in preferences, logs it and skips it.
        - If no preferences exist, defaults all channels (EMAIL, SMS, PUSH) to True (opted-in).
        """
        # Determine enabled channels
        email_ok = user_pref.email_enabled if user_pref else True
        sms_ok = user_pref.sms_enabled if user_pref else True
        push_ok = user_pref.push_enabled if user_pref else True

        pref_map = {
            ChannelEnum.EMAIL: email_ok,
            ChannelEnum.SMS: sms_ok,
            ChannelEnum.PUSH: push_ok,
        }

        # Resolve target channels
        if not requested_channels:
            targets = [chan for chan, ok in pref_map.items() if ok]
            if not targets:
                logger.info("User has opted out of all channels. Silently skipping delivery.")
            return targets

        filtered_channels = []
        for chan in requested_channels:
            if pref_map.get(chan, True):
                filtered_channels.append(chan)
            else:
                # Log silent skip per functional requirements
                logger.info(
                    f"Silently skipping notification delivery on {chan.value} channel: user has opted out.",
                    extra={"channel": chan.value}
                )

        return filtered_channels
