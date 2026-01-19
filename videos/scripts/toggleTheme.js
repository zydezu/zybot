const toggleTheme = document.getElementById("toggleThemeButton")
const meta = document.querySelector('meta[name="color-scheme"]');
const root = document.querySelector(":root");

let currentColorScheme;
if (localStorage.getItem("currentTheme")) {
    currentColorScheme = localStorage.getItem("currentTheme");
    meta.content = currentColorScheme;
    root.classList.toggle("dark", currentColorScheme === 'dark');
    root.classList.toggle("light", currentColorScheme === 'light');
} else {
    currentColorScheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? 'dark' : 'light';
    localStorage.setItem("currentTheme", currentColorScheme);
    root.classList.toggle("dark", currentColorScheme === 'dark');
}

if (toggleTheme) {
    toggleTheme.addEventListener("click", () => {
        changeTheme();
    })
}

function changeTheme() {
    currentColorScheme = currentColorScheme === 'light' ? 'dark' : 'light';
    meta.content = currentColorScheme;
    root.classList.toggle("dark", currentColorScheme === 'dark');
    root.classList.toggle("light", currentColorScheme === 'light');
    localStorage.setItem("currentTheme", currentColorScheme);
}

const toggleButton = document.getElementById("themeToggle");
if (toggleButton) {
    toggleButton.addEventListener("click", () => {
        toggleButton.classList.toggle("active");
        changeTheme();
        checkAmbientTheme();
    })
}

function clickChangeTheme() {
    if (toggleButton) toggleButton.classList.toggle("active");
    changeTheme();
    checkAmbientTheme();
    updateSettingsBox();
}