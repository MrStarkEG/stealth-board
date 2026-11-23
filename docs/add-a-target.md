# Add a target

A target is a few lines in `scoreboard.toml`:

```toml
# Confirmed: "x-datadome" header and a captcha-delivery.com page for plain clients.
[[target]]
id = "etsy"
name = "Etsy"
kind = "site"
vendor = "DataDome"
url = "https://www.etsy.com/"
expect = "<title[^>]*>Etsy"
```

| Field | Meaning |
|---|---|
| id | short name used in result files. Never change it later, or the history is lost |
| name | shown on the dashboard |
| kind | `open` (no protection), `test` (bot test page) or `site` (protected site) |
| vendor | the protection system |
| url | a public page that needs no login |
| expect | a regular expression that only the real page matches |
| reject | optional. A pattern that means "the page says we are a bot" |

## How to pick a good target

1. **Confirm the vendor from the response.** Do not guess. Look at the headers, cookies and block page that a plain client gets, and write what you saw in a comment above the target.
2. **Check that it tells tools apart.** Fetch it with a control and with a stealth tool, and save the pages:

   ```sh
   python3 -m scoreboard.run --target NEW_ID --tool playwright --tool patchright --tool camoufox --tries 1 --debug-dir debug
   ```

   A good target blocks the control and lets at least one stealth tool in.
3. **Pick `expect` from the real page.** Open the saved HTML of a passing tool and choose text that the block page does not have. The page title is often a good choice. Make sure it also works when the site shows another language.
4. **Keep it small and fair.** Use one public page with no login. Do not add sites that ask not to be tested, and do not add pages with personal data.

## When a target goes bad

The dashboard marks a target when a control opens it, or when no tool has opened it for 7 days. Then check it by hand:

- The site changed its page, so `expect` no longer matches. Fix the pattern.
- The site dropped or changed its protection. Update `vendor`, or remove the target.
- The site got harder and really blocks everything. Keep it, that is a real result.
