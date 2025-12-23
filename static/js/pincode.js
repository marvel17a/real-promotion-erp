document.addEventListener("DOMContentLoaded", function () {

    const pincodeField = document.getElementById("pincode");
    const cityField = document.getElementById("city");
    const districtField = document.getElementById("district");
    const stateField = document.getElementById("state");

    // Guard clause: if elements don't exist, stop running
    if (!pincodeField || !cityField || !districtField || !stateField) {
        return;
    }

    // 1. Store the initial city value (from database) for Edit Page
    // If it's an input field (Edit Page sometimes uses input for city), use value
    // If it's a select field, we might need a custom attribute or just grab the value
    const initialCityValue = cityField.getAttribute("data-selected-city") || cityField.value;

    async function fetchPincodeDetails(pin, preserveCity = false) {
        try {
            // Show loading state (Only if we are not preserving a pre-filled value visibly)
            if (!preserveCity) {
                cityField.innerHTML = "<option>Loading...</option>";
                districtField.placeholder = "Fetching...";
                stateField.placeholder = "Fetching...";
            }

            const res = await fetch(`https://api.postalpincode.in/pincode/${pin}`);
            const data = await res.json();

            if (!data || !data[0] || data[0].Status !== "Success") {
                if(!preserveCity) alert("Invalid Pincode or API Error");
                return;
            }

            const officeList = data[0].PostOffice || [];

            // Auto-fill District and State
            if (officeList.length > 0) {
                districtField.value = officeList[0].District;
                stateField.value = officeList[0].State;
            }

            // Populate City/Area Dropdown
            // Note: In Edit Page, 'cityField' might be an <input> (read-only) or <select>
            // Your Add Page uses <select>, Your Edit Page uses <input readonly> in your old code.
            // But my UPDATED Edit Page (provided previously) uses <input readonly> for city.
            
            // IF cityField is a SELECT (Dropdown) - Used in Add Page or if you want Dropdown in Edit
            if (cityField.tagName === "SELECT") {
                cityField.innerHTML = "<option value=''>Select City/Area</option>";
                let found = false;
                
                officeList.forEach(po => {
                    const cityName = po.Name; 
                    let opt = document.createElement("option");
                    opt.value = cityName;
                    opt.textContent = cityName;
                    
                    // Pre-select if matches database value
                    if (preserveCity && initialCityValue && cityName.toLowerCase() === initialCityValue.toLowerCase()) {
                        opt.selected = true;
                        found = true;
                    }
                    cityField.appendChild(opt);
                });

                // If the specific city from DB isn't in the API list (rare edge case), add it manually
                if (preserveCity && initialCityValue && !found) {
                     let opt = document.createElement("option");
                     opt.value = initialCityValue;
                     opt.textContent = initialCityValue;
                     opt.selected = true;
                     cityField.appendChild(opt);
                }
            } 
            // IF cityField is INPUT (Read-only) - Used in your old Edit Page logic
            else if (cityField.tagName === "INPUT") {
                // If it's an input, we usually just leave it alone on Edit Page 
                // unless user changes pincode.
                if (!preserveCity) {
                    // If user manually changed pincode, clear city or set to first available
                     if (officeList.length > 0) {
                        cityField.value = officeList[0].Name; // Default to first
                     }
                }
            }

        } catch (err) {
            console.error("API Fetch Error:", err);
        }
    }

    function resetFields() {
        districtField.value = "";
        stateField.value = "";
        if (cityField.tagName === "SELECT") {
            cityField.innerHTML = "<option value=''>Select City/Area</option>";
        } else {
            cityField.value = "";
        }
    }

    function handlePincodeInput() {
        const pin = pincodeField.value.trim();
        if (/^\d{6}$/.test(pin)) {
            // When typing manually, we do NOT preserve old city
            fetchPincodeDetails(pin, false);
        } else {
            if(districtField.value !== "") resetFields();
        }
    }

    // Event Listeners
    pincodeField.addEventListener("keyup", handlePincodeInput);
    pincodeField.addEventListener("change", handlePincodeInput);

    // --- ON PAGE LOAD (For Edit Page) ---
    const initialPin = pincodeField.value.trim();
    if (initialPin && /^\d{6}$/.test(initialPin)) {
        // Fetch details but try to preserve the currently selected city
        fetchPincodeDetails(initialPin, true);
    }
});
