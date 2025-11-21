// ===============================
// SEO Score Circle Animation
// ===============================

document.addEventListener("DOMContentLoaded", () => {

    const scoreElement = document.querySelector(".score-circle span");
    if (!scoreElement) return;

    const finalScore = parseInt(scoreElement.textContent);
    let currentScore = 0;

    const interval = setInterval(() => {
        if (currentScore >= finalScore) {
            clearInterval(interval);
        } else {
            currentScore++;
            scoreElement.textContent = currentScore;
        }
    }, 12); // Adjust for faster or slower animation
});
