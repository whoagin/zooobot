import telebot
import json
import logging

from telebot import types
from telebot.types import CallbackQuery
from config import TOKEN, present, present_media, create_markup, user_data, red, recommendation_animal, share_markup, \
    match_quiz, create_vk_share_link, user_states, send_question, main_markup, about, about_project_markup
from question import questions, animal_trait, animals

bot = telebot.TeleBot(TOKEN)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bot_logger.log'
)


@bot.message_handler(commands=['start'])
def start(message: telebot.types.Message):
    bot.send_photo(message.chat.id, present_media, present, reply_markup=main_markup)


@bot.message_handler(commands=['quiz'])
def start_quiz(message: telebot.types):
    logging.info(f'Пользователь {message.from_user.username} начал викторину')
    user_data[message.chat.id] = {'current_question': 1}
    send_next_question(message.chat.id, message)
    red.delete(message.from_user.username)


def send_next_question(chat_id, message):
    user = user_data[chat_id]
    current_question = user['current_question']
    question_data = questions.get(current_question)

    if question_data:
        markup = create_markup(question_data['answers'])
        message = bot.send_message(chat_id, question_data['question'], reply_markup=markup)
        user['last_message_id'] = message.message_id
        user['current_question'] += 1
    else:

        quiz_result = red.lrange(message.from_user.username, 0, -1)
        quiz_result_list = []
        for result in quiz_result:
            try:
                quiz_result_list.append(json.loads(result))

            except json.JSONDecodeError as e:
                print(f'Ошбика декодирования JSON: {e}')
        if len(quiz_result_list) != len(questions.keys()):
            bot.send_message(chat_id, 'При сборе ответов произошла ошибка :(, пройдите тест заново нажав на /quiz')
            red.delete(message.from_user.username)
        else:
            try:
                share_markup.keyboard.clear()
                share_markup.add(
                    types.InlineKeyboardButton(text='Попробовать ещё раз?', callback_data='restart_quiz', ))
                share_markup.add(
                    types.InlineKeyboardButton(text='Поделится результатом', callback_data='share_link',
                                               url=create_vk_share_link(message.from_user.username)))
                result = recommendation_animal(quiz_result_list, animal_trait)
                bot.send_message(chat_id, 'Викторина завершена!')

                for animal in result:
                    red.set(f'{message.from_user.username}_result', animal)
                    bot.send_photo(chat_id, animals[animal]['media'],
                                   f"Ваше тотемное животное {animal}\n{animals[animal]['description']}\n"
                                   f"Что бы узнать подробнее об опеки нажмите на кнопку 'О программе опеки'\nТак же "
                                   f"можете оставить отзыв нажав кнопку 'Задать вопрос/Обратная связь'",
                                   reply_markup=share_markup)
                    logging.info(
                        f'Пользователь {message.from_user.username} завершил викторину\nОтветы :{quiz_result_list}\n'
                        f'Результат: {result[0]}')
            except Exception as e:
                logging.info(
                    f'Пользователь {message.from_user.username} завершил не смог завершить викторину\n'
                    f'Ответы :{quiz_result_list}\nОшибка: {e}')


@bot.callback_query_handler(func=lambda call: call.data in match_quiz(questions))
def handle_callback_query(call):
    # Здесь можно обрабатывать ответ пользователя
    print(f"Пользователь {f'{call.from_user.username}'} ответил: {call.data}")
    red.lpush(call.from_user.username, json.dumps(call.data))
    # логика обработки ответа
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    send_next_question(call.message.chat.id, call)


@bot.callback_query_handler(func=lambda callback: callback.data == 'restart_quiz')
def restart_link(call: CallbackQuery):
    bot.send_message(call.message.chat.id, 'Для повторного прохождения нажмите /quiz :)')
    logging.info(f'Пользователь {call.from_user.username} начал викторину заново')


@bot.message_handler(func=lambda message: message.text == 'Задать вопрос/Обратная связь')
def feedback(message: telebot.types.Message):
    user_states[message.chat.id] = "waiting_for_feedback"
    bot.reply_to(message, 'Пожалуйста, введите вопрос')


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'waiting_for_feedback')
def send_feedback_handler(message: telebot.types.Message):
    send_question(message, bot)
    bot.reply_to(message, f"Спасибо за обращение!")
    logging.info(f'{message.from_user.username} задал вопрос/остправил обратную связь')


@bot.message_handler(func=lambda message: message.text == 'О программе опеки')
def about_project(message: telebot.types.Message):
    bot.send_photo(message.chat.id, present_media, about, reply_markup=about_project_markup)


if __name__ == '__main__':
    bot.polling()
