from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import config
import sqlite3 as sq
import secrets
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from help_keyboard import HELP_COMMAND, start
from telethon.sync import TelegramClient
from telethon import functions, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard = True)
    kb.add(KeyboardButton('/create_room'),
           KeyboardButton('/participants'),
           KeyboardButton('/join_room'),
           KeyboardButton('/exit_room'),
           KeyboardButton('/help'))
    
    return kb

bot = Bot(config.token)
dp = Dispatcher(bot, storage = MemoryStorage())

db = sq.connect('newtable_3.db')
cur = db.cursor()    

cur.execute("""CREATE TABLE IF NOT EXISTS rooms(
room_id INTEGER PRIMARY KEY AUTOINCREMENT, 
creator_id INTEGER,
room_name TEXT
)
""")
db.commit()

cur.execute("""CREATE TABLE IF NOT EXISTS participants(
participant_id INTEGER PRIMARY KEY AUTOINCREMENT, 
room_id INTEGER,
user_id INTEGER,
username TEXT,
preference TEXT,
FOREIGN KEY (room_id) REFERENCES rooms (room_id)
)
""")
db.commit()

cur.execute("""CREATE TABLE IF NOT EXISTS room_participants(
room_id INTEGER,
participant_id INTEGER,
FOREIGN KEY (room_id) REFERENCES rooms (room_id),
FOREIGN KEY (participant_id) REFERENCES participants (participant_id),
PRIMARY KEY (room_id, participant_id)
)
""")
db.commit()

class RoomStates(StatesGroup):
    UserStart = State()
    UserPrefer = State()
    RoomName = State()
    UserName = State()
    JoinPrefer = State()
    JoinRoom = State()
    ShowParticipants = State()
    GenerateQ = State()
    Exit = State()

@dp.message_handler(commands = ['start'])
async def start(message: types.Message):
    await message.answer("Hello! I'm a bot to create a queue. \nTo create new room please type /create_room. \nIf you need help - type /help", reply_markup = get_kb())
    
    
@dp.message_handler(commands = ['help'])
async def help_command(message: types.Message):
    await bot.send_message(chat_id = message.from_user.id,
                              text = HELP_COMMAND,
                              parse_mode = 'HTML')
    
@dp.message_handler(commands = ['create_room'])
async def createRoom_start(message: types.Message):
    await message.reply("Введите ваше имя ")
    await RoomStates.UserStart.set() 

    
@dp.message_handler(state = RoomStates.UserStart)
async def create_room_name(message: types.Message, state: FSMContext):    
    user_name = message.text
    await state.update_data(user_name = user_name)
    await RoomStates.next()
    await message.answer(f"Отлично! А теперь, {user_name}, напишите 3 номера в порядке убывания, каким бы вы хотели отвечать на экзамене")
    await RoomStates.UserPrefer.set()

    
@dp.message_handler(state = RoomStates.UserPrefer)
async def create_room_name(message: types.Message, state: FSMContext):    
    user_prefer = message.text
    await state.update_data(user_prefer = user_prefer)
    await RoomStates.next()
    await message.answer(f"Отлично! А теперь введите имя комнаты")

    
@dp.message_handler(state = RoomStates.RoomName)
async def set_roomname_room(message: types.Message, state: FSMContext):
    room_name = message.text
    chat_id = message.chat.id
    async with state.proxy() as data:
        user_name = data['user_name']
        user_prefer = data['user_prefer']
        
    cur.execute("INSERT INTO rooms (creator_id, room_name) VALUES (?, ?)",
                   (message.from_user.id, room_name))
    room_id = cur.lastrowid
    print(room_id)
    cur.execute("INSERT INTO participants (room_id, user_id, username, preference) VALUES (?, ?, ?, ?)",
                   (room_id, message.from_user.id, user_name, user_prefer))
    cur.execute("INSERT INTO room_participants (room_id, participant_id) VALUES (?, ?)",
                   (room_id, message.from_user.id))
    db.commit()
    await message.answer(f"Отлично! Комната {room_name} успешно создана. Номер комнаты: {room_id}.\n Чтобы остальные участники смогли присоединиться к данной комнате, им необходимо будет указать данный номер")

    
@dp.message_handler(commands = ['join_room'])    
async def create_room_name(message: types.Message):
    await message.reply("Введите ваше имя ")
    await RoomStates.UserName.set() 
    

@dp.message_handler(state = RoomStates.UserName)
async def enter_room_name(message: types.Message, state: FSMContext):    
    user_name = message.text
    await state.update_data(user_name = user_name)
    await RoomStates.next()
    await message.answer(f"Отлично! А теперь, {user_name}, напишите 3 номера в порядке убывания, каким бы вы хотели отвечать на экзамене.Например: 1, 2, 3")
 

@dp.message_handler(state = RoomStates.JoinPrefer)
async def enter_prefer(message: types.Message, state: FSMContext):    
    user_prefer = message.text
    await state.update_data(user_prefer = user_prefer)
    await RoomStates.next()
    await message.answer(f"Отлично! А теперь, чтобы присоединиться к комнате, введите ее номер")

@dp.message_handler(state = RoomStates.JoinRoom)
async def join_room(message: types.Message, state: FSMContext):
    room_id = message.text
    chat_id = message.chat.id
    async with state.proxy() as data:
        user_name = data['user_name']
        user_prefer = data['user_prefer']
            
    cur.execute("SELECT room_id FROM rooms WHERE room_id = ?", (room_id ))
    if cur.fetchone() is None:
        await message.answer(f"Введенная комната не существует")
    else:
        try:
            cur.execute("INSERT INTO room_participants (room_id, participant_id) VALUES (?, ?)",
                   (room_id, message.from_user.id))
            cur.execute("INSERT INTO participants (room_id, user_id, username, preference) VALUES (?, ?, ?, ?)",
                   (room_id, message.from_user.id, user_name, user_prefer))
            db.commit()
            await message.answer(f"Отлично! Вы присоединились к комнате")
        except:
            await message.answer(f"Вы уже состоите в данной комнате")
            
            
            
            
@dp.message_handler(commands = ['exit_room'])    
async def create_room_name(message: types.Message):
    await message.reply("Введите номер комнаты, которую хотите покинуть ")
    await RoomStates.Exit.set() 
    

@dp.message_handler(state = RoomStates.Exit)
async def exit_room_name(message: types.Message, state: FSMContext):    
    room_id = message.text
    chat_id = message.from_user.id
    cur.execute("DELETE FROM participants WHERE room_id = ? AND user_id = ?", (room_id, chat_id))
    cur.execute("DELETE FROM room_participants WHERE room_id = ? AND participant_id = ?", (room_id, chat_id))
    db.commit()
    await message.answer("Вы успешно покинули комнату")
    
    
               
def get_kb_gen() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard = True)
    kb.add(KeyboardButton('/create_room'),
           KeyboardButton('/participants'),
           KeyboardButton('/join_room'),
           KeyboardButton('/generate'),
           KeyboardButton('/help'))
    
    return kb    
    
@dp.message_handler(commands = ['participants'])
async def show_participants(message: types.Message):
    await message.answer("Введите номер комнаты", reply_markup = get_kb_gen())
    await RoomStates.ShowParticipants.set()


@dp.message_handler(state = RoomStates.ShowParticipants)
async def join_room(message: types.Message, state: FSMContext):
    room_id = message.text
    
    cur.execute("SELECT participants.username FROM participants WHERE participants.room_id = ?", (room_id))
    participants = cur.fetchall() 
    print(participants)
        
    if participants:
        response = "Participants in the room:\n"
        for participant in participants:
            username = participant
            response += f"{username[0]}\n"
    else:
        response = "No participants in the room."
    await message.reply(response)
    
        
@dp.message_handler(commands = ['generate'])
async def show_participants(message: types.Message):
    await message.reply("Введите номер комнаты")
    await RoomStates.GenerateQ.set()


@dp.message_handler(state = RoomStates.GenerateQ)
async def join_room(message: types.Message, state: FSMContext):
    room_id = message.text
    
    cur.execute("SELECT participants.username, participants.preference FROM participants WHERE participants.room_id = ?", (room_id))
    participants = cur.fetchall() 
    print(participants)
    part_q = []
    for item in participants:
        name, preferences = item
        print(item)
        import re
        preferences = tuple(map(int, re.split(r', |,| ', preferences)))
        part_q.append({'name': name, 'prefer': preferences})
    print(part_q)
    sorted_participants = sorted(part_q, key=lambda x: x['prefer'])
    print(sorted_participants)
    
    queue = "Очередь:\n"
    i = 1
    for participant in sorted_participants:
        queue += f"{i}. {participant['name']}\n"
        i += 1

    await message.reply(queue)       
    


    
    
if __name__ == '__main__':
    try:
        executor.start_polling(dp, skip_updates=True)
    finally:
        db.close()












#import telebot 
#token = '6220539025:AAGtADcPx_oXtwbGkKlWZjUBaeKYzAnFfT0'

#bot = telebot.TeleBot(token)

#@bot.message_handler(commands = ['start'])
#def send_welcome(message):
#    bot.send_message(message.chat.id, "Привет! Я бот для создания очереди")
    
#bot.polling(none_stop=True)