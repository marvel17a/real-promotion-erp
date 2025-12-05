// static/js/pincode.js
document.addEventListener("DOMContentLoaded", function () {

    const pincodeField = document.getElementById("pincode");
    const cityField = document.getElementById("city");
    const districtField = document.getElementById("district");
    const stateField = document.getElementById("state");

    // If fields do not exist (other pages), stop script
    if (!pincodeField || !cityField || !districtField || !stateField) {
        console.warn("Pincode script loaded, but form fields not found.");
        return;
    }

    async function fetchPincodeDetails(pin) {
        try {
            const res = await fetch(https://api.postalpincode.in/pincode/${pin});
            const data = await res.json();

            if (!data || !data[0] || data[0].Status !== "Success") {
                console.warn("Invalid pincode");
                districtField.value = "";
                stateField.value = "";
                cityField.innerHTML = "<option value=''>Select City/Area</option>";
                return;
            }

            const offices = data[0].PostOffice || [];

            // DISTRICT & STATE autofill
            districtField.value = offices[0].District || "";
            stateField.value = offices[0].State || "";

            // City/Area dropdown
            cityField.innerHTML = "<option value=''>Select City/Area</option>";
            offices.forEach(po => {
                const name = po.Block || po.Name || po.BranchType || po.District;
                if (!name) return;

                let opt = document.createElement("option");
                opt.value = name;
                opt.textContent = name;
                cityField.appendChild(opt);
            });

        } catch (err) {
            console.error("Pincode fetch failed:", err);
            districtField.value = "";
            stateField.value = "";
            cityField.innerHTML = "<option value=''>Select City/Area</option>";
        }
    }

    function handleInput() {
        const pin = pincodeField.value.trim();
        if (/^\d{6}$/.test(pin)) {
            fetchPincodeDetails(pin);
        } else {
            districtField.value = "";
            stateField.value = "";
            cityField.innerHTML = "<option value=''>Select City/Area</option>";
        }
    }

    pincodeField.addEventListener("keyup", handleInput);
    pincodeField.addEventListener("change", handleInput);
});
