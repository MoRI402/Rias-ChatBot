# Note: chat_id's are stored as strings because the int is too large to be stored in a PSQL database.
import threading

from sqlalchemy import Column, String, Boolean, UnicodeText, Integer

from tg_bot.modules.sql import SESSION, BASE


class Notes(BASE):
    __tablename__ = "notes"
    chat_id = Column(String(14), primary_key=True)
    name = Column(UnicodeText, primary_key=True)
    value = Column(UnicodeText, nullable=False)
    is_reply = Column(Boolean, default=False)
    has_buttons = Column(Boolean, default=False)

    def __init__(self, chat_id, name, value, is_reply=False, has_buttons=False):
        self.chat_id = str(chat_id)  # ensure string
        self.name = name
        self.value = value
        self.is_reply = is_reply
        self.has_buttons = has_buttons

    def __repr__(self):
        return "<Note %s>" % self.name


class Buttons(BASE):
    __tablename__ = "note_urls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(14), primary_key=True)
    note_name = Column(UnicodeText, primary_key=True)
    name = Column(UnicodeText, nullable=False)
    url = Column(UnicodeText, nullable=False)

    def __init__(self, chat_id, note_name, name, url):
        self.chat_id = str(chat_id)
        self.note_name = note_name
        self.name = name
        self.url = url


Notes.__table__.create(checkfirst=True)
Buttons.__table__.create(checkfirst=True)

NOTES_INSERTION_LOCK = threading.Lock()
BUTTONS_INSERTION_LOCK = threading.Lock()


def add_note_to_db(chat_id, note_name, note_data, is_reply=False, has_buttons=False):
    with NOTES_INSERTION_LOCK:
        prev = SESSION.query(Notes).get((str(chat_id), note_name))
        if prev:
            with BUTTONS_INSERTION_LOCK:
                prev_buttons = SESSION.query(Buttons).filter(Buttons.chat_id == str(chat_id),
                                                             Buttons.note_name == note_name).all()
                for b in prev_buttons:
                    SESSION.delete(b)
            SESSION.delete(prev)
        note = Notes(str(chat_id), note_name, note_data, is_reply=is_reply, has_buttons=has_buttons)

        SESSION.add(note)
        SESSION.commit()


def get_note(chat_id, note_name):
    return SESSION.query(Notes).get((str(chat_id), note_name))


def rm_note(chat_id, note_name):
    with NOTES_INSERTION_LOCK:
        note = SESSION.query(Notes).get((str(chat_id), note_name))
        if note:
            with BUTTONS_INSERTION_LOCK:
                buttons = SESSION.query(Buttons).filter(Buttons.chat_id == str(chat_id),
                                                        Buttons.note_name == note_name).all()
                for b in buttons:
                    SESSION.delete(b)
            SESSION.delete(note)
            SESSION.commit()
            return True
        else:
            return False


def get_all_chat_notes(chat_id):
    return SESSION.query(Notes).filter(Notes.chat_id == str(chat_id)).all()


def add_note_button_to_db(chat_id, note_name, b_name, url):
    with BUTTONS_INSERTION_LOCK:
        button = Buttons(chat_id, note_name, b_name, url)
        SESSION.add(button)
        SESSION.commit()


def get_buttons(chat_id, note_name):
    return SESSION.query(Buttons).filter(Buttons.chat_id == str(chat_id), Buttons.note_name == note_name).all()


def migrate_chat(old_chat_id, new_chat_id):
    with NOTES_INSERTION_LOCK:
        chat_notes = SESSION.query(Notes).filter(Notes.chat_id == str(old_chat_id)).all()
        for note in chat_notes:
            note.chat_id = str(new_chat_id)

        # TODO: test this more
        # with BUTTONS_INSERTION_LOCK:
        #     chat_buttons = SESSION.query(Buttons).filter(Buttons.chat_id == str(old_chat_id)).all()
        #     for b in chat_buttons:
        #         b.chat_id = str(new_chat_id)

        SESSION.commit()