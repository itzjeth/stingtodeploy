const TranscriptField = document.getElementById("ld-transcript");
const ExpandButton = document.getElementById("expand");
const CompressButton = document.getElementById("compress");
function ShowFullTranscript() {
  TranscriptField.classList.add("t-ld-transcript-full");
  ExpandButton.setAttribute("class", "u-hidden");
  CompressButton.setAttribute("class", "t-ld-show")
}
function HideFullTranscript() {
  TranscriptField.classList.remove("t-ld-transcript-full");
  ExpandButton.setAttribute("class", "t-ld-show");
  CompressButton.setAttribute("class", "u-hidden")
}