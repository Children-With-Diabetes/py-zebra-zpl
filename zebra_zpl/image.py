import string
import PIL.Image

from .printable import Printable


class _ImageHandler:
    """Convert PIL images to ZPL

    Based on Java example from:
    http://www.jcgonzalez.com/java-image-to-zpl-example
    """

    def __init__(self, image: PIL.Image):
        self._i = image.convert('L')

    @staticmethod
    def _image_compression_char(multiplier: int) -> str:
        alpha = string.ascii_uppercase[6:-1]
        if (multiplier - 1) in range(len(alpha)):
            return alpha[multiplier - 1]
        if multiplier >= 20 and multiplier <= 400:
            multi = multiplier // 20
            return string.ascii_lowercase[6:][multi-1]
        return ''

    @staticmethod
    def binary_to_hex_str(data: str) -> str:
        if len(data) < 8:
            data += '0'*(8-len(data))
        return '{:02X}'.format(int(data, 2))

    def _process_pixel_row(self, y: int) -> str:
        out = ''
        accumulate = ''
        for x in range(self._i.width):
            p = self._i.getpixel((x, y))
            color = '0' if p == 255 else '1'
            accumulate += str(int(color))
            if len(accumulate) == 8:
                out += self.binary_to_hex_str(accumulate)
                accumulate = ''
        if accumulate:
            out += self.binary_to_hex_str(accumulate)
        return f'{out}\n'

    @property
    def row_bytes(self):
        width_bytes = int(self._i.width / 8)
        if self._i.width % 8 > 0:
            width_bytes += 1
        return width_bytes

    @property
    def total_bytes(self):
        return self._i.height * self.row_bytes

    def _image_to_binary(self):
        return ''.join([self._process_pixel_row(y) for y in range(self._i.height)])

    def get_zpl_image_data(self):
        maxlinea = self.row_bytes * 2
        code = ''
        linea = ''
        previous_line = ''
        counter = 1
        o = self._image_to_binary()
        aux = o[0]
        first_char = False
        for c in o:
            if first_char:
                aux = c
                first_char = False
                continue
            if c == '\n':
                if counter >= maxlinea and aux == '0':
                    linea += ','
                elif counter >= maxlinea and aux == 'F':
                    linea += '!'
                elif counter > 20:
                    multi20 = int((counter/20)*20)
                    resto20 = counter % 20
                    linea += self._image_compression_char(multi20)
                    if resto20:
                        linea += self._image_compression_char(resto20)
                    linea += aux
                else:
                    linea += self._image_compression_char(counter) + aux
                counter = 1
                first_char = True
                if linea == previous_line:
                    code += ":"
                else:
                    code += linea
                previous_line = linea
                linea = ''
                continue
            if aux == c:
                counter += 1
            else:
                if counter >= 20:
                    multi20 = int((counter/20)*20)
                    resto20 = counter % 20
                    linea += self._image_compression_char(multi20)
                    if resto20:
                        linea += self._image_compression_char(resto20)
                    linea += aux
                else:
                    linea += self._image_compression_char(counter) + aux
                counter = 1
                aux = c
        return code


class Image(Printable):
    def __init__(self, image: PIL.Image, **kwargs):
        self._data = None
        self._i = _ImageHandler(image)
        super().__init__(data=self.img_data, **kwargs)

    @property
    def img_data(self):
        if self._data is None:
            self._data = self._i.get_zpl_image_data()
        return self._data

    def to_zpl(self):
        data_len = len(self.img_data)
        i = self._i
        zpl = f'^FO{self.x},{self.y}'
        zpl += f'^GFA,{data_len},{i.total_bytes},{i.row_bytes}, {self.img_data}'
        return zpl
