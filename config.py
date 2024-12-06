import redis
import telebot
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telebot import types

TOKEN = ''  # токен бота

# текст при старте
present = (f'Добро пожаловать на проект Московский зоопарк!\nНаша задача - вносить вклад в сохранение биоразнообразия\
 планеты. Сотрудники зоопарка пытаются уберечь виды от вымирания и вернуть их в естественную среду обитания.\n\
Как ты можешь помочь? - Взять под опеку можно разных обитателей зоопарка, например, слона, льва, суриката или фламинго.\
 Это возможность помочь любимому животному или даже реализовать детскую мечту подружиться с настоящим диким зверем\n\
Подобрать подходящее тебе животное ты можешь с помощью нашей викторины!\n Для начала викторины введите /quiz')
# медиа при старте
present_media = (
    'https://storage.moscowzoo.ru/storage/647edc2a70bb5462366280fc/images/about_home/9083907d-fef0-48ff-a70d-292e2272f329.jpg')
about = ('Участие в программе «Клуб друзей зоопарка» — это помощь в содержании наших обитателей, а также ваш личный '
         'вклад в дело сохранения биоразнообразия Земли и развитие нашего зоопарка.\n'
         'Основная задача Московского зоопарка с самого начала его существования это — сохранение'
         ' биоразнообразия планеты. Когда вы берете под опеку животное, вы помогаете нам в этом благородном деле.')
user_data = {}

red = redis.Redis(
    host='127.0.0.1', port=6379
)

user_states = {}

bot_href = ''  # Внесите URL вашего бота

SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 465
EMAIL = ""  # Внесите вашу почту yandex
PASSWORD = ""  # Внесите ваш пароль приложений yandex


def create_vk_share_link(message: telebot.types):  # возвращает ссылку на поделится в соц сетях(вк)

    url = f'https://t.me/{bot_href}'  # Это URL вашего тг
    title = 'Московский Зоопарк'
    user_result = red.get(f'{message}_result').decode('utf-8')
    comment = (f'Моё тотемное животное {user_result}!'
               f' Заходи в нашего бота и узнай своё тотемное животное!')
    vk_link = f'https://vk.com/share.php?url={url}&title={title}&comment={comment}'
    return vk_link


# клавиатуры
main_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_markup.add(types.KeyboardButton('Задать вопрос/Обратная связь', ))
main_markup.add(types.KeyboardButton('О программе опеки'))
share_markup = types.InlineKeyboardMarkup()

about_project_markup = types.InlineKeyboardMarkup()
about_project_markup.add(types.InlineKeyboardButton('Подробнее о программе',
                                                    url='https://moscowzoo.ru/about/guardianship'))


def create_markup(options):  # создаёт кнопки с ответами для всех вопросов
    markup = types.InlineKeyboardMarkup()
    for option in options:
        markup.add(types.InlineKeyboardButton(text=option, callback_data=option))
    return markup


def recommendation_animal(user_option: list,
                          animal_option: dict):  # исходя из ответов подбирает животное для пользователя
    recommendations = []
    max_matches = 0

    for animal, traits in animal_option.items():
        # Подсчёт совпадений
        matches = sum(1 for trait in traits if trait in user_option)

        if matches > max_matches:
            # Обновляем максимум совпадений и перезаписываем рекомендации
            max_matches = matches
            recommendations = [animal]
        elif matches == max_matches and max_matches > 0:
            # Добавляем животное с таким же количеством совпадений
            recommendations = [animal]

    # Если совпадений не было вовсе
    if not recommendations:
        return ['Для вас нет подходящего зверька :(']

    return recommendations


def about_animal(animal: list, animal_description: dict):
    if animal[0] in animal_description:
        return animal_description[animal[0]]


def match_quiz(question: dict):
    i = 0
    quiz_answer = []
    while i in range(len(question)):
        i += 1
        for q in question[i]['answers']:
            quiz_answer.append(q)
    return quiz_answer


def send_question(message: types.Message, bot: telebot):  # отправляет письмо на почту с вопросом пользователя
    try:
        try:
            check_result = red.get(f'{message.from_user.username}_result')
            check_result = check_result.decode('utf-8')

        except Exception:

            check_result = 'Викторина ещё не пройдена'

        subject = f'Вопрос/Обратная связь от https://t.me/{message.chat.username}'
        feedback_text = message.text

        feedback_text = f'Результат викторины: {check_result}\nПользователь отправил: {feedback_text}'
        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(feedback_text, "plain"))
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)

        server.ehlo(EMAIL)
        server.login(EMAIL, PASSWORD)
        server.auth_plain()
        server.sendmail(EMAIL, EMAIL, msg.as_string())
        server.quit()

    except Exception as e:

        bot.reply_to(message, f'Ошибка при отправке: {e}')

    finally:
        user_states.pop(message.chat.id, None)
