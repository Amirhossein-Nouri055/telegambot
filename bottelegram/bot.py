import asyncio 
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
import re
import json
import aiohttp
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bot token
TOKEN = "7695882385:AAErvHK3zKI-OukdNKKk6UVckt-c-RGcl74"

# Channel IDs
CHANNEL_IDS = ["-1002665968223"]

# Admin Chat ID
ADMIN_CHAT_ID = "601080183"

# Product data storage
PRODUCT_DATA_STORE: Dict[str, Dict[str, Any]] = {}

# Gold price cache
class GoldPriceCache:
    def __init__(self, duration_minutes: int = 5):
        self.price: Optional[int] = None
        self.timestamp: Optional[datetime] = None
        self.duration = timedelta(minutes=duration_minutes)
        self._lock = asyncio.Lock()
    
    def is_valid(self) -> bool:
        return (self.timestamp and 
                datetime.now() - self.timestamp < self.duration and 
                self.price is not None)
    
    def update(self, price: int):
        self.price = price
        self.timestamp = datetime.now()
    
    def get(self) -> Optional[int]:
        return self.price if self.is_valid() else None

gold_price_cache = GoldPriceCache(duration_minutes=5)

# Conversation states
PHOTO, CAPTION, WEIGHT, AJRAT, PROFIT, ACCESSORIES = range(6)

# Load product data
def load_product_data():
    global PRODUCT_DATA_STORE
    try:
        with open('product_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            PRODUCT_DATA_STORE = data if isinstance(data, dict) else {}
            logger.info(f"Loaded {len(PRODUCT_DATA_STORE)} product records")
    except FileNotFoundError:
        PRODUCT_DATA_STORE = {}
    except Exception as e:
        logger.error(f"Error loading product data: {e}")
        PRODUCT_DATA_STORE = {}

# Save product data
def save_product_data():
    try:
        with open('product_data.json', 'w', encoding='utf-8') as f:
            json.dump(PRODUCT_DATA_STORE, f, ensure_ascii=False, indent=2)
        logger.info("Product data saved")
    except Exception as e:
        logger.error(f"Error saving product data: {e}")

# Clean old data
def clean_old_data():
    threshold = datetime.now() - timedelta(days=90)
    removed_count = 0
    
    for message_id in list(PRODUCT_DATA_STORE.keys()):
        if 'timestamp' in PRODUCT_DATA_STORE[message_id]:
            try:
                if datetime.fromisoformat(PRODUCT_DATA_STORE[message_id]['timestamp']) < threshold:
                    del PRODUCT_DATA_STORE[message_id]
                    removed_count += 1
            except ValueError:
                del PRODUCT_DATA_STORE[message_id]
                removed_count += 1
    
    if removed_count > 0:
        logger.info(f"Removed {removed_count} old records")
        save_product_data()

# Get gold price
async def get_gold_price() -> Tuple[Optional[int], Optional[str]]:
    cached_price = gold_price_cache.get()
    if cached_price is not None:
        return cached_price, None

    async with gold_price_cache._lock:
        cached_price = gold_price_cache.get()
        if cached_price is not None:
            return cached_price, None

        url = "https://www.tgju.org/profile/geram18"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return None, f"خطا در دریافت قیمت: HTTP {response.status}"
                    
                    html_content = await response.text()
            
            soup = BeautifulSoup(html_content, "html.parser")
            price_tag = soup.find("span", {"data-col": "info.last_trade.PDrCotVal"})
            
            if price_tag:
                price_str = price_tag.text.strip().replace(",", "")
                try:
                    price = int(price_str)
                    gold_price_cache.update(price)
                    return price, None
                except ValueError:
                    return None, "قیمت طلا نامعتبر است!"
            else:
                return None, "قیمت طلا پیدا نشد!"
        
        except Exception as e:
            logger.error(f"Error fetching gold price: {e}")
            return None, f"خطای غیرمنتظره: {e}"

# Calculate price
def calculate_price(weight: float, ajrat: float, ajrat_type: str,
                    profit: float, profit_type: str, price_per_gram: int, accessories: float = 0) -> int:
    base_price = weight * price_per_gram
    ajrat_amount = base_price * (ajrat / 100) if ajrat_type == 'p' else ajrat
    intermediate_price = base_price + ajrat_amount
    profit_amount = intermediate_price * (profit / 100) if profit_type == 'p' else profit
    accessories_amount = accessories * 10
    total_price = intermediate_price + profit_amount + accessories_amount
    return int(total_price)

# Start command
async def start_product(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("🔒 این دستور فقط برای ادمین قابل استفاده است!")
        return ConversationHandler.END
    
    context.user_data.clear()
    await update.message.reply_text("🎯 مرحله 1 از 6: لطفاً تصویر محصول را ارسال کنید")
    return PHOTO

# Handle photo
async def handle_photo(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ لطفاً یک تصویر معتبر ارسال کنید!")
        return PHOTO
    
    photo = update.message.photo[-1]
    if photo.file_size and photo.file_size > 10 * 1024 * 1024:
        await update.message.reply_text("⚠️ حجم تصویر خیلی بزرگ است! حداکثر حجم مجاز: 10 مگابایت")
        return PHOTO
    
    context.user_data['photo'] = photo.file_id
    await update.message.reply_text("✅ تصویر با موفقیت دریافت شد!\n\n🎯 مرحله 2 از 6: لطفاً کپشن محصول را وارد کنید")
    return CAPTION

# Handle caption
async def handle_caption(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    caption = update.message.text.strip()
    if not caption:
        await update.message.reply_text("❌ کپشن نمی‌تواند خالی باشد! لطفاً متن کپشن را وارد کنید:")
        return CAPTION
    
    if len(caption.encode('utf-8')) > 1024:
        await update.message.reply_text("⚠️ کپشن خیلی طولانی است! حداکثر 1024 کاراکتر مجاز است")
        return CAPTION
    
    context.user_data['caption'] = caption
    await update.message.reply_text("✅ کپشن با موفقیت ثبت شد!\n\n🎯 مرحله 3 از 6: لطفاً وزن محصول را به گرم وارد کنید\nمثال: 2.5")
    return WEIGHT

# Handle weight
async def handle_weight(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text.strip())
        if weight <= 0 or weight > 10000:
            await update.message.reply_text("❌ وزن نامعتبر است! لطفاً عددی بین 0.1 تا 10000 گرم وارد کنید:")
            return WEIGHT
        
        context.user_data['product'] = {'weight': weight}
        await update.message.reply_text(f"✅ وزن محصول: {weight} گرم\n\n🎯 مرحله 4 از 6: لطفاً اجرت را وارد کنید\nمثال: 15% یا 50000 تومان")
        return AJRAT
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!\nمثال: 2.5")
        return WEIGHT

# Handle ajrat
async def handle_ajrat(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = re.match(r'^([\d.,]+)\s*(%|تومان|تومن)?$', text, re.IGNORECASE)
    if not match:
        await update.message.reply_text("❌ فرمت نامعتبر! لطفاً یکی از فرمت‌های زیر را استفاده کنید:\n• 15%\n• 50000 تومان")
        return AJRAT
    
    ajrat_str, ajrat_type = match.groups()
    try:
        ajrat = float(ajrat_str.replace(',', ''))
    except ValueError:
        await update.message.reply_text("❌ عدد نامعتبر! لطفاً دوباره وارد کنید:")
        return AJRAT
    
    ajrat_type = 'p' if ajrat_type == '%' else 'f'
    
    if ajrat < 0 or (ajrat_type == 'p' and ajrat > 100):
        await update.message.reply_text("❌ اجرت نامعتبر است! درصد باید بین 0 تا 100 باشد")
        return AJRAT
    
    if ajrat_type == 'f':
        ajrat *= 10
    
    context.user_data['product']['ajrat'] = ajrat
    context.user_data['product']['ajrat_type'] = ajrat_type
    
    ajrat_display = f"{ajrat}%" if ajrat_type == 'p' else f"{ajrat / 10:,.0f} تومان"
    await update.message.reply_text(f"✅ اجرت: {ajrat_display}\n\n🎯 مرحله 5 از 6: لطفاً سود را وارد کنید\nمثال: 7% یا 30000 تومان")
    return PROFIT

# Handle profit
async def handle_profit(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = re.match(r'^([\d.,]+)\s*(%|تومان|تومن)?$', text, re.IGNORECASE)
    if not match:
        await update.message.reply_text("❌ فرمت نامعتبر! لطفاً یکی از فرمت‌های زیر را استفاده کنید:\n• 7%\n• 30000 تومان")
        return PROFIT
    
    profit_str, profit_type = match.groups()
    try:
        profit = float(profit_str.replace(',', ''))
    except ValueError:
        await update.message.reply_text("❌ عدد نامعتبر! لطفاً دوباره وارد کنید:")
        return PROFIT
    
    profit_type = 'p' if profit_type == '%' else 'f'
    
    if profit < 0 or (profit_type == 'p' and profit > 100):
        await update.message.reply_text("❌ سود نامعتبر است! درصد باید بین 0 تا 100 باشد")
        return PROFIT
    
    if profit_type == 'f':
        profit *= 10
    
    context.user_data['product']['profit'] = profit
    context.user_data['product']['profit_type'] = profit_type
    
    profit_display = f"{profit}%" if profit_type == 'p' else f"{profit / 10:,.0f} تومان"
    await update.message.reply_text(f"✅ سود: {profit_display}\n\n🎯 مرحله 6 از 6: لطفاً هزینه متعلقات را وارد کنید ")
    return ACCESSORIES

async def post_to_channel(update, context, accessories_cost):
    context.user_data['product']['accessories'] = accessories_cost
    await update.message.reply_text(f"✅ هزینه متعلقات: {accessories_cost:,.0f} تومان")
    await update.message.reply_text("🔄 در حال پردازش و ارسال به کانال...")
    
    caption = context.user_data['caption'] + "\n\n📌 برای ثبت سفارش به آیدی زیر پیام دهید:\n🆔 @lamingoldgallery\n\n💎 برای مشاهده قیمت به‌روز، روی دکمه زیر کلیک کنید:"
    
    try:
        posted_count = 0
        for channel_id in CHANNEL_IDS:
            try:
                message = await context.bot.send_photo(
                    chat_id=channel_id,
                    photo=context.user_data['photo'],
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💎 محاسبه قیمت آنلاین", callback_data=f"calculate_price|pending")]
                    ])
                )
                
                message_id = str(message.message_id)
                PRODUCT_DATA_STORE[message_id] = {
                    'w': context.user_data['product']['weight'],
                    'a': context.user_data['product']['ajrat'],
                    'at': context.user_data['product']['ajrat_type'],
                    'p': context.user_data['product']['profit'],
                    'pt': context.user_data['product']['profit_type'],
                    'accessories': context.user_data['product']['accessories'],
                    'timestamp': datetime.now().isoformat()
                }
                
                callback_data = f'calculate_price|{message_id}'
                if len(callback_data.encode('utf-8')) <= 64:
                    await context.bot.edit_message_reply_markup(
                        chat_id=channel_id,
                        message_id=message.message_id,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💎 محاسبه قیمت آنلاین", callback_data=callback_data)]
                        ])
                    )
                posted_count += 1
                
            except Exception as e:
                logger.error(f"Error posting to channel {channel_id}: {e}")
                continue
        
        if posted_count > 0:
            save_product_data()
            clean_old_data()
            await update.message.reply_text(f"🎉 محصول با موفقیت در {posted_count} کانال منتشر شد!\n\n✅ عملیات تکمیل شد")
        else:
            await update.message.reply_text("❌ خطا در انتشار پست در تمام کانال‌ها!\nلطفاً دوباره تلاش کنید")
            
    except Exception as e:
        logger.error(f"Error posting to channel: {e}")
        await update.message.reply_text(f"❌ خطا در انتشار پست: {e}\nلطفاً دوباره تلاش کنید")

async def handle_accessories(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "0":
        await post_to_channel(update, context, 0)
        return ConversationHandler.END
    
    try:
        accessories_cost = float(text.replace(',', ''))
        if accessories_cost < 0:
            await update.message.reply_text("❌ هزینه متعلقات نمی‌تواند منفی باشد! لطفاً یک عدد مثبت وارد کنید:")
            return ACCESSORIES
        await post_to_channel(update, context, accessories_cost)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!\nمثال: 100000 یا 0")
        return ACCESSORIES

# Cancel command
async def cancel(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد.\n\nبرای شروع دوباره از دستور /start استفاده کنید.")
    return ConversationHandler.END

# Handle button clicks
async def button_callback(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    callback_data = query.data.split('|', 1)
    if len(callback_data) != 2 or callback_data[0] != 'calculate_price':
        await query.answer("❌ خطا: داده‌های نامعتبر!", show_alert=True)
        return
    
    message_id = callback_data[1]
    
    if message_id == 'pending':
        await query.answer("⏳ پست در حال پردازش است، لطفاً چند لحظه صبر کنید.", show_alert=True)
        return
    
    product_data = PRODUCT_DATA_STORE.get(message_id)
    if not product_data:
        await query.answer("❌ خطا: اطلاعات این محصول یافت نشد!\nلطفاً محصول را دوباره ثبت کنید.", show_alert=True)
        return
    
    try:
        weight = float(product_data['w'])
        ajrat = float(product_data['a'])
        ajrat_type = product_data['at']
        profit = float(product_data['p'])
        profit_type = product_data['pt']
        accessories = float(product_data['accessories'])
    except (KeyError, ValueError) as e:
        await query.answer("❌ خطا: اطلاعات محصول ناقص یا نامعتبر است!", show_alert=True)
        return
    
    price_per_gram, error = await get_gold_price()
    if price_per_gram is None:
        await query.answer(f"❌ خطا در دریافت قیمت طلا:\n{error}", show_alert=True)
        return
    
    total_price = calculate_price(
        weight, ajrat, ajrat_type, profit, profit_type, price_per_gram, accessories
    )
    
    message = (
        f"💰 قیمت طلا (هر گرم): {price_per_gram // 10:,} تومان\n"
        f"💵 قیمت کل: {total_price // 10:,} تومان"
    )
    
    try:
        await query.answer(message, show_alert=True)
    except Exception as e:
        logger.error(f"Error sending result: {e}")
        short_message = f"💵 قیمت کل: {total_price // 10:,} تومان"
        await query.answer(short_message, show_alert=True)

# Error handler
async def error_handler(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# Main function
def main():
    load_product_data()
    clean_old_data()
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_product)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight)],
            AJRAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ajrat)],
            PROFIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profit)],
            ACCESSORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_accessories)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    
    logger.info("Starting bot...")
    application.run_polling(
        allowed_updates=telegram.Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()