const COURSE_CODE_PATTERN = /\b[A-Z]{2,5}\s?-?\d{2,4}[A-Z]?\b/g;

function cleanText(value) {
  return (value || "").replace(/\s+/g, " ").trim();
}

function firstText(selectors) {
  for (const selector of selectors) {
    const value = cleanText(document.querySelector(selector)?.textContent);
    if (value) {
      return value;
    }
  }
  return "";
}

function professorName() {
  const heading = firstText([
    "main h1",
    "[class*='NameTitle__Name']",
    "[class*='TeacherInfo__Name']"
  ]);

  if (heading) {
    return heading.replace(/^Professor\s+/i, "");
  }

  return cleanText(document.title)
    .replace(/\s*at\s+.*$/i, "")
    .replace(/\s*-\s*Rate My Professors.*$/i, "");
}

function pageContext() {
  const bodyText = cleanText(document.body?.innerText);
  const courseCodes = [
    ...new Set((bodyText.match(COURSE_CODE_PATTERN) || []).map((code) =>
      code.replace(/[\s-]/g, "")
    ))
  ].slice(0, 12);

  return {
    kind: "rmp-professor",
    professorName: professorName(),
    professorId: location.pathname.match(/\/professor\/(\d+)/)?.[1] || "",
    pageTitle: document.title,
    url: location.href,
    courseCodes,
    pageText: bodyText.slice(0, 15000)
  };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "GET_PAGE_CONTEXT") {
    sendResponse(pageContext());
  }
});
