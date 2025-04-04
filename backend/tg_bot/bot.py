#####################################
#            Created by             #
#               SBR                 #
#####################################
import asyncio
from telebot.async_telebot import AsyncTeleBot

from api.utilities.config import generic_settings
from api.repository.heroes import select_hero, hero_is_existed
from api.broker.redis import RedisBroker
from api.storage.local import FileManager
from api.repository.heroes import update_hero_moderation_status
from api.repository.wars import select_war_by_id
from api.repository.military_ranks import select_military_rank_by_id
from tg_bot.buttons import BotButtons
from api.utilities.types_storage import ModerationStatus

#####################################


bot = AsyncTeleBot(generic_settings.TG_BOT_TOKEN)


async def null_wrapper(data: any) -> any:
    return "Не указано" if data is None else data


def split_string(s: str, max_length: int) -> list[str]:
    return [s[i:i + max_length] for i in range(0, len(s), max_length)]


async def application_events_handler():
    file_manager = FileManager()
    bot_buttons = BotButtons()
    pubsub = RedisBroker().broker_client.pubsub()
    await pubsub.subscribe("hero:hero_insert_events")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            payload = message["data"].decode()
            new_hero_id = int(payload)

            await hero_is_existed(hero_id=new_hero_id)
            hero_obj = await select_hero(hero_id=new_hero_id)
            hero_military_rank_obj = None
            hero_war_obj = await select_war_by_id(war_id=hero_obj.war_id)
            if hero_obj.military_rank_id is not None:
                hero_military_rank_obj = await select_military_rank_by_id(military_rank_id=hero_obj.military_rank_id)

            msg = (f"ID героя: {await null_wrapper(new_hero_id)}\n"
                   f"Имя: {await null_wrapper(hero_obj.name)}\n"
                   f"Фамилия: {await null_wrapper(hero_obj.surname)}\n"
                   f"Отчество: {await null_wrapper(hero_obj.patronymic)}\n"
                   f"Дата рождения: {await null_wrapper(hero_obj.birth_date)}\n"
                   f"Место рождения: {await null_wrapper(hero_obj.birth_place)}\n"
                   f"Дата смерти: {await null_wrapper(hero_obj.death_date)}\n"
                   f"Война: {await null_wrapper(hero_war_obj.title)}\n"
                   f"Воинское звание: {await null_wrapper(None if hero_military_rank_obj is None else hero_military_rank_obj.title)}\n"
                   f"Воинская специальность: {await null_wrapper(hero_obj.military_specialty)}\n"
                   f"Дата призывы: {await null_wrapper(hero_obj.enlistment_date)}\n"
                   f"Дата демобилизации: {await null_wrapper(hero_obj.discharge_date)}\n"
                   f"Доп. информация: {await null_wrapper(hero_obj.additional_information)}\n"
                   f"Время отправки заявки: {await null_wrapper(hero_obj.created_at)}\n")

            if hero_obj.photo_name is not None:
                photo_obj = await file_manager.read_file(generic_settings.MEDIA_FOLDER / hero_obj.photo_name)
                split_msg = split_string(s=msg, max_length=1024)
                for index, chunk in enumerate(split_msg):
                    if len(split_msg) == 1:
                        await bot.send_photo(generic_settings.TG_BOT_ADMIN, photo_obj, caption=chunk,
                                             reply_markup=bot_buttons.hero(hero_id=new_hero_id))
                    elif index == 0:
                        await bot.send_photo(generic_settings.TG_BOT_ADMIN, photo_obj, caption=chunk)
                    elif index == len(split_msg) - 1:
                        await bot.send_message(generic_settings.TG_BOT_ADMIN, chunk,
                                               reply_markup=bot_buttons.hero(hero_id=new_hero_id))
                    else:
                        await bot.send_message(generic_settings.TG_BOT_ADMIN, chunk)
            else:
                split_msg = split_string(s=msg, max_length=4096)
                for index, chunk in enumerate(split_msg):
                    if index == len(split_msg) - 1:
                        await bot.send_message(generic_settings.TG_BOT_ADMIN, chunk, reply_markup=bot_buttons.hero(hero_id=new_hero_id))
                    else:
                        await bot.send_message(generic_settings.TG_BOT_ADMIN, chunk)
    finally:
        await pubsub.unsubscribe("hero:hero_insert_events")


@bot.message_handler(commands=['start'])
async def start_msg(message):
    user_id = message.from_user.id
    command = message.text.replace('/', '')

    if "start" in command:
        if user_id == generic_settings.TG_BOT_ADMIN:
            await bot.send_message(user_id, "Доброго дня, модератор")
        else:
            await bot.send_message(user_id, "Бот не функционирует")


@bot.callback_query_handler(func=lambda call: True)
async def callback(call):
    command = call.data
    message_id = call.message.message_id
    user_id = call.message.chat.id

    if user_id != generic_settings.TG_BOT_ADMIN:
        return None

    if "accept" in command:
        await update_hero_moderation_status(hero_id=int(command[6:]), new_moderation_status=ModerationStatus.APPROVED.name)
        status = "\n\n Заявка была подтверждена"
    elif "reject" in command:
        await update_hero_moderation_status(hero_id=int(command[6:]), new_moderation_status=ModerationStatus.REJECTED.name)
        status = "\n\n Заявка была отклонена"
    else:
        return None

    if call.message.photo:
        await bot.edit_message_caption(call.message.caption + status,
                                       generic_settings.TG_BOT_ADMIN, message_id)
    else:
        await bot.edit_message_text(call.message.text + status, generic_settings.TG_BOT_ADMIN,
                                    message_id)



async def main():
    asyncio.create_task(application_events_handler())
    await bot.infinity_polling(timeout=10)

if '__main__' == __name__:
    asyncio.run(main())
