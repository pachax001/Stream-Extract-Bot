# script.py

class Script:
    """Holds all bot message templates and formatters."""

    _START_TEMPLATE = (
        "<b>Hello {user},\n\n"
        "I can extract audio and subtitles from video files.\n\n"
        "Send me any video file and extract what you want :).  \n\n"
        "See <i>help</i> for more details.\n\n"
        "© @gunaya001</b>"
    )

    _HELP_TEMPLATE = (
        "<b>Hi, Follow these Steps…</b>\n\n"
        "🌀 <i>Send me any valid video file.</i>\n"
        "🌀 <i>Click Download and Process to download the file to my server.</i>\n"
        "🌀 <i>Wait while I process the video!</i>\n"
        "🌀 <i>Select the stream(s) you want to extract.</i>\n\n"
        "© @gunaya001"
    )

    _ABOUT_TEMPLATE = (
        "⭕️<b>My Name:</b> Stream Extract Bot\n\n"
        "⭕️<b>Creator:</b> @hellohoneybuny\n"
        "⭕️<b>Modified by:</b> @gunaya001\n"
        "⭕️<b>Language:</b> <code>Python 3</code>\n"
        "⭕️<b>Library:</b> <a href='https://wzgram.com/'>WZGram</a>"
    )

    @classmethod
    def start_msg(cls, user_name: str) -> str:
        """Return the /start message personalized for a user."""
        return cls._START_TEMPLATE.format(user=user_name)

    @classmethod
    def help_msg(cls) -> str:
        """Return the /help message."""
        return cls._HELP_TEMPLATE

    @classmethod
    def about_msg(cls) -> str:
        """Return the /about message."""
        return cls._ABOUT_TEMPLATE
