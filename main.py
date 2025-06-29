import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
BOT_TOKEN = "7918352098:AAEqEP-U1fa3iYxzGYjwCNrODGNZmIEEHcI"



# دالة لجلب معلومات الدواء من موقع rosheta
def fetch_drug_info(drug_id):
    url = f"https://www.rosheta.com/ar/{drug_id}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers , timeout=20)
    if response.status_code != 200:
        return None, None, None, None

    soup = BeautifulSoup(response.text, 'html.parser')

    # اسم الدواء
    name_tag = soup.find("h1", class_="product-name")
    drug_name = name_tag.get_text(strip=True) if name_tag else "اسم غير معروف"

    # الاسم العلمي
    scientific_name = "غير متوفر"
    list_items = soup.select("ul.arw-list-default li")
    for item in list_items:
        if "الاسم العلمي" in item.text:
            strongs = item.find_all("strong")
            if len(strongs) >= 2:
                scientific_name = strongs[1].get_text(strip=True)

    # الصورة
    img_tag = soup.select_one(".product-img img")
    image_url = img_tag["src"] if img_tag else None

    # الوصف
    desc_div = soup.select_one("div.myp_div")
    description = desc_div.get_text(separator=" ", strip=True) if desc_div else "الوصف غير متوفر."

    return drug_name, scientific_name, image_url, description


# دالة بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! فقط أرسل رقم الدواء (مثال: 9910) وسأجلب لك معلوماته من.")


# دالة التعامل مع أي رسالة نصية تحتوي على رقم
async def handle_drug_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.isdigit():
        drug_id = text
        name, scientific, image_url, description = fetch_drug_info(drug_id)

        if not image_url and not description:
            await update.message.reply_text("❌ لم يتم العثور على الدواء، تأكد من الرقم.")
        else:
            caption = f"📦 *اسم الدواء:* {name}\n🧪 *الاسم العلمي:* {scientific}\n\n📝 *الوصف:* {description}"
            if image_url:
                await update.message.reply_photo(photo=image_url, caption=caption, parse_mode='Markdown')
            else:
                await update.message.reply_text(caption, parse_mode='Markdown')
    else:
        await update.message.reply_text("🔎 فقط أرسل رقم الدواء للحصول على التفاصيل.")

# تشغيل البوت
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_drug_id))

    print("✅ البوت يعمل الآن...")
    app.run_polling()
