# anwaltsagent.de — Session Checkpoint (Freeze v1.0)

_Last updated: 2026-03-08_

## أين وقفنا؟
وصل المشروع إلى **Baseline ثابت** يعمل كنظام Inbound SEO لبيع الدومين:

1. توليد مقال SEO عبر `scripts/generate_article.py`.
2. حفظ المقال داخل `content/posts/`.
3. تنزيل صورة من Unsplash وحفظها في `static/images/` وربطها في front matter.
4. نشر الموقع عبر GitHub Actions إلى Cloudflare Pages.
5. عرض CTA بيع الدومين داخل الصفحة الرئيسية والمقال.

## System Freeze — Version 1.0

```text
Domain
↓
Cloudflare DNS
↓
Cloudflare Pages
↓
GitHub Repo
↓
GitHub Actions
↓
generate_article.py
↓
Hugo Static Site
↓
SEO Articles + Domain Sale CTA
```

## قرارات مثبتة (Locked Decisions)

- الصفحة الرئيسية تعرض **أول 3 مقالات** للحفاظ على UX والتركيز على بيع الدومين.
- CTA داخل المقال يجب أن يكون طبيعيًا وغير سبامي.
- تنظيف مخرجات AI إلزامي (junk prefixes + fenced markdown + front matter lines داخل body).
- خط الصور المعتمد: Unsplash API → `static/images/` → front matter → Hugo render.

## قالب المجلدات المعتمد (Template Seed)

```text
anwaltsagent-site
├─ content/posts/article.md
├─ static/images/article-image.jpg
├─ layouts/index.html
├─ layouts/_default/single.html
├─ scripts/generate_article.py
├─ .github/workflows/publish.yml
└─ config.toml (أو hugo.toml)
```

## خط بداية الغد (Start Here)

1. **Email automation**: تفعيل `GMAIL_APP_PASSWORD` واختبار إرسال إيميل تلقائي بعد النشر.
2. **Google Search Console**: إضافة `https://anwaltsagent.de` ثم إرسال `sitemap.xml`.
3. **Bing Webmaster**: إضافة الموقع.
4. **Domain listings**: Sedo ✅ ثم Afternic وDan.
5. **تحويل المشروع إلى domain-template** لإطلاق نطاقات جديدة بسرعة.

## المرحلة التالية

الهدف القادم: **Domain Factory Template v1**

```text
1 command
↓
new domain SEO site
↓
auto articles
↓
auto images
↓
auto publish
↓
domain sales CTA
```

---

> هذا الملف هو مرجع الاستئناف الرسمي للجلسة القادمة لتفادي إعادة أي إعدادات من الصفر.
