from datetime import datetime

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout


class ProgressPopup(Popup):
    def __init__(self, *args, **kwargs):
        self._started = None
        self.auto_dismiss = False
        kwargs['content'], content = None, kwargs['content']
        kwargs['content'] = self.setup_contents(content)
        super(self.__class__, self).__init__(*args, **kwargs)

    def setup_contents(self, msg):
        content = GridLayout(cols=1, rows=2)

        self.exit = Button(text='OK')
        self.exit.bind(on_press=self.dismiss)

        self.cancel = Button(text='Cancel')

        text = Label(text=msg, id='popup_content')
        content.add_widget(text)
        return content

    def set_cancel(self, fn):
        self.cancel.bind(on_press=fn)
        self.content.add_widget(self.cancel)

    def show_exit(self):
        if self.cancel in self.content.children:
            self.content.remove_widget(self.cancel)
        self.content.add_widget(self.exit)

    def show_msg(self, msg, title=None):
        self.content.text = msg
        if title:
            self.title = title

    def update_msg(self, transferred, total=None):
        mb_transferred = transferred / 1024 / 1024
        unit = 'MB'
        if total:
            progressed = (transferred / float(total)) * 100
            unit = '%'
        else:
            progressed = mb_transferred

        if not self._started:
            self._started = datetime.now()

        avg_speed = mb_transferred / (datetime.now() - self._started
                                      ).total_seconds()

        for child in self.content.children:
            if child.id == 'popup_content':
                child.text = ('Transferred: {0:.2f}{1}. '
                              'Avg Speed: {2:.2f}MB/s').format(
                    progressed, unit, avg_speed)
