import feedparser
import telebot
import time
import schedule
import os
import requests
from datetime import datetime
from html.parser import HTMLParser

# ════════════════════════════════════════════
# ⚙️ الإعدادات الأساسية
# ════════════════════════════════════════════
TOKEN = "8531181643:AAGYZgnY46GzrelXkUPdFrCYOg0xetJm-5Y"
CHANNEL = "@sdghd43"

RSS_SOURCES = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptoslate.com/feed/",
    "https://www.bitcoinmagazine.com/feed",
]

POSTED_FILE = "posted.txt"
SCHEDULED_TIMES = ["01:47"]  # 4 مرات يوميًا

bot = telebot.TeleBot(TOKEN)

# ════════════════════════════════════════════
# 📝 دوال مساعدة
# ════════════════════════════════════════════

def translate_text(text):
    """ترجمة النص للعربية باستخدام Google Translate API المجاني"""
    try:
        if len(text) > 5000:
            text = text[:5000]
        
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': 'en',
            'tl': 'ar',
            'dt': 't',
            'q': text
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            translated = ''.join([item[0] for item in result[0] if item[0]])
            return translated if translated else text
        else:
            return text
    except Exception as e:
        print(f"⚠️ خطأ في الترجمة: {e}")
        return text

def get_article_content(link):
    """جلب محتوى المقال الكامل من الرابط"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(link, timeout=10, headers=headers)
        if response.status_code == 200:
            # استخراج نص بسيط من HTML
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.in_paragraph = False
                
                def handle_starttag(self, tag, attrs):
                    if tag == 'p':
                        self.in_paragraph = True
                
                def handle_endtag(self, tag):
                    if tag == 'p':
                        self.in_paragraph = False
                
                def handle_data(self, data):
                    if self.in_paragraph and data.strip():
                        self.text.append(data.strip())
            
            parser = TextExtractor()
            parser.feed(response.text)
            
            # دمج الفقرات وأخذ أول 3-4 فقرات
            paragraphs = parser.text[:4]
            content = ' '.join(paragraphs)
            
            # تحديد الطول (حوالي 800-1000 حرف)
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            return content if content else None
    except Exception as e:
        print(f"⚠️ خطأ في جلب محتوى المقال: {e}")
        return None

def already_posted(link):
    """التحقق من نشر الخبر سابقاً"""
    if not os.path.exists(POSTED_FILE):
        return False
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        return link.strip() in f.read().splitlines()

def save_posted(link):
    """حفظ رابط الخبر المنشور"""
    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(link.strip() + "\n")

def fetch_news():
    """جلب خبر من المصادر مع التنوع بين المصادر"""
    import random
    
    # خلط المصادر عشوائياً لضمان التنوع
    shuffled_sources = RSS_SOURCES.copy()
    random.shuffle(shuffled_sources)
    
    all_entries = []
    
    # جمع كل الأخبار من المصادر
    for source in shuffled_sources:
        try:
            print(f"🔍 فحص المصدر: {source}")
            feed = feedparser.parse(source)
            for entry in feed.entries:
                # إضافة معلومة المصدر لكل خبر
                entry.source_url = source
                all_entries.append(entry)
        except Exception as e:
            print(f"⚠️ خطأ في قراءة المصدر {source}: {e}")
            continue
    
    if not all_entries:
        return None
    
    # خلط الأخبار عشوائياً لضمان التنوع
    random.shuffle(all_entries)
    
    # أولاً: حاول تلاقي خبر جديد لم ينشر
    for entry in all_entries:
        if not already_posted(entry.link):
            return entry
    
    # ثانياً: لو كل الأخبار منشورة، خذ خبر عشوائي (حتى لو قديم)
    print("⚠️ كل الأخبار منشورة، سيتم إعادة نشر خبر قديم...")
    return random.choice(all_entries) if all_entries else None

def format_message(title, link, source_name, summary=""):
    """تنسيق رسالة الخبر بشكل جريدة احترافية"""
    
    # ترجمة العنوان
    print("🔤 جاري ترجمة العنوان...")
    title_ar = translate_text(title)
    
    # ترجمة الملخص إذا كان موجود
    summary_ar = ""
    if summary:
        print("🔤 جاري ترجمة المحتوى...")
        summary_ar = translate_text(summary)
    
    # الوقت الحالي
    now = datetime.now()
    date_ar = now.strftime("%d/%m/%Y")
    time_ar = now.strftime("%I:%M %p")
    
    # التنسيق كجريدة احترافية
    message = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   📰 *صحيفة الكريبتو*   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

*{title_ar}*

━━━━━━━━━━━━━━━━━━━━━━

"""
    
    # إضافة الملخص إذا كان موجود
    if summary_ar:
        message += f"""📄 *التفاصيل:*

{summary_ar}

━━━━━━━━━━━━━━━━━━━━━━

"""
    
    message += f"""📌 *المصدر:* {source_name}
📅 *التاريخ:* {date_ar}
🕐 *الوقت:* {time_ar}

🔗 [اقرأ الخبر كاملاً]({link})

━━━━━━━━━━━━━━━━━━━━━━
💎 _تابعنا لآخر أخبار عالم الكريبتو_
    """
    
    return message

def get_source_name(link):
    """استخراج اسم المصدر من الرابط"""
    if "cointelegraph" in link:
        return "CoinTelegraph"
    elif "coindesk" in link:
        return "CoinDesk"
    elif "cryptoslate" in link:
        return "CryptoSlate"
    elif "bitcoinmagazine" in link:
        return "Bitcoin Magazine"
    elif "decrypt.co" in link:
        return "Decrypt"
    else:
        return "مصدر خارجي"

def publish_news():
    """نشر خبر على القناة (جديد أو قديم)"""
    print(f"\n{'='*50}")
    print(f"🔍 جاري البحث عن أخبار...")
    print(f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    news = fetch_news()
    
    if news is None:
        print("❌ لا توجد أخبار متاحة من المصادر")
        print(f"{'='*50}\n")
        return
    
    source_name = get_source_name(news.link)
    
    # محاولة جلب ملخص المقال
    print("📄 جاري جلب محتوى المقال...")
    summary = get_article_content(news.link)
    
    if summary:
        print(f"✅ تم جلب الملخص ({len(summary)} حرف)")
    else:
        print("⚠️ لم يتم العثور على محتوى، سيتم استخدام الوصف من RSS")
        # استخدام الوصف من RSS كبديل
        summary = getattr(news, 'summary', '')
    
    message = format_message(news.title, news.link, source_name, summary)
    
    try:
        bot.send_message(
            CHANNEL, 
            message, 
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        save_posted(news.link)
        print(f"✅ تم نشر خبر من {source_name}")
        print(f"📝 العنوان: {news.title[:50]}...")
    except Exception as e:
        print(f"❌ خطأ في النشر: {e}")
    
    print(f"{'='*50}\n")

# ════════════════════════════════════════════
# 🚀 تشغيل البوت
# ════════════════════════════════════════════

def main():
    print("\n" + "="*50)
    print("🤖 بوت أخبار الكريبتو - تم التشغيل بنجاح!")
    print("="*50)
    print(f"📢 القناة: {CHANNEL}")
    print(f"⏰ مواعيد النشر: {', '.join(SCHEDULED_TIMES)}")
    print(f"📡 عدد المصادر: {len(RSS_SOURCES)}")
    print("="*50 + "\n")
    
    # جدولة المهام
    for t in SCHEDULED_TIMES:
        schedule.every().day.at(t).do(publish_news)
        print(f"⏰ تم جدولة النشر في الساعة: {t}")
    
    print("\n🔄 البوت يعمل الآن... اضغط Ctrl+C للإيقاف\n")
    
    # نشر خبر عند التشغيل (للاختبار)
    print("🧪 جاري نشر خبر تجريبي...")
    publish_news()
    
    # الحلقة الرئيسية
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # فحص كل 30 ثانية
    except KeyboardInterrupt:
        print("\n\n❌ تم إيقاف البوت بواسطة المستخدم")
        print("="*50 + "\n")

if __name__ == "__main__":
    main()