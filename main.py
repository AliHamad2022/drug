import requests
from bs4 import BeautifulSoup
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, InlineQueryHandler

# توكن البوت
BOT_TOKEN = "7918352098:AAEqEP-U1fa3iYxzGYjwCNrODGNZmIEEHcI"

# قراءة ملف الأدوية
df = pd.read_excel("drug.xlsx")
df.fillna("", inplace=True)
df = df.astype(str)
df.columns = df.columns.str.strip()

# --------- دوال الكود الأول: جلب معلومات الدواء من rosheta ---------
def fetch_drug_info(drug_id):
    url = f"https://www.rosheta.com/ar/{drug_id}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return None, None, None, None
        soup = BeautifulSoup(response.text, 'html.parser')

        name_tag = soup.find("h1", class_="product-name")
        drug_name = name_tag.get_text(strip=True) if name_tag else "اسم غير معروف"

        scientific_name = "غير متوفر"
        list_items = soup.select("ul.arw-list-default li")
        for item in list_items:
            if "الاسم العلمي" in item.text:
                strongs = item.find_all("strong")
                if len(strongs) >= 2:
                    scientific_name = strongs[1].get_text(strip=True)

        img_tag = soup.select_one(".product-img img")
        image_url = img_tag["src"] if img_tag else None

        desc_div = soup.select_one("div.myp_div")
        description = desc_div.get_text(separator=" ", strip=True) if desc_div else "الوصف غير متوفر."

        return drug_name, scientific_name, image_url, description
    except Exception as e:
        return None, None, None, None

# --------- أوامر وبوت الكود الثاني ---------

# بدء البوت: يعرض القائمة + خيارات البحث
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # لو الرسالة من أمر /start
    if update.message:
        keyboard = [
            [InlineKeyboardButton("📋 عرض الأدوية", callback_data="list_drugs_1")],
            [InlineKeyboardButton("🏷️ تصنيف حسب الشكل", callback_data="by_form")],
            [InlineKeyboardButton("🔍 بحث عن دواء", switch_inline_query_current_chat="")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("أهلاً بك! اختار أحد الخيارات، أو أرسل رقم دواء لجلب معلوماته  :", reply_markup=reply_markup)

# عرض قائمة الأدوية مع صفحات
async def list_drugs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split('_')[-1])
    items_per_page = 5

    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    subset = df.iloc[start_idx:end_idx]

    keyboard = []
    for _, row in subset.iterrows():
        keyboard.append([InlineKeyboardButton(f"{row['Brand Name']} ({row['Strength']})", callback_data=f"drug_{row['id']}")])

    nav = []
    if start_idx > 0:
        nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"list_drugs_{page-1}"))
    if end_idx < len(df):
        nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"list_drugs_{page+1}"))
    if nav:
        keyboard.append(nav)

    await query.edit_message_text("قائمة الأدوية:", reply_markup=InlineKeyboardMarkup(keyboard))

# عرض التصنيفات
async def show_forms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    forms = sorted(df["Dosage Form"].unique())
    keyboard = [[InlineKeyboardButton(f, callback_data=f"form_{f}")] for f in forms]
    await query.edit_message_text("اختر شكل الدواء:", reply_markup=InlineKeyboardMarkup(keyboard))

# عرض الأدوية حسب الشكل
async def list_by_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    form = query.data.split('_', 1)[1]
    filtered = df[df["Dosage Form"] == form]

    keyboard = []
    for _, row in filtered.iterrows():
        keyboard.append([InlineKeyboardButton(f"{row['Brand Name']} ({row['Strength']})", callback_data=f"drug_{row['id']}")])

    await query.edit_message_text(f"الأدوية بشكل: {form}", reply_markup=InlineKeyboardMarkup(keyboard))

# عرض تفاصيل الدواء
async def show_drug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    drug_id = query.data.split('_', 1)[1]
    row = df[df["id"] == drug_id].iloc[0]

    text = f"💊 <b>{row['Brand Name']}</b>\n"
    text += f"• الإسم العلمي: {row['Generic Name']}\n"
    text += f"• الشكل الدوائي: {row['Dosage Form']}\n"
    text += f"• التركيز: {row['Strength']}"
    await query.edit_message_text(text, parse_mode="HTML")

# البحث الذكي بالوضع inline
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower()
    results = []

    if query:
        filtered = df[
            df["Brand Name"].str.lower().str.contains(query) |
            df["Generic Name"].str.lower().str.contains(query) |
            df["Dosage Form"].str.lower().str.contains(query) |
            df["Strength"].str.lower().str.contains(query)
        ].head(20)

        for _, row in filtered.iterrows():
            text = f"💊 <b>{row['Brand Name']}</b>\n"
            text += f"• الإسم العلمي: {row['Generic Name']}\n"
            text += f"• الشكل الدوائي: {row['Dosage Form']}\n"
            text += f"• التركيز: {row['Strength']}"
            results.append(
                InlineQueryResultArticle(
                    id=row['id'],
                    title=row['Brand Name'],
                    input_message_content=InputTextMessageContent(text, parse_mode="HTML"),
                    description=row['Generic Name']
                )
            )

    await update.inline_query.answer(results, cache_time=1)

# --------- دالة التعامل مع رسالة رقم الدواء لجلب معلومات من rosheta ---------
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

# --------- بناء التطبيق وتسجيل الهاندلرز ---------
app = ApplicationBuilder().token(BOT_TOKEN).build()

# هاندلر البداية (start)
app.add_handler(CommandHandler("start", start))

# هاندلرز القائمة والتصنيفات
app.add_handler(CallbackQueryHandler(list_drugs, pattern="^list_drugs_"))
app.add_handler(CallbackQueryHandler(show_forms, pattern="^by_form$"))
app.add_handler(CallbackQueryHandler(list_by_form, pattern="^form_"))
app.add_handler(CallbackQueryHandler(show_drug, pattern="^drug_"))

# هاندلر الرسائل النصية: يحاول جلب دواء برقم، أو يعرض رسالة إرشادية
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_drug_id))

# هاندلر البحث بالوضع inline
app.add_handler(InlineQueryHandler(inline_query))

print("✅ البوت يعمل الآن...")
app.run_polling()
