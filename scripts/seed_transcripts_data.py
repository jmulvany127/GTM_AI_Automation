SEED_TRANSCRIPTS = [
    {
        "title": "Discovery Call — Terrabrook BTR Partners",
        "description": "Strong buying intent call with VP of Growth at a build-to-rent operator; budget approved, pilot can start immediately, Entrata integration is the key requirement.",
        "lead_index": 10,
        "transcript": """Rep: Garrett, thanks for jumping on. I know you mentioned in your intake form that budget was already approved — I want to make sure I understand exactly what you're looking to accomplish so we use this time well.

Prospect: Appreciate that. Yeah, we have a line item approved specifically for an AI leasing tool in H2. What I care about is speed to value and integration quality. We're on Entrata and Salesforce. Any vendor that can't connect natively to both of those isn't worth my time.

Rep: Understood. Domino AI has native Entrata integration — direct API, no middleware. We sync lead data, unit availability, and lease events bidirectionally. For Salesforce, we push lead scores, AI-generated outreach, and pipeline status in real time. You own the field mapping configuration, no engineering required.

Prospect: Okay. What does the data flow actually look like? Walk me through what happens when a lead comes in through CoStar.

Rep: Lead comes in through CoStar, gets pushed to Entrata via your existing ILS integration. Domino AI pulls the lead from Entrata within 30 seconds, runs our qualification model — scores the lead based on income indicators, unit match, and source quality — then generates a personalized first-touch email and a LinkedIn message if we have the contact's profile. The email goes into a draft queue in Salesforce for your leasing manager to review and send, or you can set it to auto-send. Entrata is updated with the score and next-action field.

Prospect: What's the average time from lead creation to first email sent?

Rep: Under 90 seconds in auto-send mode. In review mode, it depends on your team's response cadence — we surface the highest-scored leads at the top of the queue so they get attended to first.

Prospect: That's the kind of thing I want to prove out in a pilot. We have five BTR communities in DFW — I'd want to run this on two of them, probably Coppell and Frisco, while keeping the other three as a control group so I can measure the difference.

Rep: That's a smart pilot design. We can have your Entrata integration live in three to five business days. What does your leasing team look like at those two properties?

Prospect: Two leasing agents at Coppell, one at Frisco. They're handling everything manually right now — I want them reviewing Domino AI drafts on day one, not writing from scratch.

Rep: That's exactly how our review workflow is designed. They see a pre-written, personalized email tied to the specific lead. They click approve or edit, it sends. Average review time in our data is under 40 seconds per email.

Prospect: What does pricing look like for a 1,800 unit operation?

Rep: For your current footprint at 1,800 units, you'd be looking at $1,400 a month during pilot and $1,200 monthly on an annual contract. If you scale to 4,000 units as planned we'd reprice at a volume tier — typically around $0.65 per unit per month at that scale.

Prospect: That's manageable. I've got budget for $2K a month so there's room. What do I need from my side to get started?

Rep: Entrata API credentials, Salesforce connected app credentials, and about 30 minutes on a kickoff call with our integration engineer. I'll send you a technical intake form this afternoon. If you can have credentials back to me by end of week, we can be live in Coppell and Frisco by the 15th.

Prospect: Let's do it. Send the form over. Copy our ops manager, Diane Cho, on anything technical — her email is d.cho@terrabrookbtr.com.

Rep: Done. I'll send the intake form and a pilot agreement to both of you today. Looking forward to getting this moving, Garrett.

Prospect: Same. Talk soon.""",
    },
    {
        "title": "Competitive Evaluation — Ridgeline Residential",
        "description": "Final vendor evaluation call with Head of Leasing Technology; prospect is comparing Domino AI against LeaseFlow AI and has a specific concern about native Yardi integration.",
        "lead_index": 17,
        "transcript": """Rep: Samantha, I know you're in a final evaluation so I want to be efficient. What's the key question you need answered today?

Prospect: Direct question — does Domino AI connect to Yardi Voyager natively, or does it go through a middleware layer? Because LeaseFlow AI told us it was native and then we found out they use a third-party sync service in the background. We had a bad experience with middleware at this company before, so this is a dealbreaker question.

Rep: I'll give you the direct answer first and then the technical detail. Domino AI connects directly to the Yardi REST API. We are a Yardi certified integration partner. There is no middleware, no third-party sync service, no intermediary. We authenticate with your Yardi Voyager instance using OAuth and call the API directly.

Prospect: Okay. Can you prove that? Like, is there documentation?

Rep: Yes. I'll send you our Yardi certification letter, the API architecture diagram that shows the direct connection, and a data flow document that maps every field we read and write. I can also get you on a call with our Yardi integration engineer if you want to go deep technically.

Prospect: That would be helpful. What write-back permissions does Domino AI request in Yardi?

Rep: We write to the guest card record — lead score, contact attempt log, and AI-generated outreach tag. We also write to the unit interest field and the follow-up date. We do not write to lease terms, rent, or any financial records. Read access covers guest cards, unit availability, and lease expiration dates.

Prospect: LeaseFlow AI was requesting write-back to financial fields and we pushed back. What you're describing sounds cleaner.

Rep: It's intentional. We scoped our permissions to the minimum required for leasing automation. No financial data write-back.

Prospect: Tell me about your support model. LeaseFlow AI took four business days to respond to a configuration question during our evaluation.

Rep: Enterprise accounts get a dedicated customer success manager and a 4-hour response SLA on business days. For critical issues — integration downtime, data sync failures — we have a 1-hour response SLA around the clock. You'd also have a direct Slack channel with your CSM and integration engineer during the first 60 days.

Prospect: That's materially better. What's the pricing difference between you and LeaseFlow AI at 8,700 units?

Rep: I don't know LeaseFlow's current pricing so I won't speculate on the comparison. For 8,700 units our annual contract would be $6,100 per month. I can send you a formal quote today.

Prospect: LeaseFlow is at $4,800. So you're about 27% higher.

Rep: I understand the gap. The differentiation is native Yardi certification, the support model, and — I'll say directly — we won't surprise you with a middleware dependency six weeks after you sign. That gap cost us the initial conversation but tends to be recoverable once teams see what undisclosed middleware issues actually look like in production.

Prospect: Fair enough. Send me the Yardi documentation, the architecture diagram, and the formal quote. I'll have a recommendation for my VP by the end of next week.

Rep: Everything will be in your inbox within two hours. And I'll get our Yardi integration engineer booked for a 30-minute technical call whenever you're ready. Just say the word.

Prospect: I'll reach out after I review the docs. Thanks for being straight with me on the middleware question.

Rep: Always. Talk soon, Samantha.""",
    },
    {
        "title": "Budget Evaluation Call — New Horizons Housing Foundation",
        "description": "Call with Property Management Director at an affordable housing nonprofit; strong product fit but needs ROI justification for grant compliance and board approval.",
        "lead_index": 7,
        "transcript": """Rep: Brenda, I know you're working within a grant budget so I want to make sure we address the financial side clearly. Can you walk me through what the JPMorgan grant actually covers?

Prospect: The grant is specifically for PropTech adoption — technology that improves leasing efficiency for affordable housing operators. The grant committee defined it as software, implementation, and training costs. $45,000 total, needs to be committed by December and fully implemented by March.

Rep: That timeline works for us. What do you need to demonstrate to the grant committee that the spend was justified?

Prospect: We need a 90-day outcome report showing measurable improvement in at least two of the following: resident communication response time, application completion rate, staff hours saved on administrative tasks, or reduction in days vacant. The grant has a reporting requirement at 90 days and again at 12 months.

Rep: Domino AI can track all four of those metrics natively. We have a reporting dashboard that shows average response time before and after, applications initiated from AI-generated outreach versus manual, and a time-tracking model that estimates hours saved per staff member per week based on email volume. We've done this reporting format for two other affordable housing clients — I'll include their 90-day reports in what I send you.

Prospect: That's exactly what I need. What does implementation actually look like given we're not on a major PMS — we're on a custom-built system?

Rep: That's a fair challenge to raise. Our standard integrations are Yardi, RealPage, and Entrata. For a custom system, we'd need to assess the API documentation your volunteer developer built. If there's a REST API or even a structured data export, we can usually build a connector. Can you share any documentation on the system's data structure?

Prospect: I can get you our database schema and whatever API documentation exists. It's not comprehensive. The person who built it left in 2021 and documentation is spotty.

Rep: Understood. That's actually fairly common with legacy nonprofit systems. The fallback, if the API isn't workable, is a CSV-based sync — your staff exports lead data on a daily schedule, we ingest and process it, and the AI-generated outreach goes out through our email integration. It's not real-time but it gets you the AI quality improvements without requiring a technical integration.

Prospect: That might actually be the right approach for us. We can't risk a failed integration project when we have a grant deadline.

Rep: I agree. Let's scope the pilot as a CSV-based deployment first. That's a 2-day setup, no integration risk. If the database documentation is good enough, we upgrade to real-time sync in phase two.

Prospect: What does the full cost look like under $45,000?

Rep: For your scale — 2,800 units, 12-month contract — our cost is $9,600 annually. Implementation and training is $2,500. Reporting support for the grant documentation is included. Total commitment is $12,100, well inside your grant. The remaining $32,900 could cover extended services, additional training, or be retained for year two if the grant terms allow carryover.

Prospect: The terms allow carryover with approval. I'd need to submit a budget justification form. Can you give me a line-item cost breakdown I can include in that form?

Rep: I'll have a formal itemized quote to you by end of day. I'll format it specifically for grant reporting purposes — I've done this before and know what the JPMorgan committee looks for.

Prospect: That's more helpful than I expected from this call. Let me take it to my Executive Director. If she approves moving forward I can get you a signed agreement within two weeks.

Rep: That works perfectly for the March go-live. I'll send the quote, the two affordable housing 90-day reports, and a one-pager formatted for your ED. Anything specific she's going to push back on that I can pre-address?

Prospect: She'll ask if we can do this ourselves. She always does.

Rep: I'll include a build-vs-buy comparison with realistic staff hour estimates. That usually settles it.

Prospect: Perfect. Thank you, this was a good use of 30 minutes.

Rep: Glad to hear it. Talk soon, Brenda.""",
    },
    {
        "title": "Enterprise Evaluation Call — Coastline REIT",
        "description": "Long-decision-cycle exploratory call with Director of Asset Management; prospect requires formal business case and investment committee approval, decision in January.",
        "lead_index": 11,
        "transcript": """Rep: Harrison, thanks for making time. I know from your intake notes that you evaluate everything through an NOI lens. I want to make sure I understand your model so we can frame this conversation the right way.

Prospect: Appreciate you noting that. Here's how I think about it: a 1% improvement in portfolio occupancy across 9,800 units is roughly $2.1 million annually at our average rent. A 2% improvement is $4.2 million. So any technology investment I'm making needs to have a credible path to at least 50 basis points of occupancy improvement to justify the cost and distraction of implementation.

Rep: That's a clean model. What does your current leasing conversion funnel look like — what percentage of inquiries convert to applications, and applications to signed leases?

Prospect: We're at about 28% inquiry-to-application and 67% application-to-lease. The inquiry-to-application gap is where we're losing people. We think it's response time and outreach quality.

Rep: That's consistent with what we see across the portfolio. Domino AI's impact on inquiry-to-application conversion averages 3.2 percentage points in the first 90 days based on our existing clients — so your 28% would move to approximately 31% under that model. At your unit count and average rent, I can work through what that translates to in NOI. Can you share what your average monthly rent is?

Prospect: Coastal markets, so $3,200 across the portfolio.

Rep: At $3,200 average rent, 9,800 units, 85% base occupancy — a 3-point improvement in inquiry-to-application conversion assuming your application-to-lease rate holds would translate to roughly $8.5 million annually in incremental revenue. That's the model I'd build for your investment committee. I can produce a formal ROI analysis document.

Prospect: That would be useful, but I want to be clear — my investment committee does not accept vendor-produced ROI models without independent validation. They'll want to see our own data run through your assumptions, not a marketing document.

Rep: Understood. What if I sent you the model methodology and your team applied your own numbers? You'd own the output, I'd own the methodology transparency.

Prospect: That I could work with. What are the input assumptions your model uses?

Rep: Five inputs: average monthly rent, total units, current inquiry-to-application conversion rate, current application-to-lease rate, and average days vacant between leases. We also use our own conversion lift data as a third input — you can use our median of 3.2 points or you can discount it. I'd encourage you to discount it for your committee.

Prospect: Smart. I might discount it to 1.5 points for a conservative case and 2.5 for the base case. That's how we present to the committee — two scenarios.

Rep: Perfect approach. I'll send the model as a spreadsheet so you can populate it with your own data and adjust the conversion lift assumption. What else does your committee need before they'll approve an evaluation?

Prospect: SOC 2 Type II certification and three reference customers at comparable REIT scale. If both check out, we'd issue a formal RFP to you and two other vendors in October with responses due in November. Committee review in December, decision in January.

Rep: We have SOC 2 Type II. I can provide three reference customers at 8,000 to 20,000 unit REITs — I'll need to confirm who's willing to be named publicly and who prefers a blind reference call. Can you let me know if your committee prefers documented references or live reference calls?

Prospect: Live calls, typically 30 minutes. Our Head of Technology and CFO participate.

Rep: Understood. I'll confirm three references who can do live calls with a CFO-level contact on the call. What's the best way to get on the approved vendor list for your RFP process?

Prospect: Email my assistant at r.morrison@coastlinereit.com with your capability summary, SOC 2 certificate, and company background. She'll add you to the October RFP distribution.

Rep: I'll have that submitted by end of week. One last thing — is there anything happening between now and October that could accelerate this timeline? An occupancy challenge at a specific property, for example?

Prospect: Our two Miami properties had a rough Q2 — vacancy is running 6 points above portfolio average. If there were a way to pilot on those two properties before the formal RFP process, I'd be open to discussing it informally. But that's not something I can commit to on this call.

Rep: I appreciate you mentioning it. I'll include a two-property pilot structure in the materials I send your assistant — specifically designed for your Miami situation. You can decide independently whether to raise it internally.

Prospect: That's fine. Send it along with the SOC 2 and I'll look at it over the weekend.

Rep: Will do, Harrison. Thanks for the time.""",
    },
    {
        "title": "Technical Deep-Dive — Meridian PropTech Partners",
        "description": "CTO-level technical evaluation call; prospect had a bad experience with a previous vendor due to Yardi API coverage gaps and is running an exhaustive technical review before any commercial discussion.",
        "lead_index": 2,
        "transcript": """Rep: Ryan, you mentioned in your intake that a previous evaluation fell through on Yardi API coverage. I want to spend this call going as deep technically as you need to go. Tell me where the last vendor failed.

Prospect: Hyly.AI claimed native Yardi integration. What we found in the technical review was that they could read guest card data but couldn't write back to Yardi without going through a webhook relay they hosted on their own infrastructure. That relay introduced a 4 to 8 hour lag in data sync and created a single point of failure outside Yardi's certification boundary. We killed the evaluation at that point.

Rep: Understood. Let me describe our architecture specifically. Domino AI authenticates with Yardi Voyager using OAuth 2.0 with client credentials flow. We call the Yardi REST API directly — RENTCafé Leasing APIs for guest card operations and the Voyager APIs for unit and lease data. We do not host a relay or proxy. Every API call goes from our application servers directly to your Yardi instance.

Prospect: What is your Yardi API version certification?

Rep: We are certified on Yardi REST API v19.2 and v20.1. If your Yardi instance is on an older version we'd need to confirm compatibility, but most Voyager clients are on 19.2 or later.

Prospect: We're on 20.1. What endpoints do you call for guest card write-back?

Rep: For guest card creation we use POST /resident/guestCards. For updates we use PATCH /resident/guestCards/{id}. We write to: guestFirstName, guestLastName, guestEmail, guestPhone, unitPreference, agentNote — that's where we put the AI score and outreach log — and nextFollowUpDate.

Prospect: Do you request write access to any fields outside that set?

Rep: No. Our OAuth scope is scoped to guest card read-write and unit availability read-only. We do not request access to financial data, lease terms, resident records, or any administrative Yardi functions.

Prospect: What is your data residency model? We run on AWS us-east-1.

Rep: We are AWS us-east-1 for all production data. We don't cross regions. If you have VPC peering or PrivateLink requirements we can discuss those on an enterprise arrangement — our standard deployment uses TLS 1.3 over public internet but we support private network paths.

Prospect: How do you handle Yardi API rate limits?

Rep: Yardi's default rate limit is 100 requests per minute per Voyager instance. We implement exponential backoff with jitter starting at 50 requests per minute, scale up to 90 under normal load, and back off immediately on a 429. We maintain a local queue for write operations so no data is lost during throttling windows.

Prospect: What's your SLA for data sync latency — time from lead creation in Yardi to Domino AI processing?

Rep: Under 90 seconds from guest card creation in Yardi to score and outreach draft available in Domino AI. That's P99 based on our production telemetry.

Prospect: Can you share production telemetry data? P50, P95, P99 latency over the last 30 days.

Rep: Yes. I can share an anonymised telemetry report. I'll need to pull it from our engineering team — I can have it to you by tomorrow afternoon. Do you also want the error rate data?

Prospect: Yes, and I want to see what happens on error — how does Domino AI handle a failed Yardi write? Does it retry, log, alert?

Rep: Failed write operations are retried three times with exponential backoff. If all three attempts fail, the event is logged to our error queue, you receive an alert in the Domino AI admin dashboard with the specific error code and payload, and our on-call engineer is paged. We have a 1-hour SLA to resolve or manually remediate any persistent write failures.

Prospect: One more thing. How do you handle schema differences across Yardi Voyager versions? We have some customised fields.

Rep: We support custom field mapping through a configuration UI — you map your custom Yardi fields to our data model without engineering involvement. If your custom field is outside what our UI exposes, we can add it through a support request. Custom field additions take 5 to 7 business days.

Prospect: That's acceptable. Send me the Yardi certification documentation, the API architecture diagram, the telemetry report, and an error handling specification document. If the documentation is consistent with what you've told me today I'd want to move to a pilot proposal.

Rep: Everything except the telemetry report — which I'll have tomorrow — will be in your inbox by end of day. What's your preferred format for the pilot proposal, given you're a technical buyer?

Prospect: I want an integration spec, not a sales deck. Data flow, sequence diagrams, environment requirements, rollback plan.

Rep: Noted. I'll deliver an integration specification document in the format you've described. Thanks for the thorough review, Ryan — this is exactly the right way to evaluate a vendor.

Prospect: It's the only way to avoid the situation we had with Hyly.AI. I'll be in touch after I review the docs.""",
    },
    {
        "title": "Urgency Call — SunState Multifamily Partners",
        "description": "High-urgency call with SVP of Leasing at a fast-scaling Sun Belt operator; next acquisition closes in 45 days and new properties need to be leasing-ready immediately.",
        "lead_index": 6,
        "transcript": """Rep: Derek, you flagged urgency in your intake. Tell me what's driving the timeline.

Prospect: We close on a 740-unit acquisition in Scottsdale in 45 days. The properties come with a leasing team of four people who are completely unfamiliar with our processes. I need something that standardizes how they work from day one — outreach templates, lead scoring, a workflow they follow — and I need it operational before we take over the keys.

Rep: Got it. What does your current stack look like at your existing 12,000 units?

Prospect: Yardi across all properties. HubSpot for CRM at the corporate level, but honestly the leasing teams don't use HubSpot — they work entirely in Yardi. Leads come in through Apartments.com and CoStar, get into Yardi guest cards, and from there it's manual. Every leasing agent has their own email templates saved in Outlook. It's chaos when you acquire a new team.

Rep: Domino AI can fix the standardization problem specifically. When a guest card hits Yardi, Domino AI generates a scored lead profile and a pre-written first-touch email in your brand voice. The leasing agent sees the email in a review queue, approves or edits in one click, sends. Same process, same template quality, regardless of which team member handles it.

Prospect: Can I set the templates? Like, I want the Scottsdale properties to use a specific brand voice that matches the Scottsdale market positioning. Different from our Phoenix properties.

Rep: Yes. You can configure brand voice settings at the portfolio, property, or unit-type level. Scottsdale gets its own voice parameters separate from Phoenix. The AI generates within those parameters.

Prospect: What's the fastest you can be live on the Scottsdale properties?

Rep: If you can get me Yardi API credentials and a brand voice document for Scottsdale by end of this week, I can have a dedicated integration engineer on it Monday. Live in Yardi, first email draft generating, within 7 business days. That's two and a half weeks before your close date.

Prospect: What if the Yardi credentials take longer to get — we're still in LOI, so some of that is contingent on close.

Rep: We can set up and test the integration in your existing Yardi environment first, then migrate the configuration to the new properties the week of close. Takes about 4 hours to migrate. You'd be fully operational on day one of ownership.

Prospect: That's the right answer. What about my existing 12,000 units — are they affected by this setup?

Rep: Only if you want them to be. We'd scope the initial deployment to Scottsdale and go live there. Expansion to existing properties is a separate configuration exercise. We'd recommend doing it sequentially — Scottsdale first, validate the workflow with your team, then roll out to the broader portfolio.

Prospect: Makes sense. I don't want to destabilize what's working while I'm managing an acquisition.

Rep: Exactly right. What does your leasing team in Scottsdale know about this tool? Are they expecting it?

Prospect: They don't know yet. We announce to the acquired team at close. I want the system ready so I can walk them through it on day one of ownership — show them the queue, show them an example email, make it concrete.

Rep: We can build a demo environment with example Scottsdale leads loaded so you have something to show on day one. That's something we've done for other operators during acquisitions.

Prospect: That's exactly what I need. Can you also provide a one-page workflow guide I can hand out to the leasing team? Something simple — not a 40-page manual.

Rep: We have a one-page quick-start card we've done for acquisitions. I'll customise it for SunState's branding. You'll have it before close.

Prospect: Alright. What do I need to sign to get started?

Rep: A pilot agreement scoping the Scottsdale deployment. I can have a draft to you today. Standard 90-day initial term, then annual. No penalty if you decide not to expand beyond Scottsdale after the pilot.

Prospect: Send it. Copy our VP of Operations, Carla Mendoza, at c.mendoza@sunstatemultifamily.com — she'll be involved in the actual setup.

Rep: Done. Agreement, intake form, and a copy of the one-page quick-start template will be in both your inboxes by 3pm. Thanks for the direct conversation, Derek.

Prospect: That's how I work. Talk soon.""",
    },
]
