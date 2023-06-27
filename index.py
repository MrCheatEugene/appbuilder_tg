# -*- coding: utf-8 -*-

import logging
import os
import subprocess
import threading
import asyncio
import traceback
import shutil
import zipfile
from aiogram import Bot, Dispatcher, executor, types
from config import API_TOKEN, ANDROID_HOME
from random import randint
from shlex import quote
from pathlib import Path

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def thread_transfer(loop, args):
    asyncio.run_coroutine_threadsafe(on_zip_thread(args), loop)

async def on_zip_thread(message):
    await bot.send_message(message.from_user.id, 'Starting..\nНачинаю обработку..')
    try:
        file_id = message.document.file_id
        if message.document.file_name.endswith('.zip'):
            try:
                file = await bot.get_file(file_id)
                file_path = file.file_path
                fn = f"zips/{message.from_user.id}_{message.message_id}_{file_id}.zip"
                await bot.download_file(file_path, fn)
            except Exception as e:
                await bot.send_message(message.from_user.id, 'An error occured while downloading the file. Is it larger 25MB?\nПроизошла ошибка при скачивании файла. Возможно, его вес больше 25МБ?')
                return
            folder = f"{fn}_work"
            if not os.path.exists(folder):
                os.mkdir(folder)
            try:
                with zipfile.ZipFile(fn, 'r') as zip_ref:
                    zip_ref.extractall(folder+"www")
                try:
                    await bot.send_message(message.from_user.id, 'Preparing to build..\nПодготовка к сборке..')
                    appName = message.document.file_name.replace(".zip", "")[:15]
                    appID = f'me.t.web2apkbot_{hex(randint(10000000,9999999999999999999999999999999999999999999999999)).replace("0x", "")}'
                    cli = f'cordova create {quote(folder)} {quote(appID)} {quote(appName)}'
                    cli1 = f'cd "{quote(folder)}"'
                    cli2 = f'{cli1} && cordova platform add android'
                    os.system(cli)
                    os.system(cli1)
                    os.system(cli2)
                    shutil.rmtree(os.path.join(folder, 'www'))
                    os.mkdir(os.path.join(folder, 'www'))
                    for src_file in Path(folder+"www").glob('*.*'):
                        shutil.copy(src_file, os.path.join(folder, 'www'))
                    shutil.rmtree(folder+'www')
                    args = []
                    cfg = {}
                    if os.path.exists(os.path.join(os.path.join(folder,'www'),'web2apk_config.txt')):
                        try:
                            with open((os.path.join(os.path.join(folder,'www'),'web2apk_config.txt')), encoding="utf8") as f:
                                for line in f.read().splitlines():
                                    if line.startswith("#") or line.count("=")<0:
                                        continue
                                    key = line.split("=")[0]
                                    value=""
                                    i=-1
                                    for subval in line.split("="):
                                        i+=1
                                        if i == 0:
                                            continue
                                        value+=str(subval)
                                    if len(value)<1:
                                        continue
                                    if key == 'build_bundle' and bool(value) == True:
                                        if not '--release' in args:
                                            args.append('--release')
                                        args.append('--')
                                        args.append('--packageType=bundle')
                                    elif key == 'build_release' and bool(value) == True:
                                        if not '--release' in args:
                                            args.append('--release')
                                    elif key == 'title':
                                        cfg['title']='<name>'+value.replace("<", '').replace(">", '')+'</name>'
                                    elif key == 'description':
                                        cfg['description']='<description>'+value.replace("<", '').replace(">", '')+'</description>'
                                    elif key == 'favicon':
                                        cfg['fav']='<icon src="'+os.path.join(os.path.join(folder, 'www'),value.replace("<", '').replace(">", '').replace('"', ''))+'"/>'

                        except Exception as e:
                            await bot.send_message(message.from_user.id, f'Config error! Compilation interrupted.\nОшибка конфигурации! Компиляция прервана.\n\n{str(e)}')
                            return
                    config = f'<?xml version=\'1.0\' encoding=\'utf-8\'?>\n\
<widget id="{appID}" version="1.0.0" xmlns="http://www.w3.org/ns/widgets" xmlns:cdv="http://cordova.apache.org/ns/1.0">\n\
    {f"<name>{appName}</name>" if "title" not in cfg else cfg["title"]}\n\
    {f"<description>web2apk.t.me</description>" if "description" not in cfg else cfg["description"]}\n\
    {f"" if "fav" not in cfg else cfg["fav"]}\n\
    <content src="index.html" />\n\
    <allow-intent href="http://*/*" />\n\
    <allow-intent href="https://*/*" />\n\
</widget>'
                    with open(os.path.join(folder, 'config.xml'), encoding= "utf8", mode="w+") as f:
                        f.write(config)
                    cli3 = f'{cli1} && cordova build android {" ".join(args)}'
                    await bot.send_message(message.from_user.id, 'Build has begun..\nСборка начата..')
                    try:
                        env = dict(os.environ)
                        env['ANDROID_HOME'] = ANDROID_HOME
                        out = subprocess.run(cli3, env = env, stdout=subprocess.PIPE, shell=True).stdout.decode('utf8')
                        if '--packageType=bundle' in args:
                            strapp = 'Built the following bundle(s):'
                        else:
                            strapp = 'Built the following apk(s):'
                        print(out.split(strapp))
                        print(out)
                        await bot.send_document(message.from_user.id, types.InputFile(str(out.split(strapp)[1]).strip()), caption=f"App is Ready!\Приложение готово!\n\nAppID: {appID}")
                    except Exception as e:
                        await bot.send_message(message.from_user.id, 'Build failed.\nСборка не удалась.')
                        return
                except Exception as e:
                    await bot.send_message(message.from_user.id, 'Build preparing failed.\nПодготовка к сборке не удалась.')
                    return
            except Exception as e:
                await bot.send_message(message.from_user.id, 'Unpacking failed.\nРаспаковка не удалась.')
                return
        else:
            await bot.send_message(message.from_user.id, 'Sent your website as a ZIP!\nОтправьте ваш сайт как ZIP!')
            return
    except Exception as e:
        await bot.send_message(message.from_user.id, 'Critical error occured..\nПроизошла критическая ошибка.')

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Send me your website in .zip, and I'll make an APK from it!\nОтправь мне архив своего вебсайта в .zip, и я сделаю из него APK! \n\nLimitations: /limits\nОграничения: /limits\n\nAdditional info: /info\nДополнительная информация: /info")


@dp.message_handler(commands=['info'])
async def limits(message: types.Message):
    await message.reply('You can define additional info for compilation.\n\nTo do this, place a file called "web2apk_config.txt" in root of the ZIP.\nFormat: \n<code># Comment \n\n# Build bundle(aab): true/false\nbuild_bundle=true\n#Build release: true/false\nbuild_release=true\n# Title: string\ntitle=My awesome application\n#Description: string\ndescription=I made an awesome application!\n# Favicon: path to icon, in UNIX-format\nfavicon=assets/icon.ico</code>\n\nВы можете определить дополнительную информацию для компиляции.\n\nДля этого, создайте файл "web2apk_config.txt" в корне ZIP-архива с сайтом.\nФормат:\n<code># Комментарий\n\n# Собрать AAB: true/false\nbuild_bundle=true\n# Собрать релиз: true/false\nbuild_release=true\n# Нзавание: string\ntitle=My awesome application\n# Описание: string\ndescription=I made an awesome application!\n# Иконка: path to icon, in UNIX-format\nfavicon=assets/icon.ico</code>', parse_mode="html")

@dp.message_handler(commands=['limits'])
async def limits(message: types.Message):
    await message.reply('1. Archive size should be less than 25MB.\n2. Apps produced by this bot, are "debug" apps, made for developing purposes only.\n3. APK produced will not have builtin PHP, JS, Python or whatever interpreter. It can only do HTML, Client-JS, WASM, CSS, and any other web technology that doesn\'t require a backend.\n4. Filename should be shorter or equal 15 symbols.\n\n1. Размер архива должен быть меньше 25МБ.\n2. APK скомпилированное данным ботом, является отладочным, и его стоит использовать ТОЛЬКО В ОЗНАКОМИТЕЛЬНЫХ/ДЕМОНСТРАЦИОННЫХ/ОТЛАДОЧНЫХ целях!\n3. Интерпретаторы PHP, JS, Python, а также любых других не-клиентских языков программирования в APK не встраиваются, и работать не будут.\n4. Имя файла должно быть короче или равно 15 символам.')

@dp.message_handler(content_types=['document'])
async def on_zip(message: types.message):
    loop = asyncio.get_event_loop()
    threading.Thread(target=thread_transfer, args=[loop, message]).start()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, timeout=500)
