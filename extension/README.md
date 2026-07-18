# OneStopProf Chrome Extension

This is the first Manifest V3 extension prototype. It detects when the active
tab is a Rate My Professors professor profile and extracts:

- Professor name
- RMP professor ID
- Course codes visible on the page
- A bounded text snapshot for a future summary API

No page data leaves the browser in this version. The popup does not call Groq
or the Python application yet.

## Install Locally

1. Open `chrome://extensions` in Google Chrome.
2. Turn on **Developer mode** in the upper-right corner.
3. Select **Load unpacked**.
4. Choose this repository's `extension/` directory.
5. Pin OneStopProf from Chrome's Extensions menu.
6. Open a professor page on
   [Rate My Professors](https://www.ratemyprofessors.com/), reload the page
   once after installing, and click the OneStopProf toolbar icon.

After editing an extension file, return to `chrome://extensions`, click the
reload button on the OneStopProf card, and refresh the page being tested.

## Files

- `manifest.json` — extension metadata and RMP page matching
- `content.js` — extracts professor context from the current RMP page
- `popup.html` — toolbar popup structure
- `popup.css` — RMP-inspired popup styling
- `popup.js` — requests and displays page context

## Next Step

Add an HTTPS backend API that accepts the extracted context, fetches reviews
when necessary, and returns a cited summary. Keep the Groq API key on that
backend; never place it in extension JavaScript.
