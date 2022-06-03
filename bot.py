import config
import telebot
from telebot import types
import random
from mg import get_map_cell
from pymongo import MongoClient
import anekdoty



bot = telebot.TeleBot(config.BOT_TOKEN)

@bot.message_handler(commands=['start'])
def welcome(message):
	sti = open('AnimatedSticker.tgs', 'rb')
	bot.send_sticker(message.chat.id, sti)

	#keyboard
	markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
	item1 = types.KeyboardButton("🗺️Maze")
	item2 = types.KeyboardButton("🧩Quiz")
	item3 = types.KeyboardButton("🎲Number")
	item4 = types.KeyboardButton("🤣Anekdot")

	markup.add(item1, item2, item3, item4)

	bot.send_message(message.chat.id, "Доброго дня, {0.first_name}!\nЯ - <b>{1.first_name}</b>, бот, що створений для створення гарного настрою)".format(message.from_user, bot.get_me()),
			parse_mode = 'html', reply_markup = markup)

class DataBase:
	def __init__(self):
		cluster = MongoClient("mongodb+srv://Smolldo:22021999@cluster0.irm3j.mongodb.net/?retryWrites=true&w=majority")

		self.db = cluster["QuizBot"]
		self.users = self.db["Users"]
		self.questions = self.db["Questions"]

		self.questions_count = len(list(self.questions.find({})))

	def get_user(self, chat_id):
		user = self.users.find_one({"chat_id": chat_id})

		if user is not None:
			return user

		user = {
			"chat_id": chat_id,
			"is_passing": False,
			"is_passed": False,
			"question_index": None,
			"answers": []
		}

		self.users.insert_one(user)

		return user

	def set_user(self, chat_id, update):
		self.users.update_one({"chat_id": chat_id}, {"$set": update})

	def get_question(self, index):
		return self.questions.find_one({"id": index})

db = DataBase()


@bot.message_handler(commands=["begin"])
def begin(message):
	user = db.get_user(message.chat.id)

	if user["is_passed"]:
		bot.send_message(message.from_user.id, "Вы вже пройшли вікторину. Більше спроб немає 😥")
		return

	if user["is_passing"]:
		return

	db.set_user(message.chat.id, {"question_index": 0, "is_passing": True})

	user = db.get_user(message.chat.id)
	post = get_question_message(user)
	if post is not None:
		bot.send_message(message.from_user.id, post["text"], reply_markup=post["keyboard"])

@bot.callback_query_handler(func=lambda query: query.data.startswith("?ans"))
def answered(query):
	user = db.get_user(query.message.chat.id)

	if user["is_passed"] or not user["is_passing"]:
		return

	user["answers"].append(int(query.data.split("&")[1]))
	db.set_user(query.message.chat.id, {"answers": user["answers"]})

	post = get_answered_message(user)
	if post is not None:
		bot.edit_message_text(post["text"], query.message.chat.id, query.message.id,
						 reply_markup=post["keyboard"])

@bot.callback_query_handler(func=lambda query: query.data == "?next")
def next(query):
	user = db.get_user(query.message.chat.id)

	if user["is_passed"] or not user["is_passing"]:
		return

	user["question_index"] += 1
	db.set_user(query.message.chat.id, {"question_index": user["question_index"]})

	post = get_question_message(user)
	if post is not None:
		bot.edit_message_text(post["text"], query.message.chat.id, query.message.id,
						 reply_markup=post["keyboard"])


def get_question_message(user):
	if user["question_index"] == db.questions_count:
		count = 0
		for question_index, question in enumerate(db.questions.find({})):
			if question["correct"] == user["answers"][question_index]:
				count += 1
		percents = round(100 * count / db.questions_count)

		if percents < 40:
			smile = "😥"
		elif percents < 60:
			smile = "😐"
		elif percents < 90:
			smile = "😀"
		else:
			smile = "😎"

		text = f"Ви відповіли правильно на {percents}% питань {smile}"

		db.set_user(user["chat_id"], {"is_passed": True, "is_passing": False})

		return {
			"text": text,
			"keyboard": None
		}

	question = db.get_question(user["question_index"])

	if question is None:
		return

	keyboard = telebot.types.InlineKeyboardMarkup()
	for answer_index, answer in enumerate(question["answers"]):
		keyboard.row(telebot.types.InlineKeyboardButton(f"{chr(answer_index + 97)}) {answer}",
														callback_data=f"?ans&{answer_index}"))

	text = f"Питання №{user['question_index'] + 1}\n\n{question['text']}"

	return {
		"text": text,
		"keyboard": keyboard
	}

def get_answered_message(user):
	question = db.get_question(user["question_index"])

	text = f"Питання №{user['question_index'] + 1}\n\n{question['text']}\n"

	for answer_index, answer in enumerate(question["answers"]):
		text += f"{chr(answer_index + 97)}) {answer}"

		if answer_index == question["correct"]:
			text += " ✅"
		elif answer_index == user["answers"][-1]:
			text += " ❌"

		text += "\n"

	keyboard = telebot.types.InlineKeyboardMarkup()
	keyboard.row(telebot.types.InlineKeyboardButton("Далі", callback_data="?next"))

	return {
		"text": text,
		"keyboard": keyboard
	}

###############################################################################################################
#buttons meaning
@bot.message_handler(content_types = ['text'])
def btnCallBack(message):
	if message.chat.type == 'private':
		if message.text == "🗺️Maze":
			bot.send_message(message.chat.id, "Кулька має потрапити у нижній правий кут. Успіхів тобі😊")
			play_message(message)
		elif message.text == "🧩Quiz":
			 begin(message)
		elif message.text == "🎲Number":
			bot.send_message(message.chat.id, "Ваше випадкове число: " + str(random.randint(0,100)))
		elif message.text == "🤣Anekdot":
			bot.send_message(message.chat.id, anekdoty.anekdots[random.randint(0,4)])


cols, rows = 8, 8

keyboard = telebot.types.InlineKeyboardMarkup()
keyboard.row( telebot.types.InlineKeyboardButton('←', callback_data='left'),
			  telebot.types.InlineKeyboardButton('↑', callback_data='up'),
			  telebot.types.InlineKeyboardButton('↓', callback_data='down'),
			  telebot.types.InlineKeyboardButton('→', callback_data='right') )

maps = {}

def get_map_str(map_cell, player):
	map_str = ""
	for y in range(rows * 2 - 1):
		for x in range(cols * 2 - 1):
			if map_cell[x + y * (cols * 2 - 1)]:
				map_str += "⬛"
			elif (x, y) == player:
				map_str += "🔴"
			else:
				map_str += "⬜"
		map_str += "\n"

	return map_str

#@bot.message_handler(commands=['play'])
def play_message(message):
	map_cell = get_map_cell(cols, rows)

	user_data = {
		'map': map_cell,
		'x': 0,
		'y': 0
	}

	maps[message.chat.id] = user_data

	bot.send_message(message.from_user.id, get_map_str(map_cell, (0, 0)), reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_func(query):
	user_data = maps[query.message.chat.id]
	new_x, new_y = user_data['x'], user_data['y']

	if query.data == 'left':
		new_x -= 1
	if query.data == 'right':
		new_x += 1
	if query.data == 'up':
		new_y -= 1
	if query.data == 'down':
		new_y += 1

	if new_x < 0 or new_x > 2 * cols - 2 or new_y < 0 or new_y > rows * 2 - 2:
		return None
	if user_data['map'][new_x + new_y * (cols * 2 - 1)]:
		return None

	user_data['x'], user_data['y'] = new_x, new_y

	if new_x == cols * 2 - 2 and new_y == rows * 2 - 2:
		bot.edit_message_text( chat_id=query.message.chat.id,
							   message_id=query.message.id,
							   text="ВИ ПЕРЕМОГЛИ!" )
		return None

	bot.edit_message_text( chat_id=query.message.chat.id,
						   message_id=query.message.id,
						   text=get_map_str(user_data['map'], (new_x, new_y)),
						   reply_markup=keyboard )





bot.infinity_polling()