import io
from PIL import Image

class SerializableImage:
    def __init__(self, image: Image.Image):
        self.image = image

    def to_bytestring(self) -> bytes:
        """
        Returns a bytestring of the image's compressed contents.
        :return: Bytestring representation of the image.
        """
        byte_io = io.BytesIO()
        self.image.save(byte_io, format=self.image.format if self.image.format is not None else "PNG", quality=60)
        byte_io.seek(0)
        return byte_io.read()

    @classmethod
    def from_bytestring(cls, bytestring: bytes) -> SerializableImage:
        """
        Given a bytestring of an image file, returns a PIL Image object.
        :param bytestring: Bytestring of an image file.
        :return: PIL Image object.
        """
        byte_io = io.BytesIO(bytestring)
        byte_io.seek(0)
        image = Image.open(byte_io)
        image.load()
        return cls(image)