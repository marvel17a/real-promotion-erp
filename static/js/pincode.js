// static/js/pincode.js
document.addEventListener("DOMContentLoaded", function () {

    const pincodeField = document.getElementById("pincode");
    const cityField = document.getElementById("city");
    const districtField = document.getElementById("district");
    const stateField = document.getElementById("state");

    if (!pincodeField || !cityField || !districtField || !stateField) {
        console.warn("Pincode fields not found on this page.");
        return;
    }

    async function fetchPincodeDetails(pin) {
        try {
            // ----------------------------------------
            // THE FIX → BACKTICKS ARE REQUIRED HERE
            // ----------------------------------------
            const res = await fetch(https://api.postalpincode.in/pincode/${pin});
            const data = await res.json();

            if (!data || !data[0] || data[0].Status !== "Success") {
                console.warn("Invalid or unknown pincode");
                districtField.value = "";
                stateField.value = "";
                cityField.innerHTML = "<option value=''>Select City/Area</option>";
                return;
            }

            const officeList = data[0].PostOffice || [];

            districtField.value = officeList[0].District || "";
            stateField.value = officeList[0].State || "";

            cityField.innerHTML = "<option value=''>Select City/Area</option>";

            officeList.forEach(po => {
                const label = po.Block || po.Name || po.BranchType || po.District || "";
                if (!label) return;

                let opt = document.createElement("option");
                opt.value = label;
                opt.textContent = label;
                cityField.appendChild(opt);
            });

        } catch (err) {
            console.error("Network/API error:", err);
            districtField.value = "";
            stateField.value = "";
            cityField.innerHTML = "<option value=''>Select City/Area</option>";
        }
    }

    function handlePincodeInput() {
        const pin = pincodeField.value.trim();
        if (/^\d{6}$/.test(pin)) {
            fetchPincodeDetails(pin);
        } else {
            districtField.value = "";
            stateField.value = "";
            cityField.innerHTML = "<option value=''>Select City/Area</option>";
        }
    }

    pincodeField.addEventListener("keyup", handlePincodeInput);
    pincodeField.addEventListener("change", handlePincodeInput);
});
