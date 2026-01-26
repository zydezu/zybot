class VideoWithBackground {
    video;
    canvas;
    step;
    ctx;

    constructor(videoID, canvasID) {
        this.video = document.getElementById(videoID)
        this.canvas = document.getElementById(canvasID)

        window.addEventListener("load", this.initcheck, false);
        window.addEventListener("unload", this.cleanup, false);
    }

    draw = () => {
        if (this.currentlyDrawing) {
            this.offscreenCtx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            this.ctx.drawImage(this.offscreenCanvas, 0, 0);
        }
    };

    drawLoop = () => {
        this.draw();
        this.step = window.requestAnimationFrame(this.drawLoop);
    };

    drawPause = () => {
        window.cancelAnimationFrame(this.step);
        this.step = undefined;
    };

    initcheck = () => {
        const isFirefox = navigator.userAgent.toLowerCase().includes('firefox');
        console.log(`Initiated video canvas${isFirefox ? ' (firefox version)' : ''}`);
        this.ctx = this.canvas.getContext("2d");
        if (isFirefox) {
            this.ctx.filter = "blur(30px)";
            setInterval(this.draw, 100);
        } else {
            console.log("init")
            this.init()
        }
        this.offscreenCanvas = new OffscreenCanvas(this.canvas.width, this.canvas.height);
        this.offscreenCtx = this.offscreenCanvas.getContext('2d', { alpha: false });
        this.ctx.filter = "blur(5px)";
        this.currentlyDrawing = true;
        this.drawi = 0
        setTimeout(() => {
            this.drawInit();
        }, 100)
    }

    drawInit = () => {
        this.draw();
        this.drawi++;
        if (this.drawi < 5) setTimeout(this.drawInit, 35);
    }   


    init = () => {
        if (localStorage.ambientMode == "true" && localStorage.currentTheme == "dark") {
            this.video.addEventListener("seeked", this.draw, false);
            this.video.addEventListener("play", this.drawLoop, false);
            this.video.addEventListener("ended", this.drawPause, false);
        }
    };

    cleanup = () => {
        this.video.removeEventListener("seeked", this.draw);
        this.video.removeEventListener("play", this.drawLoop);
        this.video.removeEventListener("ended", this.drawPause);
    };

    changeBlur = (blur) => {
        this.ctx.filter = `blur(${blur}px)`;
        updateSettingsBox();
    }

    changeCanvasSize = (width, height) => {
        this.canvas.width = width;
        this.canvas.height = height;
        updateSettingsBox();
    }

    checkThemeStatus = () => {
        let currentTheme = localStorage.getItem("currentTheme");
        if (currentTheme == "dark" && localStorage.getItem("ambientMode") == "true") {
            console.log("Starting ambient mode")
            this.currentlyDrawing = true;
            this.video.addEventListener("play", this.drawLoop, false);
            this.video.addEventListener("pause", this.drawPause, false);
            this.video.addEventListener("ended", this.drawPause, false);
            this.drawLoop();
        } else {
            this.turnOffAmbientMode();
        }
    }

    turnOffAmbientMode = () => {
        console.log("Stopping ambient mode")
        this.currentlyDrawing = false;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.video.removeEventListener("seeked", this.draw);
        this.video.removeEventListener("play", this.drawLoop);
        this.drawPause();
    }
}

if (!localStorage.ambientMode) {
    localStorage.setItem("ambientMode", "false");
}
const canvas = new VideoWithBackground("ambientvideo", "ambientcanvas");
function toggleAmbientMode() {
    if (localStorage.getItem("currentTheme") == "dark") {
        if (localStorage.ambientMode == "true") {
            localStorage.ambientMode = "false"
        } else {
            localStorage.ambientMode = "true"
        }
    }
    canvas.checkThemeStatus();
    updateSettingsBox();
}

function checkAmbientTheme() {
    canvas.checkThemeStatus();
}

function turnOffAmbientMode() {
    canvas.turnOffAmbientMode();
}

Object.defineProperty(HTMLMediaElement.prototype, 'playing', {
    get: function () {
        return !!(this.currentTime > 0 && !this.paused && !this.ended && this.readyState > 2);
    }
})

document.getElementById("ambientvideo").addEventListener("loadeddata", checkResolution)

function checkResolution() {
    if (this.videoWidth / this.videoHeight < 1.6) { // 4/3 wont fit
        document.documentElement.setAttribute("style", "--maxwidth: 135vh");
    }
}