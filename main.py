cat << 'EOF' > music_bot.py
import telebot
import yt_dlp
import os
import asyncio
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from shazamio import Shazam

API_TOKEN = '8944414970:AAF_wklopgl3efO-iIDDD7UrQID0nBOU3zA'
bot = telebot.TeleBot(API_TOKEN)
shazam = Shazam()

# 1. ҶУСТУҶӮИ АУДИО ДАР YOUTUBE АЗ РӮИ МАТН Ё НОМ
def search_youtube(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Ҷустуҷӯи 5 варианти аввал
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            results = []
            if 'entries' in info:
                for entry in info['entries']:
                    results.append({
                        'title': entry.get('title'),
                        'id': entry.get('id'),
                        'uploader': entry.get('uploader', 'Номаълум')
                    })
            return results
        except Exception:
            return []

# 2. ШИНОСОИИ ОВОЗ (SHAZAM)
async def recognize_audio(file_path):
    try:
        out = await shazam.recognize_song(file_path)
        if out and 'track' in out:
            return f"{out['track']['subtitle']} {out['track']['title']}"
        return None
    except Exception:
        return None

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🎵")

# ҲАМАНД ПАЁМИ ОВОЗӢ ВА НАВОР (ШИНОСОӢ БО ОВОЗ)
@bot.message_handler(content_types=['voice', 'audio', 'video'])
def handle_audio_video(message):
    status_msg = bot.reply_to(message, "⏳")
    try:
        if message.content_type == 'voice':
            file_info = bot.get_file(message.voice.file_id)
        elif message.content_type == 'audio':
            file_info = bot.get_file(message.audio.file_id)
        else:
            file_info = bot.get_file(message.video.file_id)
            
        downloaded_file = bot.download_file(file_info.file_path)
        temp_file = f"temp_{file_info.file_id}.mp4"
        with open(temp_file, 'wb') as f:
            f.write(downloaded_file)
            
        bot.edit_message_text("⚡️", message.chat.id, status_msg.message_id)
        
        # Ёфтани номи суруд аз рӯи овоз
        song_name = asyncio.run(recognize_audio(temp_file))
        os.remove(temp_file)
        
        if song_name:
            # Агар сурудро шинохт, худкор вариантҳоро аз интернет меҷӯяд
            process_song_search(message, song_name, status_msg)
        else:
            bot.edit_message_text("🤷‍♂️ Овоз шинохта нашуд.", message.chat.id, status_msg.message_id)
            
    except Exception:
        try: bot.delete_message(message.chat.id, status_msg.message_id)
        except: pass

# ТАҲЛИЛИ МАТН (ҶУСТУҶӮ АЗ РӮИ НОМ Ё ЛИНК)
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    url = message.text
    status_msg = bot.reply_to(message, "⏳")
    
    # Агар линк бошад - мустақим зеркашӣ мекунад
    if url.startswith("http://") or url.startswith("https://"):
        download_direct_url(message, url, status_msg)
    else:
        # Агар матн бошад - аз рӯи ном меҷӯяд
        process_song_search(message, url, status_msg)

def process_song_search(message, query, status_msg):
    bot.edit_message_text("🔍", message.chat.id, status_msg.message_id)
    songs = search_youtube(query)
    
    if not songs:
        bot.edit_message_text("❌ Ҳеҷ чиз пайдо нашуд.", message.chat.id, status_msg.message_id)
        return
        
    markup = InlineKeyboardMarkup()
    for song in songs:
        # Сохтани тугма барои ҳар як вариант (маҳдудияти калима барои тугма)
        button_text = f"👤 {song['uploader'][:15]} - {song['title'][:25]}..."
        callback_data = f"dl_{song['id']}"
        markup.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
        
    bot.delete_message(message.chat.id, status_msg.message_id)
    bot.send_message(message.chat.id, "🎵 Варианти дилхоҳро интихоб кунед:", reply_markup=markup)

# ИҶРОИ ЗЕРКАШИИ ИНТИХОБШУДА АЗ РӮИ ТУГМА
@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def callback_download(call):
    video_id = call.data.split('_')[1]
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Нест кардани тугмаҳо ва нишон додани статус
    status_msg = bot.send_message(call.message.chat.id, "⚡️ Зеркашии варианти интихобшуда...")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    download_direct_url(call.message, url, status_msg)

def download_direct_url(message, url, status_msg):
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'external_downloader': 'aria2c',
        'external_downloader_args': ['-x', '16', '-s', '16'],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, ext = os.path.splitext(filename)
            mp3_filename = base + ".mp3"
            
            if not os.path.exists(mp3_filename) and os.path.exists(filename):
                os.rename(filename, mp3_filename)
                
            title = info.get('title', 'Мусиқӣ')
            performer = info.get('uploader', 'Номаълум')

        bot.edit_message_text("🚀", message.chat.id, status_msg.message_id)
        
        with open(mp3_filename, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, title=title, performer=performer)
            
        bot.delete_message(message.chat.id, status_msg.message_id)
        if os.path.exists(mp3_filename): os.remove(mp3_filename)
    except Exception:
        try: bot.delete_message(message.chat.id, status_msg.message_id)
        except: pass

if __name__ == '__main__':
    if not os.path.exists('downloads'): os.makedirs('downloads')
    bot.polling(none_stop=True)
EOF
