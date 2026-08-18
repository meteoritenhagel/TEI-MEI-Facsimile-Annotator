import io

from PIL import Image, ImageEnhance


def apply_image_properties(img: bytes, brightness: float, contrast: float, saturation: float) -> bytes:
    """
    Apply the brightness, contrast and saturation parameters to the image given as a sequence of bytes.

    :param img: Input image.
    :param brightness: Brightness value.
    :param contrast: Contrast value.
    :param saturation: Saturation value.
    :return: Image with properties applied.
    """
    img = Image.open(io.BytesIO(img)).convert("RGB")

    # Apply image settings
    # brightness
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(brightness)

    # contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)

    # saturation
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(saturation)

    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()