let originalBuyNowButton = null;
let originalForm = null;        
let originalFormAction = '';   
let originalFormMethod = '';    
let originalFormInputs = {};    


document.addEventListener('click', function(event) {
    console.log("DEBUG: Document click event fired.");

    const clickedElement = event.target; 

   
    if (clickedElement.id === 'buy-now-button' ||
        clickedElement.matches('input[name="submit.buy-now"]') ||
        clickedElement.matches('.a-button-text.a-declarative[name="submit.buy-now"]') ||
        
        clickedElement.closest('#buy-now-button, input[name="submit.buy-now"], .a-button-text.a-declarative[name="submit.buy-now"]')
    ) {
        console.log("DEBUG: 'Buy Now' button click DETECTED!");

        
        originalBuyNowButton = clickedElement.closest('#buy-now-button, input[name="submit.buy-now"], .a-button-text.a-declarative[name="submit.buy-now"]');

        const parentForm = originalBuyNowButton ? originalBuyNowButton.closest('form') : null;

        if (parentForm) {
            originalForm = parentForm;
            originalFormAction = parentForm.action;
            originalFormMethod = parentForm.method || 'GET'; 

            
            originalFormInputs = {};
            Array.from(parentForm.elements).forEach(element => {
                
                if (element.name && !element.disabled) {
                    
                    if ((element.type === 'radio' || element.type === 'checkbox') && !element.checked) {
                        return; 
                    }
                    originalFormInputs[element.name] = element.value;
                }
            });
            
            if (originalBuyNowButton.name && originalBuyNowButton.value) {
                originalFormInputs[originalBuyNowButton.name] = originalBuyNowButton.value;
            }

            console.log("DEBUG: Captured form action:", originalFormAction);
            console.log("DEBUG: Captured form method:", originalFormMethod);
            console.log("DEBUG: Captured form inputs:", originalFormInputs);

        } else {
            console.warn("WARNING: 'Buy Now' button is not within a form. May not be able to resume action reliably via form submission.");
            originalForm = null;
            originalFormAction = '';
            originalFormMethod = '';
            originalFormInputs = {};
        }

        const productData = extractProductData(); 
        if (productData) {
            console.log("DEBUG: Product data extracted:", productData);

            const isHighValue = productData.isHighValue;
            console.log("DEBUG: isHighValue flag from productData:", isHighValue);

            
            chrome.runtime.sendMessage({ action: "sendProductData", data: productData }, (response) => {
                if (response && response.status === "success") {
                    console.log("DEBUG: Data sent successfully to Cloud Function (from content.js)!");
                } else {
                    console.error("ERROR: Failed to send data to Cloud Function (from content.js):", response ? response.error : 'No response');
                }
            });

            
            if (isHighValue) {
                console.log("DEBUG: High-value item detected. Calling showInPageNotification and preventing default action.");
                event.preventDefault();
                event.stopImmediatePropagation();
                showInPageNotification(productData.name, productData.price);
                return; 
            } else {
                console.log("DEBUG: Normal value item detected. No in-page notification shown. Let click proceed.");
                
            }
        } else {
            console.warn("WARNING: Could not extract product data on 'Buy Now' click. ProductData is null. Letting click proceed.");
            
        }
    } else {
        
    }
}, true); 


function attachBuyNowListener() {
    const buyNowButton = document.querySelector('#buy-now-button'); 

    if (buyNowButton) {
        console.log("DEBUG: 'Buy Now' button element found by polling.");
        return true;
    }
    return false;
}


let attempts = 0;
const maxAttempts = 40;
const intervalId = setInterval(() => {
    if (attachBuyNowListener() || attempts >= maxAttempts) {
        clearInterval(intervalId);
        if (attempts >= maxAttempts) {
            console.error("ERROR: Max attempts reached, 'Buy Now' button not found by polling. Auto-trigger failed.");
        }
    }
    attempts++;
}, 500);

function extractProductData() {
    console.log("DEBUG: extractProductData() called.");
    const url = window.location.href;
    let urlPathname = '';
    try {
        const urlObject = new URL(url);
        urlPathname = urlObject.pathname;
    } catch (e) {
        console.error("ERROR: Error parsing URL in extractProductData:", e);
        urlPathname = url;
    }

    let productName = null;
    let productPriceString = null;
    let imageUrl = null;
    let isHighValue = false;
    let priceValue = NaN;

    if (urlPathname.includes("/dp/") || urlPathname.includes("/gp/product/")) {
        console.log("DEBUG: URL matches Amazon product page pattern.");
        const productNameElementAttempt1 = document.getElementById('productTitle');
        const productNameElementAttempt2 = document.getElementById('title');

        if (productNameElementAttempt1) {
            productName = productNameElementAttempt1.textContent.trim();
            console.log("DEBUG: Product name found via productTitle.");
        } else if (productNameElementAttempt2) {
            productName = productNameElementAttempt2.textContent.trim();
            console.log("DEBUG: Product name found via title.");
        } else {
            console.warn("WARNING: Product name element not found.");
        }

        const priceElementAttempt1 = document.querySelector('.a-price-whole');
        const priceElementAttempt2 = document.querySelector('.a-price .a-offscreen');

        if (priceElementAttempt1) {
            productPriceString = priceElementAttempt1.textContent.replace(/[^0-9.]/g, '');
            console.log("DEBUG: Price string found via .a-price-whole:", productPriceString);
        } else if (priceElementAttempt2) {
            productPriceString = priceElementAttempt2.textContent.replace(/[^0-9.]/g, '');
            console.log("DEBUG: Price string found via .a-price .a-offscreen:", productPriceString);
        } else {
            console.warn("WARNING: Product price element not found. productPriceString will be null.");
        }

        if (productPriceString) {
            priceValue = parseFloat(productPriceString);
            if (!isNaN(priceValue)) {
                console.log("DEBUG: Parsed price value:", priceValue);
                if (priceValue >= 20000) { 
                    isHighValue = true;
                    console.log("DEBUG: Price meets high-value threshold (>= 20000).");
                } else {
                    console.log("DEBUG: Price does NOT meet high-value threshold.");
                }
            } else {
                console.error("ERROR: Failed to parse productPriceString ('" + productPriceString + "') into a number.");
            }
        }

        const imageElement = document.getElementById('landingImage');
        if (imageElement) {
            imageUrl = imageElement.src;
            console.log("DEBUG: Image URL found.");
        } else {
            console.warn("WARNING: Image element not found.");
        }

    } else {
        console.log("DEBUG: URL does not match Amazon product page pattern for data extraction.");
    }

    let userId = localStorage.getItem('user_id');
    if (!userId) {
        userId = crypto.randomUUID();
        localStorage.setItem('user_id', userId);
        console.log("DEBUG: New user_id generated and stored:", userId);
    } else {
        console.log("DEBUG: Existing user_id retrieved:", userId);
    }

    if (productName && !isNaN(priceValue)) {
        console.log("DEBUG: All essential data (name, valid price) extracted successfully.");
        return {
            user_id: userId,
            source: "browser_extension",
            url: url,
            name: productName,
            price: priceValue,
            imageUrl: imageUrl,
            timestamp: new Date().toISOString(),
            eventType: isHighValue ? "product_buy_now_clicked_high_value" : "product_buy_now_clicked_normal",
            user_consent: true,
            isHighValue: isHighValue
        };
    }

    console.warn("WARNING: Essential data (product name or valid price) not found. Returning null from extractProductData.");
    return null;
}


function showInPageNotification(productName, productPrice) {
    console.log("DEBUG: showInPageNotification() called.");
    const existingNotification = document.getElementById('extension-notification-popup');
    if (existingNotification) {
        existingNotification.remove();
        console.log("DEBUG: Removed existing pop-up.");
    }

    const popup = document.createElement('div');
    popup.id = 'extension-notification-popup';
    popup.innerHTML = `
        <style>
            #extension-notification-popup {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                z-index: 10000;
                background-color: white;
                border: 2px solid #ccc;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                padding: 20px;
                border-radius: 8px;
                font-family: Arial, sans-serif;
                color: #333;
                text-align: center;
                max-width: 400px;
            }
            .extension-notification-content h3 {
                color: #d32f2f;
                margin-top: 0;
            }
            .extension-notification-content p {
                margin-bottom: 10px;
                line-height: 1.5;
            }
            .extension-notification-content strong {
                color: #e65100;
            }
            #extension-notification-ok-button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin-top: 15px;
            }
            #extension-notification-ok-button:hover {
                background-color: #45a049;
            }
        </style>
        <div class="extension-notification-content">
            <h3>High-Value Purchase Alert!</h3>
            <p>You're about to buy a high-value item:</p>
            <p><strong>Do you really need this? Please Rethink as this doesn't fit your money goals this month</strong></p>
            <p>Price: ₹${productPrice ? productPrice.toLocaleString('en-IN') : 'N/A'}</p>
            <button id="extension-notification-ok-button">OK</button>
        </div>
    `;

    document.body.appendChild(popup);
    console.log("DEBUG: Pop-up element appended to body.");

    document.getElementById('extension-notification-ok-button').addEventListener('click', function() {
        popup.remove();
        console.log("DEBUG: Pop-up dismissed by 'OK' button.");

        
        if (originalForm && originalFormAction) {
            console.log("DEBUG: Resuming action via temporary form submission.");

            
            const tempForm = document.createElement('form');
            tempForm.method = originalFormMethod;
            tempForm.action = originalFormAction;
            tempForm.style.display = 'none'; 

            for (const name in originalFormInputs) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = name;
                input.value = originalFormInputs[name];
                tempForm.appendChild(input);
            }

            document.body.appendChild(tempForm);
            console.log("DEBUG: Temporary form created and appended. Submitting...");
            tempForm.submit();             

        } else if (originalBuyNowButton) {
             
             console.warn("WARNING: No original form context captured. Falling back to direct button click.");
             originalBuyNowButton.click();
        } else {
            console.error("ERROR: No original button or form context found to resume action.");
        }

        originalBuyNowButton = null;
        originalForm = null;
        originalFormAction = '';
        originalFormMethod = '';
        originalFormInputs = {};
    });
    console.log("DEBUG: 'OK' button listener attached.");
}


chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "extractAndSend") {
        console.log("DEBUG: Received 'extractAndSend' message from popup.");
        const productData = extractProductData();
        if (productData) {
            chrome.runtime.sendMessage({ action: "sendProductData", data: productData }, (response) => {
                if (response && response.status === "success") {
                    console.log("DEBUG: Manual send successful.");
                    sendResponse({ status: "success", message: "Manual extraction and send initiated." });
                } else {
                    console.error("DEBUG: Manual send failed.");
                    sendResponse({ status: "error", error: "Manual extraction failed." });
                }
            });
            return true;
        } else {
            console.warn("DEBUG: No product data extracted for manual send.");
            sendResponse({ status: "error", error: "No product data extracted." });
        }
    }
});