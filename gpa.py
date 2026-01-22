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
        self.dashboard_url = None
        self.login_success = False
        
    def login_with_retry(self):
        """تسجيل الدخول مع إعادة المحاولة حتى النجاح"""
        attempt = 1
        while True:
            try:
                print(f"محاولة تسجيل الدخول #{attempt}...")
                
                # جلب صفحة تسجيل الدخول أولاً
                login_page = self.session.get(self.base_url, timeout=60)
                
                # فحص حالة الصفحة الأولى
                if login_page.status_code >= 500:
                    print(f"خطأ في السيرفر: {login_page.status_code} - انتظار 30 ثانية...")
                    time.sleep(30)
                    attempt += 1
                    continue
                
                if login_page.status_code != 200:
                    print(f"خطأ في الوصول للموقع: {login_page.status_code} - انتظار 15 ثانية...")
                    time.sleep(15)
                    attempt += 1
                    continue
                
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
                
                # إرسال بيانات تسجيل الدخول مع تتبع الـ redirects
                response = self.session.post(self.base_url, data=login_data, headers=headers, allow_redirects=True, timeout=60)
                
                print(f"Response Status: {response.status_code}")
                print(f"Final URL after login: {response.url}")
                
                # فحص أخطاء السيرفر
                if response.status_code >= 500:
                    print(f"خطأ في السيرفر: {response.status_code} - انتظار 30 ثانية...")
                    time.sleep(30)
                    attempt += 1
                    continue
                
                if response.status_code >= 400:
                    print(f"خطأ في الطلب: {response.status_code} - انتظار 15 ثانية...")
                    time.sleep(15)
                    attempt += 1
                    continue
                
                # حفظ الـ URL النهائي (الصفحة الرئيسية)
                self.dashboard_url = response.url
                
                # فحص نجاح تسجيل الدخول
                response_text = response.text.lower()
                
                # فحص إذا كان لسه في صفحة تسجيل الدخول (علامة فشل)
                if ('txtuser' in response_text and 'txtpwd' in response_text) or 'login' in response_text:
                    print("لسه في صفحة تسجيل الدخول - انتظار 10 ثوان...")
                    time.sleep(10)
                    attempt += 1
                    continue
                
                # فحص حجم المحتوى (صفحة تسجيل الدخول عادة أصغر)
                if len(response.text) < 5000:
                    print("حجم المحتوى صغير - قد يكون لسه في صفحة تسجيل الدخول - انتظار 10 ثوان...")
                    time.sleep(10)
                    attempt += 1
                    continue
                
                # علامات نجاح تسجيل الدخول
                success_indicators = [
                    'welcome', 'dashboard', 'home', 'logout', 'profile',
                    'gpa', 'grades', 'student', 'contentplaceholder4_lblcurgpa',
                    'contentplaceholder', 'main', 'menu', 'default'
                ]
                
                success_found = any(indicator in response_text for indicator in success_indicators)
                
                if success_found:
                    print("✅ تم تسجيل الدخول بنجاح!")
                    self.login_success = True
                    return True
                else:
                    print("غير متأكد من حالة تسجيل الدخول - انتظار 10 ثوان...")
                    time.sleep(10)
                    attempt += 1
                    continue
                    
            except requests.exceptions.Timeout:
                print("انتهت مهلة الاتصال - انتظار 30 ثانية...")
                time.sleep(30)
                attempt += 1
                continue
            except requests.exceptions.ConnectionError:
                print("خطأ في الاتصال - انتظار 30 ثانية...")
                time.sleep(30)
                attempt += 1
                continue
            except Exception as e:
                print(f"خطأ غير متوقع: {e} - انتظار 15 ثانية...")
                time.sleep(15)
                attempt += 1
                continue
    
    def get_page_content(self):
        """جلب محتوى الصفحة مع إعادة المحاولة"""
        if not self.login_success:
            if not self.login_with_retry():
                return None
        
        attempt = 1
        while True:
            try:
                # استخدام الـ URL الصحيح (الصفحة الرئيسية بعد تسجيل الدخول)
                target_url = self.dashboard_url if self.dashboard_url else self.base_url
                
                print(f"جلب محتوى الصفحة من: {target_url} (محاولة #{attempt})")
                
                # جلب الصفحة المطلوبة بعد تسجيل الدخول
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': self.base_url
                }
                
                response = self.session.get(target_url, headers=headers, timeout=60)
                
                # فحص حالة الاستجابة
                if response.status_code >= 500:
                    print(f"خطأ في السيرفر: {response.status_code} - انتظار 30 ثانية...")
                    time.sleep(30)
                    attempt += 1
                    continue
                
                if response.status_code >= 400:
                    print(f"خطأ في الطلب: {response.status_code} - إعادة تسجيل الدخول...")
                    self.login_success = False
                    if not self.login_with_retry():
                        continue
                    attempt += 1
                    continue
                
                response.encoding = 'utf-8'
                
                print(f"طول محتوى الصفحة: {len(response.text)}")
                
                # فحص إذا كان المحتوى يحتوي على بيانات مفيدة
                if 'contentplaceholder4_lblcurgpa' in response.text.lower():
                    print("✅ تم العثور على عنصر GPA في الصفحة")
                elif len(response.text) < 5000:
                    print("حجم المحتوى صغير - إعادة تسجيل الدخول...")
                    self.login_success = False
                    if not self.login_with_retry():
                        continue
                    attempt += 1
                    continue
                else:
                    print("⚠️ لم يتم العثور على عنصر GPA - لكن المحتوى يبدو صحيح")
                
                return response.text
                
            except requests.exceptions.Timeout:
                print("انتهت مهلة الاتصال - انتظار 30 ثانية...")
                time.sleep(30)
                attempt += 1
                continue
            except requests.exceptions.ConnectionError:
                print("خطأ في الاتصال - انتظار 30 ثانية...")
                time.sleep(30)
                attempt += 1
                continue
            except Exception as e:
                print(f"خطأ في جلب الصفحة: {e} - انتظار 15 ثانية...")
                time.sleep(15)
                attempt += 1
                continue
    
    def send_telegram_message(self, message):
        """إرسال رسالة على Telegram مع إعادة المحاولة"""
        attempt = 1
        while attempt <= 3:  # محاولة 3 مرات فقط للتليجرام
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                
                max_length = 4096
                if len(message) <= max_length:
                    data = {
                        'chat_id': self.chat_id,
                        'text': message,
                        'parse_mode': 'HTML'
                    }
                    response = requests.post(url, data=data, timeout=10)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        print(f"فشل إرسال الرسالة: {response.status_code}")
                        time.sleep(5)
                        attempt += 1
                        continue
                else:
                    # تقسيم الرسالة لأجزاء
                    parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
                    for i, part in enumerate(parts):
                        data = {
                            'chat_id': self.chat_id,
                            'text': f"الجزء {i+1}/{len(parts)}:\n\n{part}",
                            'parse_mode': 'HTML'
                        }
                        requests.post(url, data=data, timeout=10)
                        time.sleep(1)
                    return True
                    
            except Exception as e:
                print(f"خطأ في إرسال الرسالة: {e}")
                time.sleep(5)
                attempt += 1
                continue
        
        print("فشل في إرسال الرسالة بعد 3 محاولات")
        return False
    
    def send_telegram_document(self, content, filename, caption):
        """إرسال ملف HTML على Telegram مع إعادة المحاولة"""
        attempt = 1
        while attempt <= 3:  # محاولة 3 مرات فقط للتليجرام
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
                    response = requests.post(url, files=files, data=data, timeout=30)
                
                try:
                    os.remove(filename)
                except:
                    pass
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"فشل إرسال الملف: {response.status_code}")
                    time.sleep(5)
                    attempt += 1
                    continue
                    
            except Exception as e:
                print(f"خطأ في إرسال الملف: {e}")
                time.sleep(5)
                attempt += 1
                continue
        
        print("فشل في إرسال الملف بعد 3 محاولات")
        return False
    
    def check_gpa_change(self):
        """فحص تغيير النص في الصفحة - التنبيه الوحيد عند تغيير النتيجة"""
        print("جاري فحص الصفحة...")
        content = self.get_page_content()
        
        if not content:
            print("فشل في جلب محتوى الصفحة - سيتم إعادة المحاولة في الدورة التالية")
            return False
        
        # البحث عن النص المحدد
        if self.target_text in content:
            print(f"✅ تم العثور على النص: {self.target_text}")
            print("لا يوجد تغيير - النتيجة لم تظهر بعد")
            return False
        else:
            print(f"🚨 لم يتم العثور على النص: {self.target_text}")
            print("🎓 النتيجة ظهرت! إرسال التنبيه...")
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            alert_message = f"""
🎉 <b>النتيجة ظهرت!</b>

🔍 النص المتوقع: {self.target_text}
❌ لم يتم العثور على النص في الصفحة
📅 الوقت: {timestamp}
🔗 الموقع: {self.dashboard_url or self.base_url}

🎓 هذا يعني أن النتيجة الجديدة ظهرت!

⏳ جاري إرسال محتوى الصفحة...
            """
            self.send_telegram_message(alert_message)
            
            # إرسال محتوى الصفحة
            html_filename = f"result_final_{timestamp.replace(':', '-').replace(' ', '_')}.html"
            caption = f"🎓 النتيجة النهائية!\nالوقت: {timestamp}"
            
            self.send_telegram_document(content, html_filename, caption)
            
            return True

if __name__ == "__main__":
    WEBSITE_URL = "http://abr.su.edu.eg/"
    
    # بيانات تسجيل الدخول
    USERNAME = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")
    
    # إعدادات Telegram
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    print(f"Username: {USERNAME}")
    print(f"Password: {PASSWORD}")
    print("بدء مراقبة النتيجة...")
    
    monitor = GPAMonitor(WEBSITE_URL, USERNAME, PASSWORD, BOT_TOKEN, CHAT_ID)
    monitor.check_gpa_change()

