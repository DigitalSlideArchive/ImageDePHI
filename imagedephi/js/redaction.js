window.onload = (event) => {

const redactBanner = document.getElementById("redacting");
const redactButton = document.getElementById("dephi");
const redactForm = document.getElementById('redact')
redactForm.addEventListener("submit", () => {
  redactButton.setAttribute("disabled", "true")
  redactBanner.classList.remove("hidden")
})

}
