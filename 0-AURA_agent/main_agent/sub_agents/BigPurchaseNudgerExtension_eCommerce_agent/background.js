let userId;
chrome.storage.local.get(['userId'], (result) => {
  if (result.userId) {
    userId = result.userId;
  } else {
    userId = crypto.randomUUID(); 
    chrome.storage.local.set({ userId: userId });
  }
  console.log("Extension User ID:", userId);
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "sendToADK") {
    const productData = request.data;
    const payload = {
      user_id: userId,
      ...productData 
    };


    const webhookUrl = "";

    fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.text(); 
    })
    .then(data => {
      console.log('Successfully sent data to Cloud Function:', data);
      sendResponse({ status: "success", response: data });
    })
    .catch(error => {
      console.error('Error sending data to Cloud Function:', error);
      sendResponse({ status: "error", error: error.message });
    });

    return true; 
  }
});