"""Profile pictures.

Uploaded images are decoded and re-encoded rather than stored as they arrive.
Two reasons, both worth stating plainly.

A photo taken on a phone carries EXIF, and EXIF routinely carries the exact
coordinates where it was taken. Storing the original and serving it back means
publishing someone's home address alongside their face. Re-encoding drops every
metadata block, because Pillow only writes what it is asked to write.

And decoding is the only real check that a file is an image at all. A content
type is a string the client chose, and magic bytes are four characters anyone
can prepend. If Pillow cannot open it, it is not a picture, whatever it says.
"""

import io
import uuid
from typing import IO

from PIL import Image, UnidentifiedImageError

#: Square, and small. A header avatar renders at 36 CSS pixels; 256 covers a
#: retina display at four times that and keeps the stored file in single-digit
#: kilobytes, which matters when it is base64'd into a JSON response.
SIZE = 256

#: WebP at this quality is visually indistinguishable from the original at this
#: size and roughly a third of the equivalent JPEG.
QUALITY = 82

CONTENT_TYPE = "image/webp"

#: What a browser file picker will offer for `image/*`, minus the formats that
#: are more attack surface than they are worth. No SVG: it is a document that
#: can contain script, and serving one back from our own origin is a stored
#: cross-site scripting hole rather than a picture.
ALLOWED_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})

#: Before decoding. Generous for a photo, and the point is to stop something
#: enormous being decompressed rather than to police quality.
MAX_BYTES = 5 * 1024 * 1024

#: A 10,000 by 10,000 PNG is a few hundred kilobytes on disk and around a
#: gigabyte once decoded. Pillow calls that a decompression bomb, and refusing
#: it before allocating is the only defence.
MAX_PIXELS = 50_000_000


class InvalidAvatar(Exception):
    """Rejected before anything was stored."""


def storage_key(user_id: uuid.UUID) -> str:
    """A new key per upload.

    Reusing one key would leave the old picture in any cache that had it, and
    the replacement would not show up until that expired.
    """
    return f"avatars/{user_id}/{uuid.uuid4().hex}.webp"


def normalise(source: IO[bytes], content_type: str | None) -> bytes:
    """A square 256px WebP, or InvalidAvatar."""
    declared = (content_type or "").split(";")[0].strip().lower()
    if declared not in ALLOWED_TYPES:
        raise InvalidAvatar("Upload a JPEG, PNG, WebP or GIF image.")

    raw = source.read(MAX_BYTES + 1)
    if not raw:
        raise InvalidAvatar("That file is empty.")
    if len(raw) > MAX_BYTES:
        raise InvalidAvatar(f"That image is larger than the {MAX_BYTES // (1024 * 1024)} MB limit.")

    try:
        with Image.open(io.BytesIO(raw)) as image:
            width, height = image.size
            if width * height > MAX_PIXELS:
                raise InvalidAvatar("That image has too many pixels to process.")

            # Animated GIFs and WebPs open on their first frame, which is what
            # we want — an animated avatar is not worth the bytes.
            image.load()
            square = _centre_crop(image)
            return _encode(square)
    except InvalidAvatar:
        raise
    except UnidentifiedImageError as exc:
        raise InvalidAvatar("That file is not an image we can read.") from exc
    except (OSError, ValueError) as exc:
        # A truncated or malformed file lands here. The message stays vague
        # because the details are Pillow's, not anything a user can act on.
        raise InvalidAvatar("That image could not be processed.") from exc


def _centre_crop(image: Image.Image) -> Image.Image:
    """Square from the middle, then scale.

    Squashing a portrait into a square is the obvious shortcut and it makes
    every face look wrong. Cropping to the centre keeps the proportions, and
    the centre is where the subject of a profile picture almost always is.
    """
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2

    cropped = image.crop((left, top, left + side, top + side))
    return cropped.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def _encode(image: Image.Image) -> bytes:
    """Flatten onto white and write WebP.

    A PNG with transparency would otherwise keep its alpha channel, and a
    cut-out avatar rendered on a dark background shows whatever is behind it.
    """
    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        flattened = Image.new("RGB", rgba.size, (255, 255, 255))
        flattened.paste(rgba, mask=rgba.split()[-1])
        image = flattened
    elif image.mode != "RGB":
        image = image.convert("RGB")

    buffer = io.BytesIO()
    # No exif/icc argument: whatever the original carried is simply not written.
    image.save(buffer, format="WEBP", quality=QUALITY, method=4)
    return buffer.getvalue()
