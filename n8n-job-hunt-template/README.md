# AI Job Hunter: n8n template

An n8n workflow that runs every morning and does a job search for one person:

| Step | What happens | Where it ends up |
|---|---|---|
| 1. Search from the CV | Claude reads the CV and decides what to search for (job titles, German and English terms), then searches Adzuna and Remotive | - |
| 2. Read and save the job | Opens every new job page, extracts the full job description and gives two scores (see below) | Sheet: **Title, Company, Job Description, Fit Score, CV Match, Missing Keywords, Why it fits, Gaps, Apply Email** |
| 3. Improve the CV | For good matches, Claude rewrites the CV for that job description (only true facts from the original CV) and writes a cover letter | Google Doc + PDF in Drive |
| 4. Apply | If the ad gives an application email, it sends the cover letter with the tailored CV PDF attached from your Gmail. Otherwise it marks the job "Ready - apply on company website" | Gmail |
| 5. Save the result | Writes the improved CV, what changed, the cover letter, the Doc link and the status into the **same row** | Sheet |

You also get one summary email a day with every job, its tailored CV link and its cover letter.

### The two scores

| Column | What it measures | Used for |
|---|---|---|
| **Fit Score** (0-100) | Overall chance of an interview: skills, experience, seniority, location, language and your preferences | Deciding which jobs get a tailored CV (`minScore`) |
| **CV Match (original CV)** (0-100) | Only how much of the job description your CV **as it is now** already covers | Seeing how much tailoring a job needs. A low match with a high fit means your CV undersells you for that job |
| **Missing Keywords** | Important skills from the job description that your CV doesn't show | The tailored CV adds them only where your real experience supports them. The rest are gaps to work on |

---

## Your own accounts, your own AI

This is a **template**. Everything runs in **your** n8n with **your** accounts:
- **AI:** your own Anthropic API key. You pay Anthropic directly for what you use (see costs below). The seller never sees your key or your data.
- **Google:** your own Sheets, Drive and Gmail. Applications are sent from your address.
- **Job search:** your own free Adzuna key.

---

## What you need

| Account | Cost | Used for |
|---|---|---|
| n8n (Cloud or self-hosted) | Cloud plan, or free self-hosted on a small server | Runs the workflow |
| Anthropic API key (console.anthropic.com) | Pay per use, see costs below | AI search planning, scoring, CV writing |
| Adzuna API key (developer.adzuna.com) | Free | Job search (Germany, UK, US, India and more) |
| Google account | Free | Sheets (tracker), Drive (CVs), Gmail (sending) |

## Setup (about 15 minutes)

1. **Import:** in n8n, go to *Workflows → Import from file* and choose `workflow.json`.
2. **Tracking sheet:** create a Google Sheet. Paste the first line of `applications-sheet-header.csv` into row 1. Column names must match exactly.
3. **Config node:** open it and fill in your name, email, location, country code, Adzuna keys, preferences and **the full CV as plain text** (including contact details).
4. **Claude nodes (3):** open *Plan Search from CV*. Under Credential, create a new **Header Auth** credential:
   - Name: `x-api-key`
   - Value: the Anthropic API key

   Choose the same credential in *Score Fit + Extract JD* and *Improve CV for JD*.
5. **Sheet nodes (2):** connect your Google account and pick the sheet and tab in both *Save Job to Sheet* and *Save Improved CV to Sheet*.
6. **Google Drive nodes (2):** connect Google. In *Create CV Google Doc*, choose the folder where the CVs should go.
7. **Gmail nodes (2):** connect your Gmail. Applications are sent from this address.
8. **Test:** click *Execute workflow*. Check the sheet, the Google Docs and the summary email.
9. **Go live:** switch the workflow to **Active**. It runs every day at 07:00 (change this in *Every Morning*).

> Duplicate removal only works when the workflow is **Active**. When you test by hand, the same jobs come back each time.

## Turning on automatic applying

`autoApplyByEmail` is `false` by default. Every CV is prepared and logged, and you press send.
Set it to `true` once you have checked a few tailored CVs. From then on, jobs whose ad gives an application email address are applied to automatically (at most `maxApplicationsPerDay` per day).

**Important:** jobs that need an online form (Workday, SuccessFactors, Personio, LinkedIn Easy Apply…) are **not** submitted automatically. Those sites forbid bots and use CAPTCHAs. The workflow prepares the tailored CV PDF and the cover letter and puts the job link in the sheet and the email, so applying takes about 2 minutes.

## Settings in the Config node

| Setting | Meaning |
|---|---|
| `searchQueriesOverride` | Leave `[]` to let the AI pick searches from the CV, or set your own, e.g. `['data analyst','werkstudent data']` |
| `titleMustInclude` | Leave `[]` to use the AI's keywords. A job title must contain one of them |
| `excludeKeywords` | Jobs containing these words are skipped before the AI reads them |
| `minScore` | Only jobs at or above this fit score (0-100) get a tailored CV |
| `maxJobsToScore` | Max new jobs the AI reads per run (controls cost) |
| `maxApplicationsPerDay` | Max tailored CVs / applications per day |
| `applicationLanguage` | `auto` writes in the language of the job ad. Or set `English` / `German` |
| `modelScoring` / `modelWriting` | Which Claude model to use (see costs) |

## Running costs (paid by you to Anthropic, rough estimate)

Based on 25 jobs read and 5 CVs tailored per day:

| Setup | Per day | Per month |
|---|---|---|
| `claude-opus-5-5` for both (default, best quality) | about $1.60 | about $48 |
| `modelScoring: 'claude-haiku-5-5'` + Opus for writing | about $0.40 | about $12 |

Reading jobs is most of the cost. Switching only `modelScoring` to Haiku cuts the cost by roughly 75% and keeps Opus for the CV writing you send out. Lowering `maxJobsToScore` also helps.

## Adding more job sources

Any source with an API or RSS feed can feed **Combine Sources**. Add an HTTP Request node after *Read Search Plan* and connect it to a new input on *Combine Sources* (raise its *Number of Inputs*). Then add a small block in *Clean, Filter & Dedupe* that maps the new fields (title, company, location, description, url). Useful additions in Germany: the Bundesagentur für Arbeit job search API, company career pages (Greenhouse / Lever / Personio job feeds), StepStone RSS.

Don't scrape LinkedIn or Indeed. It breaks their terms and gets your account blocked.

## Changing the sheet to Excel

The workflow uses Google Sheets because it's free and needs no Microsoft 365 licence. If you prefer Excel, you can use *File → Download → Microsoft Excel (.xlsx)*. To write straight into Excel Online, replace the two Sheet nodes with **Microsoft Excel 365** nodes (operation *Append or Update Row*, match on `Job URL`).

## Troubleshooting

| Problem | Fix |
|---|---|
| "Could not build a search from the CV" | The Anthropic credential is wrong or out of credit. Or fill `searchQueriesOverride` |
| Sheet rows are empty or in the wrong columns | Row 1 headers must match `applications-sheet-header.csv` exactly |
| No jobs found | Loosen `titleMustInclude` / `excludeKeywords`, raise `maxDaysOld`, check the Adzuna keys |
| Status "Error - check CV" | Open that execution in n8n and look at *Improve CV for JD (Claude)* |
| Job description is short | Some job pages block robots or load by JavaScript, so the workflow falls back to the job board summary |
