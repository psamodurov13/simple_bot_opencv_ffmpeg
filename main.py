import ffmpeg
from aiogram import Bot, Dispatcher, executor, types
from loguru import logger
from pathlib import Path
from aiogram.types import ContentType, File, Message
import auth
import os
import cv2
from zipfile import ZipFile


logger.add('debug.log', format='{time} {level} {message}', level='DEBUG', rotation='10 MB', compression='zip')

bot = Bot(token=auth.token)
dp = Dispatcher(bot)


@dp.message_handler(commands='start')
async def start(message: types.Message):
    await message.answer('Меня создал Самодуров Павел. Вот его резюме '
                         'https://drive.google.com/file/d/14d91RdSADs-uI_AB0AEhAXXbwuWlGfmf/view?usp=sharing. Бот '
                         'сохраняет и конвертирует аудиосообщения, а так же сохраняет фото с лицами. Для выгрузки '
                         'архива с аудиозаписями и фото введите команду /download')


async def handle_file(file, file_name, path):
    Path(f'{path}').mkdir(parents=True, exist_ok=True)
    all_files = []
    for item in os.listdir(path):
        if item.endswith('.wav') and item.startswith('audio_message_'):
            all_files.append(int(item.replace('audio_message_', '').replace('.wav', '')))
    logger.info(f'ALL FILES - {all_files}')
    if len(all_files) > 0:
        counts = max(all_files) + 1
    else:
        counts = 0
    logger.info(f'PATH TO FILE - {path}/{file_name}_{counts}.ogg')
    await bot.download_file(file_path=file.file_path, destination=f'{path}/{file_name}_{counts}.ogg')
    stream = ffmpeg.input(f'{path}/{file_name}_{counts}.ogg')
    stream = ffmpeg.output(stream, f'{path}/audio_message_{counts}.wav', format='wav', ar='16k')
    ffmpeg.run(stream)
    os.remove(f'{path}/{file_name}_{counts}.ogg')


async def handle_photo(file, path):
    photo_file = file.file_path.split("/")[-1]
    await bot.download_file(file_path=file.file_path, destination=f'{path}/{photo_file}')
    photo = cv2.imread(f'{path}/{photo_file}')
    gray_img = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
    haar_face_cascade = cv2.CascadeClassifier('model.xml')
    faces = haar_face_cascade.detectMultiScale(gray_img)
    for (x, y, w, h) in faces:
        cv2.rectangle(photo, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.imwrite(f'{path}/{photo_file}', photo)
    if len(faces) == 0:
        os.remove(f'{path}/{photo_file}')
        result = {'status': False}
    else:
        result = {'status': True, 'photo': f'{path}/{photo_file}'}
    return result


@dp.message_handler(content_types=[ContentType.VOICE])
async def voice_message_handler(message: Message):
    voice = await message.voice.get_file()
    path = f'audio/{message.from_user.id}'
    await handle_file(file=voice, file_name=f'audio.ogg', path=path)
    await message.answer('Сообщение принято и сохранено.')


@dp.message_handler(content_types=[ContentType.PHOTO])
async def photo_message_handler(message: Message):
    file = await bot.get_file(message.photo[-1].file_id)
    path = f'photo/{message.from_user.id}'
    logger.info(f'TYPE {file}')
    result = await handle_photo(file, path)
    if result['status']:
        await message.answer(f'Фото сохранено')
        photo = open(result['photo'], 'rb')
        await message.answer_photo(photo)
    else:
        await message.answer('На фото нет лиц')


@dp.message_handler(commands='download')
async def download(message: types.Message):
    if os.path.isdir(f'audio/{message.from_user.id}') or os.path.isdir(f'photo/{message.from_user.id}'):
        with ZipFile(f'archive-{message.from_user.id}.zip', 'w') as myzip:
            try:
                for root, dirs, files in os.walk(f'audio/{message.from_user.id}'):
                    for file in files:
                        myzip.write(os.path.join(root, file))
            except Exception:
                logger.debug(Exception)
            try:
                for root, dirs, files in os.walk(f'photo/{message.from_user.id}'):
                    for file in files:
                        myzip.write(os.path.join(root, file))
            except Exception:
                logger.debug(Exception)
        await message.answer('Архив с Вашими аудиозаписями и фото')
        await message.answer_document(open(f'archive-{message.from_user.id}.zip', 'rb'))
    else:
        await message.answer('У Вас пока нет сохраненных аудио и фото')


@dp.message_handler()
async def other_message_handler(message: Message):
    await message.answer('Я тебя не понимаю. Я не слишком умный бот. Пришли мне, '
                         'пожалуйста, фото или голосовое сообщение.')


@logger.catch
def main():
    executor.start_polling(dp)


if __name__ == '__main__':
    if not os.path.isdir('audio'):
        os.mkdir('audio')
    if not os.path.isdir('photo'):
        os.mkdir('photo')
    main()
