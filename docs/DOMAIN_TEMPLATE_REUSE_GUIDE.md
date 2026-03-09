# Domain Factory Template Reuse Guide

This repository currently runs **anwaltsagent.de** as the active implementation.

Below is an example of reusing the same template for a hypothetical second domain:
- `legalmatch360.de`

## 1) Example domain config

Use: `data/examples/domain.legalmatch360.de.yaml`

It demonstrates reusable values for:
- domain + brand
- niche + country + language + audience
- homepage copy
- SEO defaults + keyword set
- CTA labels + Sedo/contact links
- analytics IDs/events
- article generation settings (`article_tone`, `seo_keyword_hints`, `image_style_hints`, `article_cta`)

## 2) Example theme config

Use: `data/examples/theme.legalmatch360.de.yaml`

It demonstrates reusable visual settings for:
- color palette
- gradients
- card/button styling
- border + shadow/glow style
- visual mood + section labels

## 3) Files to change for a new domain

For a new domain launch, update/copy these files:

1. `data/domain.yaml`
   - domain, brand, SEO copy, CTAs, analytics, generator content settings.
2. `data/theme.yaml`
   - complete visual identity (colors, gradients, spacing-related tokens, style mood).
3. `hugo.toml`
   - set `baseURL` and `title` to match the new active domain.
4. Optional: `.github/workflows/publish.yml`
   - for manual runs, pass `domain_config_path` input.
   - keep defaults if using `data/domain.yaml` as canonical active config.

## 4) Step-by-step launch process

1. **Create branch for new domain**
   - e.g. `git checkout -b launch/legalmatch360-de`

2. **Apply domain config**
   - Copy `data/examples/domain.legalmatch360.de.yaml` to `data/domain.yaml`
   - Adjust real contact/Sedo/analytics values.

3. **Apply theme config**
   - Copy `data/examples/theme.legalmatch360.de.yaml` to `data/theme.yaml`
   - Fine-tune colors/gradients if needed.

4. **Update Hugo root config**
   - Set `hugo.toml` `baseURL` and `title` to the new domain/brand.

5. **Verify article generator settings**
   - Confirm `data/domain.yaml` contains:
     - `language`
     - `brand_positioning`
     - `content.article_tone`
     - `content.seo_keyword_hints`
     - `content.image_style_hints`
     - `content.article_cta`

6. **Set repository secrets**
   - Keep `OPENROUTER_KEY`, `UNSPLASH_KEY`.
   - Keep/update mail secrets (`GMAIL_USER`, `GMAIL_APP_PASSWORD`) as needed.

7. **Run workflow manually**
   - Trigger workflow dispatch.
   - Optionally provide `domain_config_path` if testing an alternate config file.

8. **Review generated output**
   - Confirm new post appears under `content/posts/`.
   - Confirm image appears under `static/images/`.
   - Confirm CTA/branding/analytics values match new domain config.

9. **Deploy**
   - Merge branch after verification.
   - Scheduled workflow continues publishing with current active config.

---

## Important

To keep this repo stable as a template:
- Keep **only one active** `data/domain.yaml` and `data/theme.yaml` at a time.
- Store additional domain presets under `data/examples/`.
