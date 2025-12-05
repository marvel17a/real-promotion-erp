document.addEventListener("DOMContentLoaded", function () {
    const pincodeField = document.getElementById("pincode");
    const cityField = document.getElementById("city_area");
    const districtField = document.getElementById("district");
    const stateField = document.getElementById("state");

    async function fetchPincodeDetails(pin) {
        try {
            const res = await fetch(https://api.postalpincode.in/pincode/${pin});
            const data = await res.json();

            if (!data || !data[0] || data[0].Status !== "Success") {
                console.warn("Invalid or unknown pincode");
                districtField.value = "";
                stateField.value = "";
                cityField.innerHTML = "";
                return;
            }

            let officeList = data[0].PostOffice || [];

            // Autofill district and state
            districtField.value = officeList[0].District || "";
            stateField.value = officeList[0].State || "";

            // Populate city/area dropdown
            cityField.innerHTML = "";
            officeList.forEach(po => {
                let opt = document.createElement("option");
                opt.value = po.Name;
                opt.textContent = po.Name;
                cityField.appendChild(opt);
            });
        } catch (err) {
            console.error("Network/API error:", err);
        }
    }

    function handlePincodeInput() {
        let pin = pincodeField.value.trim();
        if (pin.length === 6 && /^[0-9]+$/.test(pin)) {
            fetchPincodeDetails(pin);
        } else {
            districtField.value = "";
            stateField.value = "";
            cityField.innerHTML = "";
        }
    }

    pincodeField.addEventListener("keyup", handlePincodeInput);
    pincodeField.addEventListener("change", handlePincodeInput);
});
