
  const body = document.querySelector("body"),
  sidebar = document.querySelector(".sidebar"),
  toggle = document.querySelector(".toggle"),
  modeSwitch = document.querySelector(".toggle-switch"),
  modeText = document.querySelector(".mode-text"),
  searchBtn = document.querySelector(".search-bar");

modeSwitch.addEventListener("click", () => {
  body.classList.toggle("dark");


  if (body.classList.contains("dark")) {
    modeText.innerText = " Dark Mode ";
  } else modeText.innerText = " Light Mode ";
});

toggle.addEventListener("click", () => {
  sidebar.classList.toggle("close");
});

searchBtn.addEventListener("click", () => {
  sidebar.classList.remove("close");
});

