document.addEventListener("DOMContentLoaded", function () {

    const pincodeField = document.getElementById("pincode");
    const cityField = document.getElementById("city");
    const districtField = document.getElementById("district");
    const stateField = document.getElementById("state");

    // Guard clause: if elements don't exist, stop running
    if (!pincodeField || !cityField || !districtField || !stateField) {
        return;
    }

    async function fetchPincodeDetails(pin) {
        try {
            // Show loading state
            cityField.innerHTML = "<option>Loading...</option>";
            districtField.placeholder = "Fetching...";
            stateField.placeholder = "Fetching...";

            // FIXED: Added backticks around the URL for string interpolation
            const res = await fetch(`https://api.postalpincode.in/pincode/${pin}`);
            const data = await res.json();

            if (!data || !data[0] || data[0].Status !== "Success") {
                alert("Invalid Pincode or API Error");
                resetFields();
                return;
            }

            const officeList = data[0].PostOffice || [];

            // Auto-fill District and State from the first result
            if (officeList.length > 0) {
                districtField.value = officeList[0].District;
                stateField.value = officeList[0].State;
            }

            // Populate City/Area Dropdown
            cityField.innerHTML = "<option value=''>Select City/Area</option>";
            officeList.forEach(po => {
                const cityName = po.Name; 
                let opt = document.createElement("option");
                opt.value = cityName;
                opt.textContent = cityName;
                cityField.appendChild(opt);
            });

        } catch (err) {
            console.error("API Fetch Error:", err);
            resetFields();
        }
    }

    function resetFields() {
        districtField.value = "";
        stateField.value = "";
        districtField.placeholder = "";
        stateField.placeholder = "";
        cityField.innerHTML = "<option value=''>Select City/Area</option>";
    }

    function handlePincodeInput() {
        const pin = pincodeField.value.trim();
        if (/^\d{6}$/.test(pin)) {
            fetchPincodeDetails(pin);
        } else {
            // Only reset if the user had previously entered valid data
            if(districtField.value !== "") resetFields();
        }
    }

    pincodeField.addEventListener("keyup", handlePincodeInput);
    // Also trigger on change (e.g. paste)
    pincodeField.addEventListener("change", handlePincodeInput);
});
