console.log("INnovateAI Shield JS is working!");


async function analyzeAnnouncement() {

    const announcement =
        document
        .getElementById("announcement")
        .value
        .trim();

    const link =
        document
        .getElementById("link")
        .value
        .trim();

    const result =
        document
        .getElementById("result");


    if (!announcement) {

        alert(
            "Please paste an announcement first."
        );

        return;
    }


    result.innerHTML = `
        <div class="loading">
            <h2>🔍 Analyzing...</h2>

            <p>
                INnovateAI Shield is checking
                the announcement and verifying
                the organization.
            </p>

            <p>
                🌐 Searching for reliable sources...
            </p>
        </div>
    `;


    try {

        const response =
            await fetch(
                "/analyze",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        announcement: announcement,
                        link: link
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Something went wrong."
            );
        }


        // ==========================================
        // TRUST STATUS
        // ==========================================

        let statusTitle = "";
        let statusClass = "";
        let statusMessage = "";


        if (
            data.trust_status ===
            "trusted"
        ) {

            statusTitle =
                "🟢 Trusted";

            statusClass =
                "trusted";

            statusMessage =
                "This opportunity passed the current verification checks.";

        }

        else if (
            data.trust_status ===
            "needs_verification"
        ) {

            statusTitle =
                "🟡 Needs Verification";

            statusClass =
                "needs-verification";

            statusMessage =
                "The available evidence is not enough to recommend sharing yet.";

        }

        else {

            statusTitle =
                "🔴 Not Trusted";

            statusClass =
                "not-trusted";

            statusMessage =
                "This announcement is not recommended for sharing.";
        }


        // ==========================================
        // ORGANIZATION VERIFICATION
        // ==========================================

        const organizationVerification =
            data.organization_verification || {};


        let organizationStatus =
            organizationVerification.status ||
            "needs_verification";


        let organizationStatusText = "";
        let organizationClass = "";


        if (
            organizationStatus ===
            "verified"
        ) {

            organizationStatusText =
                "🟢 Organization Verified";

            organizationClass =
                "verified";

        }

        else if (
            organizationStatus ===
            "not_verified"
        ) {

            organizationStatusText =
                "🔴 Organization Not Verified";

            organizationClass =
                "not-verified";

        }

        else {

            organizationStatusText =
                "🟡 Organization Needs Verification";

            organizationClass =
                "needs-verification";
        }


        // ==========================================
        // EVIDENCE
        // ==========================================

        const evidence =
            organizationVerification.evidence ||
            [];


        const evidenceHTML =
            evidence.length > 0

            ? evidence
                .map(
                    item =>
                    `<li>${escapeHTML(item)}</li>`
                )
                .join("")

            : `<li>No sufficient evidence was found.</li>`;


        // ==========================================
        // CONCERNS
        // ==========================================

        const concerns =
            organizationVerification.concerns ||
            [];


        const concernsHTML =
            concerns.length > 0

            ? concerns
                .map(
                    item =>
                    `<li>${escapeHTML(item)}</li>`
                )
                .join("")

            : `<li>No specific concerns were reported.</li>`;


        // ==========================================
        // SOURCES
        // ==========================================

        const sources =
            organizationVerification.sources ||
            [];


        const sourcesHTML =
            sources.length > 0

            ? sources
                .map(
                    source => {

                        const safeSource =
                            escapeHTML(source);

                        return `
                            <li>
                                <a
                                    href="${safeSource}"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    ${safeSource}
                                </a>
                            </li>
                        `;
                    }
                )
                .join("")

            : `<li>No sources were returned.</li>`;


        // ==========================================
        // OFFICIAL WEBSITE
        // ==========================================

        let officialWebsiteHTML =
            "Not identified";


        if (
            organizationVerification
                .official_website
        ) {

            const website =
                escapeHTML(
                    organizationVerification
                        .official_website
                );


            officialWebsiteHTML = `
                <a
                    href="${website}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    ${website}
                </a>
            `;
        }


        // ==========================================
        // POSITIVE SIGNALS
        // ==========================================

        const positiveSignals =
            data.positive_signals ||
            [];


        const positiveHTML =
            positiveSignals.length > 0

            ? positiveSignals
                .map(
                    item =>
                    `<li>${escapeHTML(item)}</li>`
                )
                .join("")

            : `<li>No strong positive signals identified.</li>`;


        // ==========================================
        // VERIFICATION NEEDED
        // ==========================================

        const verificationNeeded =
            data.verification_needed ||
            [];


        const verificationHTML =
            verificationNeeded.length > 0

            ? verificationNeeded
                .map(
                    item =>
                    `<li>${escapeHTML(item)}</li>`
                )
                .join("")

            : `<li>No additional missing information identified.</li>`;


        // ==========================================
        // RED FLAGS
        // ==========================================

        const redFlags =
            data.strong_red_flags ||
            [];


        const redFlagsHTML =
            redFlags.length > 0

            ? redFlags
                .map(
                    item =>
                    `<li>${escapeHTML(item)}</li>`
                )
                .join("")

            : `<li>✅ No strong red flags identified.</li>`;


        // ==========================================
        // REASONS
        // ==========================================

        const reasons =
            data.reasons ||
            [];


        const reasonsHTML =
            reasons.length > 0

            ? reasons
                .map(
                    item =>
                    `<li>${escapeHTML(item)}</li>`
                )
                .join("")

            : `<li>No additional explanation provided.</li>`;


        // ==========================================
        // ORGANIZATION NOTES
        // ==========================================

        const notes =
            organizationVerification.notes ||
            [];


        const notesHTML =
            notes.length > 0

            ? notes
                .map(
                    item =>
                    `<li>${escapeHTML(item)}</li>`
                )
                .join("")

            : `<li>No additional notes.</li>`;


        // ==========================================
        // SHARE TEXT
        // ==========================================

        const shareText =
            data.share_text ||
            "No shareable announcement was generated.";


        // ==========================================
        // FINAL RESULT
        // ==========================================

        result.innerHTML = `

            <div class="trust-result">

                <!-- BRAND -->

                <div class="brand">
                    🛡️
                    <strong>
                        INnovateAI Shield
                    </strong>
                </div>


                <!-- TRUST RESULT -->

                <div class="${statusClass}">

                    <h1>
                        ${statusTitle}
                    </h1>

                    <p>
                        ${statusMessage}
                    </p>

                </div>


                <!-- TRUST SCORE -->

                <div class="score">

                    <strong>
                        ${data.trust_score}/100
                    </strong>

                    <span>
                        Trust Score
                    </span>

                </div>


                <hr>


                <!-- ORGANIZATION VERIFICATION -->

                <h3>
                    🏢 Organization Verification
                </h3>


                <div class="${organizationClass} verification-box">

                    <h3>
                        ${organizationStatusText}
                    </h3>


                    <p>

                        <strong>
                            Organization:
                        </strong>

                        ${
                            escapeHTML(
                                organizationVerification
                                    .organization ||
                                "Not identified"
                            )
                        }

                    </p>


                    <p>

                        <strong>
                            Official Website:
                        </strong>

                        ${officialWebsiteHTML}

                    </p>

                </div>


                <!-- EVIDENCE -->

                <h3>
                    📚 Evidence Found
                </h3>


                <ul>
                    ${evidenceHTML}
                </ul>


                <!-- SOURCES -->

                <h3>
                    🔗 Verification Sources
                </h3>


                <ul>
                    ${sourcesHTML}
                </ul>


                <!-- CONCERNS -->

                <h3>
                    ⚠️ Verification Concerns
                </h3>


                <ul>
                    ${concernsHTML}
                </ul>


                <!-- NOTES -->

                <h3>
                    📌 Verification Notes
                </h3>


                <ul>
                    ${notesHTML}
                </ul>


                <hr>


                <!-- ANNOUNCEMENT -->

                <h3>
                    📋 Announcement Analysis
                </h3>


                <p>

                    <strong>
                        Title:
                    </strong>

                    ${
                        escapeHTML(
                            data.title ||
                            "Not mentioned"
                        )
                    }

                </p>


                <p>

                    <strong>
                        Organization:
                    </strong>

                    ${
                        data.organizations &&
                        data.organizations.length

                        ? data.organizations
                            .map(
                                item =>
                                escapeHTML(item)
                            )
                            .join(", ")

                        : "Not mentioned"
                    }

                </p>


                <p>

                    <strong>
                        Opportunity Type:
                    </strong>

                    ${
                        escapeHTML(
                            data.opportunity_type ||
                            "Not mentioned"
                        )
                    }

                </p>


                <p>

                    <strong>
                        Cost:
                    </strong>

                    ${
                        escapeHTML(
                            data.cost ||
                            "Not mentioned"
                        )
                    }

                </p>


                <p>

                    <strong>
                        Certificate:
                    </strong>

                    ${
                        escapeHTML(
                            data.certificate ||
                            "Not mentioned"
                        )
                    }

                </p>


                <p>

                    <strong>
                        Deadline:
                    </strong>

                    ${
                        escapeHTML(
                            data.deadline ||
                            "Not mentioned"
                        )
                    }

                </p>


                <hr>


                <!-- POSITIVE -->

                <h3>
                    ✅ Positive Signals
                </h3>


                <ul>
                    ${positiveHTML}
                </ul>


                <!-- VERIFICATION NEEDED -->

                <h3>
                    🟡 Information That Needs Verification
                </h3>


                <ul>
                    ${verificationHTML}
                </ul>


                <!-- RED FLAGS -->

                <h3>
                    🚩 Strong Red Flags
                </h3>


                <ul>
                    ${redFlagsHTML}
                </ul>


                <!-- REASONS -->

                <h3>
                    💡 Why?
                </h3>


                <ul>
                    ${reasonsHTML}
                </ul>


                <hr>


                <!-- FINAL STUDENT ANNOUNCEMENT -->

                <h3>
                    📢 Final Student Announcement
                </h3>


                <textarea
                    id="shareText"
                    readonly
                >${escapeHTML(shareText)}</textarea>


                <button
                    onclick="copyShareText()"
                >
                    📋 Copy Announcement
                </button>


                <p class="branding">

                    🛡️

                    Organized & analyzed by

                    <strong>
                        INnovateAI Shield
                    </strong>

                </p>

            </div>

        `;

    }


    catch (error) {

        console.error(error);


        result.innerHTML = `

            <div class="error-box">

                <h2>
                    ❌ Error
                </h2>

                <p>
                    ${escapeHTML(error.message)}
                </p>

            </div>

        `;
    }
}


/* ==========================================
   COPY ANNOUNCEMENT
========================================== */

function copyShareText() {

    const shareText =
        document
        .getElementById("shareText");


    if (!shareText) {

        alert(
            "There is no announcement to copy."
        );

        return;
    }


    navigator.clipboard
        .writeText(
            shareText.value
        )

        .then(() => {

            alert(
                "✅ Announcement copied successfully!"
            );

        })

        .catch(() => {

            shareText.select();

            document.execCommand(
                "copy"
            );

            alert(
                "✅ Announcement copied successfully!"
            );

        });
}


/* ==========================================
   SECURITY
========================================== */

function escapeHTML(value) {

    if (value === null ||
        value === undefined) {

        return "";
    }


    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );
}