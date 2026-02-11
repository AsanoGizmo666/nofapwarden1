import random

RELAPSE_TEXTS = [
    "Рекорд: {days} дней. Почти начал становиться человеком.",
    "{days} дней держался. Организм поверил. Зря.",
    "Вот это талант — дойти до {days} дней и всё слить.",
]

START_TEXTS = [
    "Поехали. Посмотрим, на сколько тебя хватит.",
    "Попытка стать человеком №{n}.",
    "Организм снова надеется. Наивный.",
]

def relapse_text(days):
    return random.choice(RELAPSE_TEXTS).format(days=days)


def start_text(n):
    return random.choice(START_TEXTS).format(n=n)
