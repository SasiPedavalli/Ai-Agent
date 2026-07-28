"""
app.py — Resume Pipeline, local edition.

Runs entirely on your laptop. Your Anthropic API key stays in your local
.env file and is never sent anywhere except Anthropic's API.

Setup:
    pip install -r requirements.txt
    cp .env.example .env        # then paste your key into .env
    python app.py
    open http://localhost:5050
"""

import os
import json
import re
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "ANTHROPIC_API_KEY not found. Copy .env.example to .env and add your key "
        "from https://console.anthropic.com/settings/keys"
    )

client = Anthropic(api_key=API_KEY, timeout=120.0)
MODEL = "claude-sonnet-4-6"

app = Flask(__name__)


def extract_text(message) -> str:
    return "".join(block.text for block in message.content if block.type == "text").strip()


def extract_json(text: str):
    text = re.sub(r"```json|```", "", text).strip()
    match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
    return json.loads(match.group(0) if match else text)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search():
    body = request.json
    query = body.get("query", "")
    location = body.get("location", "")
    filters = body.get("filters", {})

    filter_lines = []
    if filters.get("excludeClearance"):
        filter_lines.append("Exclude any posting that requires security clearance, US citizenship, or a green card.")
    if filters.get("excludeNoSponsor"):
        filter_lines.append("Exclude any posting that explicitly states it does not offer visa/immigration sponsorship.")
    modes = filters.get("modes", [])
    if modes and len(modes) < 3:
        filter_lines.append(f"Only include postings with work mode in: {', '.join(modes)}. Skip others.")
    levels = filters.get("levels", [])
    if levels:
        filter_lines.append(f"Only include postings whose seniority/experience level matches: {', '.join(levels)}.")
    filter_lines.append(
        'Strongly prioritize the most recently posted listings — search using date filters or "posted today", '
        '"posted this week" style queries where the job board supports it. Skip anything older than 2 weeks '
        "unless nothing newer is available."
    )

    system = f"""You search the live web for current job postings across major job boards (LinkedIn, Indeed, Dice, \
ZipRecruiter, Glassdoor, Built In, Wellfound, JobRight AI) and individual company career pages, then report back \
a clean, structured shortlist, sorted newest posting first.
{' '.join(filter_lines)}
Be efficient: run a small number of targeted searches rather than exhaustively re-searching.
Output ONLY valid JSON, an array of up to 3 objects, sorted newest-first, each with:
"title", "company", "location", "work_mode" (Remote/Hybrid/Onsite/Not specified), "level" (Entry/Mid/Senior/Lead/Principal/Not specified), \
"posted" (e.g. "Today", "2 days ago", "Unknown"), "summary" (2 sentence paraphrase, never copy source text verbatim), \
"keywords" (array of 5-8 ATS terms), "url", "jd_text" (80-120 word paraphrase, your own words, no verbatim copying).
Prioritize small/mid-size and less obvious companies over the largest, most-applied-to tech employers when relevant \
results exist. Skip staffing-agency listings with no real employer named."""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1800,
            system=system,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 2}],
            messages=[{"role": "user", "content": f'Search for: "{query}" in "{location}". Return the JSON array.'}],
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"jobs": [], "error": f"API call failed: {str(e)}"}), 200

    try:
        jobs = extract_json(extract_text(message))
    except Exception:
        jobs = []
    return jsonify({"jobs": jobs})


@app.route("/api/tailor", methods=["POST"])
def tailor():
    body = request.json
    resume = body.get("resume", "")
    jd = body.get("jd", "")
    include_certs = body.get("includeCerts", True)
    include_summary = body.get("includeSummary", True)
    include_cover_letter = body.get("includeCoverLetter", True)

    certs_instruction = (
        'Add a line under CERTIFICATIONS for these real credentials if not already reflected: "Claude 101", '
        '"Claude Code in Action", "AI Fluency Framework and Foundations" — only if they plausibly strengthen fit '
        "for this role (AI/ML/automation/AI-ready data infra angle)."
        if include_certs else "Do not add any new certifications."
    )
    summary_instruction = (
        "Rewrite PROFESSIONAL SUMMARY as 5-6 bullets speaking directly to this JD's core requirements, 100% grounded "
        "in the source resume."
        if include_summary else "Keep PROFESSIONAL SUMMARY close to original with light keyword adjustments."
    )

    system_prompt = f"""You are an expert technical resume editor tailoring a real candidate's resume to a specific job posting.
HARD RULES:
1. NEVER invent employers, titles, dates, degrees, or certifications not in the source resume.
2. NEVER invent specific metrics/percentages/dollar amounts/scale figures not already in the source resume. Reword \
and re-emphasize real statements; use general strong language instead of fabricated numbers.
3. Keep company names, job titles, and employment dates EXACTLY as given.
4. Every bullet must trace to something actually in the source resume.
5. Naturally incorporate JD keywords only where real experience genuinely supports them.
{summary_instruction}
{certs_instruction}
Keep the same section structure. Each experience entry: 8-10 non-redundant bullets if supported, no padding.
Output ONLY the final tailored resume text, plain formatting, section headers in capitals. No preamble, no markdown symbols."""

    try:
        resume_msg = client.messages.create(
            model=MODEL, max_tokens=4000, system=system_prompt,
            messages=[{"role": "user", "content": f"SOURCE RESUME:\n{resume}\n\n---\n\nJOB DESCRIPTION:\n{jd}"}],
        )
    except Exception as e:
        return jsonify({"resume": "", "score": None, "letter": None, "error": f"API call failed: {str(e)}"}), 200
    tailored_resume = extract_text(resume_msg)

    score = None
    if tailored_resume:
        try:
            score_msg = client.messages.create(
                model=MODEL, max_tokens=400,
                system='You are an ATS matching evaluator. Output ONLY valid JSON: {"score": <0-100 integer>, "rationale": "<2-3 sentences>"}.',
                messages=[{"role": "user", "content": f"RESUME:\n{tailored_resume}\n\n---\n\nJOB DESCRIPTION:\n{jd}"}],
            )
            score = extract_json(extract_text(score_msg))
        except Exception:
            score = None

    letter = None
    if include_cover_letter and tailored_resume:
        letter_msg = client.messages.create(
            model=MODEL, max_tokens=1200,
            system="You write concise, professional cover letters (250-350 words). Ground every claim in the "
                   "source resume provided — no invented achievements, metrics, or skills. Warm but professional "
                   "tone, specific to the role/company where named, no generic filler. Output ONLY the letter text.",
            messages=[{"role": "user", "content": f"SOURCE RESUME:\n{resume}\n\n---\n\nJOB DESCRIPTION:\n{jd}\n\nWrite the cover letter."}],
        )
        letter = extract_text(letter_msg)

    return jsonify({"resume": tailored_resume, "score": score, "letter": letter})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)
 