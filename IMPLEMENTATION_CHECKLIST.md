# Dynamic Assets Implementation Checklist

## Pre-Deployment

### Database & Migrations
- [ ] Run `python manage.py migrate core`
- [ ] Verify `core_sitesettings` table exists
- [ ] Confirm table has single row (automatically created)

### Admin Configuration
- [ ] Log in to `/admin/`
- [ ] Navigate to **Core > Site Settings**
- [ ] Verify all fields are editable
- [ ] Check that image preview works
- [ ] Upload favicon.ico to Branding section
- [ ] Upload hero.jpg to Hero Section
- [ ] Upload about.jpg to About Section
- [ ] Upload og-preview.jpg to SEO & Meta Tags
- [ ] Upload jaysonkhan-cv.pdf to Resume/CV section

### Content Updates
- [ ] Update meta_description (160 chars max)
- [ ] Update meta_keywords
- [ ] Update hero_title and hero_subtitle
- [ ] Update about_title and about_description
- [ ] Update email address
- [ ] Update GitHub URL
- [ ] Update LinkedIn URL
- [ ] Update footer_text

### Template Verification
- [ ] Check homepage hero section displays correctly
- [ ] Check about section displays correctly
- [ ] Check footer displays correct email/social links
- [ ] Check page title in browser tab
- [ ] Inspect meta tags in page source
- [ ] Test OG image in Facebook debugger
- [ ] Test fallback to static images if media removed

### Frontend Testing
- [ ] Desktop view (1920px)
- [ ] Tablet view (768px)
- [ ] Mobile view (375px)
- [ ] Check all links work
- [ ] Verify CV download works
- [ ] Test social media links
- [ ] Check navigation responsive menu

### Performance
- [ ] Verify page load time is acceptable
- [ ] Monitor database query count (should be ~1 query for SiteSettings)
- [ ] Test with slow network (Chrome DevTools)

### SEO Validation
- [ ] Use Google's Rich Results Test
- [ ] Check Lighthouse SEO score
- [ ] Verify structured data (JSON-LD)
- [ ] Test Twitter card preview
- [ ] Test Open Graph preview

### Deployment
- [ ] Backup production database
- [ ] Run migration on staging first
- [ ] Verify static files configuration
- [ ] Set correct MEDIA_ROOT and MEDIA_URL
- [ ] Configure file upload permissions
- [ ] Enable image optimization (optional)
- [ ] Deploy to production

## Post-Deployment

### Smoke Testing
- [ ] Visit homepage
- [ ] Download CV
- [ ] Click all navigation links
- [ ] Verify footer information
- [ ] Check browser console for errors

### Monitoring
- [ ] Monitor error logs for exceptions
- [ ] Track admin login activity
- [ ] Watch for failed file uploads
- [ ] Monitor database performance

### Documentation
- [ ] Share admin credentials with team
- [ ] Create admin user guide
- [ ] Document file upload best practices
- [ ] List recommended image dimensions

## Optional Enhancements

- [ ] Add caching for SiteSettings (5-minute TTL)
- [ ] Implement image optimization
- [ ] Create data backup for media files
- [ ] Add admin history logging
- [ ] Setup CDN for media files
- [ ] Add Google Analytics field
- [ ] Implement multi-language support
- [ ] Create admin dashboard with stats

## Rollback Plan

If issues occur:

1. Restore database backup: `psql ... < backup.sql`
2. Revert templates to hardcoded values (git)
3. Remove context processor from settings
4. Restart Django application
5. Clear browser cache

No code changes needed — just revert Git commits for templates.

## Team Communication

**When notifying team about dynamic content:**

> We've successfully implemented dynamic site settings management.
> All content (titles, descriptions, images, links) is now editable
> via the Django admin panel without requiring code changes.
>
> **To update the site:**
> 1. Log in to Admin > Core > Site Settings
> 2. Edit any field (24 fields across 10 sections)
> 3. Save — changes appear immediately on the live site
>
> **Supported updates:**
> - Page title, meta tags, SEO keywords
> - Hero section (title, subtitle, image, badge)
> - About section (content, image)
> - CV/Resume file
> - Contact email and social links
> - Footer copyright text
>
> All existing static fallbacks remain for safety.

## Quick Reference

| What | Where | How |
|------|-------|-----|
| Update page title | Admin > Site Settings > Basic Settings | Edit `site_title` |
| Update hero image | Admin > Site Settings > Hero Section | Upload to `hero_image` |
| Update CV | Admin > Site Settings > Resume/CV | Upload to `resume_file` |
| Update Google description | Admin > Site Settings > SEO & Meta Tags | Edit `meta_description` |
| Update email | Admin > Site Settings > Contact & Social | Edit `email` |
| Update footer text | Admin > Site Settings > Footer | Edit `footer_text` |

---

**Status:** ✅ Ready for deployment
**Last Updated:** 2026-02-19
**Implementation Time:** ~2 hours
**Risk Level:** Low (fallbacks in place, no breaking changes)
