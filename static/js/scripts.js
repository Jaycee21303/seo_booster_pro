// ----------------------
// SAVE URL
// ----------------------
function saveURL() {
    let url = document.getElementById("urlInput").value;

    fetch("/save_url", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "url=" + encodeURIComponent(url)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showMessage("URL saved!");
        }
    });
}


// ----------------------
// ANALYZE URL
// ----------------------
function analyzeURL() {
    let url = document.getElementById("urlInput").value;

    fetch("/analyze_url", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "url=" + encodeURIComponent(url)
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showMessage(data.error);
            return;
        }

        document.getElementById("analysisTitle").innerText = data.title;
        document.getElementById("analysisMeta").innerText = data.meta;
    });
}


// ----------------------
// HELPER: RUN AI ENDPOINT
// ----------------------
function runAI(endpoint, outputBoxId) {
    let url = document.getElementById("urlInput").value;

    document.getElementById(outputBoxId).innerText = "Generating...";

    fetch(`/ai/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "url=" + encodeURIComponent(url)
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById(outputBoxId).innerText = data.result;
    });
}


// ----------------------
// MESSAGE POPUP
// ----------------------
function showMessage(msg) {
    let box = document.getElementById("messageBox");
    box.innerText = msg;
    box.style.display = "block";
    setTimeout(() => box.style.display = "none", 2000);
}
