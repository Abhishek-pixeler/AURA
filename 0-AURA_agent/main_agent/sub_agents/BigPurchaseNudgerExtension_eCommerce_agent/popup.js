document.getElementById('sendDataButton').addEventListener('click', () => {
  document.getElementById('status').textContent = "Sending...";
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, { action: "extractAndSend" }, (response) => {
        const statusElement = document.getElementById('status');
        if (response && response.status === "success") {
          statusElement.textContent = "Data sent successfully!";
        } else {
          statusElement.textContent = `Error: ${response ? response.error : "Unknown"}`;
          console.error("Error from content script:", response ? response.error : "No response");
        }
      });
    } else {
        document.getElementById('status').textContent = "No active tab found.";
    }
  });
});