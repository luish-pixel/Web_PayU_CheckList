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

input, textarea {
    width:92%;
    padding:12px;
    margin:0 auto 15px auto;
    display:block;
    border-radius:8px;
    border:1px solid #ccc;
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
}

.result {
    margin-top:30px;
    padding:20px;
    background:#eef4ff;
    border-left:4px solid #2f6edb;
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

<form method="post" enctype="multipart/form-data">

{% if ambiente == "PROD" %}

<div class="step-box">

<div class="step-title">🔐 STEP 1: ADMIN CREDENTIALS</div>

<input type="text" name="admin_user" placeholder="Admin Username" required>
<input type="password" name="admin_pass" placeholder="Admin Password" required>

</div>



{% endif %}

<div class="step-box">
<div class="step-title">📊 STEP 2: UPLOAD EXCEL TEMPLATE</div>
<input type="file" name="excel_file" accept=".xlsx,.xls" required>
</div>

<div class="step-box">

<div class="step-title">📝 STEP 3: CASE SUMMARY</div>

<textarea name="case_summary" placeholder="Write the case summary"></textarea>

</div>

<div class="step-box">

<div class="step-title">🖼️ STEP 4: UPLOAD IMAGE</div>

<input type="file" name="imagen" accept=".png,.jpg,.jpeg">

</div>

<div class="step-box">

<div class="step-title">🧵 STEP 5: NUMBER OF THREADS</div>

<input type="number" name="num_hilos" min="1" max="8" value="1" required>

</div>

<button type="submit">▶ Run Process</button>

</form>

{% if mensaje %}
<div class="result">
{{mensaje}}
</div>
{% endif %}

</div>

</body>
</html>
"""