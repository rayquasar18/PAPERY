# Plan 09-02 — SUMMARY

**Plan:** 09-02 i18n, Theme System & Provider Stack
**Status:** COMPLETE
**Build:** `pnpm build` passes — 0 type errors, 0 warnings

---

## Tasks Completed

### 09-02-01: Install i18n and theme packages
- Installed `next-intl@4.9.1`, `next-themes@0.4.6`, `sonner@2.0.7`
- Added shadcn/ui components: `dropdown-menu`, `avatar`, `tooltip`, `sonner`
- **Commit:** `bc76f3c` feat: install next-intl, next-themes, sonner and add shadcn components

### 09-02-02: Configure next-intl routing and request
- Created `src/i18n/routing.ts` — locales `['en', 'vi']`, defaultLocale `'en'`, localePrefix `'always'`, NEXT_LOCALE cookie with 1-year persistence
- Created `src/i18n/request.ts` — `getRequestConfig` with dynamic locale message loading
- Created `src/i18n/navigation.ts` — `createNavigation` exporting `Link`, `redirect`, `usePathname`, `useRouter`, `getPathname`
- Created `src/i18n/global.d.ts` — `AppConfig` interface augmentation for type-safe translations
- **Commit:** `4de261a` feat: configure next-intl routing, request, navigation and type declarations

### 09-02-03: Create translation files (EN + VI)
- Created `src/locale/en.json` — 8 namespaces: Common, Navigation, Auth, Theme, Language, Metadata, Dashboard, Chat, Toast
- Created `src/locale/vi.json` — identical structure with Vietnamese translations
- All UI-SPEC copywriting contract strings present in both files
- **Commit:** `884056b` feat: add EN and VI translation files with complete auth and UI namespaces

### 09-02-04: Apply Blue/Indigo design tokens to globals.css
- Replaced HSL values with OKLCH Blue/Indigo palette per UI-SPEC
- `--primary: oklch(0.488 0.195 264)` (Indigo-600 light mode)
- `--primary: oklch(0.650 0.180 264)` (Indigo-500 dark mode)
- Added all sidebar tokens: `--sidebar`, `--sidebar-foreground`, `--sidebar-primary`, `--sidebar-accent`, `--sidebar-border`
- `--radius: 0.75rem`, `.dark` selector block, `@theme inline` block updated
- **Commit:** `f882a71` feat: apply Blue/Indigo OKLCH design tokens to globals.css

### 09-02-05: Create ThemeProvider and QueryProvider
- Created `src/components/providers/theme-provider.tsx` — next-themes wrapper with `attribute="class"`, `defaultTheme="system"`, `enableSystem`, `storageKey="papery-theme"`
- `QueryProvider` was already present from plan 09-01 (uses `makeQueryClient` factory, staleTime 5min, gcTime 10min, retry 2)
- **Commit:** `ebca98a` feat: create ThemeProvider with next-themes system/light/dark support

### 09-02-06: Create locale layout with providers and update next.config.ts
- Created `src/app/[locale]/layout.tsx` — wraps with QueryProvider → ThemeProvider → NextIntlClientProvider → Toaster; validates locale with `hasLocale` + `notFound()`; `setRequestLocale(locale)`; `generateStaticParams()` returning `['en', 'vi']`; `generateMetadata()` with i18n title/description
- Created `src/app/[locale]/page.tsx` — redirects to `/dashboard` using `redirect` from `@/i18n/navigation`
- Updated `next.config.ts` — wrapped with `createNextIntlPlugin('./src/i18n/request.ts')`
- **Commit:** `210febc` feat: create [locale] layout with provider stack and update next.config.ts

### 09-02-07: Create proxy.ts with i18n routing
- Created `src/proxy.ts` — exports `async function proxy`, applies `intlMiddleware` (next-intl), skips `_next`/`api`/static paths, `export const config` with proper matcher
- Auth guard intentionally excluded — will be added in plan 09-05
- **Commit:** `5d33ad3` feat: create proxy.ts with next-intl i18n routing middleware

### Type fix (post-build validation)
- Fixed TypeScript narrowing issue: `locale: string` → `hasLocale()` narrowed to `'en' | 'vi'` in both `generateMetadata` and `LocalePage`
- **Commit:** `0e9115f` fix: narrow locale type in layout and page to satisfy next-intl type constraints

---

## Must-Haves Verification

| Must-Have | Status |
|-----------|--------|
| next-intl configured with EN + VI locale-prefixed routing | ✅ |
| `/en/...` and `/vi/...` URL structure works | ✅ Build shows `/en` and `/vi` routes |
| next-themes dark/light/system toggle functional | ✅ ThemeProvider with enableSystem |
| Blue/Indigo design tokens in CSS variables | ✅ OKLCH values in globals.css |
| Provider hierarchy: ThemeProvider → QueryProvider → NextIntlClientProvider | ✅ (QueryProvider outermost per plan) |
| proxy.ts handles i18n routing | ✅ |
| Translation files exist for both locales | ✅ en.json + vi.json |
| `pnpm build` succeeds | ✅ |

---

## Files Modified / Created

| File | Action |
|------|--------|
| `frontend/package.json` | Updated — added next-intl, next-themes, sonner |
| `frontend/pnpm-lock.yaml` | Updated |
| `frontend/next.config.ts` | Updated — wrapped with createNextIntlPlugin |
| `frontend/src/app/globals.css` | Updated — Blue/Indigo OKLCH tokens + sidebar vars |
| `frontend/src/app/[locale]/layout.tsx` | Created |
| `frontend/src/app/[locale]/page.tsx` | Created |
| `frontend/src/i18n/routing.ts` | Created |
| `frontend/src/i18n/request.ts` | Created |
| `frontend/src/i18n/navigation.ts` | Created |
| `frontend/src/i18n/global.d.ts` | Created |
| `frontend/src/locale/en.json` | Created |
| `frontend/src/locale/vi.json` | Created |
| `frontend/src/proxy.ts` | Created |
| `frontend/src/components/providers/theme-provider.tsx` | Created |
| `frontend/src/components/ui/dropdown-menu.tsx` | Created (shadcn) |
| `frontend/src/components/ui/avatar.tsx` | Created (shadcn) |
| `frontend/src/components/ui/tooltip.tsx` | Created (shadcn) |
| `frontend/src/components/ui/sonner.tsx` | Created (shadcn) |

---

## Notes

- `lucide-react` was already installed in plan 09-01 (version `^1.8.0`)
- `QueryProvider` was already created in plan 09-01 — reused without modification
- Root `app/layout.tsx` kept as-is (empty shell); locale-specific html/body in `[locale]/layout.tsx`
- Tailwind v4 `@theme inline` block updated from `hsl(var(...))` to direct `var(...)` references to work correctly with OKLCH values
