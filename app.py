import os
import json
import time
import threading
import requests

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

from google import genai
from google.genai import types
from google.genai import errors

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    class ResourceExhausted(Exception):
        """Fallback ResourceExhausted exception class."""
        pass


# ==================================================
# SETUP
# ==================================================

load_dotenv()

app = Flask(__name__)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY was not found in .env"
    )

client = genai.Client(
    api_key=api_key
)


# ==================================================
# RATE LIMITING & RETRY CONFIGURATION
# ==================================================

# Free tier rate limit: 20 requests per minute (60s / 20 = 3.0s minimum).
# We enforce a 3.5s delay between consecutive calls to stay safely below the limit.
CALL_DELAY_SECONDS = 3.5
INITIAL_RETRY_DELAY = 30.0  # Wait at least 30 seconds on ResourceExhausted/429 before retrying
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0
GEMINI_MODEL = "gemini-3.6-flash"

_last_call_time = 0.0
_call_lock = threading.Lock()


def wait_for_rate_limit():
    """
    Ensures an appropriate delay between consecutive Gemini API calls
    to prevent exceeding the 20 requests/minute rate limit.
    """
    global _last_call_time

    with _call_lock:
        now = time.time()
        elapsed = now - _last_call_time

        if elapsed < CALL_DELAY_SECONDS:
            sleep_time = CALL_DELAY_SECONDS - elapsed
            time.sleep(sleep_time)

        _last_call_time = time.time()


def is_rate_limit_error(exception: Exception) -> bool:
    """
    Determines if an exception represents a 429 Resource Exhausted / Rate Limit error.
    """
    if isinstance(exception, ResourceExhausted):
        return True

    if isinstance(exception, (errors.APIError, errors.ClientError)):
        if getattr(exception, "code", None) == 429:
            return True
        if getattr(exception, "status", None) == "RESOURCE_EXHAUSTED":
            return True

    err_str = str(exception).upper()
    err_type = type(exception).__name__.upper()

    if (
        "RESOURCE_EXHAUSTED" in err_str
        or "429" in err_str
        or "RATE LIMIT" in err_str
        or "RESOURCEEXHAUSTED" in err_type
        or "RESOURCE_EXHAUSTED" in err_type
    ):
        return True

    return False


def extract_retry_delay(exception: Exception, default_delay: float = INITIAL_RETRY_DELAY) -> float:
    """
    Extracts recommended retryDelay from API error response details if present,
    otherwise returns default_delay.
    """
    delay = default_delay

    try:
        details_obj = getattr(exception, "details", None)

        if isinstance(details_obj, dict):
            error_data = details_obj.get("error", details_obj)

            for item in error_data.get("details", []):
                if isinstance(item, dict) and "retryDelay" in item:
                    raw_delay = str(item["retryDelay"]).rstrip("s")
                    delay = max(delay, float(raw_delay))
                    return delay

    except Exception:
        pass

    return delay


def call_gemini_with_retry(
    contents,
    model=GEMINI_MODEL,
    config=None,
    max_retries=MAX_RETRIES,
    initial_retry_delay=INITIAL_RETRY_DELAY,
    backoff_factor=BACKOFF_FACTOR
):
    """
    Executes client.models.generate_content with rate limiting pacing and exponential backoff.
    Waits 30 seconds before retrying automatically upon encountering ResourceExhausted/429.
    """
    retry_delay = initial_retry_delay

    for attempt in range(1, max_retries + 1):
        wait_for_rate_limit()

        try:
            if config:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config
                )
            else:
                response = client.models.generate_content(
                    model=model,
                    contents=contents
                )

            return response

        except (ResourceExhausted, errors.APIError, errors.ClientError, Exception) as e:
            if is_rate_limit_error(e):
                actual_wait = extract_retry_delay(e, retry_delay)
                actual_wait = max(actual_wait, retry_delay)

                print(
                    f"[Rate Limit] Hit 429/ResourceExhausted on attempt {attempt}/{max_retries}: {e}"
                )

                if attempt < max_retries:
                    print(
                        f"[Retry] Waiting {actual_wait:.1f}s before retrying Gemini API call..."
                    )
                    time.sleep(actual_wait)
                    retry_delay = max(retry_delay * backoff_factor, actual_wait * backoff_factor)
                    continue
                else:
                    print(
                        f"[Rate Limit] Maximum retries ({max_retries}) exceeded for Gemini API call."
                    )
                    raise
            else:
                raise


# ==================================================
# CHECK LINK
# ==================================================

def check_link(url):

    if not url:
        return {
            "provided": False,
            "reachable": False,
            "status": "No link provided"
        }

    if not url.startswith(
        ("http://", "https://")
    ):
        return {
            "provided": True,
            "reachable": False,
            "status": "Invalid URL"
        }

    try:

        response = requests.get(
            url,
            timeout=10,
            allow_redirects=True,
            headers={
                "User-Agent":
                "INnovateAI-Shield/1.0"
            }
        )

        return {
            "provided": True,
            "reachable": response.ok,
            "status_code": response.status_code,
            "final_url": response.url
        }

    except requests.RequestException as e:

        return {
            "provided": True,
            "reachable": False,
            "status": "Connection failed",
            "error": str(e)
        }


# ==================================================
# ORGANIZATION VERIFICATION
# ==================================================

def verify_organization(
    organization,
    announcement,
    link
):

    if not organization:

        return {
            "organization":
                "Not identified",

            "status":
                "not_verified",

            "official_website":
                "",

            "evidence": [],

            "concerns": [
                "No organization name was identified."
            ],

            "sources": []
        }


    prompt = f"""

You are the organization verification
engine for INnovateAI Shield.

Your task is to investigate whether the
organization mentioned in the announcement
is a real organization and whether there is
credible evidence supporting it.

IMPORTANT:

Do NOT assume an organization is trustworthy
just because a website exists.

Use web search to investigate the organization.

Prefer evidence from:

- Official organization websites
- Universities
- Government websites
- Official company pages
- Reputable news organizations
- Reputable independent sources

Do NOT treat these alone as proof:

- Random blogs
- Social media posts
- User-generated pages
- The announcement itself
- Search result snippets without a reliable source

Organization:

{organization}

Announcement:

{announcement}

Announcement link:

{link}

Return ONLY valid JSON.

Use exactly this structure:

{{
    "organization": "",
    "status": "verified | needs_verification | not_verified",
    "official_website": "",
    "evidence": [],
    "concerns": [],
    "sources": []
}}

Rules:

1. Use "verified" only when there is strong
   credible evidence that the organization
   exists.

2. Use "needs_verification" when the organization
   may exist but there is not enough evidence
   to establish legitimacy or the connection
   to this announcement.

3. Use "not_verified" when credible evidence
   supporting the organization cannot be found.

4. Never invent a website.

5. Never invent sources.

6. Include URLs only for sources actually
   found during the search.

7. Separately evaluate whether the announcement
   link appears to belong to the organization.

8. A free hosting service such as Vercel,
   Netlify, or GitHub Pages is NOT automatically
   evidence of fraud.

9. Do not call an organization fraudulent
   without strong evidence.
"""


    try:

        search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )


        config = types.GenerateContentConfig(
            tools=[search_tool],

            response_mime_type=
                "application/json"
        )


        response = call_gemini_with_retry(

            model=GEMINI_MODEL,

            contents=prompt,

            config=config
        )


        text = response.text.strip()


        if text.startswith("```"):

            text = text.replace(
                "```json",
                ""
            )

            text = text.replace(
                "```",
                ""
            )

            text = text.strip()


        return json.loads(text)


    except Exception as e:

        return {

            "organization":
                organization,

            "status":
                "needs_verification",

            "official_website":
                "",

            "evidence": [],

            "concerns": [
                "Web verification could not be completed."
            ],

            "sources": [],

            "error":
                str(e)
        }


# ==================================================
# SOURCE VERIFICATION
# ==================================================

def verify_source(
    organization,
    link,
    link_info
):

    verification = {

        "organization":
            organization,

        "link_provided":
            bool(link),

        "website_reachable":
            link_info.get(
                "reachable",
                False
            ),

        "domain":
            link_info.get(
                "final_url",
                ""
            ),

        "status":
            "needs_verification",

        "notes": []
    }


    if not link:

        verification["notes"].append(
            "No source link was provided."
        )


    elif not link_info.get(
        "reachable",
        False
    ):

        verification["notes"].append(
            "The provided website could not be reached."
        )


    else:

        verification["notes"].append(
            "The provided website responded successfully."
        )


    if organization:

        verification["notes"].append(
            "Organization identified from the announcement."
        )

    else:

        verification["notes"].append(
            "Organization could not be identified."
        )


    return verification


# ==================================================
# TRUST SCORE
# ==================================================

def calculate_trust_score(
    result,
    link_info,
    organization_verification
):

    score = 50


    positive = result.get(
        "positive_signals",
        []
    )

    verification_needed = result.get(
        "verification_needed",
        []
    )

    red_flags = result.get(
        "strong_red_flags",
        []
    )


    # Positive signals
    score += min(
        len(positive) * 8,
        24
    )


    # Missing information
    score -= min(
        len(verification_needed) * 4,
        20
    )


    # Strong red flags
    score -= min(
        len(red_flags) * 15,
        45
    )


    # Link check
    if link_info.get("provided"):

        if link_info.get("reachable"):
            score += 5

        else:
            score -= 15


    # Organization verification
    organization_status = (
        organization_verification.get(
            "status"
        )
    )


    if organization_status == "verified":

        score += 15


    elif organization_status == "not_verified":

        score -= 20


    elif organization_status == "needs_verification":

        score -= 5


    score = max(
        0,
        min(score, 100)
    )


    # Final decision
    if (
        score >= 75
        and organization_status == "verified"
        and len(red_flags) == 0
    ):

        status = "trusted"

        recommendation = "share"


    elif score >= 45:

        status = "needs_verification"

        recommendation = (
            "do_not_share_yet"
        )


    else:

        status = "untrusted"

        recommendation = "do_not_share"


    return (
        score,
        status,
        recommendation
    )


# ==================================================
# CREATE STUDENT ANNOUNCEMENT
# ==================================================

def create_share_text(result):

    status = result.get(
        "trust_status"
    )


    title = result.get(
        "title",
        "Announcement"
    )


    organizations = result.get(
        "organizations",
        []
    )


    organization = ", ".join(
        organizations
    )


    opportunity = result.get(
        "opportunity_type",
        "Not mentioned"
    )


    cost = result.get(
        "cost",
        "Not mentioned"
    )


    deadline = result.get(
        "deadline",
        "Not mentioned"
    )


    links = result.get(
        "links",
        []
    )


    if status == "trusted":

        header = (
            "🟢 VERIFIED OPPORTUNITY"
        )

        message = (
            "✅ This opportunity passed "
            "the current INnovateAI Shield "
            "verification checks."
        )


    elif status == "needs_verification":

        header = (
            "🟡 NEEDS VERIFICATION"
        )

        message = (
            "⚠️ This opportunity has not "
            "been sufficiently verified. "
            "Please verify it before sharing."
        )


    else:

        header = (
            "🔴 NOT RECOMMENDED"
        )

        message = (
            "🚨 This announcement is not "
            "recommended for sharing."
        )


    link_text = (
        "\n".join(links)
        if links
        else "Not mentioned"
    )


    return f"""
🛡️ INnovateAI Shield

{header}

📢 {title}

🏢 Organization:
{organization or "Not mentioned"}

💼 Opportunity Type:
{opportunity}

💰 Cost:
{cost}

📅 Deadline:
{deadline}

🔗 Registration / Source:
{link_text}

{message}

—
Organized & analyzed by
INnovateAI Shield
""".strip()


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==================================================
# ANALYZE
# ==================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    try:

        data = request.get_json(silent=True) or {}


        announcement = data.get(
            "announcement",
            ""
        ).strip()


        link = data.get(
            "link",
            ""
        ).strip()


        if not announcement:

            return jsonify({
                "error":
                    "Please enter an announcement."
            }), 400


        # ------------------------------------------
        # Check link
        # ------------------------------------------

        link_info = check_link(
            link
        )


        # ------------------------------------------
        # Gemini analysis
        # ------------------------------------------

        prompt = f"""

You are the announcement analysis engine
for INnovateAI Shield.

Analyze the following announcement.

Return ONLY valid JSON.

Do not use Markdown.

Do not invent information.

Use exactly:

{{
    "title": "",
    "organizations": [],
    "opportunity_type": "",
    "cost": "",
    "certificate": "",
    "deadline": "",
    "links": [],
    "positive_signals": [],
    "verification_needed": [],
    "strong_red_flags": [],
    "reasons": []
}}

Rules:

- Extract facts only from the announcement.
- Do not invent missing details.
- Missing information goes into
  verification_needed.
- Strong red flags require actual evidence.
- A Vercel, Netlify, or GitHub Pages domain
  is NOT automatically a red flag.

Announcement link:

{link}

Link check:

{json.dumps(
    link_info,
    ensure_ascii=False
)}

Announcement:

{announcement}
"""


        response = call_gemini_with_retry(

            model=GEMINI_MODEL,

            contents=prompt
        )


        text = response.text.strip()


        if text.startswith("```"):

            text = text.replace(
                "```json",
                ""
            )

            text = text.replace(
                "```",
                ""
            )

            text = text.strip()


        result = json.loads(
            text
        )


        # ------------------------------------------
        # Organization
        # ------------------------------------------

        organization = ", ".join(
            result.get(
                "organizations",
                []
            )
        )


        # ------------------------------------------
        # Verify organization
        # ------------------------------------------

        organization_verification = (
            verify_organization(

                organization,

                announcement,

                link
            )
        )


        # ------------------------------------------
        # Basic source verification
        # ------------------------------------------

        source_verification = (
            verify_source(

                organization,

                link,

                link_info
            )
        )


        # ------------------------------------------
        # Trust Score
        # ------------------------------------------

        score, status, recommendation = (
            calculate_trust_score(

                result,

                link_info,

                organization_verification
            )
        )


        # ------------------------------------------
        # Add final information
        # ------------------------------------------

        result[
            "trust_score"
        ] = score


        result[
            "trust_status"
        ] = status


        result[
            "share_recommendation"
        ] = recommendation


        result[
            "link_check"
        ] = link_info


        result[
            "source_verification"
        ] = source_verification


        result[
            "organization_verification"
        ] = organization_verification


        result[
            "share_text"
        ] = create_share_text(
            result
        )


        return jsonify(
            result
        )


    except json.JSONDecodeError:

        return jsonify({

            "error":
                "The AI returned invalid JSON.",

            "raw_response":
                response.text

        }), 500


    except Exception as e:
        if is_rate_limit_error(e):
            return jsonify({
                "error":
                    "Gemini API rate limit was exceeded. Please wait a moment and try again."
            }), 429

        return jsonify({

            "error":
                str(e)

        }), 500


# ==================================================
# GLOBAL ERROR HANDLERS
# ==================================================

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "error": "An internal server error occurred. Please try again."
    }), 500


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
