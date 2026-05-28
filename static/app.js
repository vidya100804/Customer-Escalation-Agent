/* ==========================================================================
   Customer Escalation Agent UI Dashboard
   ========================================================================== */

const PRESETS = {
    stripe: {
        email: "customer@example.com",
        priority: "P2",
        reporter: "Sarah J.",
        issue: "Payment is continuously failing during checkout with an error. User says their card is active and needs help upgrading to Pro immediately.",
        meta: {
            userId: "usr_12345",
            userName: "John Doe",
            userTier: "Pro",
            userSub: "Active (Degraded Payment)",
            stripePlan: "Pro Monthly ($29.99)",
            stripeStatus: "Active",
            stripeFailed: "2 attempts",
            stripeError: "card_declined"
        },
        userDbJson: {
            user_id: "usr_12345",
            email: "customer@example.com",
            name: "John Doe",
            account_tier: "Pro",
            subscription_status: "active",
            last_login: "2026-05-26T14:22:00Z",
            api_calls_last_30_days: 15420
        },
        stripeJson: {
            plan: "Pro Monthly - $29.99",
            status: "active",
            failed_payment_attempts: 2,
            last_error: "card_declined",
            last_payment_date: "2026-05-01T00:00:00Z"
        },
        logsText: `2026-05-26T21:05:15Z [ERROR] service=payment-service error_code=PAY_503 message="Payment failed: card declined"
2026-05-26T21:03:45Z [WARNING] service=payment-service error_code=PAY_RETRY message="Retry attempt 2/3"
2026-05-26T21:00:30Z [INFO] service=api-gateway message="User checkout initiated"`,
        ticketsHtml: `
            <div class="timeline-event">
                <div class="event-marker resolved"></div>
                <div class="event-content">
                    <div class="event-header">
                        <span class="ticket-id">ZD-9876</span>
                        <span class="ticket-status resolved">Solved</span>
                    </div>
                    <h4 class="event-subject">Payment failed</h4>
                    <p class="event-res"><strong>Resolution:</strong> User updated payment credentials via checkout settings. Charges passed successfully.</p>
                </div>
            </div>`
    },
    ratelimit: {
        email: "dev-lead@megacorp.io",
        priority: "P1",
        reporter: "Sarah J.",
        issue: "Our backend integration scripts are suddenly receiving HTTP 429 Too Many Requests errors when uploading nightly analytics reports. This is halting critical reporting pipelines. Please white-list or upgrade us immediately.",
        meta: {
            userId: "usr_99887",
            userName: "Alex Mercer (MegaCorp)",
            userTier: "Pro Enterprise-Ready",
            userSub: "Active (Usage Throttled)",
            stripePlan: "Pro Custom ($149.00)",
            stripeStatus: "Active",
            stripeFailed: "0",
            stripeError: "None"
        },
        userDbJson: {
            user_id: "usr_99887",
            email: "dev-lead@megacorp.io",
            name: "Alex Mercer (MegaCorp)",
            account_tier: "Pro",
            subscription_status: "active",
            last_login: "2026-05-26T20:45:00Z",
            api_calls_last_30_days: 28940
        },
        stripeJson: {
            plan: "Pro Custom Annual - $1,788.00",
            status: "active",
            failed_payment_attempts: 0,
            last_error: null,
            last_payment_date: "2026-05-15T00:00:00Z"
        },
        logsText: `2026-05-26T21:04:10Z [ERROR] service=api-gateway error_code=API_429 message="Too Many Requests: exceeded tier limit of 20000"
2026-05-26T21:02:15Z [WARNING] service=api-gateway message="Usage warning: 95% of quota used"
2026-05-26T20:55:00Z [INFO] service=analytics-sync message="Bulk batch upload initiated"`,
        ticketsHtml: `
            <div class="timeline-event">
                <div class="event-marker resolved"></div>
                <div class="event-content">
                    <div class="event-header">
                        <span class="ticket-id">ZD-8765</span>
                        <span class="ticket-status resolved">Closed</span>
                    </div>
                    <h4 class="event-subject">API rate limit warning</h4>
                    <p class="event-res"><strong>Resolution:</strong> Customer upgraded from Starter to Pro to raise quota from 5,000 to 20,000 API calls.</p>
                </div>
            </div>`
    },
    outage: {
        email: "operations@enterprisecloud.net",
        priority: "P0",
        reporter: "Alex S. (On-Call SRE)",
        issue: "CRITICAL OUTAGE: Our customer checkouts are completely frozen. Any click on pay results in spin lock timeouts and database connection errors. This is severely blocking revenue flow.",
        meta: {
            userId: "usr_77553",
            userName: "Ops Lead (EnterpriseCloud)",
            userTier: "Enterprise Tier",
            userSub: "Active (Outage Affected)",
            stripePlan: "Enterprise Custom ($999.00)",
            stripeStatus: "Active",
            stripeFailed: "0",
            stripeError: "None"
        },
        userDbJson: {
            user_id: "usr_77553",
            email: "operations@enterprisecloud.net",
            name: "Ops Lead (EnterpriseCloud)",
            account_tier: "Enterprise",
            subscription_status: "active",
            last_login: "2026-05-26T21:01:00Z",
            api_calls_last_30_days: 185900
        },
        stripeJson: {
            plan: "Enterprise Custom Monthly - $999.00",
            status: "active",
            failed_payment_attempts: 0,
            last_error: null,
            last_payment_date: "2026-05-01T00:00:00Z"
        },
        logsText: `2026-05-26T21:05:40Z [CRITICAL] service=payment-service error_code=PAY_503 message="Database connection pool exhausted. Spiked to 12.4s timeouts."
2026-05-26T21:05:10Z [ERROR] service=payment-service error_code=DB_CONNECTION_TIMEOUT message="Timeout waiting for connection pool (max 10s)"
2026-05-26T21:03:00Z [INFO] service=payment-service message="Database connections scaled to max 50"`,
        ticketsHtml: `
            <div class="timeline-event">
                <div class="event-marker resolved"></div>
                <div class="event-content">
                    <div class="event-header">
                        <span class="ticket-id">ZD-5432</span>
                        <span class="ticket-status resolved">Closed</span>
                    </div>
                    <h4 class="event-subject">Database Timeout Degradation</h4>
                    <p class="event-res"><strong>Resolution:</strong> Previous DB pool exhaustion patched in production by hotfix deploy v2.4.1. This appears to be a new occurrence.</p>
                </div>
            </div>`
    },
    custom: {
        email: "new-user@trial.org",
        priority: "P3",
        reporter: "Sarah J.",
        issue: "How do I invite more team members to our billing dashboard? I can't find the invite button under settings.",
        meta: {
            userId: "usr_88990",
            userName: "Trial Account",
            userTier: "Free Trial",
            userSub: "Trial",
            stripePlan: "Free Starter ($0)",
            stripeStatus: "active",
            stripeFailed: "0",
            stripeError: "None"
        },
        userDbJson: {
            user_id: "usr_88990",
            email: "new-user@trial.org",
            name: "Guest Customer",
            account_tier: "Free",
            subscription_status: "trial",
            last_login: "2026-05-26T19:00:00Z",
            api_calls_last_30_days: 120
        },
        stripeJson: {
            plan: "Free Tier - $0.00",
            status: "trial",
            failed_payment_attempts: 0,
            last_error: null,
            last_payment_date: null
        },
        logsText: `2026-05-26T20:10:00Z [INFO] service=api-gateway message="Dashboard settings loaded"
2026-05-26T20:09:40Z [INFO] service=api-gateway message="User session authenticated"`,
        ticketsHtml: `<p style="font-size:0.8rem;color:var(--text-muted);text-align:center;">No previous tickets for this customer email.</p>`
    }
};

const PRIORITY_LABELS = {
    P0: "P0 - Critical Outage",
    P1: "P1 - High Severity",
    P2: "P2 - Medium Degradation",
    P3: "P3 - Low Priority"
};

let lastResponseObject = null;
let lastRequestObject = null;

document.addEventListener("DOMContentLoaded", () => {
    const selectWrapper = document.getElementById("custom-select-wrapper");
    const selectDropdown = document.getElementById("custom-select-dropdown");

    if (selectWrapper && selectDropdown) {
        selectWrapper.addEventListener("click", (event) => {
            const option = event.target.closest(".custom-select-option");
            if (option) {
                updateCustomSelect(option.getAttribute("data-value"));
            }

            selectWrapper.classList.toggle("open");
            selectDropdown.classList.toggle("open");
            event.stopPropagation();
        });

        document.addEventListener("click", (event) => {
            if (!selectWrapper.contains(event.target)) {
                selectWrapper.classList.remove("open");
                selectDropdown.classList.remove("open");
            }
        });
    }

    loadPreset("stripe");
});

function updateCustomSelect(priorityValue) {
    const input = document.getElementById("input-priority");
    if (input) input.value = priorityValue;

    const triggerValueText = document.querySelector(".custom-select-value");
    if (triggerValueText && PRIORITY_LABELS[priorityValue]) {
        triggerValueText.innerText = PRIORITY_LABELS[priorityValue];
    }

    document.querySelectorAll(".custom-select-option").forEach((option) => {
        option.classList.toggle("selected", option.getAttribute("data-value") === priorityValue);
    });
}

function loadPreset(key) {
    document.querySelectorAll(".preset-btn").forEach((btn) => btn.classList.remove("active"));
    const activeBtn = document.getElementById(`btn-preset-${key}`);
    if (activeBtn) activeBtn.classList.add("active");

    const data = PRESETS[key];
    if (!data) return;

    document.getElementById("input-email").value = data.email;
    updateCustomSelect(data.priority);
    document.getElementById("input-reporter").value = data.reporter;
    document.getElementById("input-issue").value = data.issue;

    document.getElementById("meta-user-id").innerText = data.meta.userId;
    document.getElementById("meta-user-name").innerText = data.meta.userName;
    document.getElementById("meta-user-tier").innerText = data.meta.userTier;
    document.getElementById("meta-user-sub").innerText = data.meta.userSub;

    document.getElementById("meta-stripe-plan").innerText = data.meta.stripePlan;
    document.getElementById("meta-stripe-status").innerText = data.meta.stripeStatus;
    document.getElementById("meta-stripe-failed").innerText = data.meta.stripeFailed;
    document.getElementById("meta-stripe-error").innerText = data.meta.stripeError;

    document.getElementById("code-user-db").textContent = JSON.stringify(data.userDbJson, null, 2);
    document.getElementById("code-stripe").textContent = JSON.stringify(data.stripeJson, null, 2);
    document.getElementById("code-logs").textContent = data.logsText;
    document.getElementById("code-tickets").innerHTML = data.ticketsHtml;
    document.getElementById("diag-source-summary").innerText =
        "Preset demo data loaded. Run an investigation to replace this panel with backend evidence.";
    document.getElementById("report-analysis-mode").innerText = "demo";

    resetApp();
}

function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach((btn) => btn.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));

    document.querySelectorAll(".tab-btn").forEach((btn) => {
        if (btn.getAttribute("onclick").includes(tabId)) {
            btn.classList.add("active");
        }
    });

    document.getElementById(tabId).classList.add("active");
}

function resetApp() {
    document.getElementById("report-card").classList.add("hidden");
    document.getElementById("pipeline-loader").classList.add("hidden");
    document.getElementById("diagnostics-card").classList.remove("hidden");
    document.getElementById("btn-submit-investigation").classList.remove("loading");
    document.getElementById("btn-submit-investigation").removeAttribute("disabled");
}

async function handleFormSubmit(event) {
    event.preventDefault();

    const email = document.getElementById("input-email").value.trim();
    const priority = document.getElementById("input-priority").value;
    const reporter = document.getElementById("input-reporter").value.trim();
    const issue = document.getElementById("input-issue").value.trim();

    if (!email || !issue) {
        alert("Please provide both a customer email and issue summary.");
        return;
    }

    const submitBtn = document.getElementById("btn-submit-investigation");
    submitBtn.classList.add("loading");
    submitBtn.setAttribute("disabled", "true");

    document.getElementById("report-card").classList.add("hidden");
    document.getElementById("diagnostics-card").classList.add("hidden");
    const loader = document.getElementById("pipeline-loader");
    loader.classList.remove("hidden");

    const steps = ["step-user", "step-payment", "step-logs", "step-tickets"];
    steps.forEach((id) => {
        const el = document.getElementById(id);
        el.className = "step-item";
        el.querySelector("i").className = "fa-solid fa-circle-notch fa-spin step-icon-pending";
    });

    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    await sleep(400);
    animatePipelineStep("step-user", "active");
    await sleep(500);
    animatePipelineStep("step-user", "complete");
    animatePipelineStep("step-payment", "active");
    await sleep(500);
    animatePipelineStep("step-payment", "complete");
    animatePipelineStep("step-logs", "active");
    await sleep(500);
    animatePipelineStep("step-logs", "complete");
    animatePipelineStep("step-tickets", "active");
    await sleep(500);
    animatePipelineStep("step-tickets", "complete");

    lastRequestObject = {
        user_email: email,
        issue_summary: issue,
        priority,
        reporter_name: reporter
    };

    try {
        const response = await fetch("/investigate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(lastRequestObject)
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }

        const report = await response.json();
        lastResponseObject = report;
        updateDiagnosticsFromEvidence(report.evidence);
        renderAgentReport(report);
    } catch (err) {
        console.error("Pipeline failure:", err);
        alert(`Investigation failed: ${err.message}. Running fallback report.`);
        const fallback = runClientHeuristic(email, issue);
        lastResponseObject = fallback;
        renderAgentReport(fallback);
    }
}

function animatePipelineStep(stepId, state) {
    const el = document.getElementById(stepId);
    if (!el) return;
    if (state === "active") {
        el.className = "step-item active";
        el.querySelector("i").className = "fa-solid fa-sync fa-spin step-icon-active";
    } else if (state === "complete") {
        el.className = "step-item complete";
        el.querySelector("i").className = "fa-solid fa-circle-check step-icon-complete";
    }
}

function renderAgentReport(report) {
    document.getElementById("pipeline-loader").classList.add("hidden");
    const reportCard = document.getElementById("report-card");
    reportCard.classList.remove("hidden");

    document.getElementById("report-confidence").innerText = `${Math.round(report.confidence * 100)}%`;
    document.getElementById("report-analysis-mode").innerText = report.analysis_mode || "unknown";
    document.getElementById("report-summary").innerText = report.summary;
    document.getElementById("report-root-cause").innerText = report.root_cause;

    const findingsList = document.getElementById("report-findings");
    findingsList.innerHTML = "";
    report.technical_findings.split("\n").forEach((line) => {
        const clean = line.replace(/^[•\-\*]\s*/, "").trim();
        if (!clean) return;
        const li = document.createElement("li");
        li.innerText = clean;
        findingsList.appendChild(li);
    });

    const actionsList = document.getElementById("report-actions");
    actionsList.innerHTML = "";
    report.suggested_actions.forEach((action, idx) => {
        const id = `action-check-${idx}`;
        const item = document.createElement("div");
        item.className = "action-item";
        item.innerHTML = `<input type="checkbox" id="${id}" ${idx === 0 ? "checked" : ""}><label for="${id}">${escapeHtml(action)}</label>`;
        actionsList.appendChild(item);
    });

    const banner = document.getElementById("report-escalate-banner");
    const decisionEl = document.getElementById("report-escalate-decision");
    const reasonEl = document.getElementById("report-escalate-reason");
    const bannerIcon = document.getElementById("banner-icon-ref");

    if (report.escalate_to_engineering) {
        banner.className = "escalate-banner-yes";
        decisionEl.innerText = "YES - Page Engineering & Dev Team";
        reasonEl.innerText = report.escalation_reason;
        bannerIcon.className = "fa-solid fa-radiation fa-spin";
        playEscalationAlarm();
    } else {
        banner.className = "escalate-banner-no";
        decisionEl.innerText = "NO - Support Can Handle (No Ping)";
        reasonEl.innerText = report.escalation_reason;
        bannerIcon.className = "fa-solid fa-circle-check";
    }

    reportCard.scrollIntoView({ behavior: "smooth" });
}

function updateDiagnosticsFromEvidence(evidence) {
    if (!evidence) {
        document.getElementById("diag-source-summary").innerText =
            "No backend evidence returned. The UI is still showing preset demo data.";
        return;
    }

    const userData = evidence.user_account || {};
    const paymentData = evidence.payment || {};
    const logs = evidence.logs || [];
    const tickets = evidence.tickets || [];
    const dataSources = evidence.data_sources || {};

    document.getElementById("meta-user-id").innerText = firstValue(userData, [
        "user_id", "id", "customer_id", "account_id"
    ]) || "N/A";
    document.getElementById("meta-user-name").innerText = firstValue(userData, [
        "name", "full_name", "display_name", "customer_name"
    ]) || "N/A";
    document.getElementById("meta-user-tier").innerText = firstValue(userData, [
        "account_tier", "tier", "plan", "subscription_tier"
    ]) || "N/A";
    document.getElementById("meta-user-sub").innerText = firstValue(userData, [
        "subscription_status", "status", "account_status"
    ]) || "N/A";

    document.getElementById("meta-stripe-plan").innerText = firstValue(paymentData, [
        "plan", "product", "subscription_plan"
    ]) || "N/A";
    document.getElementById("meta-stripe-status").innerText = firstValue(paymentData, [
        "subscription_status", "status", "last_payment_status"
    ]) || "N/A";
    document.getElementById("meta-stripe-failed").innerText = firstValue(paymentData, [
        "failed_payment_attempts", "failed_attempts", "attempt_count"
    ]) ?? "0";
    document.getElementById("meta-stripe-error").innerText = firstValue(paymentData, [
        "last_payment_error", "last_error", "error"
    ]) || "None";

    document.getElementById("code-user-db").textContent = prettyJson(userData);
    document.getElementById("code-stripe").textContent = prettyJson(paymentData);
    document.getElementById("code-logs").textContent = formatLogs(logs);
    document.getElementById("code-tickets").innerHTML = `<pre class="json-code">${escapeHtml(prettyJson(tickets))}</pre>`;

    const logsSource = dataSources.logs || "backend";
    document.querySelector(".console-title").innerText = `${logsSource} -- evidence`;
    document.getElementById("diag-source-summary").innerText = formatSourceSummary(dataSources);

    document.getElementById("diagnostics-card").classList.remove("hidden");
}

function formatSourceSummary(dataSources) {
    const labels = [
        `User: ${dataSources.user_account || "unknown"}`,
        `Payment: ${dataSources.payment || "unknown"}`,
        `Logs: ${dataSources.logs || "unknown"}`,
        `Tickets: ${dataSources.tickets || "unknown"}`
    ];
    return `Backend evidence sources -> ${labels.join(" | ")}`;
}

function formatLogs(logs) {
    if (Array.isArray(logs)) {
        return logs.map((entry) => formatLogEntry(entry)).join("\n");
    }
    if (typeof logs === "string") {
        return logs;
    }
    return prettyJson(logs);
}

function formatLogEntry(entry) {
    if (!entry || typeof entry !== "object") {
        return String(entry);
    }
    const timestamp = entry.timestamp || entry.created_at || entry.time || "unknown-time";
    const level = entry.level || entry.severity || "INFO";
    const service = entry.service || entry.source || "service";
    const code = entry.error_code ? ` error_code=${entry.error_code}` : "";
    const message = entry.message || entry.msg || JSON.stringify(entry);
    return `${timestamp} [${level}] service=${service}${code} message="${message}"`;
}

function firstValue(record, keys) {
    if (!record || typeof record !== "object") return null;
    for (const key of keys) {
        if (record[key] !== undefined && record[key] !== null && record[key] !== "") {
            return record[key];
        }
    }
    return null;
}

function prettyJson(value) {
    return JSON.stringify(value, null, 2);
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function playEscalationAlarm() {
    const audio = document.getElementById("escalation-alarm");
    if (!audio) return;
    audio.currentTime = 0;
    audio.play().catch((err) => console.log("Sound muted by browser:", err));
}

function copySlackReport() {
    if (!lastResponseObject || !lastRequestObject) {
        alert("Run an investigation first to copy a Slack report.");
        return;
    }

    const priorityEmoji = { P0: "🔴", P1: "🟠", P2: "🟡", P3: "🟢" }[lastRequestObject.priority] || "⚪";
    const escalateStatus = lastResponseObject.escalate_to_engineering
        ? "🚨 *YES - Escalate to Engineering*"
        : "✅ *NO - Support can handle*";
    const confidenceBar = "█".repeat(Math.round(lastResponseObject.confidence * 10))
        + "░".repeat(10 - Math.round(lastResponseObject.confidence * 10));
    const actions = lastResponseObject.suggested_actions
        .map((action, index) => `  ${index + 1}. ${action}`)
        .join("\n");

    const blockText = `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
${priorityEmoji} *Customer Escalation - ${lastRequestObject.priority}*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*User:* \`${lastRequestObject.user_email}\`
*Issue:* ${lastRequestObject.issue_summary}
*Reporter:* ${lastRequestObject.reporter_name}

*SUMMARY*
${lastResponseObject.summary}

*TECHNICAL FINDINGS*
${lastResponseObject.technical_findings}

*ROOT CAUSE*
${lastResponseObject.root_cause}

*SUGGESTED ACTIONS*
${actions}

*ESCALATE TO ENGINEERING?*
${escalateStatus}
_${lastResponseObject.escalation_reason}_

*Confidence:* \`${confidenceBar}\` ${Math.round(lastResponseObject.confidence * 100)}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`;

    navigator.clipboard.writeText(blockText)
        .then(() => alert("Slack-formatted report copied to clipboard."))
        .catch((err) => alert(`Copy failed: ${err.message}`));
}

function runClientHeuristic(email, issue) {
    const lower = issue.toLowerCase();

    if (lower.includes("decline") || lower.includes("payment") || lower.includes("card") || lower.includes("stripe")) {
        return {
            summary: "User's payment is failing because their credit card was declined by Stripe.",
            technical_findings: "• User John Doe is on the 'Pro Monthly' tier ($29.99).\n• Stripe status shows 2 failed payment attempts in 24 hours.\n• Stripe Error: card_declined.\n• Last successful charge: 2026-05-01.",
            root_cause: "The payment attempt was declined by the credit card issuer, typically due to expired details or temporary bank holds.",
            suggested_actions: [
                "Provide direct payment update link: app.example.com/billing",
                "If card is correct, advise customer to contact their card issuer.",
                "If urgent, apply temporary 48h account extension."
            ],
            escalate_to_engineering: false,
            escalation_reason: "NO - Billing issues are standard gateway declines, support can handle self-updates.",
            confidence: 0.96,
            analysis_mode: "client-fallback"
        };
    }

    if (lower.includes("rate") || lower.includes("limit") || lower.includes("429") || lower.includes("quota")) {
        return {
            summary: "User's API calls are being rate-limited (429) due to quota exceedance.",
            technical_findings: "• Account: Pro Monthly.\n• Usage: 15,420 / 10,000 monthly calls.\n• Logs: multiple HTTP 429 errors from api-gateway.",
            root_cause: "The client application has exceeded the maximum monthly request threshold for the Pro Tier subscription.",
            suggested_actions: [
                "Advise customer of usage metrics (15.4k of 10k cap).",
                "Offer upgrade links to Enterprise Tier.",
                "Provide API design docs detailing caching systems."
            ],
            escalate_to_engineering: false,
            escalation_reason: "NO - Gateway limits are active by design. Upgrades needed.",
            confidence: 0.98,
            analysis_mode: "client-fallback"
        };
    }

    return {
        summary: "Severe DB connection lockouts causing checkout timeouts.",
        technical_findings: "• payment-service pool exhaustion warnings logged.\n• Spiked timeout latency of 12.4 seconds.\n• Outage priority: P0 Critical.",
        root_cause: "Deadlock bottlenecks in database connection instances in backend checkouts.",
        suggested_actions: [
            "Contact SRE immediately via Incident Room.",
            "Flag system alert warnings on public status page.",
            "Halt manual transactions until clear clearance is set."
        ],
        escalate_to_engineering: true,
        escalation_reason: "YES - Severe connection leaks in payment backend services. SRE team must scale DB metrics.",
        confidence: 0.94,
        analysis_mode: "client-fallback"
    };
}
