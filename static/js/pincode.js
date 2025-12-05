// static/js/pincode.js
document.addEventListener("DOMContentLoaded", function () {
    const pincodeField = document.getElementById("pincode");
    const cityField = document.getElementById("city");
    const districtField = document.getElementById("district");
    const stateField = document.getElementById("state");

    // Safety: if we are on some other page without these fields, just exit.
    if (!pincodeField || !cityField || !districtField || !stateField) {
        return;
    }

    async function fetchPincodeDetails(pin) {
        try {
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

            if (!officeList.length) {
                districtField.value = "";
                stateField.value = "";
                cityField.innerHTML = "<option value=''>Select City/Area</option>";
                return;
            }

            // Autofill district and state from first entry
            districtField.value = officeList[0].District || "";
            stateField.value = officeList[0].State || "";

            // Populate city/area dropdown
            cityField.innerHTML = "<option value=''>Select City/Area</option>";

            officeList.forEach(po => {
                const label = po.Block || po.Name || po.District || "";
                if (!label) return;

                const opt = document.createElement("option");
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
        if (pin.length === 6 && /^\d{6}$/.test(pin)) {
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
