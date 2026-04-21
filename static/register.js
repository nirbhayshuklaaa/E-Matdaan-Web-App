// Typing Animation FIXED (no error)

const text = "Welcome to India's Secure Digital Voting System";
let i = 0;

function typingEffect() {
  const element = document.getElementById("typing-text");

  if (!element) return; // ✅ prevents null error

  if (i < text.length) {
    element.innerHTML += text.charAt(i);
    i++;
    setTimeout(typingEffect, 50);
  }
}

// Run after page loads
document.addEventListener("DOMContentLoaded", function () {
  typingEffect();
});