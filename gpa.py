import requests
import re
import time
import os
import json
from datetime import datetime

class GPAMonitor:
    def __init__(self, url, cookies, telegram_bot_token, telegram_chat_id):
        self.url = url
        self.cookies = cookies
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id
        self.last_gpa = None
        
    def extract_gpa_from_html(self, html_content):
        """استخراج قيمة GPA من HTML"""
        match = re.search(r'<span id="ContentPlaceHolder4_lblCurCGPA">:\s*([0-9.]+)\s*/\s*4</span>', html_content)
        if match:
            return float(match.group(1))
        return None
    
    def get_page_content(self):
        """جلب محتوى الصفحة بـ requests"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            response = requests.get(self.url, cookies=self.cookies, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            return response.text
        except Exception as e:
            print(f"خطأ في جلب الصفحة: {e}")
            return None
    
    def send_telegram_message(self, message):
        """إرسال رسالة نصية على Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            # تقسيم الرسالة إذا كانت طويلة جداً
            max_length = 4096
            if len(message) <= max_length:
                data = {
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, data=data)
                return response.json()
            else:
                # تقسيم الرسالة لأجزاء
                parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
                for i, part in enumerate(parts):
                    data = {
                        'chat_id': self.chat_id,
                        'text': f"الجزء {i+1}/{len(parts)}:\n\n{part}",
                        'parse_mode': 'HTML'
                    }
                    requests.post(url, data=data)
                    time.sleep(1)  # تأخير بسيط بين الرسائل
                
        except Exception as e:
            print(f"خطأ في إرسال الرسالة: {e}")
    
    def send_telegram_document(self, content, filename, caption):
        """إرسال ملف HTML على Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
            
            # حفظ المحتوى في ملف مؤقت
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            with open(filename, 'rb') as document:
                files = {'document': document}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, files=files, data=data)
            
            # حذف الملف المؤقت
            try:
                os.remove(filename)
            except:
                pass
                
            return response.json()
        except Exception as e:
            print(f"خطأ في إرسال الملف: {e}")
    
    def check_gpa_change(self):
        """فحص تغيير GPA والتعامل معه"""
        print("جاري فحص الصفحة...")
        content = self.get_page_content()
        
        if not content:
            print("فشل في جلب محتوى الصفحة")
            return False
            
        current_gpa = self.extract_gpa_from_html(content)
        
        if current_gpa is None:
            print("لم يتم العثور على GPA في الصفحة")
            return False
            
        print(f"GPA الحالي: {current_gpa}")
        
        # إذا كانت أول مرة
        if self.last_gpa is None:
            self.last_gpa = current_gpa
            print(f"تم حفظ GPA الأولي: {current_gpa}")
            return False
            
        # إذا تغير GPA
        if current_gpa != self.last_gpa:
            print(f"🚨 تغير GPA من {self.last_gpa} إلى {current_gpa}")
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # إرسال رسالة التنبيه الأولى
            alert_message = f"""
🎓 <b>تحديث GPA!</b>

📊 GPA السابق: {self.last_gpa}
📈 GPA الجديد: {current_gpa}
📅 الوقت: {timestamp}
🔗 الموقع: {self.url}

⏳ جاري إرسال محتوى الصفحة كاملاً...
            """
            self.send_telegram_message(alert_message)
            
            # إرسال محتوى الصفحة كاملاً
            html_filename = f"gpa_result_{timestamp.replace(':', '-').replace(' ', '_')}.html"
            caption = f"📄 محتوى الصفحة كاملاً\nGPA: {self.last_gpa} → {current_gpa}\nالوقت: {timestamp}"
            
            self.send_telegram_document(content, html_filename, caption)
            
            # إرسال جزء من النص أيضاً للمراجعة السريعة
            text_preview = f"""
📋 <b>معاينة سريعة للمحتوى:</b>

{content[:1000]}...

📎 تم إرسال الملف HTML كاملاً أعلاه
            """
            self.send_telegram_message(text_preview)
            
            # تحديث آخر GPA
            self.last_gpa = current_gpa
            return True
            
        else:
            print("لا يوجد تغيير في GPA")
            
        return False

# الاستخدام
if __name__ == "__main__":
    # إعدادات الموقع
    WEBSITE_URL = "http://abr.su.edu.eg/"
    
    # الكوكيز المحدثة من الملف JSON
    COOKIES = {
        '_ga': 'GA1.1.945105666.1738610763',
        '_ga_87KWQHSQGL': 'GS2.1.s1748892301$o18$g1$t1748892829$j60$l0$h0',
        '_ga_JNGYN0KRYJ': 'GS2.1.s1746617694$o7$g1$t1746617705$j0$l0$h0',
        '_ga_SQJQFBDRE6': 'GS2.1.s1748257152$o15$g1$t1748257297$j60$l0$h0$d47LOJIUH4fZjrVmnwFW5bRYeVz3u1KzGRg',
        '_gcl_au': '1.1.600585025.1746617688',
        '_tt_enable_cookie': '1',
        '_ttp': 'zCT_WB3rWg6rKgbGWBo1T5lObyK.tt.2',
        'PHPSESSID': '6fe18eb7a6b3e354011ca876ec8c7d3c',
        'ttcsid': '1746617695875::d5xAgPANMPPZ_Tx14C7O.2.1746617695878',
        'ttcsid_CG9HV9JC77U77CS2FAQ0': '1746617695874::6EKoa3BZRfZvtcqBIj1K.2.1746617696099',
        'ttcsid_COEJ6HJC77U9JEKSS7K0': '1746617695878::qXwVkb6A8Dh2h-OszltG.2.1746617696099',
        '.ASPXAUTH': '0CC6F9102E8E6200311C99DACB84FD5C77A439520B30C68AA061C27EEF3C63AA4A9B561898EA23107D244986FF67C6FD31BD62AC2C977D3C1C74157BCF8CBA100034268194F673AEC828C54E28496A8F8C8DC257D90942B03AA5DD2DA5F483A8',
        'acaid': '2024',
        'ai_user': 'US9R0|2025-04-06T00:34:50.955Z',
        'ASP.NET_SessionId': 'xvpbbrsaz4qbg5d5ieszh3sc',
        'calc_grade': '2',
        'facid': '2',
        'gid': '9179586123494hamKJSD876ASLAS917hmed+md917D876ASLASAhmed+9179586',
        'myUsr': '202301209',
        'progid': '1',
        'pwd': 'm2qBkSVX',
        'regAllow': '1',
        'regno': '2',
        'sav': '1',
        'semid': '2',
        'sess': 'xvpbbrsaz4qbg5d5ieszh3sc',
        'sq': '9179586',
        'stat': '1',
        'stdid': '20230111',
        'trials': '0',
        'UN': '202301209'
    }
    
    # إعدادات Telegram
    BOT_TOKEN = "7680451124:AAFGU99rxasd99ZbyaRxkbbV85tg2yKfG6o"
    CHAT_ID = "5824638955"
    
    monitor = GPAMonitor(WEBSITE_URL, COOKIES, BOT_TOKEN, CHAT_ID)
    monitor.check_gpa_change()
