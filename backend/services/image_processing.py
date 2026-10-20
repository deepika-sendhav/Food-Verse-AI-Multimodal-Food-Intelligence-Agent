import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from backend.config import MAX_IMAGE_SIDE

MAX_IMAGE_PIXELS = 40_000_000


class InvalidImageError(Exception):
    pass


def preprocess_image(image_bytes: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as image:
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise InvalidImageError("Image dimensions exceed the safe pixel limit.")
                image.verify()

            with Image.open(BytesIO(image_bytes)) as opened_image:
                opened_image.load()
                with ImageOps.exif_transpose(opened_image) as oriented_image:
                    if "A" in oriented_image.getbands() or "transparency" in oriented_image.info:
                        with oriented_image.convert("RGBA") as rgba_image:
                            with Image.new(
                                "RGBA",
                                rgba_image.size,
                                (255, 255, 255, 255),
                            ) as background:
                                background.alpha_composite(rgba_image)
                                rgb_image = background.convert("RGB")
                    else:
                        rgb_image = oriented_image.convert("RGB")
                    try:
                        rgb_image.thumbnail(
                            (MAX_IMAGE_SIDE, MAX_IMAGE_SIDE),
                            Image.Resampling.LANCZOS,
                        )
                        output = BytesIO()
                        rgb_image.save(output, format="JPEG", quality=90, optimize=True)
                        return output.getvalue()
                    finally:
                        rgb_image.close()
    except InvalidImageError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        EOFError,
    ) as exc:
        raise InvalidImageError("Image data could not be decoded safely.") from exc
