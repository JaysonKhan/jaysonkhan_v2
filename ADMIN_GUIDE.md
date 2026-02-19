# Django Admin Guide — Site Settings

## Accessing Site Settings

1. Go to: `http://localhost:8000/admin/`
2. Log in with superuser credentials
3. In the left sidebar under **CORE**, click **Site Settings**
4. You'll automatically see the single settings instance (no need to create one)

---

## Admin Interface Layout

The Site Settings form is organized into **10 sections** (tabs):

### 📋 Section 1: Basic Settings
**Fields:**
- `site_title` — Full site name (appears in browser tab, nav logo)
  - Example: "JaysonKhan | Portfolio"
- `site_tagline` — One-liner description (appears in footer)
  - Example: "Senior Python Backend Architect & Full-stack Developer."

**Tips:**
- Max 255 characters for site_title
- Max 500 characters for site_tagline
- Tagline is shown below site name in footer

---

### 🎨 Section 2: Branding (Collapsed)
**Fields:**
- `favicon` — Browser tab icon
- `logo` — Site logo (for future use)

**How to upload:**
1. Click "Choose File" button
2. Select image from computer
3. Image preview appears below field
4. Save form

**Recommended sizes:**
- Favicon: 32×32 or 64×64 pixels (ICO, PNG, or JPEG)
- Logo: 200×100 pixels (PNG with transparency recommended)

**Where used:**
- Favicon: Browser tab, bookmarks
- Logo: Reserved for future navbar/header use

---

### 🔍 Section 3: SEO & Meta Tags
**Fields:**
- `meta_description` — Google search result snippet
- `meta_keywords` — Comma-separated keywords
- `og_url` — Website URL for social media
- `og_image` — Image shown in social media preview

**Character limits:**
- meta_description: Max 160 characters (Google limits)
- meta_keywords: Max 255 characters

**Examples:**
```
Description: "Senior Python Backend Architect specializing in Django, PostgreSQL, and Clean Architecture."

Keywords: "Python, Django, PostgreSQL, Backend Developer, Software Architect, Portfolio"

OG URL: https://jaysonkhan.com
```

**OG Image specs:**
- Size: 1200×630 pixels (recommended)
- Format: JPG or PNG
- Used by: Facebook, LinkedIn, Telegram, WhatsApp
- Preview: Use Facebook Sharing Debugger to test

**How to test:**
1. Go to https://developers.facebook.com/tools/debug/sharing/
2. Enter your website URL
3. Check that og:image displays correctly

---

### 🦸 Section 4: Hero Section
**Fields:**
- `hero_availability_badge` — Text above the main heading
- `hero_title` — Main headline ("I build...")
- `hero_subtitle` — Supporting text below headline
- `hero_image` — Large image on right side of hero section

**What it controls:**
```
┌─────────────────────────────────────┐
│ Available for work        [BADGE]   │
│                                     │
│ I build high-performance           │
│ backend systems.         [TITLE]    │
│                                     │
│ Senior Python Backend... [SUBTITLE] │
│                           [HERO IMG]│
└─────────────────────────────────────┘
```

**Character limits:**
- Badge: 100 characters max
- Title: 255 characters max
- Subtitle: 500 characters max

**Image specs:**
- Size: 400×400 pixels minimum (square or landscape)
- Format: JPG or PNG
- Content: Portrait photo or avatar
- Quality: High resolution (200+ DPI)

**Tips:**
- Keep title punchy and short
- Subtitle explains the title
- Badge text should highlight availability status
- Image should be professional headshot or styled photo

---

### 📖 Section 5: About Section
**Fields:**
- `about_title` — Section heading
- `about_description` — Paragraph text
- `about_image` — Photo on right side

**What it controls:**
```
┌──────────────────────────────────┐
│ About Me       [TITLE]           │
│                                  │
│ [Long text about experience]     │
│ [and expertise...]    [ABOUT IMG]│
│                                  │
│ [Download CV button]             │
└──────────────────────────────────┘
```

**Character limits:**
- Title: 255 characters max
- Description: No limit (unlimited text field)

**Tips:**
- Write in first person: "I build..." / "I specialize in..."
- Include years of experience, main technologies, philosophies
- 2-3 paragraphs is good (80-200 words)
- Image should be professional photo of you

**Image specs:**
- Size: 400×500 pixels minimum
- Format: JPG or PNG
- Aspect ratio: Portrait (9:11 or similar)
- Content: Professional photo of you
- Style: Matching site color scheme preferred

---

### 📄 Section 6: Resume / CV (Collapsed)
**Fields:**
- `resume_file` — PDF file for download
- `resume_button_text` — Label on download button
- `resume_preview` — Link to view file (read-only)

**How to upload PDF:**
1. Click "Choose File"
2. Select your PDF from computer
3. File appears as link below field
4. Save form

**Button text examples:**
- "Download CV"
- "Download Resume"
- "Get My CV"
- "Download Resume (PDF)"

**Tips:**
- Keep PDF file size under 5MB
- Use clear filename: "jaysonkhan-cv.pdf"
- Ensure PDF is searchable text (not scanned image)
- Update at least quarterly

**Where used:**
- About section (download link)
- Footer (optional future use)

---

### 📧 Section 7: Contact & Social
**Fields:**
- `email` — Primary contact email
- `github_url` — GitHub profile link
- `linkedin_url` — LinkedIn profile link

**What it controls:**
```
Footer:
┌─────────────────────────────────┐
│ Email: [email]                  │
│                                 │
│ [GitHub icon] [LinkedIn icon]   │
└─────────────────────────────────┘
```

**Format examples:**
- Email: jayson@jaysonkhan.com
- GitHub: https://github.com/jaysonkhan
- LinkedIn: https://linkedin.com/in/jaysonkhan

**Tips:**
- Use full HTTPS URLs
- Email appears as text in footer
- Social links are clickable icons
- Both social fields are optional (if blank, icons won't appear)

---

### 📌 Section 8: Footer (Collapsed)
**Fields:**
- `footer_text` — Copyright notice and other footer text

**Character limit:** 255 characters max

**Common examples:**
- "© 2026 JaysonKhan. All rights reserved."
- "© 2024-2026 Jayson Khan. Made with ❤️"
- "© 2026 JK Portfolio. Licensed under MIT."

**Where used:**
- Very bottom of every page
- Below navigation links in footer

**Tips:**
- Update year annually
- Can include emoji (❤️, 🚀, etc.)
- Keep short and professional

---

### 🕐 Section 9: Timestamps (Collapsed)
**Fields:**
- `created_at` — When settings were first created (read-only)
- `updated_at` — When settings were last edited (read-only)

**These are automatic:**
- You cannot edit these fields
- They update automatically when you save
- Useful for auditing changes

---

## Step-by-Step: Uploading Images

### To Upload a New Image:

1. **Find the image field** (e.g., "Hero Image")
2. **Click the "Choose File" button** next to it
3. **Select image from your computer**
4. **See preview appear below the field**
5. **Click "Save Site Settings"** at bottom
6. **Done!** Image appears on site immediately

### To Replace an Existing Image:

1. **Click "Clear"** checkbox under existing image preview
2. **Click "Choose File"** to select new image
3. **Click "Save"**

### To Remove an Image:

1. **Click "Clear"** checkbox under image
2. **Click "Save"** — no image appears on site

---

## Common Tasks

### 🔄 Update Company Name
1. Edit `site_title` in "Basic Settings"
2. Click "Save Site Settings"
3. ✅ Title changes in browser tab and navigation

### 🖼️ Change Homepage Hero Image
1. Scroll to "Hero Section"
2. Upload new image to `hero_image`
3. Click "Save"
4. ✅ New image appears on homepage

### 📄 Upload New Resume
1. Scroll to "Resume / CV" section
2. Upload PDF to `resume_file`
3. Optionally change button text in `resume_button_text`
4. Click "Save"
5. ✅ Download button works on homepage

### 🔗 Update GitHub Link
1. Scroll to "Contact & Social"
2. Update `github_url` (include https://)
3. Click "Save"
4. ✅ Footer icon links to new GitHub profile

### 📝 Update Google Search Description
1. Scroll to "SEO & Meta Tags"
2. Edit `meta_description` (keep under 160 characters)
3. Click "Save"
4. ✅ Appears in Google search results (after reindexing)

### 🎯 Update About Section
1. Scroll to "About Section"
2. Edit `about_title` and `about_description`
3. Upload new `about_image` if desired
4. Click "Save"
5. ✅ Changes appear on homepage "About Me" section

---

## Keyboard Shortcuts

While editing in the admin form:

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save form (same as clicking Save button) |
| `Tab` | Move to next field |
| `Shift+Tab` | Move to previous field |
| `Enter` (in text field) | New line |
| `Escape` | Cancel (lose unsaved changes) |

---

## Troubleshooting

### Issue: "Only one SiteSettings instance is allowed"
**Solution:** This is normal. Only edit the existing settings, don't try to create a new one. You'll automatically see the instance when you visit Site Settings.

### Issue: Image not appearing after upload
**Possible causes:**
1. Image file type not supported (use JPG or PNG)
2. Image too large (check file size)
3. Browser cache issue (clear cache with Ctrl+Shift+Delete)
4. Server hasn't reloaded (restart Django)

**Solution:**
1. Ensure image is .jpg, .png, or .gif
2. Compress large images (under 5MB)
3. Clear browser cache
4. Try a different image file

### Issue: "Permission denied" when uploading
**Solution:**
1. Check MEDIA_ROOT directory permissions (should be 755)
2. Ensure Django user has write access
3. Check disk space (at least 1GB free)
4. Verify MEDIA_URL in settings.py

### Issue: URL fields show error about format
**Solution:**
- Start with `https://` (not http://)
- Examples:
  - ✅ https://github.com/jaysonkhan
  - ❌ github.com/jaysonkhan
  - ❌ http://github.com/jaysonkhan

---

## Before You Save: Checklist

Before clicking "Save Site Settings", verify:

- [ ] `site_title` — Is it correct? (will appear in browser tab)
- [ ] `meta_description` — Under 160 characters? (Google limit)
- [ ] URLs — All start with https://?
- [ ] Email — Valid email address format?
- [ ] Images — JPG or PNG format?
- [ ] Text — Proofread for typos?
- [ ] Special characters — Escaped correctly? (Use " not ")

---

## File Upload Best Practices

### Image Optimization
Before uploading, optimize images:

**Online tools:**
- https://tinypng.com/ (compress PNG/JPG)
- https://imageresizer.com/ (resize)

**Recommended specs:**
- Favicon: 64×64 pixels, 10KB max
- Hero Image: 800×600 pixels, 100KB max
- About Image: 400×500 pixels, 150KB max
- OG Image: 1200×630 pixels, 200KB max
- CV PDF: 1-2 MB max

### Naming Convention
Use clear, descriptive filenames:
- ✅ jaysonkhan-hero.jpg
- ✅ profile-about.jpg
- ✅ jaysonkhan-cv.pdf
- ❌ image1.jpg
- ❌ photo.jpg
- ❌ file.pdf

---

## Permissions & Security

**Who can access Site Settings?**
- Superusers (always)
- Staff users with "core.change_sitesettings" permission
- No other users

**To give someone access:**
1. Go to **Users** in admin
2. Click their name
3. Under "Permissions", check **core | site settings | Can change site settings**
4. Save user

**Important:**
- Don't give access to untrustworthy staff
- Monitor edits (check updated_at timestamp)
- Only superusers can delete (never needed)

---

## Getting Help

**What to check if something goes wrong:**

1. **Page doesn't show new content?**
   - Hard-refresh browser (Ctrl+Shift+R)
   - Check `updated_at` timestamp in admin
   - Verify image uploaded successfully

2. **Image preview not showing?**
   - Try JPG or PNG format
   - Reduce image size
   - Check browser developer console for errors

3. **Changes disappeared?**
   - Go back to admin and check if saved
   - Ask if someone else edited settings
   - Check database wasn't rolled back

4. **Can't upload files?**
   - Check Django superuser login
   - Verify disk space available
   - Check MEDIA_ROOT directory permissions

---

## Support Contact

For issues:
1. Check this guide first
2. Clear browser cache and try again
3. Contact the developer if still broken

---

**Last Updated:** February 19, 2026
**Version:** 1.0
**For:** jaysonkhan.com Django Admin
