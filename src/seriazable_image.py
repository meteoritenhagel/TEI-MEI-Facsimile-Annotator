import io
from PIL import Image

class SerializableImage(Image.Image):
    def to_bytestring(self) -> bytes:
        """
        Teturns a bytestring of the image's compressed contents.
        :return: Bytestring representation of the image.
        """
        byte_io = io.BytesIO()
        self.save(byte_io, format=self.format, quality=60)
        byte_io.seek(0)
        return byte_io.read()

    @classmethod
    def from_bytestring(cls, bytestring: bytes) -> Image.Image:
        """
        Given a bytestring of an image file, returns a PIL Image object.
        :param bytestring: Bytestring of an image file.
        :return: PIL Image object.
        """
        byte_io = io.BytesIO(bytestring)
        byte_io.seek(0)
        image = Image.open(byte_io)
        image.load()
        return image