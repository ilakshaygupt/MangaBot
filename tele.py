from bs4 import BeautifulSoup
import requests
import telebot
from dotenv import load_dotenv
import os
load_dotenv()
API_KEY = os.getenv("API_KEY")

bot = telebot.TeleBot(API_KEY)


search_results = {}


@bot.message_handler(commands=["start"])
def send_greeting(message):
    bot.reply_to(message, "Hello! Welcome to the bot.")


@bot.message_handler(commands=["search"])
def send_search(message):
    text = message.text
    text = text.split(" ")
    text = "_".join(text).replace("/search_", "")
    send_search_results(message.chat.id, text, 1)


def send_search_results(chat_id, manga_name, page_number):

    start_index = (page_number - 1) * 5
    if not start_index:
        start_index = 1
    end_index = start_index + 5
    url = f"https://manganato.com/search/story/{manga_name}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    search_items = soup.find_all("div", class_="search-story-item")

    results = []
    for item in search_items:
        result = {}
        result["title"] = item.find("h3").text.strip()
        result["link"] = item.find("a")["href"]
        results.append(result)

    if results:
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        end_index = min(end_index, len(results))
        for i in range(start_index, end_index):
            result = results[i]
            button = telebot.types.InlineKeyboardButton(
                text=result["title"], callback_data=f"manga_{result['link']}"
            )
            markup.add(button)

        if len(results) > end_index:
            next_button = telebot.types.InlineKeyboardButton(
                text="Next", callback_data=f"search_{manga_name}_{page_number+1}"
            )
            markup.add(next_button)
        if page_number > 1:
            prev_button = telebot.types.InlineKeyboardButton(
                text="Previous", callback_data=f"search_{manga_name}_{page_number-1}"
            )
            markup.add(prev_button)

        bot.send_message(
            chat_id, f"Page {page_number} of search results:", reply_markup=markup
        )
    else:
        bot.send_message(chat_id, "No results found.")


def sendchapters(chat_id, url, page_number):
    start_index = (page_number - 1) * 5
    if not start_index:
        start_index = 1
    end_index = start_index + 5
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    manga_info = soup.find("div", class_="panel-story-info")
    title = manga_info.find("h1").text.strip()
    description = soup.find("div", class_="panel-story-info-description").find_all(
        text=True,
    )
    description = " ".join(description)[:200]
    image_link = soup.find("div", class_="story-info-left").find("img")["src"]
    chapters = soup.find_all("a", class_="chapter-name text-nowrap")
    end_index = min(end_index, len(chapters))
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    for chapter in range(start_index, end_index):
        chapter = chapters[chapter]
        chapter_link = chapter["href"]
        chapter_title = chapter.text.strip()
        chapter_button = telebot.types.InlineKeyboardButton(
            text=chapter_title, callback_data=f"chapter_{chapter_link}"
        )
        markup.add(chapter_button)
    if len(chapters) > end_index:
        next_button = telebot.types.InlineKeyboardButton(
            text="Next", callback_data=f"chapters_{url}_{page_number+1}"
        )
        markup.add(next_button)
    if page_number > 1:
        prev_button = telebot.types.InlineKeyboardButton(
            text="Previous", callback_data=f"chapters_{url}_{page_number-1}"
        )
        markup.add(prev_button)
    if page_number == 1:

        bot.send_photo(chat_id, image_link, caption=f"Title: {title}\n {description}")
    bot.send_message(
        chat_id,
        "Chapters:",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    data = call.data.split("_")
    #while searching for manga using manga name
    if data[0] == "search":
        page_number = int(data[-1])
        manga_name = "_".join(data[1:-1:])
        send_search_results(call.message.chat.id, manga_name, page_number)

    # while getting some chapters of a manga
    elif data[0] == "chapters":
        page_number = int(data[-1])
        url = data[1]
        sendchapters(call.message.chat.id, url,page_number)

    #while clicking on a manga displayed by /search command
    elif data[0] == "manga":
        url = data[1]
        sendchapters(call.message.chat.id, url, 1)

    # to read a specific manga chapter
    elif data[0] == "chapter":
        url = data[1]
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        all_images = soup.find_all("div", class_="container-chapter-reader")
        img_tags = [img_tag for div in all_images for img_tag in div.find_all("img")]
        alling = []
        bot.send_message(call.message.chat.id, "Total Pages: " + str(len(img_tags)))
        for idx, img_tag in enumerate(img_tags):
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
                "Accept": "image/avif,image/webp,*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://chapmanganato.to/",
            }
            img_url = img_tag["src"]

            response = requests.get(img_url, headers=headers)

            if response.status_code == 200:
                bot.send_photo(
                    call.message.chat.id,
                    response.content,
                    caption=f"Page Number: {idx + 1}",
                )
                alling.append((response.content, idx + 1))
            else:
                print(f"Failed to fetch image from URL: {img_url}")
                bot.send_message(call.message.chat.id, "Failed to fetch image")

bot.polling()
