# GitHub Integration Setup Guide

## مراحل راه‌اندازی GitHub برای ذخیره‌سازی داده‌ها

### 1. ایجاد GitHub Token

1. به آدرس https://github.com/settings/tokens بروید
2. روی "Generate new token" کلیک کنید
3. نام token را وارد کنید (مثل: telegram-bot-token)
4. دسترسی‌های زیر را انتخاب کنید:
   - `repo` (Full control of private repositories)
   - `public_repo` (Access public repositories)
5. روی "Generate token" کلیک کنید
6. Token را کپی کنید (فقط یک بار نمایش داده می‌شود)

### 2. تنظیم متغیرهای محیطی در Railway

در پنل Railway:

1. به پروژه خود بروید
2. روی تب "Variables" کلیک کنید
3. متغیرهای زیر را اضافه کنید:

```
GITHUB_TOKEN=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
GITHUB_REPO=Amirhossein-Nouri055/telegambot.git
```

### 3. تنظیم Repository

1. Repository خود را public کنید (یا token را با دسترسی private تنظیم کنید)
2. فایل `product_data.json` را در root directory قرار دهید
3. محتوای اولیه فایل:
```json
{}
```

### 4. تست عملکرد

پس از تنظیم، bot به صورت خودکار:
- داده‌ها را از GitHub می‌خواند
- تغییرات را در GitHub ذخیره می‌کند
- در صورت عدم دسترسی به GitHub، از فایل محلی استفاده می‌کند

### 5. مشاهده داده‌ها

می‌توانید داده‌های ذخیره شده را در GitHub repository خود مشاهده کنید:
- فایل `product_data.json` در root directory
- تاریخچه تغییرات در تب "Commits"
