// setup
const videoInfo = document.getElementById("videoInfo");
const selectedFile = document.getElementById("selectedFile");
const filterButtons = document.getElementById("filterButtons");
const sortingButton = document.getElementById("sortingButton");
const toggleRepliesButton = document.getElementById("toggleReplies");
const switchCommentsLayoutButton = document.getElementById("switchCommentsLayoutButton");
const scrollingPlace = document.getElementById("sideBarScroll")
let sortedByTop;
let showingReplies;
resetButtonStates();
let oldCommentPosition = false;
var commentsBox;
var commentCount;
let startingIndex;
let commentsLoaded;
var commentsToLoadInitially = 20;
var commentsToLoadAtOnce = 10;
let allCommentsLoaded = false;
let currentFilter = "";
var loadedSuccessfully = false;
let errorMessage = "";
getCommentsBox();

function getCommentsBox() {
    if (!localStorage.commentPosition) {
        localStorage.setItem("commentPosition", "side");
    }
    oldCommentPosition = localStorage.commentPosition == "classic" ? true : false;
    commentsBox = document.getElementById(oldCommentPosition ? "classicCommentsBox" : "commentsBox");
    commentCount = document.getElementById(oldCommentPosition ? "classicCommentCount" : "commentCount");
}

function resetButtonStates() {
    sortedByTop = false;
    showingReplies = true;
    sortingButton.textContent = "Sort by top";
    toggleRepliesButton.innerHTML = showingReplies ? "Hide replies" : "Show replies";
}

function switchCommentsLayout() {
    let temp = [commentsBox.innerHTML, commentCount.innerHTML];
    commentsBox.innerHTML = "";
    commentCount.innerHTML = "";
    oldCommentPosition = 1 - oldCommentPosition;
    localStorage.setItem("commentPosition", oldCommentPosition == 0 ? "side" : "classic");
    getCommentsBox();
    commentsBox.innerHTML = temp[0];
    commentCount.innerHTML = temp[1];
    renderCommentCount();
    updateSettingsBox();
}

function openFile() {
    document.getElementById('getFile').click()
}

function readFile(file) {
    return new Promise((resolve, reject) => {
        let fr = new FileReader();
        fr.onload = x => resolve(fr.result);
        fr.readAsText(file);
    })
}

function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
}

async function getDislikes(id) {
    try {
        const response = await fetch("https://returnyoutubedislikeapi.com/votes?videoId=" + id);
        if (!response.ok) {
            throw new Error("Network response was not ok");
        }
        let dislikeresponse = await response.json();
        const dislikeCounter = document.getElementById("dislikeCounter");
        dislikeCounter.innerHTML = dislikeresponse.dislikes;
    } catch (error) {
        console.error("Error fetching dislikes:", error);
        const dislikeCounter = document.getElementById("dislikeCounter");
        if (dislikeCounter) {
            dislikeCounter.innerHTML = "N/A";
        }
    }
}

function fetchError(error) {
    console.log(error)
    errorMessage = error;
    renderCommentCount()
}

function readFile(input) {
    let loadedSuccessfully = false;
    videoInfo.innerHTML = "Loading information...";
    commentsBox.innerHTML = "";
    filterButtons.classList.add("hidden");

    fetch(input)
        .then((response) => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            return response.text();
        })
        .then((returndata) => {
            read(returndata);
            loadedSuccessfully = true;
        })
        .catch((error) => {
            console.error("Fetch error:", error);
            fetchError(error);
            // Fallback to a local file or display a message
            videoInfo.innerHTML = "Failed to load information. Please check your connection or the file path.";
        });
}

async function read(returndata) {
    data = JSON.parse(returndata);
    resetButtonStates();

    loadedSuccessfully = true;
    console.log("Loading comments...")

    commentCount.innerHTML = `${oldCommentPosition ? `<br/>` : ``} Loading comments... 
    <button class="switchCommentsLayout" onclick="switchCommentsLayout()">Switch comment layout</button>`;
    commentsBox.innerHTML = "";

    videoInfo.innerHTML = `
        <hr>
        <a target="_blank" href="https://youtube.com/watch?v=${data.id}">${data.fulltitle}</a> | 
        <a href="videos/video.mp4" download="${data.fulltitle}.mp4">Download Video</a><br/>
        Views: ${data.view_count} | Duration: ${data.duration_string}
        <br/>Uploaded by: <a target="_blank" href="${data.uploader_url}">${data.channel} (${data.uploader_id})</a> | ${data.channel_follower_count} subscribers
        <br/>Uploaded: ${data.upload_date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
        <br/>Likes: ${data.like_count} | Dislikes: <span id="dislikeCounter">Loading...</span> | Comments: ${data.comment_count}
        <br/>Categories: ${data.categories}
        <br/>Tags: ${data.tags}
        <hr>
        ${makeLinks(data.description.replace(/\n/g, '<br>'))}
        <hr>
        `;

    if (data.comments) {
        renderComments(data);
    } else {
        noCommentsMessage();
    }

    await getDislikes(data.id);
}

function makeLinks(content) {
    var re = /((?:href|src)=")?(\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig;
    content = content.replace(re, function (match, attr) {
        if (typeof attr != 'undefined') {
            return match;
        }
        return '<a target="_blank" href="' + match + '">' + match + '</a>';
    });
    return content
}

function noCommentsMessage() {
    commentCount.innerHTML = `${oldCommentPosition ? `<br/>` : ``} No comments...<br/>
    <button class="switchCommentsLayout" onclick="switchCommentsLayout()">Switch comment layout</button>`;
}

async function renderComments() {
    commentsBox.innerHTML = ''
    const fragment = document.createDocumentFragment();
    showingReplies = true

    startingIndex = 0
    allCommentsLoaded = true;
    for (let index = startingIndex; index < data.comments.length; index++) {
        if (index >= startingIndex + commentsToLoadInitially) {
            allCommentsLoaded = false;
            startingIndex = index;
            break;
        }
        commentsLoaded = index;
        renderNextComment(fragment, index)
    }
    commentsBox.appendChild(fragment);
    renderCommentCount();
    filterButtons.classList.remove("hidden");
}

function renderCommentCount() {
    if (loadedSuccessfully) {
        commentCount.innerHTML = `${oldCommentPosition ? `<br/>` : ``}  Comments: ${data.comment_count}
        <button class="switchCommentsLayout" onclick="switchCommentsLayout()">Switch comment layout</button>`;
    } else {
        commentCount.innerHTML = `${oldCommentPosition ? `<br/>` : ``} Loading failed...<br/>
        ${errorMessage}<br/>
        <button class="switchCommentsLayout" onclick="switchCommentsLayout()">Switch comment layout</button>`;
    }
}

async function loadMoreComments() {
    console.log("Loading more comments.")
    const fragment = document.createDocumentFragment();

    allCommentsLoaded = true;
    for (let index = startingIndex; index < data.comments.length; index++) {
        if (index >= startingIndex + commentsToLoadAtOnce) {
            allCommentsLoaded = false;
            startingIndex = index;
            break;
        }
        renderNextComment(fragment, index);
    }
    commentsBox.appendChild(fragment);
    filterComments(currentFilter);
    updateSettingsBox();
}

scrollingPlace.addEventListener("scroll", () => {
    if (loadedSuccessfully) sideBoxCheckNewComments();
});

function sideBoxCheckNewComments() {
    if (!allCommentsLoaded) {
        if (scrollingPlace.scrollHeight - scrollingPlace.scrollTop <= scrollingPlace.clientHeight + 1000) {
            loadMoreComments();
        }
    }
}

window.onscroll = function (ev) {
    if (loadedSuccessfully) {
        if ((oldCommentPosition || window.innerWidth < 950) && !allCommentsLoaded) {
            if ((window.innerHeight + window.scrollY) >= document.body.scrollHeight - 1000) {
                loadMoreComments();
            }
        }
    }
};

function loadAllComments() {
    const fragment = document.createDocumentFragment();
    for (let index = startingIndex; index < data.comments.length; index++) {
        renderNextComment(fragment, index)
    }
    commentsBox.appendChild(fragment);
    filterComments(currentFilter);
    commentsLoaded = data.comments.length;
    allCommentsLoaded = true;
    updateSettingsBox();
};

function renderNextComment(fragment, index) {
    const element = data.comments[index];
    const commentDiv = document.createElement('div');
    commentDiv.id = element.id;

    if (element.text) { // rarely a comment won't contain text
        if (element.parent === "root") {
            commentDiv.classList.add('SNSParent');
            commentDiv.innerHTML = `
                    <div class="SNSPost">
                        <div class="SNSArea"><a target="_blank" href="${element.author_url}"><img class="SNSIcon" onload="this.style.opacity=1" src="${element.author_thumbnail}"></a>
                            <div class="SNSUserInfo">
                                <span class="SNSUsername">
                                    <a target="_blank" href="${element.author_url}">${element.author}</a>
                                </span>
                                <br><span id="SNSDate">${element._time_text}</span>
                            </div>
                            <div class="SNSAlignRight SNSExtraInfo">
                                ${element.is_pinned ? "📌Pinned<br>" : ""}
                                ${element.is_favorited ? "💖Liked" : ""}
                            </div>
                        </div>
                        <div class="SNSPostText">
                            ${makeLinks(element.text.trim().replace(/\n/g, '<br>'))}<br/>
                            <div class="SNSExtraInfo">
                            <span class="SNSLikeCount">${element.like_count ? element.like_count : 0}</span> like${element.like_count != 1 ? `s` : ``} | 
                                <span id="${element.id}replycount">0 replies</span> |
                                <a target="_blank" href="https://youtube.com/watch?v=${data.id}&lc=${element.id}">Open</a>
                            </div>
                        </div>
                    </div>
                    <div class="SNSReplies" id="${element.id}reply"></div>
                    `;
            fragment.appendChild(commentDiv);
        } else {
            commentDiv.classList.add('SNSPost');
            commentDiv.innerHTML = `
                    <div class="SNSArea"><a target="_blank" href="${element.author_url}"><img class="SNSIcon" onload="this.style.opacity=1" src="${element.author_thumbnail}"></a>
                        <div class="SNSUserInfo">
                            <span class="SNSUsername">
                                <a target="_blank" href="${element.author_url}">${element.author}</a>
                            </span>
                            <br><span id="SNSDate">${element._time_text}</span>
                        </div>
                        <div class="SNSAlignRight SNSExtraInfo">
                            ${element.is_favorited ? "💖Liked" : ""}
                        </div>
                    </div>
                    <div class="SNSPostText">
                        ${makeLinks(element.text.trim().replace(/\n/g, '<br>'))}
                        <div class="SNSExtraInfo">
                            <span class="SNSLikeCount">${element.like_count ? element.like_count : 0}</span> like${element.like_count != 1 ? `s` : ``} | 
                            <a target="_blank" href="https://youtube.com/watch?v=${data.id}&lc=${element.id}">Open</a>
                        </div>
                    </div>
                    `;
            try {
                const replyID = fragment.getElementById(`${element.parent}reply`)
                const replyCount = fragment.getElementById(`${element.parent}replycount`)
                let newReplyCount = parseInt(replyCount.innerHTML.split(" ")[0]) + 1
                replyCount.innerText = `${newReplyCount} repl${newReplyCount == 1 ? `y` : `ies`}`
                fragment.getElementById(`${element.parent}reply`).appendChild(commentDiv);
            } catch (error) {
                // reply comment not in fragment - use global
                document.getElementById(`${element.parent}reply`).appendChild(commentDiv);
            }
        }
    }

    commentsLoaded++;

    if (element.is_pinned) commentDiv.dataset.info = "Pinned "
    if (element.is_favorited) {
        if (commentDiv.dataset.info) {
            commentDiv.dataset.info += "Liked "
        } else {
            commentDiv.dataset.info = "Liked "
        }
    }
};

function filterComments(filterBy) {
    currentFilter = filterBy
    let visibleCount = 0;
    for (const element of commentsBox.children) {
        const hasFilter = filterBy && element.dataset.info && element.dataset.info.includes(filterBy);
        const isVisible = !filterBy || hasFilter;
        element.classList.toggle("hidden", !isVisible);
        if (isVisible) {
            visibleCount++;
        }
    }
    if (filterBy) {
        sideBoxCheckNewComments();
        commentCount.innerHTML = `Comments: ${data.comment_count} ${filterBy ? `(Showing: ${visibleCount})` : ""}
        <button class="switchCommentsLayout" onclick="switchCommentsLayout()">Switch comment layout</button>`;
    }
};

function switchSorting() {
    scrollingPlace.scrollTo(0, 0)
    if (sortedByTop) {
        sortedByTop = false;
        sortingButton.textContent = "Sort by top";
        renderComments();
        return;
    }
    loadAllComments();
    console.log("Loaded all comments")
    filterComments();
    sortedByTop = true;
    sortingButton.textContent = "Sort by new";
    const divList = Array.from(commentsBox.querySelectorAll('.SNSParent'))
        .map((div) => {
            const likes = parseInt(div.querySelector('.SNSLikeCount').innerText.trim());
            const text = div.querySelector('.SNSPostText').innerText.trim();
            return { likes, text, div };
        })
        .sort((a, b) => b.likes - a.likes);
    commentsBox.innerHTML = ""
    divList.forEach((entry) => {
        commentsBox.appendChild(entry.div);
    });
};

function toggleReplies() {
    for (const element of commentsBox.children) {
        const reply = element.children[1];
        if (reply) {
            reply.classList.toggle("hidden", showingReplies);
        }
    }
    showingReplies = !showingReplies;
    toggleRepliesButton.innerHTML = showingReplies ? "Hide replies" : "Show replies";
};

// video loading
const video = document.getElementById("ambientvideo");
getComments();

let lastDroppedFrames = 0;
let droppingFrames = false;
let droppedFrames = 0;
let totalFrames = 0;
let forgiveFrames = 0;
video.addEventListener('timeupdate', () => {
    droppedFrames = video.getVideoPlaybackQuality().droppedVideoFrames;
    totalFrames = video.getVideoPlaybackQuality().totalVideoFrames;
    if (droppedFrames > lastDroppedFrames) {
        console.log("Dropping frames - " + droppedFrames);
        if (droppedFrames > lastDroppedFrames + 3) {
            turnOffAmbientMode();
        }
        lastDroppedFrames = droppedFrames;
        droppingFrames = true;
    } else {
        droppingFrames = false;
    }
})

async function getComments() {
    let idpath = "videos/video.info.json"
    await readFile(idpath);
}

// settings

const settingsBox = document.getElementById("settingsBox");
const settingsBoxJS = document.getElementById("settingsBoxJS");
const BGBlur = document.getElementById("BGBlur");
let showingSettings = false;
function viewSettings() {
    if (showingSettings) {
        settingsBox.classList.add("hideSettings");
        BGBlur.classList.add("hidden");
    } else {
        settingsBox.classList.remove("hidden");
        settingsBox.classList.remove("hideSettings");

        BGBlur.classList.remove("hidden");

        BGBlur.addEventListener("click", viewSettings);
        updateSettingsBox();
    }
    showingSettings = 1 - showingSettings;
    return showingSettings;
};

function updateSettingsBox() {
    const ambCanvas = document.getElementById("ambientcanvas");
    var style = getComputedStyle(document.body)
    try {
        settingsBoxJS.innerHTML = `
        <div class="settingSubheading">Apperance</div><hr />
        Theme<a href="javascript:void(0)" onclick="clickChangeTheme()" class="settingsOption">${localStorage.currentTheme == "dark" ? "Dark" : "Light"} theme</a><br />
        Ambient Mode <a href="javascript:void(0)" onclick="toggleAmbientMode()" class="settingsOption">${localStorage.ambientMode == "true" ? "ON" : "OFF"}</a>
        <span class="settingsExtraInfo">(only available in dark theme)</span><br />

        <div class="settingSubheading">Comments</div><hr />
        Default comment position<a href="javascript:void(0)" onclick="switchCommentsLayout()" class="settingsOption">${oldCommentPosition ? "Bottom" : "Side"}</a>
        <span class="settingsExtraInfo">(doesn't apply on mobile)</span><br />
        Comments to load initially<span class="settingsOption">${commentsToLoadInitially}</span><br />
        Subsequent comments to load at once<span class="settingsOption">${commentsToLoadAtOnce}</span><br />

        <div class="settingSubheading">Localstorage<span class="settingsExtraInfo"> (data stored on your device)</span></div><hr />
        currentTheme<span class="settingsOption">${localStorage.currentTheme}</span><br />
        ambientMode<span class="settingsOption">${localStorage.ambientMode}</span><br />
        commentPosition<span class="settingsOption">${localStorage.commentPosition}</span><br />
        Clear data<a href="javascript:void(0)" onclick="clearLocalStorage()" class="settingsOption">Clear</a>
        <span class="settingsExtraInfo">(this will reload the page)</span></div><br />

        <div class="settingSubheading">Debug</div><hr />
        View video JSON file<a target="_blank" href="${video.src.substr(0, video.src.lastIndexOf('.')) + ".info.json"}" class="settingsOption">View</a><br />
        Comments loaded<span class="settingsOption">${commentsLoaded}</span><br />
        Video resolution<span class="settingsOption">${video.videoWidth}x${video.videoHeight}</span><br />
        Dropped frames<span class="settingsOption">${droppedFrames}/${totalFrames}</span>
        <span class="settingsExtraInfo">(doesn't update when in this menu)</span><br />
        Ambient width / height<span class="settingsOption">${ambCanvas.width}/${ambCanvas.height}</span><br />
        Ambient blur<span class="settingsOption">${canvas.ctx.filter}</span><br />
        Ambient opacity<span class="settingsOption">${style.getPropertyValue('--ambient-canvas-opacity')}</span><br />
        Ambient saturation<span class="settingsOption">${style.getPropertyValue('--ambient-saturation')}</span><br />
        Fullscreen ambient mode<a href="javascript:void(0)" class="settingsOption">OFF</a>
        <span class="settingsExtraInfo">(not implemented)</span><br />
    `
    } catch (error) {
        settingsBoxJS.innerHTML = `<br/>Failed to load<br/>${error}`
    }
};

clearLocalStorage = () => {
    localStorage.clear();
    location.reload();
}

// header transparency

var header = document.getElementById("navBar");
var sticky = 5;
document.addEventListener("scroll", () => {
    if (window.scrollY > sticky) {
        header.classList.add("solid")
    }
    else {
        header.classList.remove("solid")
    };
});