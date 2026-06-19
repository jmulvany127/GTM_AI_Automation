SEED_TRANSCRIPTS = [
    {
        "title": "Discovery Call — Greystone Residential Partners",
        "description": "Initial discovery call with VP of Operations; prospect demonstrates strong buying intent and requests a pilot proposal.",
        "lead_index": 0,
        "transcript": """Rep: Hi Sarah, thanks for making time today. I know Q3 is hectic for operations teams. I wanted to start by understanding where your biggest leasing friction points are right now.

Prospect: Happy to jump in. Honestly, it's lead response time. We're getting maybe 200 to 300 inbound inquiries a week across our Austin portfolio and my team is manually triaging them. A prospect fills out a form on Thursday afternoon, and they might not hear back until Monday morning. By then, they've already toured somewhere else.

Rep: That delay-to-response problem is something we hear constantly. What does your current workflow look like once a lead comes in?

Prospect: It's embarrassing, honestly. They come in through our property websites, some through Apartments.com, and then someone manually copies the info into our CRM. From there it's assigned to a leasing agent. No scoring, no prioritization, no automated outreach. It's all manual.

Rep: What CRM are you running?

Prospect: HubSpot, but we're barely using it. It's basically a contact database at this point. We're not running any sequences, no automation. My team knows it's capable of more but no one has had time to set it up properly.

Rep: Makes sense. So if we could automatically qualify leads the moment they come in, score them, and fire off a personalized first-touch email within 60 seconds — how much of an impact would that have for you?

Prospect: That would be transformational. I mean genuinely. If we close even 5% more of the leads we're already generating, that's meaningful revenue. We don't need more leads, we need to convert the ones we have.

Rep: What does the decision process look like on your end? Is this a unilateral call for you or does it go to a committee?

Prospect: I have budget authority up to $30K annually. Anything above that I'd loop in our CFO but I don't think we'd be anywhere near that. If you can show me a pilot on two properties for 30 days and the numbers are there, I'm ready to move forward before end of quarter.

Rep: That's very helpful. What would success look like at the end of a 30-day pilot?

Prospect: I want to see lead response time under two minutes on average, and I want outreach quality that matches our brand voice — not generic templates. If those two things check out, you have a customer.

Rep: We can absolutely structure a pilot around those two metrics. I'll put together a proposal this week. Are you available Thursday at 2pm to walk through it?

Prospect: Yes, Thursday works. Send it over beforehand if you can so I can review it before we meet.

Rep: Will do. One last question — is HubSpot integration a hard requirement for the pilot?

Prospect: Yes, non-negotiable. Everything has to live in HubSpot. If it's not in the CRM, it didn't happen as far as my team is concerned.

Rep: Understood. We have a native HubSpot integration, so that's covered. I'll get the proposal over to you by Wednesday. Thanks, Sarah.

Prospect: Great. Looking forward to it.""",
    },
    {
        "title": "Qualification Call — CommunityFirst Affordable Housing",
        "description": "Call with Head of Revenue Operations at affordable housing nonprofit; prospect is interested but faces significant budget constraints.",
        "lead_index": 3,
        "transcript": """Rep: David, appreciate you joining. I know nonprofits run lean, so I'll keep this focused. Tell me about the leasing challenges you're dealing with at CommunityFirst.

Prospect: The core problem is our staff capacity. We have a leasing team of four people managing waitlists and inquiries for over 3,000 units. Most of our applicants are income-qualified, so there's a lot of documentation, a lot of follow-up, and a lot of manual work that doesn't require a skilled housing counselor — it just requires time.

Rep: Where specifically is the bottleneck? Is it initial outreach, document collection, or something else?

Prospect: Initial communication and follow-up. We get an inquiry, someone emails back a list of required documents, the applicant takes two weeks to respond, then we email again. That loop is eating our counselors' time. If that first phase were automated I'd free up probably 40% of their workload.

Rep: That's a solvable problem. What does your current tech stack look like?

Prospect: We use a custom-built database that one of our volunteers built in 2018. It's held together with duct tape at this point. No automation, no CRM in the traditional sense. We have a HUD reporting integration that we cannot touch.

Rep: Understood. Budget is often a sensitive topic for nonprofits, so I want to address it directly. Our platform starts at $800 a month for organizations your size. Does that range work?

Prospect: That's where it gets complicated. Our annual tech budget is $15,000 total. We have five existing contracts that eat most of that. I'd need to find an offset somewhere, or apply for a technology grant. I've actually been looking at the JPMorgan Chase PRO Neighborhoods grant which covers PropTech adoption for affordable housing operators.

Rep: We've actually had three other affordable housing clients go through that grant process successfully. I can connect you with our nonprofit success manager who has template language that's worked.

Prospect: That would be incredibly helpful. I want to be honest with you — even if this is the right tool, it might take us 6 to 9 months to get budget approved through a grant cycle. This isn't a fast procurement.

Rep: I appreciate the transparency. What I'd suggest is we do a free 60-day pilot while the grant application is in progress. If you're seeing results, that's data you can put in the grant application. Does that change the timeline dynamic at all?

Prospect: It might. Let me talk to my Executive Director and see if she'd be willing to approve an unpaid pilot evaluation. If the numbers are good, she'll support the grant application.

Rep: That sounds like a reasonable next step. I'll send over a one-pager you can share with her that includes our affordable housing case studies. What's the best email for her?

Prospect: Send it to me first and I'll forward it with my own context. She responds better to internal recommendations than vendor outreach.

Rep: Smart. I'll have that over by end of day. Thanks, David — I know this is a longer process but the impact potential is real.""",
    },
    {
        "title": "Technical Deep-Dive — Landmark Multifamily REIT",
        "description": "Technical evaluation call with Senior VP; prospect reveals they are currently piloting a competing solution.",
        "lead_index": 5,
        "transcript": """Rep: Robert, good to connect. You mentioned in your intake form you were already in evaluation mode. What does that look like?

Prospect: We're 45 days into a pilot with Knock. Their conversational AI product is running on three of our properties — two in Chicago, one in Indianapolis. So far results are mixed.

Rep: What's working and what isn't?

Prospect: The chatbot piece is decent. It handles FAQ traffic well and captures lead data consistently. Where it falls down is the backend — the CRM sync with Salesforce is unreliable. We're getting duplicate contacts, field mapping errors, and their support team took 11 days to respond to a P1 ticket. That's not acceptable for a REIT our size.

Rep: Understood. What's the business impact of the Salesforce sync issues?

Prospect: Our asset management team relies on Salesforce data for lease absorption reporting. When data is dirty, the reports are wrong. When reports are wrong, investment committee meetings go off the rails. I've had to manually pull raw data twice in the past month to correct reports. That should never happen.

Rep: How important is Salesforce integration quality when you're evaluating us?

Prospect: It's the single most important thing. If your Salesforce integration is unreliable, the conversation is over. I need bidirectional sync, I need field mapping that I can control without engineering support, and I need error logging that's visible to my ops team.

Rep: Our Salesforce integration is built on the official Salesforce REST API and syncs bidirectionally in near real-time. You configure field mappings through a UI, no engineering required. Every sync event is logged with a status in your admin dashboard. Failed syncs trigger a Slack alert to whoever you designate.

Prospect: How long does a typical Salesforce integration setup take?

Prospect: Sorry — I mean how long does it take on your end to set it up?

Rep: For an enterprise with your Salesforce configuration, typically 3 to 5 business days. We have a dedicated enterprise integration team who does the initial setup and stays on for 30 days.

Prospect: What does the pilot structure look like? Knock gave us three properties with no SLA.

Rep: We offer a structured pilot with defined success criteria agreed upfront, a dedicated integration engineer, and a 48-hour SLA on any critical issues. For a REIT your size I'd also include executive escalation to our VP of Customer Success if needed.

Prospect: What does pricing look like at 22,000 units?

Rep: At your scale we'd be looking at an enterprise agreement. I'd rather give you accurate numbers than ballpark. Can we schedule a commercial call with our enterprise team next week?

Prospect: Yes. Tuesday or Wednesday afternoon. Make sure your integration lead is on the call — I want technical answers, not sales answers.

Rep: Absolutely. I'll confirm the time and include both our enterprise AE and our integration lead. One more thing — how soon does the Knock pilot contract expire?

Prospect: 30 days. If we're going to switch, the decision needs to happen in the next three weeks.

Rep: Noted. We'll prioritize accordingly. Talk Tuesday.""",
    },
    {
        "title": "Evaluation Call — Harborview Residential REIT",
        "description": "Exploratory call with VP of Asset Management at coastal REIT; prospect is cautious and signals a long enterprise procurement timeline.",
        "lead_index": 8,
        "transcript": """Rep: Rachel, thank you for making time. I know your portfolio is spread across several markets — how are you thinking about AI tooling for leasing right now?

Prospect: Honestly, we're in early stages. Our asset management team put together a technology roadmap for 2026 in November, and AI-assisted leasing is on the list for H2. We're not actively buying right now.

Rep: That's helpful context. What's driving the H2 timeline specifically?

Prospect: Two things. First, we just renewed our Entrata contract in August — three years — so changing our core property management system is off the table. Any AI layer would have to integrate with Entrata. Second, our procurement process requires a formal RFP for any contract above $50K annually, and that process alone takes four to six months.

Rep: Understood. What would an ideal solution look like at the end of that evaluation, assuming it goes well?

Prospect: Something that sits on top of Entrata, pulls lead data, scores prospects using AI, and generates outreach drafts for our leasing managers to review and send. Not fully automated — our properties are in high-touch markets where a robotic email would do more damage than no email. We want AI-assisted, not AI-autonomous.

Rep: That's a distinction we hear more and more. Do you have a sense of what the RFP evaluation criteria would look like?

Prospect: We'd weight integration quality with Entrata heavily — probably 30% of the score. AI output quality, specifically how well it captures brand voice, maybe 25%. Pricing and commercial terms, 20%. Security and compliance — we have SOC 2 Type II requirements — probably 15%. Support model the rest.

Rep: We have an Entrata integration, SOC 2 Type II certification, and a configurable brand voice layer. I'd like to make sure we're positioned correctly when your RFP goes out. Is there someone on your technology team I should be in contact with to understand the requirements before the formal process opens?

Prospect: That would be our VP of Technology, but she's not going to take vendor calls until we're formally in the RFP phase. I'd suggest getting on our approved vendor list now. That's the right move.

Rep: How do we do that?

Prospect: Email our procurement team at procurement@harborviewreit.com with a vendor capability summary, proof of SOC 2, and three customer references. They review it quarterly. Next review is in March.

Rep: Perfect. I'll get that submitted before March. Is there anything you personally would want to know before the formal process that would help you advocate internally for AI tooling being on the roadmap?

Prospect: Honestly, ROI data from comparable REITs. If you can show me that a REIT of similar scale saw measurable improvement in lead-to-lease conversion, that's the language my investment committee speaks. Not feature lists.

Rep: I have two case studies from comparable coastal REITs I can share under NDA. Would that be useful to see informally?

Prospect: Yes. Send those to my email and I'll look at them. Don't expect a fast response — I read things in waves.

Rep: Understood. I'll send the case studies along with our vendor submission package this week. Thank you, Rachel.""",
    },
    {
        "title": "Urgent Evaluation Call — Southwest Property Advisors",
        "description": "Fast-moving call with VP of Business Development; prospect has an imminent client deadline and needs a solution within 30 days.",
        "lead_index": 12,
        "transcript": """Rep: Laura, you mentioned urgency in your intake notes. Can you walk me through what's driving that?

Prospect: We just won a contract to onboard a new property management client — 2,300 units in Phoenix and Tucson. They go live in 47 days. Part of our pitch to them was that we bring an AI-enhanced leasing workflow. We don't have one yet.

Rep: So you need something that's live within 47 days and ready for a client-facing deployment.

Prospect: Exactly. And it needs to look polished. This client is sophisticated — they came from a self-managed situation with a large in-house tech team. They have high standards.

Rep: What commitments did you make to them specifically around AI?

Prospect: We promised AI-assisted lead qualification and personalized outreach generation. We didn't over-specify — we kept it general intentionally — but they're going to ask about the specifics when we onboard them.

Rep: Okay. Our standard onboarding for a new account is 10 to 14 business days. For your situation, we can run an expedited onboarding in 7 business days if we start this week. That gives you a live system with 30 days of buffer before your client goes live.

Prospect: What does expedited onboarding include?

Rep: Dedicated onboarding engineer, daily check-ins for the first week, priority support queue, and I personally stay involved until you're live. We've done this for three clients in the past year who had similar situations.

Prospect: What integrations are you going to need from my side?

Prospect: Sorry — I mean what does our team need to provide to make this happen?

Rep: Access to your CRM, your ILS feed credentials, and a brand voice document or examples of outreach emails your team has sent. That's 90% of what we need.

Prospect: Our CRM is HubSpot. ILS feeds are CoStar and Apartments.com. Brand voice document I can put together in a day.

Rep: We have native integrations for all three. I can have a technical intake form to you this afternoon so we can kick off immediately.

Prospect: What's the commitment structure? I don't want a 12-month contract if this doesn't work out.

Rep: For new clients with urgent timelines we offer a 90-day initial term with the option to renew annually. If it's not delivering value in 90 days you're not locked in.

Prospect: That's reasonable. What's the cost?

Rep: For your client portfolio at this size, you'd be looking at $1,800 a month during the 90-day term. If you expand beyond this client, we reprice at scale.

Prospect: Send me a one-page summary and a contract draft. If legal is clean I can sign this week.

Rep: I'll have both to you by 5pm today. Who should I copy on the contract email?

Prospect: Me and our CEO, Michael Barrera. His email is m.barrera@southwestpropertyadvisors.com.

Rep: Got it. Talk soon, Laura.""",
    },
    {
        "title": "Exploratory Call — Cityscape Living REIT",
        "description": "Ambiguous early-stage call with VP of Resident Success; prospect is interested but unfocused and signals competing internal priorities.",
        "lead_index": 17,
        "transcript": """Rep: Aaron, good to connect. I saw from the form you submitted that you're thinking about resident retention automation. Can you give me a bit more context on where that fits in your priorities right now?

Prospect: Yeah, so, it's on my radar. I wouldn't call it top priority at the moment but it's something our COO has mentioned a few times in leadership meetings. The theory is that if we reach out proactively before someone gives notice, we might change more of their minds. The question is whether we can do that at scale.

Rep: What does your current renewal outreach process look like?

Prospect: Honestly it's pretty ad hoc. Leasing managers reach out to residents 60 days before lease expiration — sometimes. It depends on how busy they are. We don't have a system that flags it automatically or sends anything without a human kicking it off.

Rep: So the gap is consistency — some residents get proactive outreach and some don't.

Prospect: Right. And we have no visibility into which ones are likely to leave. Someone who's been here three years and just got a rent increase is probably a different risk level than someone in their first year, but we treat them the same.

Rep: How much of your attrition do you think is preventable with better outreach?

Prospect: I genuinely don't know. It's something we've been meaning to analyze but haven't. Maybe 10, 15 percent? I'm speculating.

Rep: What would need to be true for this to move up in priority for you?

Prospect: Probably if someone ran the numbers and showed what even a 5% improvement in retention is worth in revenue. That's something I've been meaning to do but keep pushing. Also, we have a fairly large system migration happening right now — we're moving from RealPage to Yardi — and that's consuming most of my team's bandwidth. I don't want to layer in something new while we're in the middle of that.

Rep: When does the Yardi migration wrap up?

Prospect: Q1 of next year. Maybe late Q1. It's been slipping.

Rep: So realistically, revisiting this in Q2 next year makes sense?

Prospect: Probably. Unless something changes. I want to stay informed — I'm not saying never, just not right now. Can you send me some material I can read on my own timeline?

Rep: Of course. I'll send a brief capability overview and a retention ROI calculator you can fill in with your own data. No commitment, just something useful to have when the timing is right.

Prospect: That works. And honestly, if the Yardi migration goes smoothly, things might open up sooner. Hard to say.

Rep: Understood. I'll follow up in March unless I hear from you sooner. Does that work?

Prospect: Sure. March is fine. I'll put a note in my calendar.

Rep: Great. Thanks for the candid conversation, Aaron. Talk soon.""",
    },
]
