"""Print text a word at a time, at roughly the pace it would be spoken.

Used in place of speech when audio output is off, so that replies take about
as long to appear as they would take to say:

    from output.paced_print import print_at_speech_speed

    print_at_speech_speed("Good evening. Shall I put the kettle on?")
"""
import re
import sys
import time

# About 150 words a minute, counted in characters so that long words take longer than short ones
SECONDS_PER_CHARACTER = 0.085
SENTENCE_PAUSE_SECONDS = 0.35
CLAUSE_PAUSE_SECONDS = 0.15


def print_at_speech_speed(text: str):
    """
    Print the text followed by a newline, blocking until the last word is out.
    """
    # Each piece is a word with the whitespace after it, so line breaks in the text are kept
    for piece in re.findall(r"\S+\s*", text):
        sys.stdout.write(piece)
        sys.stdout.flush()

        word = piece.strip()
        pause = len(word) * SECONDS_PER_CHARACTER
        if word.endswith((".", "!", "?", ":")):
            pause += SENTENCE_PAUSE_SECONDS
        elif word.endswith((",", ";")):
            pause += CLAUSE_PAUSE_SECONDS
        time.sleep(pause)

    sys.stdout.write("\n")
    sys.stdout.flush()
