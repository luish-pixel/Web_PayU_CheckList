# form_html_case.py

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
<title>RPA Bot - Rapyd</title>
<meta charset="UTF-8" />

<style>

body {
    font-family: Segoe UI, Arial, sans-serif;
    background:#f2f4f8;
    margin:0;
}

.wrapper {
    max-width:700px;
    margin:40px auto;
    background:white;
    padding:40px;
    border-radius:12px;
    box-shadow:0 10px 25px rgba(0,0,0,0.08);
}

.top-header {
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.title h1 {
    font-size:40px;
    margin:0;
    font-weight:800;
}

.title span {
    color:#2f6edb;
}

.subtitle {
    font-size:18px;
    margin:5px 0;
}

.badge {
    display:inline-block;
    background:#2f6edb;
    color:white;
    padding:4px 12px;
    border-radius:4px;
    font-size:12.5px;
    font-weight:600;
}

.step-box {
    border:2px dashed #2f6edb;
    padding:25px;
    margin-bottom:25px;
    border-radius:10px;
}

.step-title {
    font-weight:700;
    font-size:18px;
    margin-bottom:15px;
}

input,
textarea {
    width:92%;
    padding:12px;
    margin:0 auto 15px auto;
    display:block;
    border-radius:8px;
    border:1px solid #ccc;
    box-sizing:border-box;
}

textarea {
    height:120px;
}

button {
    display:block;
    margin:30px auto 0;
    padding:14px 40px;
    background:#2f6edb;
    color:white;
    border:none;
    border-radius:8px;
    font-weight:600;
    cursor:pointer;
    transition:0.2s;
}

button:hover {
    background:#2458b8;
}

button:disabled {

    background:#9aa9c7;

    cursor:not-allowed;

    opacity:0.85;
}

.result {
    margin-top:30px;
    padding:20px;
    background:#eef4ff;
    border-left:4px solid #2f6edb;
}

/* ========================================= */
/* RADIO FIX */
/* ========================================= */

input[type="radio"] {
    width:auto;
    margin:0;
    padding:0;
    display:inline;
}

/* ========================================= */
/* BUSINESS OPTIONS */
/* ========================================= */

.business-options {

    width:92%;

    margin:0 auto 14px auto;

    display:flex;

    justify-content:center;

    gap:8px;
}

.business-option {

    border:1px solid #d0d7e2;

    border-radius:7px;

    padding:6px 12px;

    cursor:pointer;

    transition:0.2s;

    display:flex;

    align-items:center;

    gap:6px;

    font-weight:600;

    font-size:14px;

    background:white;

    min-width:170px;

    justify-content:center;
}

.business-option:hover {
    border-color:#2f6edb;
    background:#f7faff;
}

.business-option.active {
    border-color:#2f6edb;
    background:#eef4ff;
    color:#2f6edb;
}

/* ========================================= */
/* ERROR BOX */
/* ========================================= */

#error_box,
#form_error {
    display:none;
    background:#ffe9e9;
    color:#c62828;
    border:1px solid #ef9a9a;
    padding:12px;
    border-radius:8px;
    margin-top:15px;
    font-weight:600;
}

</style>
</head>

<body>

<div class="wrapper">

<div class="top-header">

<div class="title">

<h1>BOT <span>RPA</span></h1>

<div class="subtitle">
<strong> CheckList ACI Case </strong>
</div>

<div class="badge">Case Manager</div>

</div>

<div class="logo">
<img src="/static/LogoRapyd.png" style="max-height:60px;">
</div>

</div>

<form
    method="post"
    enctype="multipart/form-data"
    onsubmit="return validateForm()"
>

{% if ambiente == "PROD" %}

<div class="step-box">

<div class="step-title">🔐 STEP 1: ADMIN CREDENTIALS</div>

<input
    type="text"
    name="admin_user"
    placeholder="Admin Username"
    required
>

<input
    type="password"
    name="admin_pass"
    placeholder="Admin Password"
    required
>

</div>

{% endif %}

<!-- ========================================= -->
<!-- STEP 2 -->
<!-- ========================================= -->

<div class="step-box">

<div class="step-title">📊 STEP 2: UPLOAD EXCEL TEMPLATE</div>

<input
    id="excel_file"
    type="file"
    name="excel_file"
    accept=".xlsx,.xls"
    required
>

</div>

<!-- ========================================= -->
<!-- STEP 3 -->
<!-- ========================================= -->

<div class="step-box">

<div class="step-title">📝 STEP 3: BUSINESS MODEL SOURCE</div>

<div class="business-options">

<label class="business-option active" id="summary_option">

<input
    type="radio"
    name="business_mode"
    value="summary"
    checked
    onclick="toggleBusinessMode()"
>

✍️ Summary

</label>

<label class="business-option" id="link_option">

<input
    type="radio"
    name="business_mode"
    value="link"
    onclick="toggleBusinessMode()"
>

🔗 Underwriting Link

</label>

</div>

<!-- SUMMARY -->

<div id="summary_box">

<textarea
    id="case_summary"
    name="case_summary"
    placeholder="Write the case summary"
></textarea>

</div>

<!-- LINK -->

<div id="link_box" style="display:none;">

<input
    id="underwriting_link"
    type="url"
    name="underwriting_link"
    placeholder="https://drive.google.com/..."
>

</div>

</div>

<!-- ========================================= -->
<!-- STEP 4 -->
<!-- ========================================= -->

<div class="step-box">

<div class="step-title">🖼️ STEP 4: UPLOAD IMAGE</div>

<input
    id="imagen"
    type="file"
    name="imagen"
    accept=".png,.jpg,.jpeg"
>

</div>

<!-- ========================================= -->
<!-- FORM ERROR -->
<!-- ========================================= -->

<div id="form_error"></div>

<div
    id="process_running"
    style="
        display:none;
        margin-top:15px;
        padding:12px;
        background:#eef4ff;
        border:1px solid #b7cdfb;
        color:#2458b8;
        border-radius:8px;
        font-weight:600;
    "
>
⏳ Process running... please wait.
</div>

<button
    id="run_button"
    type="submit"
>
▶ Run Process
</button>

</form>

{% if mensaje %}

<div class="result">
{{mensaje}}
</div>

{% endif %}

</div>

<!-- ========================================= -->
<!-- JAVASCRIPT -->
<!-- ========================================= -->

<script>

function toggleBusinessMode() {

    const selected =
        document.querySelector(
            'input[name="business_mode"]:checked'
        ).value;

    const summaryBox =
        document.getElementById("summary_box");

    const linkBox =
        document.getElementById("link_box");

    const summaryOption =
        document.getElementById("summary_option");

    const linkOption =
        document.getElementById("link_option");

    if (selected === "summary") {

        summaryBox.style.display = "block";
        linkBox.style.display    = "none";

        summaryOption.classList.add("active");
        linkOption.classList.remove("active");

    } else {

        summaryBox.style.display = "none";
        linkBox.style.display    = "block";

        summaryOption.classList.remove("active");
        linkOption.classList.add("active");
    }
}

function validateForm(event) {

    if (event) {
        event.preventDefault();
    }

    const selected =
        document.querySelector(
            'input[name="business_mode"]:checked'
        ).value;

    const summary =
        document.getElementById("case_summary")
        .value
        .trim();

    const link =
        document.getElementById("underwriting_link")
        .value
        .trim();

    const excel =
        document.getElementById("excel_file")
        .value;

    const image =
        document.getElementById("imagen")
        .value;

    const errorBox =
        document.getElementById("form_error");

    errorBox.style.display = "none";

    // =========================================
    // EXCEL VALIDATION
    // =========================================

    if (!excel) {

        showError(
            "⚠ Please upload the Excel template."
        );

        return false;
    }

    // =========================================
    // IMAGE VALIDATION
    // =========================================

    if (!image) {

        showError(
            "⚠ Please upload image evidence."
        );

        return false;
    }

    // =========================================
    // SUMMARY VALIDATION
    // =========================================

    if (selected === "summary") {

        if (!summary) {

            showError(
                "⚠ Please write the case summary."
            );

            return false;
        }
    }

    // =========================================
    // LINK VALIDATION
    // =========================================

    if (selected === "link") {

        if (!link) {

            showError(
                "⚠ Please enter the underwriting link."
            );

            return false;
        }

        try {

            new URL(link);

        } catch {

            showError(
                "⚠ Please enter a valid URL."
            );

            return false;
        }
    }

    const runButton =
        document.getElementById("run_button");

    runButton.disabled = true;

    runButton.innerHTML =
        "⏳ Running...";

    document.getElementById(
        "process_running"
    ).style.display = "block";

    return true;
}


function showError(message) {

    const errorBox =
        document.getElementById("form_error");

    errorBox.innerHTML = message;

    errorBox.style.display = "block";
}

</script>

</body>
</html>
"""