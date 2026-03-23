from aiogram.fsm.state import State, StatesGroup


class UserFlow(StatesGroup):
    after_start = State()
    after_lesson = State()
    city_choice = State()
    product_selected = State()
    payment_method = State()
    waiting_receipt = State()
    payment_sent = State()
