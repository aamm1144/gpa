import requests
import time
import os
import re
from datetime import datetime

class GPAMonitor:
    def __init__(self, base_url, username, password, telegram_bot_token, telegram_chat_id):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id
        self.target_text = "3.33 / 4"
        self.session = requests.Session()
        self.dashboard_url = None  # هنحفظ فيه رابط الصفحة الرئيسية
        
    def login(self):
        """تسجيل الدخول التلقائي"""
        try:
            print("جاري تسجيل الدخول...")
            
            # جلب صفحة تسجيل الدخول أولاً
            login_page = self.session.get(self.base_url)
            
            # استخراج ViewState باستخدام regex
            viewstate_match = re.search(r'<input[^>]*name="__VIEWSTATE"[^>]*value="([^"]*)"', login_page.text)
            eventvalidation_match = re.search(r'<input[^>]*name="__EVENTVALIDATION"[^>]*value="([^"]*)"', login_page.text)
            viewstategenerator_match = re.search(r'<input[^>]*name="__VIEWSTATEGENERATOR"[^>]*value="([^"]*)"', login_page.text)
            
            # تحضير بيانات تسجيل الدخول
            login_data = {
                'txtUser': self.username,
                'txtPwd': self.password,
            }
            
            # إضافة ViewState إذا موجود
            if viewstate_match:
                login_data['__VIEWSTATE'] = viewstate_match.group(1)
            if eventvalidation_match:
                login_data['__EVENTVALIDATION'] = eventvalidation_match.group(1)
            if viewstategenerator_match:
                login_data['__VIEWSTATEGENERATOR'] = viewstategenerator_match.group(1)
            
            # البحث عن زر تسجيل الدخول
            button_match = re.search(r'<input[^>]*type="submit"[^>]*name="([^"]*)"[^>]*value="([^"]*)"', login_page.text)
            if button_match:
                login_data[button_match.group(1)] = button_match.group(2)
            
            # Headers مهمة لـ ASP.NET
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.base_url,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            print(f"بيانات تسجيل الدخول: {login_data}")
            
            # إرسال بيانات تسجيل الدخول مع تتبع الـ redirects
            response = self.session.post(self.base_url, data=login_data, headers=headers, allow_redirects=True)
            
            print(f"Response Status: {response.status_code}")
            print(f"Final URL after login: {response.url}")
            
            # حفظ الـ URL النهائي (الصفحة الرئيسية)
            self.dashboard_url = response.url
            
            # فحص نجاح تسجيل الدخول
            response_text = response.text.lower()
            
            # فحص إذا كان لسه في صفحة تسجيل الدخول
            if 'txtuser' in response_text and 'txtpwd' in response_text:
                print("❌ لسه في صفحة تسجيل الدخول - فشل في تسجيل الدخول")
                print("أول 500 حرف من الرد:")
                print(response.text[:500])
                return False
            
            # علامات نجاح تسجيل الدخول
            success_indicators = [
                'welcome', 'dashboard', 'home', 'logout', 'profile',
                'gpa', 'grades', 'student', 'contentplaceholder4_lblcurgpa',
                'contentplaceholder', 'main', 'menu'
            ]
            
            success_found = any(indicator in response_text for indicator in success_indicators)
            
            if success_found:
                print("✅ تم تسجيل الدخول بنجاح")
                print(f"تم الانتقال للصفحة: {self.dashboard_url}")
                return True
            else:
                print("❓ غير متأكد من حالة تسجيل الدخول")
                print("أول 500 حرف من الرد:")
                print(response.text[:500])
                return True  # نجرب نكمل
                
        except Exception as e:
            print(f"خطأ في تسجيل الدخول: {e}")
            return False
    
    def get_page_content(self):
        """جلب محتوى الصفحة مع تسجيل الدخول التلقائي"""
        try:
            # محاولة تسجيل الدخول أولاً
            if not self.login():
                return None
            
            # استخدام الـ URL الصحيح (الصفحة الرئيسية بعد تسجيل الدخول)
            target_url = self.dashboard_url if self.dashboard_url else self.base_url
            
            print(f"جلب محتوى الصفحة من: {target_url}")
            
            # جلب الصفحة المطلوبة بعد تسجيل الدخول
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.base_url
            }
            
            response = self.session.get(target_url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            
            print(f"طول محتوى الصفحة: {len(response.text)}")
            
            # فحص إذا كان المحتوى يحتوي على بيانات مفيدة
            if 'contentplaceholder4_lblcurgpa' in response.text.lower():
                print("✅ تم العثور على عنصر GPA في الصفحة")
            else:
                print("⚠️ لم يتم العثور على عنصر GPA - قد نحتاج للانتقال لصفحة أخرى")
            
            return response.text
            
        except Exception as e:
            print(f"خطأ في جلب الصفحة: {e}")
            return None
    
    def send_telegram_message(self, message):
        """إرسال رسالة على Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
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
                    time.sleep(1)
                
        except Exception as e:
            print(f"خطأ في إرسال الرسالة: {e}")
    
    def send_telegram_document(self, content, filename, caption):
        """إرسال ملف HTML على Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
            
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
            
            try:
                os.remove(filename)
            except:
                pass
                
            return response.json()
        except Exception as e:
            print(f"خطأ في إرسال الملف: {e}")
    
    def check_gpa_change(self):
        """فحص تغيير النص في الصفحة"""
        print("جاري فحص الصفحة...")
        content = self.get_page_content()
        
        if not content:
            print("فشل في جلب محتوى الصفحة")
            self.send_telegram_message("❌ فشل في الوصول للموقع - مشكلة في تسجيل الدخول")
            return False
        
        # البحث عن النص المحدد
        if self.target_text in content:
            print(f"✅ تم العثور على النص: {self.target_text}")
            print("لا يوجد تغيير - النتيجة لم تظهر بعد")
            return False
        else:
            print(f"🚨 لم يتم العثور على النص: {self.target_text}")
            print("تغيير محتمل في الصفحة!")
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            alert_message = f"""
🎓 <b>تحديث محتمل في النتيجة!</b>

🔍 النص المتوقع: {self.target_text}
❌ لم يتم العثور على النص في الصفحة
📅 الوقت: {timestamp}
🔗 الموقع: {self.dashboard_url or self.base_url}

⏳ جاري إرسال محتوى الصفحة...
            """
            self.send_telegram_message(alert_message)
            
            # إرسال محتوى الصفحة
            html_filename = f"result_check_{timestamp.replace(':', '-').replace(' ', '_')}.html"
            caption = f"📄 محتوى الصفحة للفحص\nالوقت: {timestamp}"
            
            self.send_telegram_document(content, html_filename, caption)
            
            return True

if __name__ == "__main__":
    WEBSITE_URL = "http://abr.su.edu.eg/"
    
    # بيانات تسجيل الدخول
    USERNAME = "202301209"
    PASSWORD = "m2qBkSVX"
    
    # إعدادات Telegram
    BOT_TOKEN = "7680451124:AAFGU99rxasd99ZbyaRxkbbV85tg2yKfG6o"
    CHAT_ID = "5824638955"
    
    print(f"Username: {USERNAME}")
    print(f"Password: {PASSWORD}")
    
    monitor = GPAMonitor(WEBSITE_URL, USERNAME, PASSWORD, BOT_TOKEN, CHAT_ID)
    monitor.check_gpa_change()
