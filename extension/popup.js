const statusElement = document.querySelector("#status");
const professorCard = document.querySelector("#professor-card");
const emptyCard = document.querySelector("#empty-card");
const professorName = document.querySelector("#professor-name");
const professorMeta = document.querySelector("#professor-meta");
const courseSection = document.querySelector("#course-section");
const courseList = document.querySelector("#course-list");
const refreshButton = document.querySelector("#refresh");

function showEmpty(message) {
  statusElement.className = "status";
  statusElement.textContent = message;
  professorCard.hidden = true;
  emptyCard.hidden = false;
}

function showContext(context) {
  statusElement.className = "status detected";
  statusElement.textContent = "Rate My Professors page detected";
  emptyCard.hidden = true;
  professorCard.hidden = false;

  professorName.textContent = context.professorName || "Professor profile";
  professorMeta.textContent = context.professorId
    ? `RMP professor ID ${context.professorId}`
    : "Rate My Professors profile";

  courseList.replaceChildren();
  for (const course of context.courseCodes || []) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = course;
    courseList.append(chip);
  }
  courseSection.hidden = courseList.childElementCount === 0;
}

async function detectPage() {
  statusElement.className = "status loading";
  statusElement.textContent = "Checking this page…";
  professorCard.hidden = true;
  emptyCard.hidden = true;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const isProfessorPage = /^https:\/\/(www\.)?ratemyprofessors\.com\/professor\//.test(
    tab?.url || ""
  );
  if (!tab?.id || !isProfessorPage) {
    showEmpty("Open an RMP professor page");
    return;
  }

  try {
    const context = await chrome.tabs.sendMessage(tab.id, {
      type: "GET_PAGE_CONTEXT"
    });
    showContext(context);
  } catch {
    showEmpty("Reload the RMP page, then try again");
  }
}

refreshButton.addEventListener("click", detectPage);
detectPage();
