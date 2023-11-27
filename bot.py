import pandas as pd
import asyncio
import requests

from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import StateFilter
from aiogram.filters.command import Command

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.storage.redis import RedisStorage, Redis

from config_reader import config
from aiogram.enums import ParseMode
from aiogram import F
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.utils.keyboard import InlineKeyboardBuilder

from choosing_options import available_films, available_genres, available_ratings
from prepare_dataset import dataset, day_film


bot = Bot(token = config.bot_token.get_secret_value(), parse_mode=ParseMode.HTML)
redis = Redis(host='localhost') # host="127.0.0.1", port=6379 
storage = RedisStorage(redis=redis)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

ratings_dict: dict[str, dict[int, int]] = {}
filmname = ''

  
def sample_to_film(sample: pd.Series):
    global filmname
    filmname = sample["Название"]
    message = f'Фильм: {sample["Название"]} \n'
    message += f'Год: {sample["year"]} \n'
    message += f'Страна: {sample["country"]} \n'
    message += f'Жанр: {", ".join([genre.title() for genre in sample["Жанр_массив"]])} \n'
    message += f'Рейтинг: {sample["rating_ball"]}, {sample["Количество оценок на Кинопоиск"]} оценок \n\n'
    message += f'В ролях: {sample["actors"]} \n\n'
    message += f'О фильме: {sample["overview"].replace(";", ",", -1)}'
    url = sample['url_logo'][1:-1]
    
    try:  
        requests.get(url)
        photo = url
    except:
        photo = ''
    return message, photo


class FSMOrderFilm(StatesGroup):
    choosing_film = State()
    choosing_genre = State()
    choosing_rate_option = State()
    choosing_rating = State()

@router.message(Command("start"))
async def cmd_film(message: Message, state: FSMContext):

    keyboard = [
        [types.KeyboardButton(text=available_films[0]),
         types.KeyboardButton(text=available_films[1]),
         types.KeyboardButton(text=available_films[2])]
    ]
    keyboard_ = types.ReplyKeyboardMarkup(keyboard=keyboard,
                                          resize_keyboard=True)
    await message.answer("Привет, давай подберем тебе фильм на вечер?", reply_markup=keyboard_)
    await state.set_state(FSMOrderFilm.choosing_film)


@router.message(FSMOrderFilm.choosing_film, F.text.in_(['Рекомендация по жанру']))
async def cmd_genre(message: Message, state: FSMContext):

    await state.update_data(chosen_film=message.text.lower())
    gdt = await state.get_data()
    builder = ReplyKeyboardBuilder()
    for genre in available_genres:
        builder.add(types.KeyboardButton(text=genre))
    builder.adjust(4)
    await message.answer('Выбери жанр фильма', reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(FSMOrderFilm.choosing_genre)


@router.message(FSMOrderFilm.choosing_film, F.text.in_(['Фильм дня', 'Случайный фильм']))
async def random_day_film(message: Message, state: FSMContext):

    await state.update_data(chosen_film=message.text.lower())
    if (message.text == 'Фильм дня'):
        text, photo = sample_to_film(dataset.iloc[day_film])
    else:
        text, photo = sample_to_film(dataset.sample(frac=1).iloc[0])

    if (filmname not in ratings_dict):
        ratings_dict[filmname] = {}

    if (message.from_user.id not in ratings_dict[filmname]):
        ratings_dict[filmname][message.from_user.id] = -1

    keyboard = [
        [types.KeyboardButton(text='Поставить фильму оценку'),
         types.KeyboardButton(text='/start')]
    ]
    keyboard_ = types.ReplyKeyboardMarkup(keyboard=keyboard,
                                          resize_keyboard=True)
    
    if (photo):
        await message.answer_photo(photo)

    await message.answer(
        text=text,
        reply_markup=keyboard_
    )
    await state.set_state(FSMOrderFilm.choosing_rate_option)


@router.message(StateFilter("FSMOrderFilm:choosing_film"))
async def film_chosen_incorrectly(message: Message):

    keyboard = [
        [types.KeyboardButton(text=available_films[0]),
         types.KeyboardButton(text=available_films[1]),
         types.KeyboardButton(text=available_films[2])]
    ]
    keyboard_ = types.ReplyKeyboardMarkup(keyboard=keyboard,
                                          resize_keyboard=True)
    
    await message.answer(
        text="Я тебя не понимаю",
        reply_markup=keyboard_
    )

@router.message(FSMOrderFilm.choosing_genre, F.text.in_(available_genres))
async def genre_film(message: Message, state: FSMContext):

    await state.update_data(chosen_genre=message.text.lower())
    text, photo = sample_to_film(dataset[dataset['Жанр'].str.contains(message.text)].sample(frac=1).iloc[0])

    if (filmname not in ratings_dict):
        ratings_dict[filmname] = {}
        
    if (message.from_user.id not in ratings_dict[filmname]):
        ratings_dict[filmname][message.from_user.id] = -1

    keyboard = [
        [types.KeyboardButton(text='Поставить фильму оценку'),
         types.KeyboardButton(text='/start')]
    ]
    keyboard_ = types.ReplyKeyboardMarkup(keyboard=keyboard,
                                          resize_keyboard=True)
    
    if (photo):
        await message.answer_photo(photo)

    await message.answer(
        text=text,
        reply_markup=keyboard_
    )
    await state.set_state(FSMOrderFilm.choosing_rate_option)


@router.message(StateFilter("FSMOrderFilm:choosing_genre"))
async def genre_chosen_incorrectly(message: Message):

    builder = ReplyKeyboardBuilder()
    for genre in available_genres:
        builder.add(types.KeyboardButton(text=genre))
    builder.adjust(5)
    
    await message.answer('Я тебя не понимаю', reply_markup=builder.as_markup(resize_keyboard=True))


@router.message(FSMOrderFilm.choosing_rate_option, F.text.in_(['Поставить фильму оценку']))
async def cmd_rate_option(message: Message, state: FSMContext):

    await state.update_data(chosen_rate_option=message.text.lower())
    builder = ReplyKeyboardBuilder()
    for rating in available_ratings:
        builder.add(types.KeyboardButton(text=str(rating)))
    builder.adjust(3)
    await message.answer('Выбери оценку', reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(FSMOrderFilm.choosing_rating)


@router.message(StateFilter("FSMOrderFilm:choosing_rate_option"))
async def rate_option_chosen_incorrectly(message: Message):

    keyboard = [
        [types.KeyboardButton(text='Поставить фильму оценку'),
         types.KeyboardButton(text='/start')]
    ]
    keyboard_ = types.ReplyKeyboardMarkup(keyboard=keyboard,
                                          resize_keyboard=True)

    await message.answer('Я тебя не понимаю', reply_markup=keyboard_)

@router.message(FSMOrderFilm.choosing_rating, F.text.in_(available_ratings))
async def cmd_rating(message: Message, state: FSMContext):
    await state.update_data(chosen_rating=message.text.lower())
    rating_data = await state.get_data()
    ratings_dict[filmname][message.from_user.id] = rating_data['chosen_rating']
    await message.answer('Спасибо за оценку! Нажми /start, чтобы вернуться в начало')
    await state.clear()


@router.message(StateFilter("FSMOrderFilm:choosing_rating"))
async def rating_chosen_incorrectly(message: Message):

    builder = ReplyKeyboardBuilder()
    for rating in available_ratings:
        builder.add(types.KeyboardButton(text=str(rating)))
    builder.adjust(3)

    await message.answer('Я тебя не понимаю', reply_markup=builder.as_markup(resize_keyboard=True))


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())