import io
import re
from utilities.GeneralUtilities import IS_MACOS, IS_WIN
import os
import subprocess
from gtts import gTTS

try:
    from pydub import AudioSegment, playback

    # patch pydup - hide std output
    FNULL = open(os.devnull, 'w')
    _subprocess_call = playback.subprocess.call
    playback.subprocess.call = lambda cmd: _subprocess_call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)


    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False




if IS_MACOS:
    from os import system
else:
    import pyttsx3


def create_voice(self, gtts_status, rate=180, elevenlabs_status=False):
    """
    Checks that status of the online engines, and calls the correct speech engine
    :param rate: Speech rate for the engine (if supported by the OS)
    :param elevenlabs_status: use ElevenLabs (needs ELEVENLABS_API_KEY)
    """

    if PYDUB_AVAILABLE and elevenlabs_status is True:
        try:
            return VoiceElevenLabs()
        except Exception as e:
            print("ElevenLabs voice unavailable ({}); using another engine.".format(e))

    if PYDUB_AVAILABLE and gtts_status is True:
        return VoiceGTTS()
    else:
        if IS_MACOS:
            return VoiceMac()
        elif IS_WIN:
            return VoiceWin(rate)
        else:
            try:
                return VoiceLinux(rate)
            except OSError:
                return VoiceNotSupported()


def remove_ansi_escape_seq(text):
    """
    This method removes ANSI escape sequences (such as a colorama color
    code) from a string so that they aren't spoken.
    :param text: The text that may contain ANSI escape sequences.
    :return: The text with ANSI escape sequences removed.
    """
    if text:
        text = re.sub(r'''(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]''', '', text)
    return text


# class Voice:
#     """
#     ABOUT: This class is the Voice of Jarvis.
#         The methods included in this class
#         generate audio output of Jarvis while
#         interacting with the user.
#     DOCUMENTATION on pyttsx3:
#         https://pyttsx3.readthedocs.io/en/latest/
#     """

class VoiceGTTS():
    def text_to_speech(self, speech):
        speech = remove_ansi_escape_seq(speech)
        tts = gTTS(speech, lang="en")
        tts.save("voice.mp3")
        audio = AudioSegment.from_mp3('voice.mp3')
        playback.play(audio)
        os.remove("voice.mp3")


class VoiceElevenLabs():
    """
    Text to speech through the ElevenLabs API.
    The API key is read from the ELEVENLABS_API_KEY environment variable.
    Voice and model can be overridden with ELEVENLABS_VOICE_ID and
    ELEVENLABS_MODEL_ID.
    """
    DEFAULT_VOICE_ID = "NOpBlnGInO9m6vDvFkFC"
    DEFAULT_MODEL_ID = "eleven_v4"

    def __init__(self):
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY is not set")
        from elevenlabs.client import ElevenLabs
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", self.DEFAULT_VOICE_ID)
        self.model_id = os.getenv("ELEVENLABS_MODEL_ID", self.DEFAULT_MODEL_ID)
        self.elevenlabs = ElevenLabs(api_key=api_key)

    def text_to_speech(self, speech):
        speech = remove_ansi_escape_seq(speech)
        if not speech or not speech.strip():
            return
        try:
            audio = self.elevenlabs.text_to_speech.convert(
                voice_id=self.voice_id,
                text=speech,
                model_id=self.model_id,
                language_code="en",
            )
            data = b"".join(audio)
            playback.play(AudioSegment.from_file(io.BytesIO(data), format="mp3"))
        except Exception as e:
            status = getattr(e, "status_code", None)
            body = getattr(e, "body", None)
            detail = ""
            if isinstance(body, dict):
                d = body.get("detail", body)
                detail = d.get("message", "") if isinstance(d, dict) else str(d)
            if status == 401:
                print("ElevenLabs error: invalid API key. Check ELEVENLABS_API_KEY, "
                      "or type 'disable elevenlabs'.")
            elif status:
                print("ElevenLabs error {}: {}".format(status, detail or "request failed"))
            else:
                print("ElevenLabs error: {}".format(e))


class VoiceMac():
    def text_to_speech(self, speech):
        speech = remove_ansi_escape_seq(speech)
        speech = speech.replace("'", "\\'")
        system('say $\'{}\''.format(speech))


class Voice_general():
    def __init__(self, rate):
        self.rate = rate
        self.min_rate = 50
        self.max_rate = 500
        self.create()

    def create(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', self.rate)

    def destroy(self):
        """
        Destroys a pyttsx3 object in order
        to create a new one in the next interaction.
        """
        del self.engine


class VoiceLinux(Voice_general):
    def __init__(self, rate):
        super().__init__(rate)

    def text_to_speech(self, speech):
        """
        :param speech: The text we want Jarvis to generate as audio
        :return: Nothing to return.
        A bug in pyttsx3 causes segfault if speech is '', so used 'if' to avoid that.
        Instability in the pyttsx3 engine can cause problems if the engine is
        not created and destroyed every time it is used.
        """
        if speech != '':
            speech = remove_ansi_escape_seq(speech)
            self.create()
            self.engine.say(speech)
            self.engine.runAndWait()
            self.destroy()

    def change_rate(self, delta):
        """
        Changes the speech rate which is used to set the speech
        engine rate. Restrict the rate to a usable range.
        :param delta: The amount to modify the rate from the current rate.
        Note: The actual engine rate is set by create().
        """
        if self.rate + delta > self.max_rate:
            self.rate = self.max_rate
        elif self.rate + delta < self.min_rate:
            self.rate = self.min_rate
        else:
            self.rate = self.rate + delta


class VoiceWin():

    def __init__(self, rate):
        self.rate = rate
        self.min_rate = 50
        self.max_rate = 500
        self.create()

    def create(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', self.rate)

    def destroy(self):
        """
        This method destroys a pyttsx3 object in order
        to create a new one in the next interaction.
        :return: Nothing to return.
        """
        del self.engine

    def text_to_speech(self, speech):
        """
        This method converts a text to speech.
        :param speech: The text we want Jarvis to generate as audio
        :return: Nothing to return.

        Instability in the pyttsx3 engine can cause problems if the engine is
        not created and destroyed every time it is used.
        """
        speech = remove_ansi_escape_seq(speech)
        self.create()
        self.engine.setProperty('rate', 170)  # setting up new voice rate
        voices = self.engine.getProperty('voices')  # getting details of current voice
        self.engine.setProperty('voices', voices[1].id)  # changing index, changes voices. 1 for female
        self.engine.say(speech)
        self.engine.runAndWait()
        self.destroy()

    def change_rate(self, delta):
        """
        This method changes the speech rate which is used to set the speech
        engine rate. Restrict the rate to a usable range.
        :param delta: The amount to modify the rate from the current rate.

        Note: The actual engine rate is set by create().
        """
        if self.rate + delta > self.max_rate:
            self.rate = self.max_rate
        elif self.rate + delta < self.min_rate:
            self.rate = self.min_rate
        else:
            self.rate = self.rate + delta


class VoiceNotSupported():
    def __init__(self):
        self.warning_print = False

    def text_to_speech(self, speech):
        if not self.warning_print:
            print(
                "Speech not supported! Please install pyttsx3 text-to-speech engine (sapi5, nsss or espeak)")
            self.warning_print = True
