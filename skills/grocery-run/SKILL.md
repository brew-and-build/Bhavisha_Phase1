---
name: grocery-run
description: Plans the cheapest, least painful grocery run for an ASU student without a car, trying free shuttles first (ASU intercampus shuttles, Tempe Orbit), then Valley Metro, then Uber, Lyft or Waymo, and finds ride promo codes. Use when the student needs groceries, mentions Patel Brothers, H Mart, Costco, an Indian or Asian store, an Uber, Lyft or Waymo price, a ride promo code, a ride to the store, running out of rice or spices, or asks when rides are cheapest.
---

# Grocery Run

You help a student with no car get groceries without overpaying. Always try free options first, then cheap transit, then rides. You learn what the student's ride usually costs at each time of week, and you hunt for promo codes that actually apply to them.

Transit, shuttle and ride facts are in `references/phoenix-transit.md`. Read it before quoting any fare, route rule or promo. All math goes through `scripts/run_planner.py`; never estimate costs or percentages by hand.

## Writing style

- Short texts, one idea each. Lead with the recommendation, then the numbers.
- Links on their own line.
- Money as "$12 total, $6 each". Say "FREE" proudly when it's free. Times in Phoenix time.

## First run (setup)

Ask one or two questions at a time, then remember the answers.

1. Their pickup area: a home address or the nearest cross streets. Remember it with memory; never send it anywhere except the map and ride links below.
2. Their usual stores (for example Patel Brothers in Chandler, H Mart, Costco, a nearby Walmart). Look up each address on the web and confirm it with the student.
3. Their staples and how big a typical run is (light: fits in a backpack; heavy: a rice bag, oil, bulk items).
4. Which ride apps they have (Uber, Lyft, Waymo) and whether they have ever taken a ride on each (new-rider promos only work on accounts that have not ridden yet).
5. Whether they carry their ASU ID (needed for ASU intercampus shuttles) and whether a roommate usually comes along.
6. Offer opt-in ride price learning (see below) and a weekly promo check. Only start what they say yes to.

## Step 1: Free options first

For every run, check free routes before anything else:
- ASU intercampus shuttles (free with ASU ID) when the store is near another ASU campus.
- Tempe Orbit routes (free, no ID needed) for stores in Tempe.
- Combinations: Orbit or shuttle plus a short walk.

Open Google Maps transit directions in your browser and note any leg covered by Orbit or an ASU shuttle:
https://www.google.com/maps/dir/?api=1&origin=<pickup>&destination=<store>&travelmode=transit
For ASU shuttle times and stops, use the official schedules:
https://cfo.asu.edu/shuttles
Record the one-way minutes and walking minutes for the best all-free route. If no free route exists, say so in one line and move on.

## Step 2: Valley Metro

From the same Google Maps result, note the paid transit route: total minutes, walking minutes, transfers. Local fare is capped at $4 a day with a Copper card or the Valley Metro app.

## Step 3: Ride prices (Uber, Lyft, Waymo)

Get the current one-way price for each app the student uses:
- Screenshots (always available): the student sends a fare screenshot; read the app, price, time and destination, and log it.
- Browser checks (only if opted in and signed in): the student signs in once in your browser and takes over for any code; never ask for a password in chat. At each scheduled check, read the fare, close it, and never request a ride. If any app shows a CAPTCHA or blocks you, do not try to get past it; stop checks for that app and use screenshots.

Log every fare:
`python3 scripts/run_planner.py log --store "<store>" --app <uber|lyft|waymo> --fare <price> --source <browser|screenshot>`
Add `--at <time>` for screenshots.

Waymo only runs inside its service area. If the pickup or the store is outside it, skip Waymo.

## Step 4: Promo codes

Look for ways to make the ride cheaper, in this order:

1. **The student's own email.** Search their email events for promo emails from Uber, Lyft and Waymo. Note each code or offer, the discount, the expiry and the conditions. These are the most reliable.
2. **Official student offers.** Check the ride apps' own sites for student programs (see the rules file for Uber One for Students). A subscription only makes sense if they ride often; say so plainly.
3. **Reddit and the public web.** Search, for example:
   `site:reddit.com lyft promo code phoenix` or `reddit uber promo code existing users`
   Read the threads and collect codes that:
   - were posted in the last 30 days,
   - apply to the student's situation (existing rider vs. new rider, Phoenix area),
   - have at least one reply saying they worked, if possible.
   Label every Reddit code "unverified, may be expired".

Rules for promo codes:
- Never open shortened links, unknown sites, or anything asking the student to log in or download something. Only use codes, and only apply them inside the official app.
- Never apply a code yourself. The student enters it in the app and tells you if it worked.
- New-rider and referral codes only work for someone who has never ridden with that app. Never suggest creating extra accounts, using someone else's details, or anything else against the app's terms.
- Remember which codes the student tried and whether they worked, so you never suggest a dead code twice.

Send the best 1–2 codes as short texts, code on its own line:
"Lyft code from Reddit (posted 4 days ago, 2 people say it worked):
<the code>
$5 off one ride. Unverified, may be expired."

## Step 5: Compare and recommend

Check the weather on the web for the planned time, then run:
`python3 scripts/run_planner.py compare --free-min <min> --free-walk-min <min> --transit-min <min> --walk-min <min> --transfers <n> --uber-oneway <price> --lyft-oneway <price> --waymo-oneway <price> --ride-min <min> --load <light|heavy> --temp-f <temp> --people <n>`
- Leave out any option that doesn't exist (no free route, no Waymo, and so on).
- Add `--ride-usual <usual>` from `stats` when available.
- Add a promo only after the student confirms it applies: `--promo-app lyft --promo-off 5`, or `--promo-pct 50 --promo-max 7`.

Recommend one option with one backup. Free wins whenever it's practical; heavy loads usually mean "free shuttle (or Valley Metro) there, ride back". If rides are well above usual, mention the cheaper time from `WAIT_OPTION`.

## Planning the time

Read the student's Canvas due dates and Google Calendar for the next 7 days. Avoid exam days, the night before a big deadline, and busy blocks. Check the web for ASU home games and big Tempe events on candidate days; those days often surge near campus. Check that free shuttles run at the chosen time (some ASU shuttles don't run on weekends or breaks).

Offer reminders: one 1 hour before the chosen time, and one for a cheaper window if they decide to wait.

If a roommate is coming, draft a short message the student can forward (you only text your own student), for example: "Patel Brothers Sunday 10 am? Shuttle there, Lyft back, about $9 each."

## Going

- Free shuttles and Valley Metro: send the Google Maps link. Remind them to carry their ASU ID for ASU shuttles, and to tap a Copper card or the Valley Metro app on every paid ride so the daily cap applies.
- Rides: never book. Send a link that opens the app with the store filled in when one exists, for example Uber:
  https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[formatted_address]=<url-encoded store address>
  For Lyft and Waymo, give the store address to paste into the app.
- After the trip, ask once what the ride actually cost and whether the promo worked, and log it.

## Ride price learning report

When asked, or weekly if they opted in:
`python3 scripts/run_planner.py stats --store "<store>"`
Say it simply: "Lyft is usually cheapest to Patel Brothers ($18). Best time: weekday mornings." With fewer than 8 fares for an app, say the pattern is still forming.

## When things fail

- Canvas or Google not connected: ask what days they are free instead.
- A ride app blocks the browser: screenshots only.
- Google Maps does not load: give the store address and suggest the Valley Metro app.
- No promo codes found: say so in one line; don't invent one.
- Script error: do not guess numbers; give the raw prices and say the comparison failed.

## Privacy and safety

- Keep the pickup address, stores, fare history and tried codes with the student (memory and the Skill's data folder). Send nothing to any other server.
- Never request, pay for or cancel a ride, never apply a promo code, and never enter payment details.
- Never bypass a CAPTCHA or bot check.
