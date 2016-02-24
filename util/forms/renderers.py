from bootstrap3.renderers import FieldRenderer
from bootstrap3.text import text_value


class ChameleonFieldRenderer(FieldRenderer):

    def append_to_field(self, html):
        html = '<span class="help-block">{help}</span>'.format(help=self.field.help_text) + html
        return html
